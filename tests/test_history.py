"""v1.3: `history` — an answer in the first minute, with zero setup.

Installs produced plugin loads and no receipts: nothing useful happened until
/receipt-init, and init is a decision (a key, a hook, files in the repo).
`history` answers "how much of this repo did Claude help write?" from the
commit trailers already in git history. Every "never" below is a test: it
never writes a file, never needs a key, never calls itself evidence, and it
counts AI assistance by the same rule receipts use."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from _shell import shell_argv, posix

PLUGIN = Path(__file__).resolve().parents[1]
RECEIPT = PLUGIN / "core" / "receipt.py"

CLAUDE = "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDECODE" and not k.startswith(("CLAUDE_", "TITAN_RECEIPTS_", "COMMITPROOF_"))}
    env.update(extra)
    return env


def sh(cmd, cwd, env=None):
    r = subprocess.run(shell_argv(cmd), cwd=cwd, capture_output=True, text=True,
                       env=env or clean_env())
    assert r.returncode == 0, r.stderr
    return r.stdout


def run(cwd, *args, env=None):
    return subprocess.run([sys.executable, str(RECEIPT), *args], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8",
                          env=env or clean_env())


def commit(repo: Path, msgdir: Path, name: str, lines: int, message: str,
           author: str = "Dev <dev@example.com>", date: str | None = None):
    (repo / name).write_text("".join(f"line {i}\n" for i in range(lines)))
    msg = msgdir / f"{name}.msg"
    msg.write_text(message)
    who, email = author.split(" <")
    env = clean_env(GIT_AUTHOR_NAME=who, GIT_AUTHOR_EMAIL=email.rstrip(">"),
                    GIT_COMMITTER_NAME=who, GIT_COMMITTER_EMAIL=email.rstrip(">"))
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    sh(f"git add -A && git commit -q -F {posix(msg)}", repo, env)


@pytest.fixture()
def msgdir(tmp_path):
    d = tmp_path / "msgs"   # commit messages live OUTSIDE the repo
    d.mkdir()
    return d


@pytest.fixture()
def repo(tmp_path, msgdir):
    r = tmp_path / "repo"
    r.mkdir()
    sh("git init -q -b main && git config user.email t@t && git config user.name T", r)
    commit(r, msgdir, "human.py", 30, "feat: human work\n",
           author="Hana <hana@example.com>", date="2026-08-03T10:00:00+00:00")
    commit(r, msgdir, "ai.py", 70, f"feat: ai work\n\n{CLAUDE}\n",
           author="Dev <dev@example.com>", date="2026-09-04T10:00:00+00:00")
    return r


def test_counts_commits_and_lines_from_claude_trailers(repo):
    r = run(repo, "history")
    assert r.returncode == 0, r.stderr
    out = r.stdout
    # 2 non-merge commits, 1 with a Claude trailer; 100 lines added, 70 in it
    assert "| 2 |" in out
    assert "1 (50%)" in out
    assert "70 (70%)" in out


def test_writes_nothing_and_needs_no_key(repo):
    before = sh("git status --porcelain --ignored", repo)
    r = run(repo, "history")
    assert r.returncode == 0, r.stderr
    assert sh("git status --porcelain --ignored", repo) == before
    assert not (repo / ".titan").exists()


def test_says_it_is_unsigned_and_offers_receipt_init(repo):
    out = run(repo, "history").stdout
    low = out.lower()
    assert "unsigned" in low and "commit trailers" in low
    assert "/receipt-init" in out
    # it must never present trailer counts as evidence
    assert "not evidence" in low


def test_lowercase_github_style_trailer_counts(repo, msgdir):
    commit(repo, msgdir, "squash.py", 10,
           "fix: squashed\n\nCo-authored-by: Claude <noreply@anthropic.com>\n")
    out = run(repo, "history").stdout
    assert "2 (67%)" in out


def test_claude_session_trailer_counts_and_human_coauthor_does_not(repo, msgdir):
    commit(repo, msgdir, "pair.py", 10,
           "feat: pairing\n\nCo-Authored-By: Jane Doe <jane@example.com>\n")
    commit(repo, msgdir, "sess.py", 10,
           "feat: session\n\nClaude-Session: https://claude.ai/code/session_x\n")
    out = run(repo, "history").stdout
    assert "| 4 |" in out
    assert "2 (50%)" in out


def test_kernel_style_assisted_by_trailer_counts(repo, msgdir):
    """The Linux kernel records AI help as `Assisted-by: AGENT:MODEL`; 1,732
    kernel commits named Claude that way and were counted as 0."""
    commit(repo, msgdir, "k.c", 10, "mm: fix\n\nAssisted-by: Claude:claude-opus-4-6\n"
                                    "Signed-off-by: Dev <dev@example.com>\n")
    commit(repo, msgdir, "k2.c", 10, "mm: other\n\nAssisted-by: coccinelle\n")
    out = run(repo, "history").stdout
    assert "| 4 |" in out and "2 (50%)" in out


def test_by_author_and_by_month(repo):
    out = run(repo, "history").stdout
    assert "## By author" in out and "## By month" in out
    assert "Hana <hana@example.com>" in out
    assert "| 2026-08 | 1 | 0 (0%) |" in out
    assert "| 2026-09 | 1 | 1 (100%) |" in out


def test_merge_commits_are_not_counted(repo, msgdir):
    sh("git checkout -q -b side", repo)
    commit(repo, msgdir, "side.py", 5, "feat: side\n")
    sh("git checkout -q main", repo)
    commit(repo, msgdir, "main2.py", 5, "feat: main2\n")
    sh("git merge -q --no-ff side -m 'Merge side'", repo)
    out = run(repo, "history").stdout
    assert "| 4 |" in out          # 2 + side + main2, the merge excluded


def test_titan_bookkeeping_lines_are_excluded(repo, msgdir):
    (repo / ".titan" / "attestations").mkdir(parents=True)
    (repo / ".titan" / "attestations" / "r.json").write_text("{}\n" * 500)
    sh("git add -A && git commit -qm 'chore: receipts'", repo)
    out = run(repo, "history").stdout
    assert "70 (70%)" in out       # the 500 receipt lines don't dilute the share


def test_json_summary_is_labelled_unsigned(repo):
    r = run(repo, "history", "--json")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert (d["commits"], d["ai_commits"]) == (2, 1)
    assert (d["lines_added"], d["ai_lines_added"]) == (100, 70)
    assert d["basis"] == "commit-trailers" and d["signed"] is False


def test_initialized_repo_points_to_the_signed_report(repo):
    assert run(repo, "init", "--no-git-hook").returncode == 0
    out = run(repo, "history").stdout
    assert "/receipt-report" in out


def test_outside_a_repo_is_a_usage_error(tmp_path):
    lone = tmp_path / "not-a-repo"
    lone.mkdir()
    r = run(lone, "history", env=clean_env(GIT_CEILING_DIRECTORIES=str(tmp_path)))
    assert r.returncode == 2
    assert "not inside a git repository" in r.stderr


def test_repo_without_commits_is_not_an_error(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    sh("git init -q -b main", empty)
    r = run(empty, "history")
    assert r.returncode == 0, r.stderr
    assert "no commits" in r.stdout.lower()


def test_output_is_utf8_even_for_a_non_latin_author(repo, msgdir):
    """On Windows a piped stdout defaulted to cp1252: '—' arrived as invalid
    UTF-8 and an author like 张伟 raised UnicodeEncodeError. Output and the
    report file are UTF-8 on every platform."""
    commit(repo, msgdir, "zh.py", 2, f"feat: zh\n\n{CLAUDE}\n", author="张伟 <zw@example.com>")
    env = {k: v for k, v in clean_env().items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    r = subprocess.run([sys.executable, str(RECEIPT), "history"], cwd=repo,
                       capture_output=True, env=env)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert "张伟".encode() in r.stdout and "—".encode() in r.stdout
    assert run(repo, "init", "--no-git-hook").returncode == 0
    assert run(repo, "create").returncode == 0
    out = repo.parent / "report.md"
    r = subprocess.run([sys.executable, str(RECEIPT), "report", "--out", str(out)],
                       cwd=repo, capture_output=True, env=env)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert "张伟" in out.read_text(encoding="utf-8")


def test_receipts_use_the_same_case_insensitive_trailer_rule(repo, msgdir):
    """history and receipts must agree: a lowercase GitHub-style trailer made
    receipts say ai_assisted=false while history counted the commit."""
    assert run(repo, "init", "--no-git-hook").returncode == 0
    commit(repo, msgdir, "lower.py", 3,
           "fix: lower\n\nCo-authored-by: Claude <noreply@anthropic.com>\n")
    r = run(repo, "create")
    assert r.returncode == 0, r.stderr
    receipts = list((repo / ".titan" / "attestations").rglob("*.json"))
    assert len(receipts) == 1
    prov = json.loads(receipts[0].read_text())["provenance"]
    assert prov["ai_assisted"] is True and prov["basis"] == ["commit-trailers"]


def test_receipts_record_and_count_assisted_by(repo, msgdir):
    assert run(repo, "init", "--no-git-hook").returncode == 0
    commit(repo, msgdir, "k.c", 3, "fix: k\n\nAssisted-by: Claude:claude-opus-4-6\n")
    assert run(repo, "create").returncode == 0
    r = json.loads(next((repo / ".titan" / "attestations").rglob("*.json")).read_text())
    assert r["provenance"]["ai_assisted"] is True
    assert r["attribution"]["assisted_by"] == ["Claude:claude-opus-4-6"]
