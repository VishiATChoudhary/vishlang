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


def make_server(lm, system: str):
    from mcp.server.mcpserver import MCPServer  # mcp 2.x name for FastMCP

    mcp = MCPServer("vishlang")

    @mcp.tool()
    def rewrite(text: str) -> str:
        """Rewrite text in Vishi's voice. Keeps facts, structure and language; changes only tone and wording."""
        return rewrite_text(lm, text, system)

    return mcp


def build_system(mode: str, corpus: Path = Path("data/corpus.jsonl")) -> str:
    if mode == "lora":
        return REWRITE_SYSTEM
    from .clean import read_jsonl

    rows = read_jsonl(corpus)
    examples = [r["text"] for r in random.Random(0).sample(rows, min(FEWSHOT_EXAMPLES, len(rows)))]
    return fewshot_system(examples)


def mcp_add_command(mode: str, project_dir: Path | None = None) -> str:
    root = (project_dir or Path(__file__).resolve().parent.parent)
    return f"claude mcp add -s user vishlang -- uv --directory {root} run vishlang serve --mode {mode}"
