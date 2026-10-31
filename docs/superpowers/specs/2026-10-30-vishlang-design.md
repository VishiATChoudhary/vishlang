# VishLang: local voice model for agents

Date: 2026-10-30. Status: approved by Vishi 2026-10-30 with defaults below.

## Intent

Vishi hates how LLMs formulate things. VishLang turns a pile of his own raw
writing exports into a small language model that runs on his Mac and rewrites
any text into his voice. Claude Code (and any other MCP client) calls it as a
tool: agent drafts the email, VishLang rephrases it, Vishi gets text that
sounds like him.

v0 captures ONE tone. Vishi tries it on real drafts and says whether it is good.
Everything else (multiple tones, register classifier, UI, Instinct) waits on
that verdict.

## Goals

1. Manual upload: Vishi drops export files into a folder. No UI.
2. Ingest five source formats (v0): WhatsApp chat `.txt`, Gmail Takeout `.mbox`
   (Sent mail), Google Docs exported as `.txt` or `.md`, ChatGPT
   `conversations.json`, LinkedIn `Shares.csv`.
3. Clean: keep only text Vishi wrote, strip noise, drop AI-smelling passages,
   dedupe. Output a corpus of his paragraphs with source and language tags.
4. Build (neutral, vishi) training pairs by back-translation, fine-tune a small
   model locally with LoRA, produce an adapter.
5. Serve a local MCP server with one tool, `rewrite(text)`, plus a Claude Code
   skill that tells Claude when to call it.
6. Blind test so Vishi can judge quality without guessing.
7. Publish: the tool as a public GitHub repo (matches his other projects).

## Non-goals (v0)

- Web UI, "Language Profile" page. Folder is the UI.
- Multiple tones or a professional/casual classifier. Later, if v0 passes.
- Live Gmail API, Instinct integration, Wispr Flow (no sample export yet).
- Cloud anything. No API keys needed to run.
- `.docx` parsing. Export Docs as `.txt`/`.md` instead.

## Anti-goals (failure even if it "works")

- Any of Vishi's data leaves the machine.
- Rewrite changes meaning, drops facts, invents facts.
- Model trained on other people's messages (WhatsApp counterparts, email senders).
- Model trained on text Vishi pasted from ChatGPT/Claude: that would teach the
  LLM voice back in.

## Constraints

- Hardware: Apple M5, 24 GB unified memory, ~150 GB free disk, macOS.
- Toolchain: Python 3.12, `uv`, `mlx-lm` for train and inference. No PyTorch.
- Base model: `mlx-community/Qwen3-4B-Instruct-2507-4bit` (QLoRA). 4B is the
  smallest size prior work found faithful for content-preserving rewrite; 4-bit
  keeps training under ~10 GB. Builder may fall back to Qwen3-1.7B if memory
  fails, and must say so.
- Corpus is bilingual (German/English likely). Keep both. Tag language per
  paragraph. `rewrite` preserves the input language.

## Decisions already made (Vishi's, or my call where marked)

**Data flow** (my call on structure):

```
data/raw/<anything>        drop exports here, any filename, nested ok
  -> vishlang ingest       data/corpus.jsonl   {text, source, lang, ai_score}
  -> vishlang pairs        data/pairs/train.jsonl, valid.jsonl, test.jsonl
  -> vishlang train        adapters/<timestamp>/   (+ symlink adapters/latest)
  -> vishlang serve        MCP stdio server, tool rewrite(text)
  -> vishlang test         blind A/B in the terminal + AI-score report
```

**Source weighting** (my call after builder check): v0 tone is "prose Vishi
writes to humans". Email, Docs, LinkedIn, merged WhatsApp paragraphs count.
ChatGPT user turns are parsed and tagged but weight 0 by default: they are
instructions to a bot and often contain pasted third-party or AI text.
Per-source weight and a per-source `after`/`before` date cutoff live in
`vishlang.toml`. Date cutoff exists because the heuristic detector will not
catch lightly edited LLM email; dropping everything after the date Vishi
started drafting with LLMs is the strong filter.

**Ingest rules.** Format detected by extension plus a sniff of the first lines.
Author name/email list is a config value (`vishlang.toml`), used to pick
Vishi's lines in WhatsApp, Vishi's `From:` in mbox, `role == "user"` in
ChatGPT. Everything else is discarded, never stored.

**Cleaning rules** (my call, builder refines):
- Drop quoted replies, signatures, forwarded blocks in email.
- Drop lines that are mostly URLs, media placeholders (`<Media omitted>`),
  system messages.
- Merge consecutive WhatsApp messages from Vishi within 2 minutes into one
  paragraph so the model sees paragraphs, not fragments.
