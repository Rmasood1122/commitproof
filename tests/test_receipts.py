"""End-to-end: init -> create -> chain -> verify, plus every tamper path,
in a real throwaway git repo. A receipt system whose tamper cases were
never seen failing is decoration."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from _shell import shell_argv

PLUGIN = Path(__file__).resolve().parents[1]
RECEIPT = PLUGIN / "core" / "receipt.py"


def run(args, cwd, env=None):
    return subprocess.run([sys.executable, str(RECEIPT), *args],
                          cwd=cwd, capture_output=True, text=True, env=env)


def sh(cmd, cwd):
    r = subprocess.run(shell_argv(cmd), cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


@pytest.fixture()
def repo(tmp_path):
    sh("git init -q -b main && git config user.email t@t && git config user.name T",
       tmp_path)
    (tmp_path / "a.py").write_text("print('hi')\n")
    sh("git add -A && git commit -qm 'first change\n\nCo-Authored-By: "
       "Claude <noreply@anthropic.com>\nClaude-Session: https://claude.ai/s/123'",
       tmp_path)
    return tmp_path


def receipts(repo):
    return sorted((repo / ".titan/attestations").rglob("*.json"))


def test_init_creates_gitignored_key(repo):
    r = run(["init"], repo)
    assert r.returncode == 0, r.stderr
    assert (repo / ".titan/key").exists()
    assert ".titan/key" in (repo / ".gitignore").read_text()
    tracked = subprocess.run(["git", "ls-files", ".titan/key"],
                             cwd=repo, capture_output=True, text=True)
    assert tracked.stdout.strip() == ""


def test_init_is_idempotent(repo):
    assert run(["init"], repo).returncode == 0
    key1 = (repo / ".titan/key").read_text()
    assert run(["init"], repo).returncode == 0
    assert (repo / ".titan/key").read_text() == key1  # not rotated silently


def test_create_chain_and_verify_roundtrip(repo):
    run(["init"], repo)
    assert run(["create"], repo).returncode == 0
    r1 = json.loads(receipts(repo)[0].read_text())
    assert r1["schema_version"] == "change-attestation/v1"
    assert r1["prev_receipt_hash"] == "GENESIS"
    assert r1["commit"]["subject"] == "first change"
    assert r1["files"][0]["path"] == "a.py" and "sha256" in r1["files"][0]
    assert r1["attribution"]["session"] == "https://claude.ai/s/123"
    assert r1["attribution"]["co_authored_by"] == ["Claude <noreply@anthropic.com>"]

    (repo / "a.py").write_text("print('bye')\n")
    sh("git add -A && git commit -qm second", repo)
    assert run(["create"], repo).returncode == 0
    rs = [json.loads(p.read_text()) for p in receipts(repo)]
    assert len(rs) == 2
    prevs = {r["prev_receipt_hash"] for r in rs}
    assert "GENESIS" in prevs and r1["receipt_hash"] in prevs  # chained

    v = run(["verify"], repo)
    assert v.returncode == 0, v.stderr
    assert "chain OK: 2" in v.stdout
    assert "does not identify the signer" in v.stdout  # honest limit printed


def test_duplicate_sha_not_rereceipted(repo):
    run(["init"], repo)
    run(["create"], repo)
    assert run(["create"], repo).returncode == 0
    assert len(receipts(repo)) == 1


def test_tampered_content_fails_chain(repo):
    run(["init"], repo)
    run(["create"], repo)
    p = receipts(repo)[0]
    r = json.loads(p.read_text())
    r["files"][0]["sha256"] = "0" * 64  # rewrite history
    p.write_text(json.dumps(r))
    v = run(["verify"], repo)
    assert v.returncode == 1
    assert "does not match recomputed" in v.stderr


def test_tampered_signature_fails(repo):
    run(["init"], repo)
    run(["create"], repo)
    p = receipts(repo)[0]
    r = json.loads(p.read_text())
    r["signature"] = "ab" * 32
    p.write_text(json.dumps(r))
    v = run(["verify"], repo)
    assert v.returncode == 1 and "SIG FAIL" in v.stderr


def test_broken_chain_refuses_extension(repo):
    run(["init"], repo)
    run(["create"], repo)
    p = receipts(repo)[0]
    r = json.loads(p.read_text())
    r["prev_receipt_hash"] = "f" * 64  # dangling prev
    # keep receipt_hash consistent so ONLY the linkage is broken
    import hashlib
    sys.path.insert(0, str(PLUGIN / "core"))
    from canonical import canonical_bytes
    r["receipt_hash"] = hashlib.sha256(canonical_bytes(r)).hexdigest()
    key = bytes.fromhex((repo / ".titan/key").read_text().strip())
    import hmac as _h
    r["signature"] = _h.new(key, r["receipt_hash"].encode(), hashlib.sha256).hexdigest()
    p.write_text(json.dumps(r))
    (repo / "a.py").write_text("x\n")
    sh("git add -A && git commit -qm third", repo)
    c = run(["create"], repo)
    assert c.returncode == 1 and "broken chain" in c.stderr
    v = run(["verify"], repo)
    assert v.returncode == 1


def test_auto_mode_never_breaks_commits(repo, tmp_path):
    # no key -> --auto exits 0 with no output, writes nothing
    r = run(["create", "--auto"], repo)
    assert r.returncode == 0 and r.stdout == "" and not receipts(repo)
    # not even a git repo -> still exit 0
    outside = tmp_path / "not_a_repo"
    outside.mkdir()
    assert run(["create", "--auto"], outside).returncode == 0


def test_create_without_key_fails_loud_when_not_auto(repo):
    r = run(["create"], repo)
    assert r.returncode == 2 and "init first" in r.stderr


def test_unicode_and_special_filenames_are_hashed(repo):
    """git C-quotes non-ASCII paths in line mode; the -z parser must record
    the raw path WITH its content hash — silently dropping a hash is the
    exact failure an attestation tool exists to prevent."""
    run(["init"], repo)
    names = ["café résumé.py", "with space.txt"]
    if sys.platform != "win32":
        names.append('q"uote.md')  # NTFS forbids '"' in filenames; the C-quoting
                                   # path is still exercised by the non-ASCII name
    for name in names:
        (repo / name).write_text("x\n")
    sh("git add -A && git commit -qm unicode", repo)
    assert run(["create"], repo).returncode == 0
    r = json.loads(receipts(repo)[-1].read_text())
    by_path = {f["path"]: f for f in r["files"]}
    for name in names:
        assert name in by_path, (name, list(by_path))
        assert "sha256" in by_path[name], name
    assert not any(p.startswith('"') for p in by_path)  # no C-quoted paths
    assert run(["verify"], repo).returncode == 0


def test_hashes_are_over_gits_raw_utf8_bytes_on_every_platform(repo):
    """A receipt must attest the same thing whichever OS wrote it. Decoding
    git's output with the platform locale (cp1252 on Windows) re-encoded
    non-ASCII bytes before hashing, so diff_sha256 for one commit differed
    between Windows and Linux, and a non-ASCII filename matched no file and
    lost its content hash. Compare against git's RAW bytes, no text mode."""
    run(["init"], repo)
    (repo / "notes — café.md").write_text("em dash — and café ✓\n", encoding="utf-8")
    sh("git add -A && git commit -qm 'non-ascii content and name'", repo)
    assert run(["create"], repo).returncode == 0
    r = json.loads(receipts(repo)[-1].read_text(encoding="utf-8"))
    sha = sh("git rev-parse HEAD", repo).strip()
    raw_diff = subprocess.run(["git", "show", "--format=", sha], cwd=repo,
                              capture_output=True).stdout          # bytes
    assert r["diff_sha256"] == hashlib.sha256(raw_diff).hexdigest()
    by_path = {f["path"]: f for f in r["files"]}
    assert "notes — café.md" in by_path, list(by_path)
    # Content hashes attest the COMMITTED blob, not the working tree: on
    # Windows with core.autocrlf the checkout has CRLF while the commit (and a
    # Linux receipt of the same commit) has LF, so only the blob is the same
    # thing on every platform.
    blob = subprocess.run(["git", "cat-file", "blob", f"{sha}:notes — café.md"],
                          cwd=repo, capture_output=True, check=True).stdout
    assert by_path["notes — café.md"]["sha256"] == hashlib.sha256(blob).hexdigest()


