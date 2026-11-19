"""1.3.3 integrity fixes. Each test here failed on 1.3.2.

- File hashes must describe the COMMITTED content, not whatever sits in the
  working tree when the receipt is written.
- A commit with non-UTF-8 bytes in its diff must still get a receipt.
- Fields the canonical hash skips (_meta, _debug, ...) must not ride along
  unsigned in a change-attestation receipt.
- verify must surface commits with no receipt (including a deleted newest
  receipt) and receipts whose commit is no longer in history.
- The CI action must not write the key through a symlink the audited repo planted.
"""
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from _env import clean_env
from _shell import posix, shell_argv

PLUGIN = Path(__file__).resolve().parents[1]
RECEIPT = PLUGIN / "core" / "receipt.py"


def run(args, cwd):
    return subprocess.run([sys.executable, str(RECEIPT), *args], cwd=cwd,
                          capture_output=True, text=True, env=clean_env())


def sh(cmd, cwd):
    r = subprocess.run(shell_argv(cmd), cwd=cwd, capture_output=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


@pytest.fixture()
def repo(tmp_path):
    sh("git init -q -b main && git config user.email t@t && git config user.name T",
       tmp_path)
    (tmp_path / "a.py").write_text("v1\n")
    sh("git add -A && git commit -qm one", tmp_path)
    assert run(["init", "--no-git-hook"], tmp_path).returncode == 0
    return tmp_path


def receipts(repo):
    return [json.loads(p.read_text())
            for p in sorted((repo / ".titan/attestations").rglob("*.json"))]


def receipt_for(repo, subject):
    return next(r for r in receipts(repo) if r["commit"]["subject"] == subject)


def test_file_hash_is_committed_blob_not_dirty_worktree(repo):
    (repo / "a.py").write_text("v2\n")
    sh("git add a.py && git commit -qm two", repo)
    (repo / "a.py").write_text("UNCOMMITTED EDIT\n")      # dirty at receipt time
    assert run(["create"], repo).returncode == 0
    f = receipt_for(repo, "two")["files"][0]
    assert f["sha256"] == hashlib.sha256(b"v2\n").hexdigest()


def test_file_deleted_from_worktree_still_hashed(repo):
    (repo / "b.py").write_text("bee\n")
    sh("git add b.py && git commit -qm addb", repo)
    (repo / "b.py").unlink()                               # gone before receipt
    assert run(["create"], repo).returncode == 0
    f = receipt_for(repo, "addb")["files"][0]
    assert f["path"] == "b.py"
    assert f["sha256"] == hashlib.sha256(b"bee\n").hexdigest()


def test_partial_staging_hashes_what_was_committed(repo):
    (repo / "a.py").write_text("v1\nstaged\n")
    sh("git add a.py", repo)
    (repo / "a.py").write_text("v1\nstaged\nnot staged\n")
    sh("git commit -qm partial", repo)
    assert run(["create"], repo).returncode == 0
    f = receipt_for(repo, "partial")["files"][0]
    assert f["sha256"] == hashlib.sha256(b"v1\nstaged\n").hexdigest()


def test_non_utf8_content_gets_a_receipt(repo):
    (repo / "latin1.txt").write_bytes(b"caf\xe9\n")
    sh("git add latin1.txt && git commit -qm latin", repo)
    r = run(["create"], repo)
    assert r.returncode == 0, r.stderr
    rec = receipt_for(repo, "latin")
    assert rec["files"][0]["sha256"] == hashlib.sha256(b"caf\xe9\n").hexdigest()
    assert run(["verify"], repo).returncode == 0


def test_external_diff_config_does_not_change_receipt(repo, tmp_path_factory):
    (repo / "a.py").write_text("v2\n")
    sh("git add a.py && git commit -qm two", repo)
    assert run(["create"], repo).returncode == 0
    want = receipt_for(repo, "two")["diff_sha256"]
    # same commit, but a user config that rewrites diff output
    other = tmp_path_factory.mktemp("clone")
    sh(f"git clone -q {posix(repo)} {posix(other / 'c')}", other)
    c = other / "c"
    sh("git config user.email t@t && git config user.name T && "
       "git config color.ui always && git config diff.noprefix true && "
       "git config diff.algorithm histogram && git config diff.context 7", c)
    (c / ".titan").mkdir()
    (c / ".titan/key").write_text((repo / ".titan/key").read_text())
    assert run(["create"], c).returncode == 0
    assert receipt_for(c, "two")["diff_sha256"] == want


def _tamper(repo, edit):
    p = sorted((repo / ".titan/attestations").rglob("*.json"))[0]
    r = json.loads(p.read_text())
    edit(r)
    p.write_text(json.dumps(r, indent=2))


@pytest.mark.parametrize("field", ["_meta", "_debug", "prev_receipt_hash_verified"])
def test_unsigned_field_injection_fails_verify(repo, field):
    assert run(["create"], repo).returncode == 0
    assert run(["verify"], repo).returncode == 0
    _tamper(repo, lambda r: r.__setitem__(field, {"reviewed_by": "security team"}))
    v = run(["verify"], repo)
    assert v.returncode == 1, v.stdout + v.stderr
    assert field in v.stderr


def test_unsigned_field_blocks_extending_the_chain(repo):
    assert run(["create"], repo).returncode == 0
    _tamper(repo, lambda r: r.__setitem__("_meta", "x"))
    (repo / "a.py").write_text("v3\n")
    sh("git add a.py && git commit -qm three", repo)
    r = run(["create"], repo)
    assert r.returncode == 1
    assert len(receipts(repo)) == 1


def test_report_marks_unsigned_field_as_failed(repo):
    assert run(["create"], repo).returncode == 0
    _tamper(repo, lambda r: r.__setitem__("_debug", "x"))
    rep = run(["report", "--badge", "badge.svg"], repo)
    assert "BROKEN" in rep.stdout
    assert "verification FAILED" in (repo / "badge.svg").read_text()


def test_verify_reports_unreceipted_commits_after_tail_deletion(repo):
    assert run(["create"], repo).returncode == 0
    for i in range(2):
        (repo / "a.py").write_text(f"n{i}\n")
        sh(f"git add a.py && git commit -qm n{i}", repo)
        assert run(["create"], repo).returncode == 0
    newest = next(p for p in (repo / ".titan/attestations").rglob("*.json")
                  if json.loads(p.read_text())["commit"]["subject"] == "n1")
    newest.unlink()                         # truncate the chain at the tail
    v = run(["verify"], repo)
    assert v.returncode == 0               # structurally still a valid chain...
    out = v.stdout + v.stderr
    assert "COVERAGE: 2 of 3 commits" in out   # ...but the gap is now visible
    assert "n1" in out


def test_verify_reports_receipts_for_rewritten_history(repo):
    (repo / "a.py").write_text("v2\n")
    sh("git add a.py && git commit -qm two", repo)
    assert run(["create"], repo).returncode == 0
    sh("git commit -q --amend -m two-amended", repo)    # receipted sha leaves history
    out = run(["verify"], repo)
    text = out.stdout + out.stderr
    assert "not in the current history" in text


def test_verify_full_coverage_line(repo):
    assert run(["create"], repo).returncode == 0
    v = run(["verify"], repo)
    assert "COVERAGE: 1 of 1 commits" in v.stdout


def test_action_never_writes_key_through_a_symlink():
    act = (PLUGIN / "action.yml").read_text()
    assert "rm -f .titan/key" in act.split('printf')[0]   # removed BEFORE writing
    assert "umask 077" in act
