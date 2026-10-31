---
name: vishlang
description: Use when drafting any text Vishi will send or publish (email, chat message, LinkedIn post, doc paragraph). Call the vishlang MCP tool rewrite on the finished draft before showing it, then show only the rewritten version.
---

# vishlang

Vishi has a local voice model served over MCP as the tool `rewrite(text)`.

- When you finish a draft Vishi will send or publish, call `rewrite` with the whole draft, including subject line, greeting and sign-off. Structure passes through untouched; only prose blocks change.
- Show Vishi the rewritten version only. If the tool is unavailable, say so in one line and show the plain draft.
- Never call `rewrite` on code, quoted third-party text, or text Vishi pasted in himself.

Install: `ln -s "$(pwd)/skill" ~/.claude/skills/vishlang` from the vishlang repo root.
