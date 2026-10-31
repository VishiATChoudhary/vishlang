import asyncio

from vishlang.cli import main
from vishlang.llm import FakeLM
from vishlang.serve import make_server, rewrite_text, split_blocks

DRAFT = """Subject: Parser update

Hi Anna,

I went through the notes you sent and I think the parser change is safe to ship this week, the only open point is the date format on Android exports.

- merge window
- media lines

Best,
Vishi"""


def test_split_blocks_marks_only_prose():
    blocks = split_blocks(DRAFT)
    assert [b[1] for b in blocks] == [False, False, True, False, False]
    assert blocks[2][0].startswith("I went through")


def test_split_blocks_code_fence_and_quote_are_not_prose():
    text = "```\nsome code here that is long enough to pass eight words easily\n```\n\n> quoted line that is also long enough to pass eight words\n\nA real paragraph that is long enough to count as prose for the rewriter."
    assert [b[1] for b in split_blocks(text)] == [False, False, True]


def test_rewrite_text_only_touches_prose_and_preserves_layout():
    lm = FakeLM(lambda s, u: "REWRITTEN")
    out = rewrite_text(lm, DRAFT, "sys")
    assert out.startswith("Subject: Parser update\n\nHi Anna,\n\nREWRITTEN\n\n- merge window")
    assert out.endswith("Best,\nVishi") and len(lm.calls) == 1 and lm.calls[0][0] == "sys"


def test_rewrite_text_no_prose_returns_input_without_calls():
    lm = FakeLM(lambda s, u: "X")
    assert rewrite_text(lm, "", "sys") == ""
    assert rewrite_text(lm, "Subject: hi\n\n- a\n- b", "sys") == "Subject: hi\n\n- a\n- b"
    assert lm.calls == []


def test_rewrite_text_empty_model_output_falls_back():
    lm = FakeLM(lambda s, u: "")
    assert rewrite_text(lm, DRAFT, "sys") == DRAFT


def test_rewrite_text_strips_preamble_from_model():
    lm = FakeLM(lambda s, u: "Here is the rewritten text:\nREWRITTEN")
    assert "Here is" not in rewrite_text(lm, DRAFT, "sys")


def test_server_exposes_rewrite_tool():
    srv = make_server(FakeLM(lambda s, u: "Y"), "sys")
    tools = asyncio.run(srv.list_tools())
    assert [t.name for t in tools] == ["rewrite"]
    assert "Vishi's voice" in tools[0].description


def test_print_config(capsys):
    assert main(["serve", "--mode", "fewshot", "--print-config"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith("claude mcp add vishlang -- uv --directory ") and out.endswith("run vishlang serve --mode fewshot")
