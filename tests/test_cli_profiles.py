import shutil
import tomllib

from tests.conftest import FIX
from vishlang import cli
from vishlang.llm import FakeLM
from vishlang.paths import Profile


def test_init_creates_profile(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    assert cli.main(["--profile", "work", "init", "--name", "Vishi", "--email", "v@x.io"]) == 0
    p = Profile.load("work")
    assert p.raw.is_dir()
    cfg = tomllib.loads(p.toml.read_text())
    assert cfg["author"] == {"names": ["Vishi"], "emails": ["v@x.io"]}
    assert str(p.raw) in capsys.readouterr().out


def test_init_name_argument_wins_over_profile_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    assert cli.main(["init", "casual"]) == 0
    assert Profile.load("casual").toml.exists()


def test_profiles_lists_state(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    cli.main(["init", "a"])
    cli.main(["init", "b"])
    Profile.load("a").data.mkdir(parents=True)
    Profile.load("a").corpus.write_text('{"text":"x"}\n{"text":"y"}\n')
    assert cli.main(["profiles"]) == 0
    out = capsys.readouterr().out
    assert "a" in out and "b" in out and "2" in out and "no" in out


def test_ingest_defaults_to_profile_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    cli.main(["init", "default", "--name", "Vishi", "--email", "vishisht@invertix.ai"])
    p = Profile.load("default")
    shutil.copytree(FIX, p.raw, dirs_exist_ok=True)
    assert cli.main(["--config", str(FIX / "cfg_all.toml"), "ingest"]) == 0
    assert p.corpus.exists() and p.holdout.exists()


def test_rewrite_uses_profile_adapter(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    seen = {}

    def fake(cfg, adapter=None):
        seen["adapter"] = adapter
        return FakeLM(lambda s, u: u)

    monkeypatch.setattr(cli, "_lm", fake)
    assert cli.main(["--profile", "work", "rewrite", "one two three four five six seven eight nine."]) == 0
    assert seen["adapter"] == str(Profile.load("work").latest)
