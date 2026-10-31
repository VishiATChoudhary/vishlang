import pytest

from vishlang.llm import LM, FakeLM, clean_output
from vishlang.prompts import NEUTRALISE_SYSTEM, REWRITE_SYSTEM, fewshot_system


def test_clean_output_strips_think_preamble_quotes():
    raw = '<think>hmm</think>\nHere is the rewritten text:\n"ok ship it tonight"'
    assert clean_output(raw) == "ok ship it tonight"


def test_clean_output_leaves_plain_text_alone():
    assert clean_output("ok ship it tonight") == "ok ship it tonight"


def test_fake_lm_records_calls():
    lm = FakeLM(lambda s, u: u.upper())
    assert lm.chat("sys", "hi") == "HI" and lm.calls == [("sys", "hi")]


def test_prompts_fixed_copy():
    assert REWRITE_SYSTEM.startswith("You rewrite text so it sounds like Vishi wrote it.")
    assert "generic AI assistant" in NEUTRALISE_SYSTEM
    fs = fewshot_system(["a", "b"])
    assert fs.startswith("Here are examples of how Vishi writes:\n\na\n\n---\n\nb") and fs.endswith(REWRITE_SYSTEM)


@pytest.mark.slow
def test_real_lm_roundtrip():
    lm = LM("mlx-community/Qwen3-4B-Instruct-2507-4bit")
    out = lm.chat(REWRITE_SYSTEM, "Please find attached the document for your review.", max_tokens=60)
    assert out.strip()
