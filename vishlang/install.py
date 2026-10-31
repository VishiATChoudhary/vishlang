"""Install the skill into Claude Code and Codex, register the MCP server in both."""
import shutil
import subprocess
from pathlib import Path

from .serve import mcp_add_command

SKILL_DIRS = {
    "claude": Path.home() / ".claude" / "skills",
    "agents": Path.home() / ".agents" / "skills",  # Codex reads ~/.agents/skills
}


def skill_source() -> Path:
    here = Path(__file__).resolve().parent
    for cand in (here / "skill", here.parent / "skills" / "vishlang"):
        if (cand / "SKILL.md").exists():
            return cand
    raise FileNotFoundError("vishlang skill files missing from this install")


def _copy_skill(dst: Path) -> None:
    if dst.is_symlink() or dst.is_file():
        dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_source(), dst, dirs_exist_ok=True)


def install(claude_skills: Path = SKILL_DIRS["claude"], agents_skills: Path = SKILL_DIRS["agents"],
            which=shutil.which, run=subprocess.run) -> list[str]:
    lines = []
    for dst in (claude_skills / "vishlang", agents_skills / "vishlang"):
        _copy_skill(dst)
        lines.append(f"skill   -> {dst}")
    exe = which("vishlang") or "vishlang"
    for cli in ("claude", "codex"):
        path = which(cli)
        if not path:
            lines.append(f"{cli:7} not found on PATH, skipped MCP registration")
            continue
        scope = ["-s", "user"] if cli == "claude" else []
        run([path, "mcp", "remove", *scope, "vishlang"], capture_output=True)
        run([path, "mcp", "add", *scope, "vishlang", "--", exe, "serve"], capture_output=True)
        lines.append(f"{cli:7} mcp server registered: {mcp_add_command(cli, exe)}")
    return lines
