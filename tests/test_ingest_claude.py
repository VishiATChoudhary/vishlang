from vishlang.config import load_config
from vishlang.ingest import detect_format, ingest_dir, parse_claude
from tests.conftest import FIX


def test_parse_claude_keeps_only_typed_prompts():
    paras = parse_claude(FIX / "claude" / "session.jsonl")
    assert len(paras) == 2
    assert paras[0].text.startswith("Bro, how can we make this as easy as possible?")
    assert paras[1].text.startswith("Oh just build that shape") and "system-reminder" not in paras[1].text
    assert all(p.source == "claude" and p.date.startswith("2026-10-30T10:0") for p in paras)


def test_detect_format_claude():
    assert detect_format(FIX / "claude" / "session.jsonl") == "claude"


def test_ingest_dir_walks_claude_path(tmp_path):
    (tmp_path / "raw").mkdir()
    cfg = load_config(FIX / "cfg_all.toml")
    cfg["sources"]["claude"]["path"] = str(FIX / "claude")
    paras = ingest_dir(tmp_path / "raw", cfg)
    assert [p.source for p in paras] == ["claude", "claude"]
