import json

from vishlang.clean import read_jsonl, write_jsonl
from vishlang.config import load_config
from vishlang.llm import FakeLM
from vishlang.pairs import build_pairs, make_example, neutralise
from vishlang.prompts import NEUTRALISE_SYSTEM, REWRITE_SYSTEM
from tests.conftest import FIX

CFG = load_config(FIX / "cfg_all.toml")


def _corpus(path, n=40, source="gmail"):
    write_jsonl(path, [{"text": f"original {i} " * 3, "source": source, "lang": "en", "ai_score": 0.1, "date": ""} for i in range(n)])


def test_neutralise_uses_neutralise_prompt():
    lm = FakeLM(lambda s, u: "N " + u)
    assert neutralise(lm, "hey") == "N hey" and lm.calls[0][0] == NEUTRALISE_SYSTEM


def test_make_example_shape():
    ex = make_example("neutral", "orig")
    assert ex == {"messages": [{"role": "system", "content": REWRITE_SYSTEM},
                               {"role": "user", "content": "neutral"},
                               {"role": "assistant", "content": "orig"}]}


def test_build_pairs_writes_splits_and_resumes(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    _corpus(corpus)
    calls = []
    lm = FakeLM(lambda s, u: (calls.append(u), "neutral " + u)[1])
    out = build_pairs(corpus, tmp_path / "pairs", lm, CFG)
    assert out["train"] + out["valid"] + out["test"] == 40 and len(calls) == 40
    n_first = len(calls)
    build_pairs(corpus, tmp_path / "pairs", lm, CFG)  # resume: nothing new to neutralise
    assert len(calls) == n_first
    rows = read_jsonl(tmp_path / "pairs" / "train.jsonl")
    assert rows[0]["messages"][0] == {"role": "system", "content": REWRITE_SYSTEM}
    assert rows[0]["messages"][1]["content"].startswith("neutral ")
    assert len({json.dumps(r) for r in rows}) == len(rows)
    assert (tmp_path / "pairs" / "valid.jsonl").exists() and (tmp_path / "pairs" / "test.jsonl").exists()


def test_build_pairs_skips_empty_or_unchanged_neutral(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    _corpus(corpus, n=10)
    lm = FakeLM(lambda s, u: "" if "original 0 " in u else (u if "original 1 " in u else "n " + u))
    out = build_pairs(corpus, tmp_path / "pairs", lm, CFG)
    assert out["train"] + out["valid"] + out["test"] == 8


def test_weight_repeats_in_train_only(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    _corpus(corpus, n=40)
    cfg = load_config(FIX / "cfg_all.toml")
    cfg["sources"]["gmail"]["weight"] = 2.0
    out = build_pairs(corpus, tmp_path / "pairs", FakeLM(lambda s, u: "n " + u), cfg)
    valid = len(read_jsonl(tmp_path / "pairs" / "valid.jsonl"))
    test = len(read_jsonl(tmp_path / "pairs" / "test.jsonl"))
    train = len(read_jsonl(tmp_path / "pairs" / "train.jsonl"))
    assert valid == 2 and test == 2 and train == 2 * (40 - 4) and out["train"] == train


def test_build_pairs_limit(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    _corpus(corpus, n=40)
    lm = FakeLM(lambda s, u: "n " + u)
    build_pairs(corpus, tmp_path / "pairs", lm, CFG, limit=5)
    assert len(lm.calls) == 5
