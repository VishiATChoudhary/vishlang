"""Build (neutral -> original) training pairs by back-translation with the base model.

Each corpus paragraph is rewritten into generic assistant register; the model is then
trained on the reverse direction. Inverse-transfer data augmentation (Shao et al. 2024).
"""
import hashlib
import json
import random
from pathlib import Path

from .clean import read_jsonl, write_jsonl
from .prompts import NEUTRALISE_SYSTEM, REWRITE_SYSTEM


def neutralise(lm, text: str) -> str:
    return lm.chat(NEUTRALISE_SYSTEM, text, max_tokens=max(64, int(len(text.split()) * 3)), temp=0.3)


def make_example(neutral: str, original: str) -> dict:
    return {"messages": [{"role": "system", "content": REWRITE_SYSTEM},
                         {"role": "user", "content": neutral},
                         {"role": "assistant", "content": original}]}


def _h(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def build_pairs(corpus: Path, out_dir: Path, lm, cfg: dict, valid_frac: float = 0.05,
                limit: int | None = None, log=print) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(corpus)
    cache_path = out_dir / "neutral.jsonl"
    cache = {r["h"]: r["neutral"] for r in read_jsonl(cache_path)}

    todo = [r for r in rows if _h(r["text"]) not in cache]
    if limit is not None:
        todo = todo[:limit]
    with cache_path.open("a", encoding="utf-8") as fh:
        for i, r in enumerate(todo, 1):
            neutral = neutralise(lm, r["text"])
            cache[_h(r["text"])] = neutral
            fh.write(json.dumps({"h": _h(r["text"]), "neutral": neutral}, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 50 == 0 or i == len(todo):
                log(f"neutralised {i}/{len(todo)}")

    usable = []
    for r in rows:
        neutral = cache.get(_h(r["text"]))
        if not neutral or neutral.strip() == r["text"].strip():
            continue
        usable.append((r, make_example(neutral, r["text"])))

    random.Random(0).shuffle(usable)
    k = max(1, round(len(usable) * valid_frac)) if usable else 0
    valid, test, train = usable[:k], usable[k:2 * k], usable[2 * k:]

    train_rows = []
    for r, ex in train:
        weight = float(cfg["sources"].get(r["source"], {}).get("weight", 1.0))
        train_rows.extend([ex] * max(1, round(weight)))
    write_jsonl(out_dir / "train.jsonl", train_rows)
    write_jsonl(out_dir / "valid.jsonl", [ex for _, ex in valid])
    write_jsonl(out_dir / "test.jsonl", [ex for _, ex in test])
    return {"train": len(train_rows), "valid": len(valid), "test": len(test),
            "skipped": len(rows) - len(usable), "neutralised_now": len(todo)}
