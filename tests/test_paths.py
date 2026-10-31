from pathlib import Path

from vishlang.paths import Profile, home, profile_dir


def test_home_follows_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    assert home() == tmp_path
    assert profile_dir("work") == tmp_path / "profiles" / "work"


def test_profile_without_toml_uses_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    p = Profile.load("default")
    assert p.name == "default"
    assert p.config["clean"]["min_words"] == 8
    assert p.raw == tmp_path / "profiles" / "default" / "raw"
    assert p.corpus == p.data / "corpus.jsonl"
    assert p.latest == p.adapters / "latest"


def test_profile_reads_its_toml(monkeypatch, tmp_path):
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    d = tmp_path / "profiles" / "casual"
    d.mkdir(parents=True)
    (d / "profile.toml").write_text('[author]\nnames = ["V"]\n[clean]\nmin_words = 3\n')
    p = Profile.load("casual")
    assert p.config["author"]["names"] == ["V"]
    assert p.config["clean"]["min_words"] == 3
    assert p.config["clean"]["holdout"] == 0.1


def test_profile_trained_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    p = Profile.load("x")
    assert p.trained is False
    (p.adapters / "20260101").mkdir(parents=True)
    (p.adapters / "20260101" / "adapters.safetensors").write_bytes(b"")
    p.latest.symlink_to(p.adapters / "20260101")
    assert Profile.load("x").trained is True


def test_profile_dir_rejects_path_escapes(monkeypatch, tmp_path):
    import pytest
    monkeypatch.setenv("VISHLANG_HOME", str(tmp_path))
    for bad in ("../evil", "/abs/path", "a/b", "", "x" * 65, "sp ace"):
        with pytest.raises(ValueError):
            profile_dir(bad)
    assert profile_dir("work-2_v1") == tmp_path / "profiles" / "work-2_v1"
