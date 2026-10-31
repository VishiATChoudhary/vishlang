from vishlang.ingest import detect_format, parse_docs, parse_linkedin, parse_whatsapp
from tests.conftest import FIX


def test_whatsapp_ios_merges_within_window_and_drops_others():
    paras = parse_whatsapp(FIX / "whatsapp_ios.txt", {"Vishi"}, merge_minutes=2)
    assert [p.text for p in paras] == [
        "ok so the plan is we ship the parser first\nthen the detector, then we look at the data together",
        "unrelated later message about dinner plans tonight",
    ]
    assert paras[0].date == "2026-10-30T14:03"
    assert all(p.source == "whatsapp" for p in paras)


def test_whatsapp_android_continuation_and_media(tmp_path):
    src = (FIX / "whatsapp_android.txt").read_bytes().replace(b"\n", b"\r\n")
    p = tmp_path / "wa.txt"
    p.write_bytes(b"\xef\xbb\xbf" + src)  # BOM + CRLF
    paras = parse_whatsapp(p, {"Vishi"})
    assert [x.text for x in paras] == ["first line of a long message\nthat continues on the next line without a prefix"]


def test_docs_single_para_per_file():
    paras = parse_docs(FIX / "doc.md")
    assert len(paras) == 1 and paras[0].source == "docs" and "\n\n" in paras[0].text


def test_linkedin_skips_empty_commentary():
    paras = parse_linkedin(FIX / "Shares.csv")
    assert len(paras) == 1 and paras[0].source == "linkedin" and paras[0].date.startswith("20")


def test_detect_format():
    assert detect_format(FIX / "whatsapp_ios.txt") == "whatsapp"
    assert detect_format(FIX / "whatsapp_android.txt") == "whatsapp"
    assert detect_format(FIX / "doc.md") == "docs"
    assert detect_format(FIX / "Shares.csv") == "linkedin"
    assert detect_format(FIX / "nothing.xyz") is None