def test_merge_commit_attests_first_parent_diff(repo):
    """'git show' on a merge prints the combined diff (usually empty) — a
    receipt with files=[] attests nothing. Merges diff vs first parent."""
    run(["init"], repo)
    run(["create"], repo)
    sh("git checkout -qb feat", repo)
    (repo / "feat.txt").write_text("f\n")
    sh("git add -A && git commit -qm feat", repo)
    run(["create"], repo)
    sh("git checkout -q main", repo)
    (repo / "main.txt").write_text("m\n")
    sh("git add -A && git commit -qm main2", repo)
    run(["create"], repo)
    sh("git merge -q --no-ff -m merged feat", repo)
    assert run(["create"], repo).returncode == 0
    rs = [json.loads(p.read_text()) for p in receipts(repo)]
    merge = [r for r in rs if r["commit"]["subject"] == "merged"][0]
    assert merge["commit"]["parents"] == 2
    paths = {f["path"] for f in merge["files"]}
    assert "feat.txt" in paths  # what the merge brought in vs first parent
    assert run(["verify"], repo).returncode == 0


def test_corrupt_key_fails_clean_never_signs(repo):
    run(["init"], repo)
    (repo / ".titan/key").write_text("NOT HEX AT ALL\n")
    r = run(["create"], repo)
    assert r.returncode == 1
    assert "Traceback" not in r.stderr and "not valid hex" in r.stderr
    assert not receipts(repo)  # nothing signed with a corrupt key
    # --auto: still nonzero (|| true protects the commit) and no traceback
    ra = run(["create", "--auto"], repo)
    assert ra.returncode == 1 and "Traceback" not in ra.stderr


