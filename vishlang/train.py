"""Thin wrapper around `python -m mlx_lm.lora`. We only write the config and run it."""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LORA_KEYS = ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj"]


def train_config(base: str, data_dir: Path, adapter_dir: Path, iters: int = 1000) -> dict:
    return {
        "model": base,
        "train": True,
        "data": str(data_dir),
        "fine_tune_type": "lora",
        "mask_prompt": True,  # loss on the assistant turn only, never on the neutral input
        "num_layers": 16,
        "batch_size": 2,
        "iters": iters,
        "learning_rate": 1e-4,
        "steps_per_eval": 100,
        "save_every": 200,
        "adapter_path": str(adapter_dir),
        "max_seq_length": 1024,
        "grad_checkpoint": True,
        "lora_parameters": {"rank": 16, "scale": 20.0, "dropout": 0.05, "keys": LORA_KEYS},
    }


def _yaml(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(f'"{v}"' for v in value) + "]"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def write_yaml(cfg: dict, path: Path) -> None:
    lines = []
    for k, v in cfg.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            lines.extend(f"  {kk}: {_yaml(vv)}" for kk, vv in v.items())
        else:
            lines.append(f"{k}: {_yaml(v)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def train(cfg: dict, data_dir: Path = Path("data/pairs"), adapters_root: Path = Path("adapters"),
          iters: int = 1000, dry_run: bool = False) -> Path | list[str]:
    adapter_dir = adapters_root / datetime.now().strftime("%Y%m%d-%H%M")
    adapter_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = adapter_dir / "train.yaml"
    write_yaml(train_config(cfg["model"]["base"], data_dir, adapter_dir, iters), yaml_path)

    latest = adapters_root / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(adapter_dir.name)

    argv = [sys.executable, "-m", "mlx_lm.lora", "-c", str(yaml_path)]
    if dry_run:
        return argv
    subprocess.run(argv, check=True)
    return adapter_dir
