"""Where a profile lives on disk. State root is $VISHLANG_HOME, default ~/.vishlang."""
import os
from dataclasses import dataclass
from pathlib import Path

from .config import load_config


def home() -> Path:
    return Path(os.environ.get("VISHLANG_HOME") or Path.home() / ".vishlang").expanduser()


def profile_dir(name: str) -> Path:
    return home() / "profiles" / name


@dataclass
class Profile:
    name: str
    dir: Path
    config: dict

    @classmethod
    def load(cls, name: str) -> "Profile":
        d = profile_dir(name)
        return cls(name, d, load_config(d / "profile.toml"))

    @property
    def toml(self) -> Path:
        return self.dir / "profile.toml"

    @property
    def raw(self) -> Path:
        return self.dir / "raw"

    @property
    def data(self) -> Path:
        return self.dir / "data"

    @property
    def corpus(self) -> Path:
        return self.data / "corpus.jsonl"

    @property
    def holdout(self) -> Path:
        return self.data / "holdout.jsonl"

    @property
    def pairs(self) -> Path:
        return self.data / "pairs"

    @property
    def adapters(self) -> Path:
        return self.dir / "adapters"

    @property
    def latest(self) -> Path:
        return self.adapters / "latest"

    @property
    def trained(self) -> bool:
        return (self.latest / "adapters.safetensors").exists()

    @property
    def corpus_size(self) -> int:
        return sum(1 for _ in self.corpus.open()) if self.corpus.exists() else 0
