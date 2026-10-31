"""Load vishlang.toml with defaults filled in."""
import copy
import tomllib
from pathlib import Path

_SOURCE = {"weight": 1.0, "before": ""}

DEFAULTS = {
    "author": {"names": [], "emails": []},
    "model": {"base": "mlx-community/Qwen3-4B-Instruct-2507-4bit"},
    "clean": {"min_words": 8, "ai_threshold": 0.5, "merge_minutes": 2, "holdout": 0.1},
    "sources": {
        "whatsapp": dict(_SOURCE),
        "gmail": dict(_SOURCE),
        "docs": dict(_SOURCE),
        "linkedin": dict(_SOURCE),
        "chatgpt": {"weight": 0.0, "before": ""},
        "claude": {"weight": 1.0, "before": "", "path": "~/.claude/projects"},
    },
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: Path | str = "vishlang.toml") -> dict:
    p = Path(path)
    data = tomllib.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _merge(DEFAULTS, data)