def test_empty_key_refused(repo):
    """bytes.fromhex('') == b'' — an empty key would HMAC 'successfully'
    and sign receipts that prove nothing. Must refuse."""
    run(["init"], repo)
    (repo / ".titan/key").write_text("\n")
    r = run(["create"], repo)
    assert r.returncode == 1 and "too short" in r.stderr
    assert not receipts(repo)


def hook_run(payload, cwd):
    import subprocess as sp
    return sp.run([sys.executable, str(RECEIPT), "hook"], cwd=cwd,
                  input=payload, capture_output=True, text=True)


def test_hook_fires_only_on_git_commit(repo):
    run(["init"], repo)
    # non-commit bash -> no receipt
    r = hook_run(json.dumps({"tool_name": "Bash",
                             "tool_input": {"command": "ls -la"}}), repo)
    assert r.returncode == 0 and not receipts(repo)
    # git commit bash -> receipt created
    r = hook_run(json.dumps({"tool_name": "Bash",
                             "tool_input": {"command": "git commit -m 'x'"}}), repo)
    assert r.returncode == 0, r.stderr
    assert len(receipts(repo)) == 1
    # garbage stdin -> exit 0, nothing breaks
    assert hook_run("not json {", repo).returncode == 0
    assert hook_run("", repo).returncode == 0
    # uninitialized repo (no key): commit-shaped input is still a no-op
    assert len(receipts(repo)) == 1


def test_verify_without_receipts_fails_loud(repo):
    run(["init"], repo)
    assert run(["verify"], repo).returncode == 2
