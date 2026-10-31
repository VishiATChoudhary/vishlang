import io

from vishlang import cli
from vishlang.llm import FakeLM


def _fake(*a, **k):
    return FakeLM(lambda system, user: user.upper())


def test_rewrite_takes_text_argument(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_lm", _fake)
    assert cli.main(["--config", "tests/fixtures/cfg.toml", "rewrite", "hello there friend, can you look at the parser bug today."]) == 0
    assert capsys.readouterr().out.strip() == "HELLO THERE FRIEND, CAN YOU LOOK AT THE PARSER BUG TODAY."


def test_rewrite_reads_stdin_when_no_text(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_lm", _fake)
    monkeypatch.setattr("sys.stdin", io.StringIO("from stdin please, this one is long enough to count as prose.\n"))
    assert cli.main(["--config", "tests/fixtures/cfg.toml", "rewrite"]) == 0
    assert capsys.readouterr().out.strip() == "FROM STDIN PLEASE, THIS ONE IS LONG ENOUGH TO COUNT AS PROSE."
