# VishLang v1: profiles, one-line install, skill for Claude Code and Codex

Date: 2026-10-31. Extends the v0 design (2026-10-30). Everything in v0 still holds: local only,
never store other people's text, never train on LLM-written text.

## Intent

Pitch: "If you have Claude Code or Codex, train a model that writes the way you speak, on your
device, then use it for everything else." Onboarding must be one line. The agent you already use
does the rest through a skill: it can train profiles and it can call them.

## Goals

- `curl -fsSL .../install.sh | sh` installs vishlang as a uv tool, drops the skill into Claude Code
  and Codex, registers the MCP server in both. Zero exports needed for the first profile: Claude Code
  and Codex prompt history are auto-detected sources.
- Profiles. A profile is one tone: its own config, raw drops, corpus, pairs, adapter. Stored under
  `~/.vishlang/profiles/<name>/`. Any number. `rewrite(text, profile=...)` picks one. Default
  profile is `default`.
- Skill is generic (no hard-coded person), works in Claude Code (`~/.claude/skills`) and Codex
  (`~/.agents/skills`), and tells the agent how to train, list and call profiles.
- Codex session history as a sixth source, same filters as Claude Code history.
- Repo is public, README sells it in the user's pitch.

## Non-goals

- Web UI, Gmail OAuth, cloud anything. Later.
- Fusing adapters, exporting GGUF.

## Decisions

- State root `VISHLANG_HOME`, default `~/.vishlang`. Repo stays stateless so `uv tool install` works.
- Profile config `profile.toml` has the same schema as v0 `vishlang.toml`. Missing file = defaults.
- `vishlang init <name> [--name N --email E]` creates a profile and prints where to drop exports.
- CLI gets global `--profile` (env `VISHLANG_PROFILE`, default `default`). All data paths derive from it.
- MCP tool `rewrite(text, profile="default")`. Server loads the base model once per profile on first
  use and caches it. Fewshot mode stays as the untrained fallback.
- `vishlang install` is idempotent: copies the skill, re-registers MCP in whichever of `claude` and
  `codex` exist on PATH, prints what it did.
- Skill lives at `skills/vishlang/SKILL.md` in the repo (skills.sh layout) and is packaged into the
  wheel so `vishlang install` finds it without a clone.
- Requirements stated up front: Apple Silicon Mac, 16 GB RAM, macOS 15+. Linux/CUDA not in v1.
