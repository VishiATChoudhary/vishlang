"""vishlang command line: init | profiles | ingest | pairs | train | test | rewrite | serve | install | build."""
import argparse
import os
from collections import Counter
from pathlib import Path

from .config import load_config
from .paths import Profile, home, valid_name

PROFILE_TOML = '''[author]
names = [{names}]    # display names as they appear in WhatsApp exports
emails = [{emails}]  # From: addresses in Gmail Takeout

[model]
base = "mlx-community/Qwen3-4B-Instruct-2507-4bit"

[clean]
min_words = 8
ai_threshold = 0.5
merge_minutes = 2
holdout = 0.1

# weight 0 excludes a source. weight >= 1 repeats its examples round(weight) times in training.
# before = "YYYY-MM" drops anything written on or after that month (when you started drafting with LLMs).
[sources.whatsapp]
weight = 1.0
before = ""
[sources.gmail]
weight = 1.0
before = ""
[sources.docs]
weight = 1.0
before = ""
[sources.linkedin]
weight = 1.0
before = ""
[sources.chatgpt]
weight = 0.0
before = ""
# Prompts you typed into Claude Code and Codex. Set path = "" to disable one.
[sources.claude]
weight = 1.0
before = ""
path = "~/.claude/projects"
[sources.codex]
weight = 1.0
before = ""
path = "~/.codex/sessions"
'''


def _q(items: list[str]) -> str:
    return ", ".join(f'"{x}"' for x in items)


def _init(args, cfg, prof: Profile) -> int:
    prof = Profile.load(args.name or prof.name)
    prof.raw.mkdir(parents=True, exist_ok=True)
    if not prof.toml.exists():
        prof.toml.write_text(PROFILE_TOML.format(names=_q(args.author_name), emails=_q(args.email)))
    print(f"profile {prof.name!r} at {prof.dir}")
    print(f"  config  {prof.toml}")
    print(f"  drop WhatsApp / Gmail Takeout / Docs / LinkedIn / ChatGPT exports in {prof.raw}")
    print(f"  Claude Code and Codex prompt history are picked up automatically")
    print(f"next: vishlang --profile {prof.name} build")
    return 0


def _profiles(args, cfg, prof: Profile) -> int:
    root = home() / "profiles"
    names = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    if not names:
        print(f"no profiles under {root}; run `vishlang init`")
        return 0
    print(f"{'profile':16} {'corpus':>7} {'trained':>8}")
    for n in names:
        p = Profile.load(n)
        print(f"{n:16} {p.corpus_size:7d} {'yes' if p.trained else 'no':>8}")
    return 0


