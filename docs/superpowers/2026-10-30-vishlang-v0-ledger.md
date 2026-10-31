# SDD ledger — plan: docs/superpowers/plans/2026-10-30-vishlang-v0.md
Spec: docs/superpowers/specs/2026-10-30-vishlang-design.md (read)
Setup: Ruling: `git init` in vishlang/ moved from Task 1 step 1 to setup, docs committed first — SDD scripts need a git root — cost if wrong: none, same end state
Pre-flight (shared interfaces):
- T1 load_config -> T4/T5/T7/T8 consume cfg["sources"][s]["weight"|"before"], cfg["model"]["base"], cfg["clean"][*]: keys match T1 defaults. clean
- T3 Para/detect_format/read_text -> T4/T5: positional Para(text, source, date) used consistently. clean
- T2 ai_score -> T5 clean, T10 blind: float 0..1. clean
- T5 read_jsonl/write_jsonl (clean.py) -> T7/T9/T10/T11. clean
- T6 LM/FakeLM.chat(system, user, max_tokens, temp), prompts -> T7/T9/T10: T10 FakeLM keys on "generic AI assistant" which is in NEUTRALISE_SYSTEM. clean
- T7 neutralise(lm, text), build_pairs(corpus, out_dir, lm, cfg) -> T10/T11: same arg order. clean
- T9 rewrite_text(lm, text, system) -> T10. clean
- T5 cli main(argv) global --config before subcommand: T5 test fixed to that order, T9 test_print_config uses default vishlang.toml, T11 puts --config first. clean
- T4 creates cfg.toml and cfg_all.toml; T5/T7/T8/T11 consume. clean
Task 1: complete (commits 5a761a3..0f1a238, tests: uv run pytest tests/test_config.py -q → 1 passed in 4.68s)
Task 2: complete (commits 0f1a238..e44ad9c, tests: uv run pytest tests/test_detect.py -q → 5 passed in 0.01s)
Task 3: complete (commits e44ad9c..2027677, tests: uv run pytest tests/test_ingest_text.py -q → 5 passed in 0.01s)
Task 4: complete (commits 2027677..1f70ea2, tests: uv run pytest tests/test_ingest_mail.py -q → 4 passed in 0.01s)
Task 5: complete (commits 1f70ea2..0e97b23, tests: uv run pytest tests/test_clean.py -q → 8 passed in 0.01s)
Task 13: Ruling: added Claude Code prompt-history source mid-run — Vishi asked for his agent prompts as voice data; parse_claude drops tool results, sidechains, slash wrappers, strips harness tags — cost if wrong: corpus skews to short imperative prompts, fixable via weight
Task 13: complete (commits 0e97b23..473ce84, tests: uv run pytest tests/test_ingest_claude.py -q → 3 passed in 0.01s)
Task 13: Ruling: claude path root accepts only .jsonl session files — ~/.claude/projects also holds Claude-written memory .md that leaked in as docs — cost if wrong: none, raw/ still accepts any format; suite was red after first Task 13 commit, fixed here (fixtures set claude path='')
Task 13: Ruling: added template-prefix rule (8-word prefix repeated >5x) in clean and harness prefix drop in parse_claude — real corpus showed programmatic eval prompts and hook output — cost if wrong: a human who starts many messages identically loses those
Task 6: complete (commits 10dda07..b3c7443, tests: uv run pytest tests/test_llm.py -q → 4 passed, 1 skipped in 0.01s)
Task 7: complete (commits b3c7443..c566b2d, tests: uv run pytest tests/test_pairs.py -q → 6 passed in 0.03s)
Task 8: complete (commits c566b2d..7bd3461, tests: uv run pytest tests/test_train.py -q → 2 passed in 0.01s)
Task 9: Ruling: mcp.server.fastmcp.FastMCP -> mcp.server.mcpserver.MCPServer — installed mcp is 2.x, FastMCP renamed upstream — cost if wrong: none, same API surface (tool/run/list_tools)
Task 9+10: Ruling: one commit for both — cli.py changes interleaved after parallel RED tests — cost if wrong: coarser bisect
Task 9: complete (commits 7bd3461..7283220, tests: uv run pytest tests/test_serve.py -q → 8 passed in 0.21s)
Task 10: complete (commits 7bd3461..7283220, tests: uv run pytest tests/test_blind.py -q → 3 passed in 0.01s)
Task 11: complete (commits 7283220..a4bcc7e, tests: uv run pytest -q → 55 passed, 1 skipped in 0.27s)
Final review: fresh reviewer (fable), Needs work -> fix pass below, suite 64 passed 1 skipped
Final: fixed lexicon CSV gitignored — test_lexicon_is_tracked_by_git RED→GREEN, suite 64/64
Final: fixed claude history leaks (isMeta, compact summaries, teammate msgs, goal check-ins, [Image] tokens, 4-word templates) — test_parse_claude_drops_meta_compact_teammate_goal_and_strips_image_tokens + test_clean_drops_scripted_prompts_with_varying_entity_in_prefix RED→GREEN
Final: fixed wrapped reply header and forwarded block kept in mbox — test_mbox_cuts_wrapped_reply_header_and_forwarded_block RED→GREEN
Final: fixed mask_prompt missing — test_train_config_values RED→GREEN
Final: fixed blind test neutralising with the adapter — test_run_blind_neutralises_with_base_lm_when_given RED→GREEN
Final: fixed neutral token budget and truncated/runaway pairs — test_neutralise_budget_scales_with_length + test_build_pairs_skips_truncated_or_runaway_neutrals RED→GREEN
Final: fixed greeting/sign-off/signature in training targets — test_clean_trims_greeting_signoff_and_signature_from_email RED→GREEN
Final: fixed (regraded Minor->Important) partial cache line crashes overnight rerun — test_build_pairs_survives_partial_cache_line RED→GREEN
Final: minor (deferred): serve._is_prose greeting rule unreachable; 7-10 word sign-offs get rewritten
Final: minor (deferred): clean_output preamble regex can eat a legitimate "Here is what I think:" opener; unclosed <think> not stripped
Final: minor (deferred): python -m mlx_lm.lora prints a deprecation notice (still runs)
Final: minor (deferred): blind pass uses <= not <; sub-8-word neutrals show two identical options
Final: minor (deferred): serve --mode lora before training gives a raw traceback instead of "run vishlang train first"
Final: minor (deferred): WhatsApp merge glues Vishi's messages across a counterpart's reply within the window
Final: Ruling: shared Synapse workspace sessions may hold other people's typing — no typist field exists in the jsonl; Vishi can set weight/path or delete those project dirs — cost if wrong: a few foreign prompts in corpus
Final: Ruling: US-locale WhatsApp dates (MM/DD) parse wrong — user is DE/EN, `before` off by default — cost if wrong: date filter misfires on US exports
Final: Ruling: Slack-style single-newline drafts with a bullet line pass through unrewritten — plan defines blank-line blocks — cost if wrong: some drafts come back unchanged
Final: Ruling: template rule may drop genuine repeated openers — accepted earlier — cost if wrong: small corpus loss
Final: Ruling: mcp_add_command unquoted path — no spaces in Vishi's path — cost if wrong: one quoting fix
Final: Ruling: hashtag line makes a whole LinkedIn block non-prose — depends on drafting agent's formatting — cost if wrong: posts with inline hashtags not rewritten
Final: Ruling: set MLX_METAL_GPU_ARCH=applegpu_g16g at import on M5 + macOS <26.2 — mlx#4525, wheel targets 26.2, NAX kernels fail to compile on 26.1; upstream says update macOS — cost if wrong: slower inference until Vishi updates macOS; env var respected if user sets it
Final: fixed neutraliser answered instruction-like prompts and left short ones unchanged — test_neutralise_wraps_text_so_model_rewrites_instead_of_answering + test_usable_pair_rejects_near_identical_neutral RED→GREEN, suite 69/69
Final: fixed scripted prompts with fixed ending escaped template rule — test_clean_drops_scripted_prompts_sharing_a_fixed_ending RED→GREEN
Final: Ruling: neutralise temp 0.3 -> 0.7 and perspective sentence in NEUTRALISE_SYSTEM — short imperative prompts came back near-identical at 0.3; two of eight samples replied/apologised instead of rewriting — cost if wrong: noisier neutrals, caught partly by usable_pair
Task 12: ingest on real Claude Code history: 1625 corpus / 180 holdout after hygiene fixes; pairs --sample reviewed by executor (6/8 clean, then prompt tweak); full pairs run started 2026-10-30 in background (data/pairs.log)
Final: fixed assistant-style replies accepted as neutrals — test_usable_pair_rejects_assistant_replies RED→GREEN, suite 70/70
Final: fixed 'Certainly.' openers in neutrals — test_build_pairs_strips_assistant_filler_openers RED→GREEN, suite 71/71
Task 12: pairs run finished 19:02 (35 min): 1625 neutralised, splits 1252/70/70, 233 rejected (identity, truncated, reply-style)
Task 12: Ruling: train pairs 1252 < 3k target, did NOT raise claude weight to 2 — single source, duplication = extra epoch, 1000 iters x batch 2 already covers ~1.6 epochs — cost if wrong: undertrained adapter, rerun with --iters 2000
Task 12: train started 19:03 in background (data/train.log), adapter -> adapters/latest
Task 12: train finished 19:35 (32 min, 1000 iters), adapters/latest/adapters.safetensors 21 MB
Task 12: sanity rewrite with adapter on 4 holdout + 1 LLM email draft: voice shift clear, facts and structure kept (executor judgement, blind test still Vishi's)
Task 12: skill symlinked to ~/.claude/skills/vishlang; MCP registered at user scope (claude mcp add -s user)
Task 12: Ruling: served adapter stays the final iteration-1000 weights — val loss minimum was at 500 (1.382) but save_every=200 left no 500 checkpoint; 600 (1.513) vs 1000 (1.601) is within noise and the 1000 weights were the ones sanity-checked by eye — cost if wrong: slightly overfit adapter; future runs: --iters 600 or save_every 100
Final review clean after fix pass; workspace archived to docs/superpowers and deleted 2026-10-30
