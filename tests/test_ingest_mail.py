import shutil

from vishlang.config import load_config
from vishlang.ingest import ingest_dir, parse_chatgpt, parse_mbox
from tests.conftest import FIX


def test_mbox_keeps_own_plain_text_strips_quotes_and_signature():
    paras = parse_mbox(FIX / "sent.mbox", {"vishisht@invertix.ai"})
    texts = [p.text for p in paras]
    assert len(texts) == 4
    assert "wrote:" not in texts[0] and ">" not in texts[0] and "-- " not in texts[0]
    assert "Invertix" not in texts[0] and texts[0].startswith("Thanks for the notes")
    assert paras[0].source == "gmail" and paras[0].date.startswith("2026-10")


def test_mbox_html_only_body_is_stripped_to_text():
    paras = parse_mbox(FIX / "sent.mbox", {"vishisht@invertix.ai"})
    assert "Thanks for the notes on the parser" in paras[1].text and "<p>" not in paras[1].text


def test_chatgpt_user_turns_only():
    paras = parse_chatgpt(FIX / "conversations.json")
    assert len(paras) == 1 and paras[0].text.startswith("please rewrite") and paras[0].source == "chatgpt"
    assert paras[0].date.startswith("2023-11")


def test_ingest_dir_applies_weight_zero_and_before(tmp_path):
    (tmp_path / "raw").mkdir()
    for f in ["whatsapp_ios.txt", "conversations.json", "Shares.csv"]:
        shutil.copy(FIX / f, tmp_path / "raw" / f)
    cfg = load_config(FIX / "cfg.toml")
    paras = ingest_dir(tmp_path / "raw", cfg)
    assert {p.source for p in paras} == {"linkedin"}


def test_mbox_cuts_wrapped_reply_header_and_forwarded_block():
    paras = parse_mbox(FIX / "sent.mbox", {"vishisht@invertix.ai"})
    wrapped = next(p.text for p in paras if p.text.startswith("Short answer is yes"))
    assert "Mustermann" not in wrapped and "anna@x.com" not in wrapped and "wrote:" not in wrapped
    fwd = next(p.text for p in paras if p.text.startswith("Forwarding this"))
    assert "Carol" not in fwd and "Forwarded message" not in fwd
