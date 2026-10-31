from tests.conftest import FIX
from vishlang.config import load_config
from vishlang.ingest import detect_format, ingest_dir, parse_codex


def test_parse_codex_keeps_only_typed_prompts():
    paras = parse_codex(FIX / "codex" / "rollout.jsonl")
    assert [p.text for p in paras] == [
        "Bro this needs to work now! Like end to end!",
        "My CTO said to bring main into the current branch as well. There are some new changes we need to integrate!",
    ]
    assert all(p.source == "codex" and p.date.startswith("2026-10-29T08:3") for p in paras)
    assert paras[0].date == "2026-10-29T08:31"


def test_detect_format_codex_vs_claude():
    assert detect_format(FIX / "codex" / "rollout.jsonl") == "codex"
    assert detect_format(FIX / "claude" / "session.jsonl") == "claude"


def test_ingest_dir_walks_codex_path(tmp_path):
    cfg = load_config(FIX / "cfg_all.toml")
    cfg["sources"]["codex"]["path"] = str(FIX / "codex")
    paras = ingest_dir(tmp_path, cfg)
    assert [p.source for p in paras] == ["codex", "codex"]


def test_codex_default_path_and_weight():
    cfg = load_config("/nonexistent.toml")
    assert cfg["sources"]["codex"] == {"weight": 1.0, "before": "", "path": "~/.codex/sessions"}


def test_parse_codex_dedupes_replayed_prompts_and_drops_json_wrapped_messages():
    texts = [p.text for p in parse_codex(FIX / "codex" / "rollout.jsonl")]
    assert texts.count("Bro this needs to work now! Like end to end!") == 1
    assert not any(t.startswith("{") for t in texts)


def test_parse_codex_skips_subagent_rollouts():
    assert parse_codex(FIX / "codex" / "subagent.jsonl") == []
