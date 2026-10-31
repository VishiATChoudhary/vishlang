"""Build (neutral -> original) training pairs by back-translation with the base model.

Each corpus paragraph is rewritten into generic assistant register; the model is then
trained on the reverse direction. Inverse-transfer data augmentation (Shao et al. 2024).
"""
import hashlib
import json
import random
from pathlib import Path

from .clean import read_jsonl, write_jsonl  # noqa: F401  (read_jsonl kept for callers)
from .clean import normalize
from .prompts import NEUTRALISE_SYSTEM, REWRITE_SYSTEM, neutralise_user


def neutral_budget(text: str) -> int:
    """German runs 2 to 2.5 tokens per word and the neutral register is wordier."""
    return 4 * len(text.split()) + 128


def neutralise(lm, text: str) -> str:
    return lm.chat(NEUTRALISE_SYSTEM, neutralise_user(text), max_tokens=neutral_budget(text), temp=0.7)


_TERMINAL = tuple(".!?\"'\u201d)")
RATIO_MIN, RATIO_MAX = 0.5, 2.5


def usable_pair(neutral: str, original: str) -> bool:
    """Reject neutrals that were cut off or ran away; both would teach fact invention."""
    if not neutral or normalize(neutral) == normalize(original):
        return False  # identity pairs teach nothing
    if not neutral.rstrip().endswith(_TERMINAL):
        return False
    ratio = len(neutral.split()) / max(1, len(original.split()))
    return RATIO_MIN <= ratio <= RATIO_MAX


def _load_cache(path: Path) -> dict:
    cache = {}
    if not path.exists():
        return cache
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
                cache[r["h"]] = r["neutral"]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue  # a kill mid-write leaves one partial line; that item is redone
    return cache


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
    cache = _load_cache(cache_path)

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
        if not usable_pair(neutral or "", r["text"]):
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
