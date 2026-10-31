<p align="center">
  <h1 align="center">vishlang</h1>
  <p align="center"><b>Yo. If you have Claude Code or Codex, train a model to write the way you speak, on your device. Then use that for everything else.</b></p>
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#how-it-feels">How it feels</a> ·
  <a href="#profiles-one-per-tone">Profiles</a> ·
  <a href="#feed-it-more-of-you">Sources</a> ·
  <a href="#what-stays-private">Privacy</a> ·
  <a href="#method">Method</a>
</p>

---

Every LLM draft sounds like an LLM. vishlang fine-tunes a small model on text **you** wrote and hands
it to your coding agent as a `rewrite` tool plus a skill. The agent drafts, calls `rewrite`, and you
get the draft in your own voice. Nothing leaves your Mac.

- **Zero exports to start.** Your Claude Code and Codex prompt history is already on disk. That is you,
  unfiltered, talking to a machine. First profile trains from that alone.
- **Profiles.** One tone per profile: `default`, `work`, `linkedin`, `dm`. Train as many as you like,
  the agent picks one per call.
- **One line install.** Installs the CLI, drops the skill into Claude Code and Codex, registers the MCP
  server in both.
- **On device.** QLoRA on a 4B model via [mlx-lm](https://github.com/ml-explore/mlx-lm). About 30 to 60
  minutes on an M-series Mac. The adapter is 13 MB.

## Install

Apple Silicon Mac, 16 GB RAM or more, macOS 15+.

```bash
curl -fsSL https://raw.githubusercontent.com/VishiATChoudhary/vishlang/main/install.sh | sh
```

That runs `uv tool install` for the CLI, then `vishlang install`, which copies the skill to
`~/.claude/skills/vishlang` and `~/.agents/skills/vishlang` and registers the `vishlang` MCP server
in Claude Code and Codex if they are on your PATH. Re-run it any time; it is idempotent.

Then train your first profile:

```bash
vishlang init --name "Your Name" --email you@example.com
vishlang build          # ingest, back-translate, train. Go get coffee.
vishlang test           # blind A/B: which one sounds like you?
```

Open a new Claude Code or Codex session. Ask it to draft an email. It sounds like you.

## How it feels

Input, written by an LLM:

> Could you please investigate the failing test in the authentication module? It would be helpful if
> you could identify the root cause and propose a comprehensive solution. Additionally, please ensure
> that all existing tests continue to pass after your changes.

`rewrite`, profile trained on 1,600 of the author's Claude Code prompts:

> Can you look into the failing test in the auth module? Find the cause and then write a solution!
> Make sure that all existing tests still pass!

Facts, names, numbers and links are kept. Headings, lists, code and quotes pass through untouched.
Only prose paragraphs change. The skill tells the agent to call `rewrite` on every draft you will send
or publish, and never on code or on text you pasted in yourself.

From the shell:

```bash
vishlang rewrite "Hey, wanted to reach out to see if you'd be interested in grabbing coffee next week."
# hey! Do you want to do coffee next week?
pbpaste | vishlang --profile work rewrite
```

## Profiles, one per tone

A profile lives under `~/.vishlang/profiles/<name>/` with its own config, raw exports, corpus and adapter.

```bash
vishlang init linkedin --name "Your Name"      # new profile
vishlang profiles                              # list: corpus size, trained yes/no
vishlang --profile linkedin build              # train it
vishlang --profile linkedin rewrite "..."      # use it
```

The MCP tool is `rewrite(text, profile="")`. Empty picks `default`. The agent passes the profile you
name ("rewrite that in my linkedin voice"). An untrained profile answers with the list of trained ones
instead of failing.

Shape a tone through `profile.toml`: set `weight = 0` on the sources that do not belong to it. A
`linkedin` profile that only learns from your LinkedIn posts sets everything else to 0. A `dm` profile
learns from WhatsApp only.

## Feed it more of you

Drop exports into `~/.vishlang/profiles/<name>/raw/`. Any filename, subfolders fine, formats are
detected automatically. Then `vishlang --profile <name> build` again.

| Source | How to export |
|---|---|
| Claude Code | Nothing. Read from `~/.claude/projects` automatically. |
| Codex | Nothing. Read from `~/.codex/sessions` automatically. |
| WhatsApp | In a chat: menu > More > Export chat > **Without media**. One `.txt` per chat. |
| Gmail | [takeout.google.com](https://takeout.google.com): deselect all, select **Mail**, format `.mbox`. Only mail *from* your addresses is kept, drafts are skipped. |
| Google Docs | Takeout > **Drive**, choose `.txt` as the Docs format. Or File > Download > Plain text. |
| LinkedIn | Settings > Data privacy > Get a copy of your data > tick **Shares**. Drop `Shares.csv`. |
| ChatGPT | Settings > Data controls > Export data. Keep `conversations.json`. Weight 0 by default. |

Text written by other people (chat partners, email senders, the assistant) is never stored. Set
`before = "YYYY-MM"` on a source to drop everything written after you started drafting with LLMs;
the built-in AI-writing detector catches the obvious cases, not lightly edited ones.

## The blind test

```bash
vishlang test --mode fewshot   # no training, 20 examples in the prompt
vishlang test                  # with the adapter
```

20 held-out paragraphs. For each you see the neutral (LLM register) version and the rewrite in random
order and pick which sounds like you. Pass = rewrite picked 15 or more times and the mean AI score drops.

## Commands

```
vishlang init [NAME] [--name N] [--email E]   create a profile
vishlang profiles                             list profiles
vishlang build [--iters N]                    ingest + pairs + train
vishlang ingest | pairs | train               the steps, individually
vishlang pairs --sample 20                    eyeball 20 neutralised paragraphs first
vishlang test [--mode fewshot]                blind A/B
vishlang rewrite [TEXT]                       one-off rewrite, stdin if no text
vishlang serve                                MCP server (stdio), rewrite(text, profile)
vishlang serve --print-config                 the claude mcp add line
vishlang install                              skill + MCP into Claude Code and Codex
```

Every command takes `--profile NAME` (or `VISHLANG_PROFILE`). State root is `~/.vishlang`
(`VISHLANG_HOME`).

## What stays private

Everything. Corpus, pairs and adapters live in `~/.vishlang`, never in this repo. No network calls
except the one-time base model download from Hugging Face. The skill forbids rewriting text you pasted
in, so other people's words never reach the model.

## Method

Pairs are built by inverse transfer: the base model (`Qwen3-4B-Instruct-2507`, 4-bit) rewrites each of
your paragraphs into generic assistant register, and a rank-16 LoRA adapter is trained on the reverse
direction, neutral in, you out (Shao et al., *Authorship style transfer with inverse transfer data
augmentation*, 2024). The AI-writing filter uses the excess-vocabulary list from Kobak et al., *Science
Advances* 2025, plus em-dash density, rule-of-three frequency and sentence length flatness. The adapter
is never fused, so swapping profiles is swapping a 13 MB file.

M5 Macs on macOS 26.0 or 26.1: MLX ships kernels that OS cannot compile
([mlx#4525](https://github.com/ml-explore/mlx/issues/4525)). vishlang sets
`MLX_METAL_GPU_ARCH=applegpu_g16g` automatically. Update to macOS 26.2+ for full speed.

## Develop

```bash
git clone https://github.com/VishiATChoudhary/vishlang && cd vishlang
# re-run install.sh any time to update; it refreshes the cached archive
uv sync && uv run pytest
VISHLANG_SLOW=1 uv run pytest   # also loads the real model once
```

Design notes and the execution ledger are under `docs/superpowers/`.
