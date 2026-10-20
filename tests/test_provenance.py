"""v1.1: provenance block, git post-commit coverage, structure-only verify,
and the compliance report. Every claim the README makes about these is
asserted here; every "never" is a test."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from _shell import shell_argv

PLUGIN = Path(__file__).resolve().parents[1]
RECEIPT = PLUGIN / "core" / "receipt.py"


def clean_env(**extra):
    """An environment that is NOT inside Claude Code (the test runner may be)."""
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDECODE" and not k.startswith("CLAUDE_")}
    env.update(extra)
    return env


def run(args, cwd, env=None, stdin=None):
    return subprocess.run([sys.executable, str(RECEIPT), *args], cwd=cwd,
                          capture_output=True, text=True, env=env or clean_env(),
                          input=stdin)


def sh(cmd, cwd, env=None):
    r = subprocess.run(shell_argv(cmd), cwd=cwd, capture_output=True, text=True,
                       env=env or clean_env())
    assert r.returncode == 0, r.stderr
    return r.stdout


def receipts(repo):
    return [json.loads(p.read_text())
            for p in sorted((repo / ".titan/attestations").rglob("*.json"))]


@pytest.fixture()
def repo(tmp_path):
    sh("git init -q -b main && git config user.email t@t && git config user.name T", tmp_path)
    (tmp_path / "a.py").write_text("print('hi')\n")
    sh("git add -A && git commit -qm 'first'", tmp_path)
    return tmp_path


# ------------------------------------------------------------ init + hook
def test_init_vendors_tools_and_installs_git_hook(repo):
    r = run(["init"], repo)
    assert r.returncode == 0, r.stderr
    for f in ("receipt.py", "canonical.py", "chain_state.py"):
        assert (repo / ".titan/tools" / f).read_bytes() == (PLUGIN / "core" / f).read_bytes()
    hook = repo / ".git/hooks/post-commit"
    assert hook.exists() and os.access(hook, os.X_OK)
    assert "ai-audit-trail" in hook.read_text()
    gi = (repo / ".gitignore").read_text()
    assert ".titan/key" in gi and ".titan/tools/__pycache__/" in gi


def test_init_no_git_hook_flag(repo):
    r = run(["init", "--no-git-hook"], repo)
    assert r.returncode == 0
    assert not (repo / ".git/hooks/post-commit").exists()
    assert not (repo / ".titan/tools").exists()


def test_install_hook_appends_to_existing_hook_never_clobbers(repo):
    hook = repo / ".git/hooks/post-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\necho theirs >> hooks.log\n")
    r = run(["install-hook"], repo)
    assert r.returncode == 0, r.stderr
    text = hook.read_text()
    assert "echo theirs" in text and "ai-audit-trail" in text
    # idempotent
    run(["install-hook"], repo)
    assert hook.read_text().count("ai-audit-trail post-commit hook") == 1


def test_human_commit_gets_receipt_with_ai_assisted_false(repo):
    run(["init"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'human edit'", repo)      # real git hook fires
    rs = receipts(repo)
    assert len(rs) == 1
    p = rs[0]["provenance"]
    assert p["ai_assisted"] is False and p["basis"] == []
    assert p["recorder"] == "git-post-commit"
    assert "session_id" not in p            # a human terminal has no session
    assert rs[0]["commit"]["author"] == "T <t@t>"
    assert rs[0]["commit"]["committed_at"]


def test_git_hook_defers_inside_claude_session(repo):
    """Inside Claude Code the PostToolUse hook owns the receipt; the git hook
    must step aside or the richer receipt would be deduped away."""
    run(["init"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'ai edit'", repo, env=clean_env(CLAUDECODE="1"))
    assert receipts(repo) == []


def test_trailer_marks_ai_assisted_even_from_git_hook(repo):
    run(["init"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'ai edit' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'", repo)
    p = receipts(repo)[0]["provenance"]
    assert p["ai_assisted"] is True and p["basis"] == ["commit-trailers"]
    assert p["recorder"] == "git-post-commit"


def test_non_claude_coauthor_is_not_ai(repo):
    run(["init"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'pair' -m 'Co-Authored-By: Jane <jane@x.io>'", repo)
    assert receipts(repo)[0]["provenance"]["ai_assisted"] is False


# ------------------------------------------------------- claude-code hook
def test_claude_hook_records_session_model_version_transcript(repo, tmp_path):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'ai edit' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'", repo)
    tr = tmp_path / "t.jsonl"
    tr.write_text('{"type":"user","version":"2.1.288"}\n'
                  '{"type":"assistant","version":"2.1.288","message":{"model":"claude-sonnet-4-6"}}\n'
                  '{"type":"assistant","message":{"model":"<synthetic>"}}\n'
                  'not json\n')
    payload = {"session_id": "sess-1", "transcript_path": str(tr), "tool_use_id": "toolu_9",
               "permission_mode": "default", "tool_name": "Bash",
               "tool_input": {"command": "git commit -m x"}}
    r = run(["hook"], repo, env=clean_env(CLAUDECODE="1"), stdin=json.dumps(payload))
    assert r.returncode == 0, r.stderr
    p = receipts(repo)[0]["provenance"]
    assert p["ai_assisted"] is True
    assert p["basis"] == ["commit-trailers", "claude-code-hook"]
    assert p["recorder"] == "claude-code-hook" and p["recorder_version"]
    assert p["session_id"] == "sess-1" and p["tool_use_id"] == "toolu_9"
    assert p["models"] == ["claude-sonnet-4-6"]        # synthetic filtered out
    assert p["claude_code_version"] == "2.1.288"
    assert p["transcript"]["lines"] == 4 and len(p["transcript"]["content_sha256"]) == 64


def test_claude_hook_without_trailers_still_ai_assisted_by_hook_basis(repo):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'no trailers'", repo)
    r = run(["hook"], repo, env=clean_env(CLAUDECODE="1"),
            stdin=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}))
    assert r.returncode == 0, r.stderr
    p = receipts(repo)[0]["provenance"]
    assert p["ai_assisted"] is True and p["basis"] == ["claude-code-hook"]


def test_missing_transcript_is_omitted_not_invented(repo):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'x'", repo)
    r = run(["hook"], repo, env=clean_env(CLAUDECODE="1"),
            stdin=json.dumps({"session_id": "s", "transcript_path": "/nonexistent/t.jsonl",
                              "tool_name": "Bash", "tool_input": {"command": "git commit"}}))
    assert r.returncode == 0
    p = receipts(repo)[0]["provenance"]
    assert "transcript" not in p and "models" not in p


def test_provenance_is_signed_tampering_it_breaks_verify(repo):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'x'", repo)
    run(["create"], repo)
    f = next((repo / ".titan/attestations").rglob("*.json"))
    r = json.loads(f.read_text())
    r["provenance"]["ai_assisted"] = not r["provenance"]["ai_assisted"]   # launder the flag
    f.write_text(json.dumps(r))
    assert run(["verify"], repo).returncode == 1
    assert run(["verify", "--structure-only"], repo).returncode == 1


# ------------------------------------------------------- structure-only
def test_structure_only_verifies_without_key_and_says_so(repo):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'x'", repo)
    run(["create"], repo)
    (repo / ".titan/key").unlink()                        # CI clone: no secret
    assert run(["verify"], repo).returncode == 2          # full verify refuses
    r = run(["verify", "--structure-only"], repo)
    assert r.returncode == 0, r.stderr
    assert "NOT CHECKED: signatures" in r.stdout


# ----------------------------------------------------------------- report
def test_report_counts_and_carries_limits(repo):
    run(["init"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'human'", repo)
    (repo / "c.py").write_text("x\n")
    sh("git add -A && git commit -qm 'ai' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'", repo)
    r = run(["report"], repo)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "| Receipted commits | 2 |" in out
    assert "| AI-assisted (per recorded basis) | 1 | 50% |" in out
    assert "**intact**" in out and "all valid" in out
    assert "| T <t@t> | 2 | 1 (50%) |" in out
    assert "does **not** prove who" in out        # limits footer is mandatory
    assert "shared secret" in out


def test_report_shows_broken_chain_instead_of_hiding_it(repo):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'x'", repo)
    run(["create"], repo)
    f = next((repo / ".titan/attestations").rglob("*.json"))
    r = json.loads(f.read_text())
    r["files"] = []
    f.write_text(json.dumps(r))
    out = run(["report"], repo).stdout
    assert "BROKEN" in out


def test_report_to_file(repo, tmp_path):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'x'", repo)
    run(["create"], repo)
    out = tmp_path / "r.md"
    assert run(["report", "--out", str(out)], repo).returncode == 0
    assert out.read_text().startswith("# AI-assisted change receipts")


def test_report_on_v1_0_receipts_without_provenance(repo):
    """Receipts written by 1.0.0 have no provenance block; the report must
    classify them as unknown, not silently as human."""
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'x'", repo)
    run(["create"], repo)
    f = next((repo / ".titan/attestations").rglob("*.json"))
    r = json.loads(f.read_text())
    del r["provenance"]
    del r["commit"]["author"]
    # re-sign so the chain is valid: recompute hash + hmac like 1.0 would have
    sys.path.insert(0, str(PLUGIN / "core"))
    import hashlib, hmac
    from canonical import canonical_bytes
    r["receipt_hash"] = hashlib.sha256(canonical_bytes(r)).hexdigest()
    key = bytes.fromhex((repo / ".titan/key").read_text().strip())
    r["signature"] = hmac.new(key, r["receipt_hash"].encode(), hashlib.sha256).hexdigest()
    f.write_text(json.dumps(r))
    assert run(["verify"], repo).returncode == 0
    out = run(["report"], repo).stdout
    assert "Unknown (v1.0 receipts without provenance) | 1" in out


# -------------------------------------------------------------- versions
def test_recorder_version_matches_plugin_manifest():
    m = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
    src = (PLUGIN / "core/receipt.py").read_text()
    assert f'PLUGIN_VERSION = "{m["version"]}"' in src


# ------------------------------------------------ hook must not over-claim
def _hook(repo, cmd, resp=None, age_s=0):
    """Fire the PostToolUse hook for `cmd` with an optional tool_response,
    after making HEAD `age_s` seconds old."""
    if age_s:
        ts = int(sh("git log -1 --format=%ct HEAD", repo).strip()) - age_s
        sh(f"GIT_COMMITTER_DATE=@{ts} git commit --amend --no-edit -q --date=@{ts}", repo)
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    if resp is not None:
        payload["tool_response"] = resp
    return run(["hook"], repo, env=clean_env(CLAUDECODE="1"), stdin=json.dumps(payload))


def test_hook_ignores_commands_that_merely_mention_commit(repo):
    run(["init", "--no-git-hook"], repo)
    for cmd in ("git log --oneline | grep commit", "git status; echo commit",
                "echo 'git commit' > notes.txt", "git show HEAD --stat  # last commit"):
        assert _hook(repo, cmd).returncode == 0
        assert receipts(repo) == [], cmd


def test_hook_accepts_real_commit_forms(repo):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'x'", repo)
    assert _hook(repo, "cd /repo && git add -A && git -c user.name=T commit -m 'x'").returncode == 0
    assert len(receipts(repo)) == 1
    assert receipts(repo)[0]["provenance"]["basis"] == ["claude-code-hook"]


def test_failed_commit_does_not_receipt_existing_head_as_ai(repo):
    """The human's HEAD has no receipt yet; Claude runs `git commit` and it
    fails. Receipting HEAD here would be a false AI-assisted claim."""
    run(["init", "--no-git-hook"], repo)
    r = _hook(repo, "git commit -m 'x'",
              resp={"stdout": "On branch main\nnothing to commit, working tree clean\n",
                    "exit_code": 1})
    assert r.returncode == 0 and receipts(repo) == []
    r = _hook(repo, "git commit -m 'x'", resp={"stdout": "", "stderr": "", "exit_code": 1})
    assert receipts(repo) == []


def test_stale_head_is_not_receipted_by_hook(repo):
    run(["init", "--no-git-hook"], repo)
    assert _hook(repo, "git commit -m 'x'", age_s=3600).returncode == 0
    assert receipts(repo) == []


# ------------------------------------------------ hook install refusals
def test_install_hook_refuses_when_existing_hook_exits_first(repo):
    hook = repo / ".git/hooks/post-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\n. \"$(dirname \"$0\")/h\"\nexit $c\n")
    r = run(["install-hook"], repo)
    assert r.returncode == 1 and "NOT installed" in r.stdout
    assert "ai-audit-trail" not in hook.read_text()


def test_install_hook_refuses_non_shell_hook(repo):
    hook = repo / ".git/hooks/post-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/usr/bin/env python3\nprint('hi')\n")
    r = run(["install-hook"], repo)
    assert r.returncode == 1 and "not a shell script" in r.stdout
    assert hook.read_text() == "#!/usr/bin/env python3\nprint('hi')\n"


def test_init_on_initialized_repo_still_installs_hook(repo):
    run(["init", "--no-git-hook"], repo)              # v1.0-style: key only
    assert not (repo / ".git/hooks/post-commit").exists()
    r = run(["init"], repo)                           # upgrade path
    assert r.returncode == 0 and "key exists" in r.stdout
    assert (repo / ".git/hooks/post-commit").exists()
    assert (repo / ".titan/tools/receipt.py").exists()


# ------------------------------------------------ report accounting
def test_report_v1_0_receipt_with_claude_trailer_is_ai_not_unknown(repo):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'x' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'", repo)
    run(["create"], repo)
    f = next((repo / ".titan/attestations").rglob("*.json"))
    r = json.loads(f.read_text())
    del r["provenance"]
    sys.path.insert(0, str(PLUGIN / "core"))
    import hashlib, hmac
    from canonical import canonical_bytes
    r["receipt_hash"] = hashlib.sha256(canonical_bytes(r)).hexdigest()
    key = bytes.fromhex((repo / ".titan/key").read_text().strip())
    r["signature"] = hmac.new(key, r["receipt_hash"].encode(), hashlib.sha256).hexdigest()
    f.write_text(json.dumps(r))
    out = run(["report"], repo).stdout
    assert "| AI-assisted (per recorded basis) | 1 | 100% |" in out
    assert "| Not AI-assisted | 0 | 0% |" in out
    assert "Unknown (v1.0 receipts" not in out and "| -1 |" not in out


def test_report_survives_receipt_missing_hash(repo):
    run(["init", "--no-git-hook"], repo)
    (repo / "b.py").write_text("x\n")
    sh("git add -A && git commit -qm 'x'", repo)
    run(["create"], repo)
    f = next((repo / ".titan/attestations").rglob("*.json"))
    r = json.loads(f.read_text())
    del r["receipt_hash"]
    f.write_text(json.dumps(r))
    r = run(["report"], repo)
    assert r.returncode == 0 and "BROKEN" in r.stdout
