import shutil
from pathlib import Path

from vishlang.clean import read_jsonl
from vishlang.cli import main
from vishlang.config import load_config
from vishlang.llm import FakeLM
from vishlang.pairs import build_pairs
from tests.conftest import FIX


def test_fixtures_flow_to_pairs_with_fake_lm(tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(FIX, raw)
    rc = main(["--config", str(FIX / "cfg_all.toml"), "ingest", "--raw", str(raw), "--out", str(tmp_path / "d")])
    assert rc == 0
    corpus = read_jsonl(tmp_path / "d" / "corpus.jsonl") + read_jsonl(tmp_path / "d" / "holdout.jsonl")
    assert corpus and all(r["source"] != "chatgpt" for r in corpus)
    assert {r["source"] for r in corpus} >= {"whatsapp", "gmail", "docs", "linkedin", "claude"}
    out = build_pairs(tmp_path / "d" / "corpus.jsonl", tmp_path / "d" / "pairs",
                      FakeLM(lambda s, u: "n " + u), load_config(FIX / "cfg_all.toml"))
    assert out["train"] >= 1


def test_skill_and_readme_exist():
    root = Path(__file__).resolve().parent.parent
    skill = (root / "skill" / "SKILL.md").read_text()
    assert skill.startswith("---\nname: vishlang\n") and "rewrite" in skill
    readme = (root / "README.md").read_text()
    for must in ["vishlang ingest", "vishlang pairs --sample 20", "vishlang test --mode fewshot",
                 "vishlang train", "vishlang serve --print-config", "takeout.google.com", "before"]:
        assert must in readme, must


def test_lexicon_is_tracked_by_git():
    import subprocess
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run(["git", "ls-files", "--error-unmatch", "vishlang/data/excess_words.csv"], cwd=root, capture_output=True)
    assert r.returncode == 0, "excess_words.csv is not committed; a fresh clone cannot import vishlang.detect"
