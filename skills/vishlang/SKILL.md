---
name: vishlang
description: Use when drafting any text the user will send or publish (email, chat message, LinkedIn post, doc paragraph, PR description) or when the user asks to train, list or switch their voice profiles. Rewrites drafts in the user's own voice with a model trained on their writing, on their machine.
---

# vishlang

The user has a local voice model. It is served over MCP as the tool `rewrite(text, profile)`.
It was trained on how they actually write. Use it so your drafts stop sounding like a model.

## Rewrite a draft

- When you finish any draft the user will send or publish, call `rewrite` with the whole draft,
  including subject line, greeting and sign-off. Structure passes through untouched (headings,
  lists, code, quotes); only prose paragraphs change.
- Show the rewritten version only. If the tool is unavailable, say so in one line and show the
  plain draft.
- Never call `rewrite` on code, quoted third-party text, or text the user pasted in themselves.
- Facts, names, numbers and links must survive. If the rewrite dropped one, put it back by hand.

## Profiles (tones)

One profile = one tone, stored under `~/.vishlang/profiles/<name>/`. The default is `default`.
Pass `profile="work"` (or whatever the user named it) to pick another. If the user does not say,
use the default. If the tool answers that a profile is not trained, tell the user and offer to
train it (below).

```bash
vishlang profiles                  # list profiles, corpus size, trained yes/no
```

## Train a profile

Everything runs on the user's machine. Apple Silicon Mac, 16 GB RAM or more.

```bash
vishlang init work --name "Their Name" --email them@example.com   # creates ~/.vishlang/profiles/work
# optional: user drops WhatsApp .txt, Gmail Takeout .mbox, Docs .md/.txt, LinkedIn Shares.csv,
# ChatGPT conversations.json into ~/.vishlang/profiles/work/raw/
vishlang --profile work build      # ingest, back-translate pairs, QLoRA train. 30 to 90 min.
vishlang --profile work test       # blind A/B, interactive, the user picks what sounds like them
```

Claude Code and Codex prompt history are picked up automatically; a first profile needs no
exports at all. `build` is long: run it in the background and tell the user roughly how long.
Each profile's `profile.toml` controls which sources count and how much each weighs. A tone that
should only learn from, say, LinkedIn posts sets every other source to `weight = 0`.

## One-off rewrite from the shell

```bash
vishlang --profile work rewrite "text here"      # or pipe text on stdin
```
