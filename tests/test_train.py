from vishlang.config import load_config
from vishlang.train import train, train_config
from tests.conftest import FIX

CFG = load_config(FIX / "cfg_all.toml")


def test_train_config_values(tmp_path):
    c = train_config("base/x", tmp_path / "pairs", tmp_path / "ad")
    assert c["model"] == "base/x" and c["train"] is True and c["fine_tune_type"] == "lora"
    assert c["lora_parameters"]["rank"] == 16 and c["learning_rate"] == 1e-4
    assert c["mask_prompt"] is True
    assert c["iters"] == 1000 and c["batch_size"] == 2 and c["num_layers"] == 16 and c["max_seq_length"] == 1024
    assert c["data"] == str(tmp_path / "pairs") and c["adapter_path"] == str(tmp_path / "ad")


def test_train_dry_run_writes_yaml_and_argv(tmp_path):
    argv = train(CFG, tmp_path / "pairs", tmp_path / "adapters", dry_run=True)
    assert argv[1:3] == ["-m", "mlx_lm.lora"] and argv[-1].endswith("train.yaml")
    from pathlib import Path
    yaml = Path(argv[-1])
    assert yaml.exists() and not (tmp_path / "adapters" / "latest").exists()
    text = yaml.read_text()
    assert "rank: 16" in text and "learning_rate: 0.0001" in text and "self_attn.q_proj" in text


def test_latest_only_moves_after_a_successful_run(tmp_path, monkeypatch):
    import subprocess
    import pytest

    adapters = tmp_path / "adapters"
    (adapters / "old").mkdir(parents=True)
    (adapters / "latest").symlink_to("old")

    def boom(argv, check):
        raise subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(subprocess.CalledProcessError):
        train(CFG, tmp_path / "pairs", adapters)
    assert (adapters / "latest").resolve() == (adapters / "old").resolve()

    monkeypatch.setattr(subprocess, "run", lambda argv, check: None)
    out = train(CFG, tmp_path / "pairs", adapters)
    assert (adapters / "latest").resolve() == out.resolve()
