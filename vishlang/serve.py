"""MCP server exposing rewrite(text). Structure passes through, prose blocks get rewritten."""
import random
import re
from pathlib import Path

from .prompts import REWRITE_SYSTEM, fewshot_system

_STRUCT_LINE = re.compile(r"^(subject:|#|\s*[-*]\s|\s*\d+[.)]\s|>|```|\|)", re.I)
_SPLIT = re.compile(r"(\n\s*\n)")
MIN_PROSE_WORDS = 8
FEWSHOT_EXAMPLES = 20


def _is_prose(block: str) -> bool:
    lines = [l for l in block.split("\n") if l.strip()]
    if not lines or len(block.split()) < MIN_PROSE_WORDS:
        return False
    if any(_STRUCT_LINE.match(l) for l in lines):
        return False
    if len(lines) == 1 and len(block.split()) <= 6 and block.rstrip().endswith(","):
        return False  # greeting or sign-off
    return True


def _parts(text: str) -> list[tuple[str, bool | None]]:
    """Content blocks with prose flag, separators flagged None, in document order."""
    out = []
    in_fence = False
    for part in _SPLIT.split(text):
        if part == "":
            continue
        if _SPLIT.fullmatch(part):
            out.append((part, None))
            continue
        fenced = in_fence or part.lstrip().startswith("```")
        if part.count("```") % 2 == 1:
            in_fence = not in_fence
        out.append((part, False if fenced else _is_prose(part)))
    return out


def split_blocks(text: str) -> list[tuple[str, bool]]:
    return [(p, flag) for p, flag in _parts(text) if flag is not None]


def rewrite_text(lm, text: str, system: str) -> str:
    out = []
    for block, prose in _parts(text):
        if not prose:
            out.append(block)
            continue
        new = lm.chat(system, block)
        out.append(new if new.strip() else block)
    return "".join(out)


class ProfileRouter:
    """One LM per profile, loaded on first use. load(name) returns (lm, system) or None if untrained."""

    def __init__(self, load, default: str = "default", available=None):
        self.load, self.default = load, default
        self.available = available or self._profiles_on_disk
        self.cache: dict[str, tuple] = {}

    @staticmethod
    def _profiles_on_disk() -> list[str]:
        from .paths import Profile, home

        root = home() / "profiles"
        return sorted(p.name for p in root.iterdir() if p.is_dir() and Profile.load(p.name).trained) if root.is_dir() else []

    def rewrite(self, text: str, profile: str | None = None) -> str:
        from .paths import valid_name

        name = profile or self.default
        if not valid_name(name):
            return f"vishlang: invalid profile name {name!r}. Run `vishlang profiles` to see the available ones."
        if name not in self.cache:
            self.cache[name] = self.load(name)
        if self.cache[name] is None:
            del self.cache[name]
            have = ", ".join(self.available()) or "none"
            return f"vishlang: profile '{name}' is not trained. Trained profiles: {have}. Run `vishlang --profile {name} build`."
        lm, system = self.cache[name]
        return rewrite_text(lm, text, system)


def make_server(router: ProfileRouter):
    from mcp.server.mcpserver import MCPServer  # mcp 2.x name for FastMCP

    mcp = MCPServer("vishlang")

    @mcp.tool()
    def rewrite(text: str, profile: str = "") -> str:
        """Rewrite text in the user's own voice. Keeps facts, structure and language; changes only tone
        and wording. profile picks a trained tone (run `vishlang profiles` to list); empty = default."""
        return router.rewrite(text, profile or None)

    return mcp


def build_system(mode: str, corpus: Path = Path("data/corpus.jsonl")) -> str:
    if mode == "lora":
        return REWRITE_SYSTEM
    from .clean import read_jsonl

    rows = read_jsonl(corpus)
    examples = [r["text"] for r in random.Random(0).sample(rows, min(FEWSHOT_EXAMPLES, len(rows)))]
    return fewshot_system(examples)


def mcp_add_command(cli: str = "claude", exe: str = "vishlang") -> str:
    scope = " -s user" if cli == "claude" else ""
    return f"{cli} mcp add{scope} vishlang -- {exe} serve"
