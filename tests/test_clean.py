import shutil

from vishlang.clean import chunk, clean, detect_lang, normalize, read_jsonl, split_holdout, write_jsonl
from vishlang.cli import main
from vishlang.config import load_config
from vishlang.ingest import Para
from tests.conftest import FIX
from tests.test_detect import HUMAN, LLM


def test_chunk_packs_paragraphs_up_to_max_words():
    text = "\n\n".join(["w " * 60, "w " * 60, "w " * 60])
    out = chunk(text, max_words=150)
    assert len(out) == 2 and all(len(c.split()) <= 150 for c in out)


def test_chunk_keeps_oversized_paragraph_whole():
    assert len(chunk("w " * 400, max_words=150)) == 1


def test_detect_lang():
    assert detect_lang("ich glaube wir sollten das morgen nochmal mit dem team besprechen und dann entscheiden") == "de"
    assert detect_lang("I think we should talk this through with the team tomorrow and then decide") == "en"


def test_normalize_collapses_case_and_punct():
    assert normalize("Hello,  World!") == normalize("hello world")


def test_clean_applies_rules():
    paras = [
        Para("too short here", "docs", ""),
        Para("https://a.com https://b.com https://c.com https://d.com see these links ok thanks", "docs", ""),
        Para(HUMAN, "whatsapp", "2026-01-01T00:00"),
        Para(HUMAN.upper(), "gmail", ""),
        Para(LLM, "gmail", ""),
    ]
    out, stats = clean(paras, load_config(FIX / "cfg.toml"))
    assert [r["source"] for r in out] == ["whatsapp"]
    assert set(out[0]) == {"text", "source", "lang", "ai_score", "date"}
    assert out[0]["lang"] == "en" and out[0]["date"] == "2026-01-01T00:00"
    assert stats == {"min_words": 1, "url_heavy": 1, "dupe": 1, "template": 0, "ai_score": 1}


def test_split_holdout_is_deterministic():
    rows = [{"text": str(i)} for i in range(100)]
    a, b = split_holdout(rows, 0.1, seed=0)
    assert len(b) == 10 and len(a) == 90 and split_holdout(rows, 0.1, seed=0) == (a, b)


def test_jsonl_roundtrip(tmp_path):
    rows = [{"a": 1}, {"b": "ü"}]
    write_jsonl(tmp_path / "x.jsonl", rows)
    assert read_jsonl(tmp_path / "x.jsonl") == rows


def test_cli_ingest_writes_corpus(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for f in ["whatsapp_ios.txt", "doc.md", "Shares.csv", "sent.mbox"]:
        shutil.copy(FIX / f, raw / f)
    rc = main(["--config", str(FIX / "cfg_all.toml"), "ingest", "--raw", str(raw), "--out", str(tmp_path / "d")])
    assert rc == 0
    assert (tmp_path / "d" / "corpus.jsonl").exists() and (tmp_path / "d" / "holdout.jsonl").exists()
    assert read_jsonl(tmp_path / "d" / "corpus.jsonl")


def test_clean_drops_templated_prompts_sharing_a_long_prefix():
    tpl = "These entity mentions may or may not refer to the same real thing, here is the list:"
    paras = [Para(f"{tpl} item {i} with some more words to pass the minimum", "claude", "") for i in range(6)]
    paras.append(Para(HUMAN, "claude", ""))
    out, stats = clean(paras, load_config(FIX / "cfg.toml"))
    assert [r["text"] for r in out] == [HUMAN] and stats["template"] == 6


def test_clean_drops_scripted_prompts_with_varying_entity_in_prefix():
    paras = [Para(f"You previously concluded: entity {i} equals entity {i} in some cancer type, the evidence is now exactly this", "claude", "") for i in range(12)]
    paras.append(Para(HUMAN, "claude", ""))
    out, stats = clean(paras, load_config(FIX / "cfg.toml"))
    assert [r["text"] for r in out] == [HUMAN] and stats["template"] == 12


def test_clean_trims_greeting_signoff_and_signature_from_email():
    body = "Thanks for the notes, I went through them on the train and most of it is already handled by the merge window."
    mail = f"Hi Anna,\n\n{body}\n\nBest,\nVishi\nInvertix GmbH\n+49 170 0000000\nwww.invertix.ai"
    out, _ = clean([Para(mail, "gmail", "")], load_config(FIX / "cfg.toml"))
    assert [r["text"] for r in out] == [body]


def test_clean_drops_scripted_prompts_sharing_a_fixed_ending():
    tail = "Would you still conclude it, from this evidence alone? Answer with one word, YES or NO. Do not explain."
    paras = [Para(f"Case {i} cites case {i+1} as precedent and the evidence is now exactly this. {tail}", "claude", "") for i in range(12)]
    paras.append(Para(HUMAN, "claude", ""))
    out, stats = clean(paras, load_config(FIX / "cfg.toml"))
    assert [r["text"] for r in out] == [HUMAN] and stats["template"] == 12
