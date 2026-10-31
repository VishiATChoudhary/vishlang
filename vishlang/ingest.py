"""Parse raw exports into paragraphs written by the configured author."""
import csv
import email
import email.utils
import html
import json
import mailbox
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


@dataclass
class Para:
    text: str
    source: str
    date: str  # ISO "YYYY-MM-DDTHH:MM" or ""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


# [30.10.26, 14:03:12] Name: msg      (iOS)
# 30/10/2026, 14:03 - Name: msg       (Android)
_WA_LINE = re.compile(
    r"^‎?\[?(?P<d>\d{1,2})[./](?P<m>\d{1,2})[./](?P<y>\d{2,4}),? (?P<H>\d{1,2}):(?P<M>\d{2})(?::\d{2})?\s?(?P<ap>[AaPp][Mm])?\]?(?: -)? (?P<name>[^:]+?): (?P<msg>.*)$"
)
_WA_SKIP = re.compile(
    r"(<Media omitted>|<Medien ausgeschlossen>|\b(image|video|audio|sticker|document|GIF|Contact card) omitted\b|"
    r"Messages and calls are end-to-end encrypted|This message was deleted|You deleted this message|"
    r"Bild weggelassen|Video weggelassen|Nachricht wurde gelöscht)",
    re.I,
)


def _wa_minutes(d: str, m: str, y: str, H: str, M: str, ap: str | None) -> tuple[str, int]:
    year = int(y) + (2000 if len(y) == 2 else 0)
    hour = int(H)
    if ap:
        hour = hour % 12 + (12 if ap.lower() == "pm" else 0)
    iso = f"{year:04d}-{int(m):02d}-{int(d):02d}T{hour:02d}:{int(M):02d}"
    # minute index good enough for merge windows inside one day
    stamp = ((year * 12 + int(m)) * 31 + int(d)) * 1440 + hour * 60 + int(M)
    return iso, stamp


def parse_whatsapp(path: Path, names: set[str], merge_minutes: int = 2) -> list[Para]:
    out: list[Para] = []
    last_stamp: int | None = None
    cur: Para | None = None   # message being built (continuation lines)
    cur_mine = False
    cur_stamp = 0

    def flush():
        nonlocal cur, last_stamp
        if cur is None or not cur_mine:
            cur = None
            return
        text = cur.text.strip()
        if not text or _WA_SKIP.search(text):
            cur = None
            return
        if out and last_stamp is not None and cur_stamp - last_stamp <= merge_minutes:
            out[-1].text += "\n" + text
        else:
            out.append(Para(text, "whatsapp", cur.date))
        last_stamp = cur_stamp
        cur = None

    for line in read_text(path).split("\n"):
        m = _WA_LINE.match(line)
        if m:
            flush()
            name = m.group("name").strip().lstrip("‎")
            iso, stamp = _wa_minutes(m.group("d"), m.group("m"), m.group("y"), m.group("H"), m.group("M"), m.group("ap"))
            cur = Para(m.group("msg").lstrip("‎"), "whatsapp", iso)
            cur_mine = name in names
            cur_stamp = stamp
        elif cur is not None:
            cur.text += "\n" + line
    flush()
    return out


def parse_docs(path: Path) -> list[Para]:
    text = read_text(path).strip()
    return [Para(text, "docs", "")] if text else []


def parse_linkedin(path: Path) -> list[Para]:
    out = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            text = (row.get("ShareCommentary") or "").strip()
            if text:
                out.append(Para(text, "linkedin", (row.get("Date") or "")[:16].replace(" ", "T")))
    return out


def detect_format(path: Path) -> str | None:
    if not path.is_file():
        return None
    suffix = path.suffix.lower()
    if suffix == ".mbox":
        return "gmail"
    if path.name == "conversations.json":
        return "chatgpt"
    if path.name == "Shares.csv":
        return "linkedin"
    if suffix == ".jsonl":
        with path.open(encoding="utf-8", errors="replace") as fh:
            head = fh.readline()
        try:
            return "claude" if isinstance(json.loads(head), dict) and "type" in json.loads(head) else None
        except json.JSONDecodeError:
            return None
    if suffix in (".txt", ".md"):
        head = read_text(path).lstrip().split("\n", 1)[0]
        if suffix == ".txt" and _WA_LINE.match(head):
            return "whatsapp"
        return "docs"
    return None


# ---------------------------------------------------------------- gmail mbox

