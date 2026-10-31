"""Heuristic AI-writing detector. No model, four cheap signals averaged.

Lexicon: Kobak et al., "Delving into LLM-assisted writing in biomedical publications
through excess vocabulary", Science Advances 2025. Focal set and the open-class filter
follow the strip-ai-tells reference scorer.
"""
import csv
import re
import statistics as st
from importlib import resources

FOCAL = {"delve", "delves", "delved", "delving", "intricate", "commendable", "meticulous",
         "meticulously", "surpass", "surpasses", "elevate", "elevates", "foster", "fostering",
         "tapestry", "realm", "realms", "navigate", "navigating", "landscape", "pivotal",
         "resonate", "resonates", "testament", "underscore", "underscores", "underscoring",
         "showcase", "showcases", "showcasing", "compelling", "paramount", "crucial",
         "unwavering", "alignment"}

_OPEN_CLASS = {"verb", "adjective", "noun", "adverb", "advebr", "nount", "noun/verb"}
_STOP = {"were", "based", "using", "need", "hold", "holds", "this", "these", "their", "both",
         "like", "within", "however", "across", "between", "during", "including", "into",
         "through", "while", "despite", "amid", "amidst", "alongside", "midst", "analysis",
         "research", "role", "approach", "impact", "findings", "outcomes", "individuals",
         "conditions", "complex", "potential", "various", "primary", "distinct"}

_WORD = re.compile(r"[A-Za-zÄÖÜäöüß']+")
_SENT = re.compile(r"[.!?]+(?:\s+|$)")
_TRIAD = re.compile(r"\b\w+, \w+,? and \w+\b")


def _load_review() -> set[str]:
    with resources.files("vishlang.data").joinpath("excess_words.csv").open(encoding="utf-8", newline="") as fh:
        rows = csv.DictReader(fh)
        return {r["word"].lower() for r in rows
                if r["type"].startswith("style")
                and r["part_of_speech"].strip().lower() in _OPEN_CLASS
                and r["word"].lower() not in _STOP}


REVIEW = _load_review()


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def ai_score(text: str) -> float:
    """0.0 = reads human, 1.0 = reads like a polished assistant."""
    words = [w.lower() for w in _WORD.findall(text)]
    n = len(words)
    if n == 0:
        return 0.0
    per100 = 100.0 / n

    focal = sum(w in FOCAL for w in words)
    review = sum(w in REVIEW for w in words)
    lexicon = _clamp((focal * 3 + review) * per100 / 2.0)

    emdash = _clamp(text.count("—") * per100 / 1.5)

    sentences = [s for s in _SENT.split(text) if s.strip()]
    n_sent = max(1, len(sentences))
    triads = _clamp(len(_TRIAD.findall(text)) / n_sent / 0.5)

    lengths = [len(_WORD.findall(s)) for s in sentences]
    if len(lengths) >= 3 and st.mean(lengths) > 0:
        flatness = 1.0 - min(1.0, st.stdev(lengths) / st.mean(lengths))
    else:
        flatness = 0.0

    return round(0.4 * lexicon + 0.2 * emdash + 0.2 * triads + 0.2 * flatness, 4)
