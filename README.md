# vishlang

Fine-tune a small local model on your own writing, then let any agent call `rewrite(text)` over MCP
to turn its LLM-flavoured draft into something that sounds like you. Runs entirely on an Apple
Silicon Mac with [mlx-lm](https://github.com/ml-explore/mlx-lm). Nothing you write leaves the machine.

## Install

```bash
uv sync
```

Needs Python 3.12+, `uv`, and roughly 16 GB of unified memory for the default 4B base model.

M5 Macs on macOS 26.0 or 26.1: MLX ships kernels that OS cannot compile ([mlx#4525](https://github.com/ml-explore/mlx/issues/4525)). vishlang sets `MLX_METAL_GPU_ARCH=applegpu_g16g` automatically, which works but skips the M5 neural accelerators. Update to macOS 26.2+ for full speed.

## 1. Get your exports

Drop everything into `data/raw/` (any filename, subfolders fine). Formats are detected automatically.

| Source | How to export |
|---|---|
| WhatsApp | In a chat: menu > More > Export chat > **Without media**. One `.txt` per chat. |
| Gmail | [takeout.google.com](https://takeout.google.com): deselect all, select **Mail**, format `.mbox`. Drop the `.mbox` in `data/raw/`. Only mail *from* your configured addresses is kept, drafts are skipped. |
| Google Docs | Takeout > **Drive**, choose `.txt` as the Docs format. Or File > Download > Plain text per document. |
| LinkedIn | Settings > Data privacy > Get a copy of your data > tick **Shares**. Drop `Shares.csv`. |
| ChatGPT | Settings > Data controls > Export data. Keep `conversations.json`. Weight 0 by default (prompts to a bot are not prose to humans). |
| Claude Code | Nothing to do. Prompts you typed into Claude Code are read from `~/.claude/projects` automatically. Set `path = ""` under `[sources.claude]` to disable. |

Text written by other people (chat partners, email senders, the assistant) is never stored.

## 2. Configure

Edit `vishlang.toml`:

- `[author] names` : your display name(s) exactly as they appear in WhatsApp exports.
- `[author] emails` : your sending addresses for the mbox.
- `[sources.<name>] before = "YYYY-MM"` : drop anything written on or after that month. Set it to the
  month you started drafting with LLMs; the heuristic detector will not catch lightly edited LLM mail.
- `[sources.<name>] weight` : `0` excludes a source, `2` repeats its examples twice in training.

## 3. Run

```bash
uv run vishlang ingest                # parse + clean -> data/corpus.jsonl, data/holdout.jsonl
uv run vishlang pairs --sample 20     # eyeball 20 neutralised paragraphs before the long run
uv run vishlang pairs                 # back-translate the whole corpus (hours, resumable)
uv run vishlang test --mode fewshot   # step 0: blind A/B with no training at all
uv run vishlang train                 # QLoRA via mlx_lm.lora -> adapters/latest
uv run vishlang test                  # blind A/B with the adapter
uv run vishlang rewrite "some draft"  # one-off rewrite from the terminal (or pipe text on stdin)
uv run vishlang serve --print-config  # prints the `claude mcp add ...` line
```

`vishlang build` runs ingest, pairs and train in sequence.

### The blind test

20 held-out paragraphs. For each you see the neutral (LLM register) version and the model's rewrite
in random order and pick which sounds like you. Pass = rewrite picked at least 15 times and the
mean AI score drops. If few-shot already passes, training is optional.

## 4. Use it from Claude Code

```bash
eval "$(uv run vishlang serve --print-config)"   # registers at user scope, available in every project
ln -s "$(pwd)/skill" ~/.claude/skills/vishlang
```

Claude Code now has a `rewrite` tool and a skill telling it to call that tool on drafts.

## What stays private

`data/` and `adapters/` are gitignored. The tool is public; your corpus and adapter are not,
unless you choose to publish them.

## Method

Pairs are built by inverse transfer: the base model rewrites your paragraph into generic assistant
register, and the adapter is trained on the reverse direction (Shao et al., *Authorship style transfer
with inverse transfer data augmentation*, 2024). The AI-writing filter uses the excess-vocabulary list
from Kobak et al., *Science Advances* 2025, plus em-dash density, rule-of-three frequency and sentence
length flatness.