- Drop paragraphs under 8 words. Dedupe exact and near-exact (normalised).
- Drop paragraphs whose AI score exceeds a threshold (default 0.5).
- Hold out 10% of paragraphs as test set before pair generation.

**AI detector** (my call): heuristic, no model. Reuse the Kobak et al. excess
vocabulary list and scorer already on this machine at
`~/.claude/skills/strip-ai-tells/reference/` (copy the CSV into the repo),
plus em-dash density, rule-of-three frequency, and low burstiness. Returns
0..1. `ponytail:` ceiling is heuristic precision; upgrade path is a small
classifier if the blind test shows LLM text leaking through.

**Pair generation** (my call, this is the core method): for each corpus
paragraph, the base model rewrites it into generic polished assistant
register ("neutralise": keep every fact, change only style). Training pair is
`(neutral -> original)`. This is inverse-transfer data augmentation
(Shao et al. 2024; Liu et al. 2026 round-trip variant). Runs locally with
`mlx-lm`, overnight is fine. Target 3k to 10k pairs. Chat-format JSONL with a
fixed short system prompt.

**Training** (my call): `mlx_lm.lora` CLI, no custom loop. Start rank 16,
lr 1e-4, ~1000 iterations, batch 2 to 4, evaluate on `valid.jsonl`. Adapter
saved, never fused (keeps base model shared and swap cheap).

**Serving** (Vishi: MCP or skill; my call: both):
- MCP stdio server via the Python `mcp` SDK. Tool `rewrite(text: str) -> str`.
  Loads base + adapter once. `--mode fewshot` flag serves the step-0 baseline
  (base model, 20 random corpus paragraphs as examples, no adapter).
- Claude Code skill `skill/SKILL.md`: "when drafting text Vishi will send or
  publish (email, message, post, docs), call `rewrite` before showing it."
- Registration: one `claude mcp add` line printed by `vishlang serve --print-config`.

**Step 0 before training** (my call, from ponytail rung 1): run the blind test
with `--mode fewshot` first. If few-shot already passes, training is optional.

**Blind test** (my call, revised after builder check): 20 held-out
paragraphs. Showing the real original would let Vishi recognise his own text
from memory, not from voice. So for each item show `neutral` (LLM register) and
`rewrite(neutral)` in random order; Vishi picks "which sounds more like me".
Pass = rewrite picked in at least 15 of 20 AND mean AI score drops. Same
criterion for step 0 (few-shot) and for the trained adapter. Also report mean
length ratio rewrite/neutral as a cheap meaning-drift signal.

**Serve-time input shape** (my call): `rewrite` receives whole drafts
(subject line, greeting, bullets, markdown). Server splits into text blocks,
passes structural lines (subject, greeting, sign-off, list markers, headings,
code) through untouched, rewrites each prose block separately, reassembles.
Keeps inference in-distribution with 1 to 3 paragraph training examples and
limits fact loss to one block at a time.

**Publish** (Vishi said "publish the result"; my call on what): the tool goes
public as `VishiATChoudhary/vishlang`, added as a submodule in shennies.
Adapter weights and `data/` are gitignored and stay private by default.
Flipping to publish the adapter is a one-line README step later.

## Layout

```
vishlang/
  pyproject.toml          deps: mlx-lm, mcp. Nothing else.
  vishlang.toml           author names/emails, thresholds, base model id
  vishlang/
    ingest.py             five parsers + detection
    clean.py              rules above + AI detector
    pairs.py              neutralise with base model, write JSONL splits
    train.py              thin wrapper around mlx_lm.lora
    serve.py              MCP server, fewshot and lora modes
    test.py               blind A/B
    cli.py                vishlang ingest|pairs|train|serve|test|build
  skill/SKILL.md
  data/                   gitignored
  adapters/               gitignored
  docs/superpowers/specs/ this file
```

`vishlang build` = ingest, pairs, train in sequence.

## Left to the builder

- Exact regexes per format (WhatsApp export has several date formats by
  locale; mbox needs `email` stdlib + quote stripping).
- Neutralisation prompt wording. Must be checked on 20 samples by eye before
  the full run.
- Chunking of long docs (target 1 to 3 paragraphs per training example).
- Hyperparameter tuning if valid loss plateaus.
- One runnable self-check per non-trivial module (parsers, detector, pair
  writer), assert-based, no framework.

## Resolved defaults (Vishi said "build that shape")

1. v0 tone: prose to humans (see Source weighting).
2. LLM date cutoff: config field `before = ""` per source, off by default.
   README tells Vishi to set it to the month he started drafting with LLMs.
3. Exports not in hand. Builder ships with small synthetic fixtures per format
   under `tests/fixtures/` and the README lists how to export each source.
