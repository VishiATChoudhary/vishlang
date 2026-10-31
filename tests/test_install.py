from pathlib import Path

from vishlang.install import install, skill_source


def test_skill_source_is_the_repo_skill():
    src = skill_source()
    assert (src / "SKILL.md").read_text().startswith("---\nname: vishlang\n")


def test_install_copies_skill_and_registers_both_clis(tmp_path):
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)

        class R:
            returncode = 0
        return R()

    lines = install(claude_skills=tmp_path / "c", agents_skills=tmp_path / "a",
                    which=lambda x: f"/bin/{x}" if x in ("claude", "codex", "vishlang") else None, run=run)
    assert (tmp_path / "c" / "vishlang" / "SKILL.md").exists()
    assert (tmp_path / "a" / "vishlang" / "SKILL.md").exists()
    assert ["/bin/claude", "mcp", "remove", "-s", "user", "vishlang"] in calls
    assert ["/bin/claude", "mcp", "add", "-s", "user", "vishlang", "--", "/bin/vishlang", "serve"] in calls
    assert ["/bin/codex", "mcp", "remove", "vishlang"] in calls
    assert ["/bin/codex", "mcp", "add", "vishlang", "--", "/bin/vishlang", "serve"] in calls
    assert any("claude" in l for l in lines) and any("codex" in l for l in lines)


def test_install_skips_missing_clis_and_replaces_old_symlink(tmp_path):
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "vishlang").symlink_to(tmp_path / "nowhere")
    calls = []
    lines = install(claude_skills=tmp_path / "c", agents_skills=tmp_path / "a",
                    which=lambda x: None, run=lambda cmd, **kw: calls.append(cmd))
    assert (tmp_path / "c" / "vishlang" / "SKILL.md").is_file()
    assert not (tmp_path / "c" / "vishlang").is_symlink()
    assert calls == []
    assert any("not found" in l for l in lines)
