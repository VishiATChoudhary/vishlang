"""Blind A/B: neutral (LLM register) vs rewrite(neutral). Vishi picks which sounds like him."""
import math
import random
import statistics
from typing import Callable

from .detect import ai_score
from .pairs import neutralise
from .serve import rewrite_text

PASS_FRACTION = 0.75


def run_blind(lm, holdout: list[dict], system: str, n: int = 20, ask: Callable[[str], str] = input,
              rng_seed: int = 0) -> dict:
    rng = random.Random(rng_seed)
    items = rng.sample(holdout, min(n, len(holdout)))
    hits, ai_n, ai_r, ratios = 0, [], [], []
    for i, row in enumerate(items, 1):
        neutral = neutralise(lm, row["text"])
        rw = rewrite_text(lm, neutral, system)
        ai_n.append(ai_score(neutral))
        ai_r.append(ai_score(rw))
        ratios.append(len(rw.split()) / max(1, len(neutral.split())))
        rw_first = rng.random() < 0.5
        a, b = (rw, neutral) if rw_first else (neutral, rw)
        prompt = f"\n[{i}/{len(items)}]\n1) {a}\n\n2) {b}\n\nWhich sounds more like you? [1/2] "
        answer = ""
        while answer not in ("1", "2"):
            answer = ask(prompt).strip()
        if (answer == "1") == rw_first:
            hits += 1
    need = math.ceil(PASS_FRACTION * len(items)) if items else 0
    ai_neutral = statistics.mean(ai_n) if ai_n else 0.0
    ai_rewrite = statistics.mean(ai_r) if ai_r else 0.0
    return {
        "hits": hits, "n": len(items), "need": need,
        "ai_neutral": round(ai_neutral, 3), "ai_rewrite": round(ai_rewrite, 3),
        "len_ratio": round(statistics.mean(ratios), 2) if ratios else 0.0,
        "passed": bool(items) and hits >= need and ai_rewrite <= ai_neutral,
    }


def report(r: dict, mode: str) -> str:
    return "\n".join([
        f"blind test  mode={mode}  n={r['n']}",
        f"hits        {r['hits']}/{r['n']}   (need {r['need']})",
        f"ai score    neutral {r['ai_neutral']}  rewrite {r['ai_rewrite']}",
        f"len ratio   {r['len_ratio']}",
        "PASS" if r["passed"] else "FAIL",
    ])