_CUT = re.compile(
    r"^(On .+wrote:\s*|Am .+schrieb.*:\s*|-- ?|_{5,}|From: .*|Von: .*|Sent from my.*|Gesendet von .*)$"
)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        if tag in ("p", "div", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\n\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _html_to_text(s: str) -> str:
    p = _Text()
    p.feed(s)
    return html.unescape("".join(p.parts))


def _body(msg) -> str:
    plain, rich = None, None
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        ctype = part.get_content_type()
        if ctype not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True) or b""
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if ctype == "text/plain" and plain is None:
            plain = text
        elif ctype == "text/html" and rich is None:
            rich = text
    if plain is not None:
        return plain
    return _html_to_text(rich) if rich is not None else ""


def _strip_reply(body: str) -> str:
    kept = []
    for line in body.replace("\r\n", "\n").split("\n"):
        if _CUT.match(line.strip()):
            break
        if line.lstrip().startswith(">"):
            continue
        kept.append(line.rstrip())
    text = "\n".join(kept)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_mbox(path: Path, emails: set[str]) -> list[Para]:
    emails = {e.lower() for e in emails}
    out = []
    for msg in mailbox.mbox(str(path)):
        sender = email.utils.parseaddr(msg.get("From", ""))[1].lower()
        if sender not in emails or "Draft" in (msg.get("X-Gmail-Labels") or ""):
            continue
        text = _strip_reply(_body(msg))
        if not text:
            continue
        date = ""
        try:
            date = email.utils.parsedate_to_datetime(msg.get("Date", "")).strftime("%Y-%m-%dT%H:%M")
        except (TypeError, ValueError):
            pass
        out.append(Para(text, "gmail", date))
    return out


# ---------------------------------------------------------------- chatgpt
def parse_chatgpt(path: Path) -> list[Para]:
    out = []
    data = json.loads(read_text(path))
    for conv in data if isinstance(data, list) else [data]:
        for node in (conv.get("mapping") or {}).values():
            m = (node or {}).get("message") or {}
            if (m.get("author") or {}).get("role") != "user":
                continue
            content = m.get("content") or {}
            if content.get("content_type") != "text":
                continue
            text = "\n".join(p for p in content.get("parts") or [] if isinstance(p, str)).strip()
            if not text:
                continue
            ts = m.get("create_time")
            date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M") if ts else ""
            out.append(Para(text, "chatgpt", date))
    return out


# ---------------------------------------------------------------- claude code history
_TAG_BLOCKS = re.compile(r"<(system-reminder|pasted_content)\b[^>]*>.*?</\1>", re.S)


def parse_claude(path: Path, max_words: int = 200) -> list[Para]:
    """Prompts Vishi typed into Claude Code. Tool results, subagent sidechains,
    slash-command wrappers and harness notifications (anything starting with a tag)
    are dropped; inline harness tags are stripped; prompts over max_words are
    treated as pasted material, not voice, and dropped."""
    out = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"type":"user"' not in line and '"type": "user"' not in line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") != "user" or o.get("isSidechain"):
                continue
            content = (o.get("message") or {}).get("content")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
                if not parts:
                    continue
                text = "\n".join(parts)
            else:
                continue
            text = _TAG_BLOCKS.sub("", text).strip()
            if not text or text.startswith("<") or len(text.split()) > max_words:
                continue
            out.append(Para(text, "claude", (o.get("timestamp") or "")[:16]))
    return out


# ---------------------------------------------------------------- directory
_PARSERS = {
    "whatsapp": lambda p, cfg: parse_whatsapp(p, set(cfg["author"]["names"]), cfg["clean"]["merge_minutes"]),
    "gmail": lambda p, cfg: parse_mbox(p, set(cfg["author"]["emails"])),
    "docs": lambda p, cfg: parse_docs(p),
    "chatgpt": lambda p, cfg: parse_chatgpt(p),
    "linkedin": lambda p, cfg: parse_linkedin(p),
    "claude": lambda p, cfg: parse_claude(p),
}


def _files(root: Path):
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(root).parts):
            yield path


def ingest_dir(raw: Path, cfg: dict) -> list[Para]:
    out: list[Para] = []
    roots = [(raw, None)]
    claude_path = (cfg["sources"].get("claude") or {}).get("path") or ""
    if claude_path and float(cfg["sources"]["claude"].get("weight", 1.0)) > 0:
        roots.append((Path(claude_path).expanduser(), "claude"))  # only session files from there
    for path, only in ((p, only) for r, only in roots for p in _files(r)):
        fmt = detect_format(path)
        if fmt is None or (only and fmt != only):
            continue
        src = cfg["sources"].get(fmt, {"weight": 1.0, "before": ""})
        if float(src.get("weight", 1.0)) <= 0:
            continue
        before = src.get("before") or ""
        for para in _PARSERS[fmt](path, cfg):
            if before and para.date and para.date >= before:
                continue
            out.append(para)
    return out
