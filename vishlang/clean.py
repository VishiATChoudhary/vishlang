"""Turn parsed paragraphs into a filtered corpus of training-ready chunks."""
import json
import random
import re
from pathlib import Path

from .detect import ai_score
from .ingest import Para

_DE = {"und", "der", "die", "das", "ich", "nicht", "ist", "auch", "mit", "ein", "eine", "wir", "du", "dass", "aber"}
_EN = {"the", "and", "is", "to", "of", "that", "you", "with", "for", "this", "not", "are", "but", "have"}
_WORD = re.compile(r"[\wÄÖÜäöüß']+")


def chunk(text: str, max_words: int = 150) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out, cur, n = [], [], 0
    for p in paras:
        w = len(p.split())
        if cur and n + w > max_words:
            out.append("\n\n".join(cur))
            cur, n = [], 0
        cur.append(p)
        n += w
    if cur:
        out.append("\n\n".join(cur))
    return out


def detect_lang(text: str) -> str:
    toks = [t.lower() for t in _WORD.findall(text)]
    de = sum(t in _DE for t in toks)
    en = sum(t in _EN for t in toks)
    return "de" if de > en else "en"


def normalize(text: str) -> str:
    return re.sub(r"[^\w]+", " ", text.lower()).strip()


def _url_heavy(text: str) -> bool:
    toks = text.split()
    urls = sum(("http" in t or "www." in t) for t in toks)
    return bool(toks) and urls / len(toks) > 0.3


def clean(paras: list[Para], cfg: dict) -> tuple[list[dict], dict]:
    """Return (records, stats). Records: {text, source, lang, ai_score, date}."""
    c = cfg["clean"]
    stats = {"min_words": 0, "url_heavy": 0, "dupe": 0, "ai_score": 0}
    seen: set[str] = set()
    out: list[dict] = []
    for para in paras:
        for text in chunk(para.text):
            if len(text.split()) < c["min_words"]:
                stats["min_words"] += 1
                continue
            if _url_heavy(text):
                stats["url_heavy"] += 1
                continue
            key = normalize(text)
            if key in seen:
                stats["dupe"] += 1
                continue
            seen.add(key)
            score = ai_score(text)
            if score >= c["ai_threshold"]:
                stats["ai_score"] += 1
                continue
            out.append({"text": text, "source": para.source, "lang": detect_lang(text),
                        "ai_score": score, "date": para.date})
    return out, stats


def split_holdout(records: list[dict], frac: float, seed: int = 0) -> tuple[list[dict], list[dict]]:
    rows = list(records)
    random.Random(seed).shuffle(rows)
    k = round(len(rows) * frac)
    return (rows[:-k], rows[-k:]) if k else (rows, [])


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
