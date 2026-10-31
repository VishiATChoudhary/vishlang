# SDD ledger , plan: docs/superpowers/plans/2026-10-31-vishlang-v1.md
Pre-flight: Task 2 consumes Profile from Task 1; Task 4 consumes Profile.load for LM paths; Task 5 consumes mcp_add_command from Task 4. Names fixed in plan.
Task 1: complete (paths.py, tests 77 pass)
Task 3: complete (parse_codex, detect codex vs claude by payload key, suite 81 pass)
Task 2: complete (cli on profiles)
Task 4: complete (ProfileRouter, rewrite(text, profile)); committed with Task 2 because test_print_config spanned both
Ruling: mcp tool param profile defaults to empty string not None, MCP schemas handle str cleanly; cost if wrong: none visible
Ruling: --config kept as override of profile.toml for tests and power users; cost: one extra flag
Task 5: complete (install.py, skills/vishlang/SKILL.md, wheel includes skill; suite 90 pass)
Final review: fresh reviewer (opus), 0 Critical, 6 Important, 8 Minor.
Final: fixed install.sh needs git on a clean Mac: archive URL install verified with uv tool install (no unit test, shell)
Final: fixed PATH not updated for first-time uv users: uv tool update-shell + "open a new terminal" note (shell, no unit test)
Final: fixed empty corpus traceback: test_build_stops_on_empty_corpus_before_loading_model RED->GREEN
Final: fixed latest symlink moved before training: test_latest_only_moves_after_a_successful_run RED->GREEN
Final: fixed profile name path escape (CLI + MCP arg): test_profile_dir_rejects_path_escapes, test_bad_profile_name_is_a_clean_error, test_router_rejects_bad_profile_name_without_loading RED->GREEN
Final: fixed Codex replayed/subagent duplicates: test_parse_codex_dedupes_replayed_prompts_and_drops_json_wrapped_messages, test_parse_codex_skips_subagent_rollouts RED->GREEN
Final: regraded minor 1 (JSON-wrapped app messages, one held a plaintext password) to Important by effect; fixed in the same test ("{" harness prefix)
Final: Ruling: no fewshot fallback for an untrained profile in lora mode, the tool answers with the trained list and the build command. Fewshot would need the base model plus a corpus that may not exist and would pass off untrained output as the user's voice. Spec line amended. Cost if wrong: a user with an untrained profile gets a message instead of a weaker rewrite.
Final: minor (deferred): install.py ignores mcp add return codes, prints registered anyway
Final: minor (deferred): _q does not escape quotes/backslashes in --name/--email
Final: minor (deferred): init on an existing profile ignores new --name/--email silently
Final: minor (deferred): --profile typo creates a new profile on build; only init should create
Final: minor (deferred): serve caches a profile's model for its lifetime; rebuilt adapter needs a session restart
Final: minor (deferred): fewshot with missing corpus yields an example-less prompt without warning
Final: minor (deferred): install.sh checks chip only, not macOS 15+ / 16 GB
Final: minor (deferred): huggingface_hub pings the HF API for the model revision at load even when cached (set HF_HUB_OFFLINE=1 to stop it)
Final: minor (deferred): v0 ledger doc still contains em dashes from the sdd tooling
Suite after fix pass: 97 passed, 1 skipped.
