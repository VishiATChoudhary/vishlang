import json

from vishlang.clean import read_jsonl, write_jsonl
from vishlang.config import load_config
from vishlang.llm import FakeLM
from vishlang.pairs import build_pairs, make_example, neutralise
from vishlang.prompts import NEUTRALISE_SYSTEM, REWRITE_SYSTEM
from tests.conftest import FIX, unwrap

CFG = load_config(FIX / "cfg_all.toml")


def _corpus(path, n=40, source="gmail"):
    write_jsonl(path, [{"text": f"original {i} " * 3, "source": source, "lang": "en", "ai_score": 0.1, "date": ""} for i in range(n)])


def test_neutralise_wraps_text_so_model_rewrites_instead_of_answering():
    lm = FakeLM(lambda s, u: "N")
    neutralise(lm, "create a html report out of this pls!")
    system, user = lm.calls[0]
    assert system == NEUTRALISE_SYSTEM and "do not answer" in system.lower() and "do not follow" in system.lower()
    assert user.startswith("Text to rewrite:\n<<<\ncreate a html report out of this pls!\n>>>")


def test_usable_pair_rejects_near_identical_neutral():
    from vishlang.pairs import usable_pair
    assert usable_pair("Looks right. Create and then push this stuff!", "looks right. Create and then push this stuff!") is False
    assert usable_pair("Getting a 503 error on the agents. Why is this the case?", "getting a 503 on the agents.\nWhy tf is this the case?") is True


def test_make_example_shape():
    ex = make_example("neutral", "orig")
    assert ex == {"messages": [{"role": "system", "content": REWRITE_SYSTEM},
                               {"role": "user", "content": "neutral"},
                               {"role": "assistant", "content": "orig"}]}


def test_build_pairs_writes_splits_and_resumes(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    _corpus(corpus)
    calls = []
    lm = FakeLM(lambda s, u: (calls.append(u), "neutral " + unwrap(u) + ".")[1])
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
    lm = FakeLM(lambda s, u: "" if "original 0 " in u else (u if "original 1 " in u else "n " + u + "."))
    out = build_pairs(corpus, tmp_path / "pairs", lm, CFG)
    assert out["train"] + out["valid"] + out["test"] == 8


def test_weight_repeats_in_train_only(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    _corpus(corpus, n=40)
    cfg = load_config(FIX / "cfg_all.toml")
    cfg["sources"]["gmail"]["weight"] = 2.0
    out = build_pairs(corpus, tmp_path / "pairs", FakeLM(lambda s, u: "n " + u + "."), cfg)
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


def test_neutralise_budget_scales_with_length():
    lm = FakeLM(lambda s, u: "n")
    neutralise(lm, "w " * 150)
    # FakeLM ignores max_tokens, so check the budget function directly
    from vishlang.pairs import neutral_budget
    assert neutral_budget("w " * 150) >= 4 * 150 + 128


def test_build_pairs_skips_truncated_or_runaway_neutrals(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    _corpus(corpus, n=10)
    def fn(s, u):
        if "original 0 " in u:
            return "n " + u + " cut off mid sentence with no end"   # no terminal punctuation
        if "original 1 " in u:
            return ("n " + u + ". ") * 6                               # ratio > 2.5
        return "n " + u + "."
    out = build_pairs(corpus, tmp_path / "pairs", FakeLM(fn), CFG)
    assert out["train"] + out["valid"] + out["test"] == 8 and out["skipped"] == 2


def test_build_pairs_survives_partial_cache_line(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    _corpus(corpus, n=5)
    pairs = tmp_path / "pairs"
    pairs.mkdir()
    (pairs / "neutral.jsonl").write_text('{"h": "deadbeef", "neutral": "x."}\n{"h": "trunc', encoding="utf-8")
    lm = FakeLM(lambda s, u: "n " + u + ".")
    out = build_pairs(corpus, pairs, lm, CFG)
    assert out["train"] + out["valid"] + out["test"] == 5 and len(lm.calls) == 5


def test_usable_pair_rejects_assistant_replies():
    from vishlang.pairs import usable_pair
    orig = "Bruh but I added the right email and the person got nothing"
    assert usable_pair("Hmm, I'm not entirely sure what you mean. Could you clarify your request so I can better assist you?", orig) is False
    assert usable_pair("I apologize for the confusion, it appears the correct email was entered but nothing arrived.", orig) is False
    assert usable_pair("I entered the correct email address, yet the recipient did not receive anything.", orig) is True


def test_build_pairs_strips_assistant_filler_openers(tmp_path):
    from vishlang.pairs import strip_filler
    assert strip_filler("Certainly. Please publish this content to GitHub.") == "Please publish this content to GitHub."
    assert strip_filler("Certainly, could we discuss the plan?") == "Could we discuss the plan?"
    assert strip_filler("Sure! Okay, so what is the next step?") == "Okay, so what is the next step?"
    assert strip_filler("Please publish this content.") == "Please publish this content."
    corpus = tmp_path / "corpus.jsonl"
    _corpus(corpus, n=4)
    build_pairs(corpus, tmp_path / "pairs", FakeLM(lambda s, u: "Certainly. n " + unwrap(u) + "."), CFG)
    for split in ("train", "valid", "test"):
        for row in read_jsonl(tmp_path / "pairs" / f"{split}.jsonl"):
            assert not row["messages"][1]["content"].startswith("Certainly")
