"""vishlang command line: ingest | pairs | train | serve | test | build."""
import argparse
from collections import Counter
from pathlib import Path

from .config import load_config


def _ingest(args, cfg) -> int:
    from .clean import clean, split_holdout, write_jsonl
    from .ingest import ingest_dir

    paras = ingest_dir(Path(args.raw), cfg)
    records, stats = clean(paras, cfg)
    train, hold = split_holdout(records, cfg["clean"]["holdout"])
    out = Path(args.out)
    write_jsonl(out / "corpus.jsonl", train)
    write_jsonl(out / "holdout.jsonl", hold)
    by_src = Counter(r["source"] for r in records)
    print(f"parsed {len(paras)} paragraphs from {args.raw}")
    for src, n in sorted(by_src.items()):
        print(f"  {src:10s} {n}")
    print("dropped: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
    print(f"corpus {len(train)} -> {out / 'corpus.jsonl'}   holdout {len(hold)} -> {out / 'holdout.jsonl'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="vishlang")
    ap.add_argument("--config", default="vishlang.toml")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest", help="parse data/raw into data/corpus.jsonl")
    p.add_argument("--raw", default="data/raw")
    p.add_argument("--out", default="data")
    p.set_defaults(fn=_ingest)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    return args.fn(args, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