def _ingest(args, cfg, prof: Profile) -> int:
    from .clean import clean, split_holdout, write_jsonl
    from .ingest import ingest_dir

    raw = Path(args.raw or prof.raw)
    out = Path(args.out or prof.data)
    paras = ingest_dir(raw, cfg)
    records, stats = clean(paras, cfg)
    train, hold = split_holdout(records, cfg["clean"]["holdout"])
    write_jsonl(out / "corpus.jsonl", train)
    write_jsonl(out / "holdout.jsonl", hold)
    by_src = Counter(r["source"] for r in records)
    print(f"parsed {len(paras)} paragraphs from {raw}")
    for src, n in sorted(by_src.items()):
        print(f"  {src:10s} {n}")
    print("dropped: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
    print(f"corpus {len(train)} -> {out / 'corpus.jsonl'}   holdout {len(hold)} -> {out / 'holdout.jsonl'}")
    return 0


def _lm(cfg, adapter: str | None = None):
    from .llm import LM

    return LM(cfg["model"]["base"], adapter)


def _adapter(args, prof: Profile) -> str | None:
    if getattr(args, "mode", "lora") != "lora":
        return None
    return args.adapter or str(prof.latest)


def _pairs(args, cfg, prof: Profile) -> int:
    import random

    from .clean import read_jsonl
    from .pairs import build_pairs, neutralise

    corpus = Path(args.corpus or prof.corpus)
    lm = _lm(cfg)
    if args.sample:
        rows = read_jsonl(corpus)
        for r in random.Random(0).sample(rows, min(args.sample, len(rows))):
            print("ORIGINAL:", r["text"])
            print("NEUTRAL :", neutralise(lm, r["text"]))
            print("-" * 72)
        return 0
    counts = build_pairs(corpus, Path(args.out or prof.pairs), lm, cfg, limit=args.limit)
    print(" ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


def _train(args, cfg, prof: Profile) -> int:
    from .train import train

    out = train(cfg, Path(args.data or prof.pairs), Path(args.adapters or prof.adapters), iters=args.iters)
    print(f"adapter -> {out}  ({prof.latest} points here)")
    return 0


def _serve(args, cfg, prof: Profile) -> int:
    from .serve import ProfileRouter, build_system, make_server, mcp_add_command

    if args.print_config:
        print(mcp_add_command())
        return 0

    def load(name: str):
        p = Profile.load(name)
        if args.mode == "lora" and not p.trained:
            return None
        return _lm(p.config, str(p.latest) if args.mode == "lora" else None), build_system(args.mode, p.corpus)

    make_server(ProfileRouter(load, default=prof.name)).run()
    return 0


def _test(args, cfg, prof: Profile) -> int:
    from .blind import report, run_blind
    from .clean import read_jsonl
    from .serve import build_system

    adapter = _adapter(args, prof)
    holdout = Path(args.holdout or prof.holdout)
    hold = read_jsonl(holdout) if holdout.exists() else []
    if not hold:
        print(f"no holdout at {holdout}; run `vishlang ingest` first")
        return 1
    lm = _lm(cfg, adapter)
    base_lm = _lm(cfg) if adapter else lm
    r = run_blind(lm, hold, build_system(args.mode, prof.corpus), n=args.n, base_lm=base_lm)
    print(report(r, args.mode))
    return 0 if r["passed"] else 1


def _rewrite(args, cfg, prof: Profile) -> int:
    import sys

    from .serve import build_system, rewrite_text

    text = " ".join(args.text) if args.text else sys.stdin.read()
    print(rewrite_text(_lm(cfg, _adapter(args, prof)), text.strip(), build_system(args.mode, prof.corpus)))
    return 0


def _install(args, cfg, prof: Profile) -> int:
    from .install import install

    for line in install():
        print(line)
    return 0


def _build(args, cfg, prof: Profile) -> int:
    steps = ((_ingest, {"raw": None, "out": None}),
             (_pairs, {"corpus": None, "out": None, "sample": 0, "limit": None}),
             (_train, {"data": None, "adapters": None, "iters": args.iters}))
    for fn, ns in steps:
        rc = fn(argparse.Namespace(**ns), cfg, prof)
        if rc:
            return rc
        if fn is _ingest and prof.corpus_size == 0:
            print(f"corpus is empty, nothing to train on. Drop exports into {prof.raw} "
                  f"or check the source paths in {prof.toml}.")
            return 1
    return 0


def _profile_name(value: str) -> str:
    if not valid_name(value):
        raise argparse.ArgumentTypeError(f"invalid profile name {value!r}: letters, digits, - and _ only")
    return value


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="vishlang")
    ap.add_argument("--profile", type=_profile_name, default=os.environ.get("VISHLANG_PROFILE", "default"),
                    help="tone profile under ~/.vishlang/profiles (default: default)")
    ap.add_argument("--config", default=None, help="override the profile's profile.toml")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create a profile: config + raw drop folder")
    p.add_argument("name", nargs="?", default=None, type=_profile_name)
    p.add_argument("--name", dest="author_name", action="append", default=[], help="your display name (repeatable)")
    p.add_argument("--email", action="append", default=[], help="your sending address (repeatable)")
    p.set_defaults(fn=_init)

    p = sub.add_parser("profiles", help="list profiles and their state")
    p.set_defaults(fn=_profiles)

    p = sub.add_parser("ingest", help="parse raw exports into corpus + holdout")
    p.add_argument("--raw", default=None)
    p.add_argument("--out", default=None)
    p.set_defaults(fn=_ingest)

    p = sub.add_parser("pairs", help="neutralise corpus with the base model, write train/valid/test jsonl")
    p.add_argument("--corpus", default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--sample", type=int, default=0, help="only print N original/neutral pairs to eyeball")
    p.add_argument("--limit", type=int, default=None, help="neutralise at most N new paragraphs this run")
    p.set_defaults(fn=_pairs)

    p = sub.add_parser("train", help="QLoRA fine-tune with mlx_lm.lora")
    p.add_argument("--data", default=None)
    p.add_argument("--adapters", default=None)
    p.add_argument("--iters", type=int, default=1000)
    p.set_defaults(fn=_train)

    p = sub.add_parser("serve", help="run the MCP server (stdio); rewrite(text, profile)")
    p.add_argument("--mode", choices=["lora", "fewshot"], default="lora")
    p.add_argument("--print-config", action="store_true", help="print the claude mcp add command and exit")
    p.set_defaults(fn=_serve)

    p = sub.add_parser("test", help="blind A/B on held-out paragraphs")
    p.add_argument("--mode", choices=["lora", "fewshot"], default="lora")
    p.add_argument("--adapter", default=None)
    p.add_argument("--holdout", default=None)
    p.add_argument("--n", type=int, default=20)
    p.set_defaults(fn=_test)

    p = sub.add_parser("rewrite", help="rewrite text (args or stdin) in your voice, print it")
    p.add_argument("text", nargs="*")
    p.add_argument("--mode", choices=["lora", "fewshot"], default="lora")
    p.add_argument("--adapter", default=None)
    p.set_defaults(fn=_rewrite)

    p = sub.add_parser("install", help="install the skill into Claude Code and Codex, register the MCP server")
    p.set_defaults(fn=_install)

    p = sub.add_parser("build", help="ingest, pairs, train in sequence")
    p.add_argument("--iters", type=int, default=1000)
    p.set_defaults(fn=_build)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    prof = Profile.load(args.profile)
    cfg = load_config(args.config) if args.config else prof.config
    return args.fn(args, cfg, prof)


if __name__ == "__main__":
    raise SystemExit(main())
