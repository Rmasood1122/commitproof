"""v1.3: one name everywhere — ai-audit-trail.

"Titan Gate plugin" searched as an audio noise gate, and "receipts" in the
directory is Anthropic's own plugin; the repo, plugin and marketplace had
three different names. The public name is now ai-audit-trail. Data paths
(.titan/, TITAN_KEY) are unchanged so existing chains keep verifying, and
anything an older version installed is still recognized as ours."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from _shell import shell_argv

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "core" / "receipt.py"
NAME = "ai-audit-trail"
REPO_URL = "https://github.com/Rmasood1122/ai-audit-trail"
LEGACY_MARK = "# titan-receipts post-commit hook"


def test_one_name_for_plugin_and_marketplace():
    m = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    mp = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    assert m["name"] == NAME and m["displayName"] == "AI Audit Trail"
    assert mp["name"] == NAME and mp["plugins"][0]["name"] == NAME


def test_manifest_urls_point_at_the_renamed_repo():
    m = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    for key in ("homepage", "repository", "supportUrl", "documentationUrl", "privacyPolicyUrl"):
        assert m[key].startswith(REPO_URL), (key, m[key])


def test_old_public_name_is_gone_from_user_facing_files():
    files = [ROOT / p for p in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                                "action.yml", "PRIVACY.md", "core/py.sh",
                                "skills/receipt-integrity/SKILL.md")]
    files += sorted((ROOT / "commands").glob("*.md"))
    for f in files:
        text = f.read_text(encoding="utf-8").lower()
        assert "titan-receipts" not in text and "titan receipts" not in text, f
        assert "titan-gate-plugin" not in text, f


def sh(cmd, cwd):
    r = subprocess.run(shell_argv(cmd), cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    sh("git init -q -b main && git config user.email t@t && git config user.name T", r)
    (r / "a.py").write_text("x = 1\n")
    sh("git add -A && git commit -qm first", r)
    return r


def run(cwd, *args, env=None):
    return subprocess.run([sys.executable, str(RECEIPT), *args], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_new_hook_carries_the_new_mark(repo):
    assert run(repo, "init").returncode == 0
    text = (repo / ".git/hooks/post-commit").read_text()
    assert "# ai-audit-trail post-commit hook" in text and LEGACY_MARK not in text


def test_legacy_block_appended_to_a_foreign_hook_is_still_ours(repo):
    """A block an older version appended to someone else's hook must not get
    a second copy beside it under the new mark."""
    hook = repo / ".git/hooks/post-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(f"#!/bin/sh\necho theirs\n\n{LEGACY_MARK} — old block\nexit 0\n", newline="\n")
    r = run(repo, "install-hook")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "already installed" in r.stdout
    assert "# ai-audit-trail post-commit hook" not in hook.read_text()


def test_report_and_notice_use_the_new_name(repo, tmp_path):
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDECODE" and not k.startswith(("CLAUDE_", "TITAN_RECEIPTS_", "AI_AUDIT_TRAIL_"))}
    env.update(CLAUDECODE="1", CLAUDE_PLUGIN_DATA=str(tmp_path / "data"))
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"},
               "tool_response": {"stdout": "[main 1a2b3c4] x"}}
    r = subprocess.run([sys.executable, str(RECEIPT), "hook"], cwd=repo, input=json.dumps(payload),
                       capture_output=True, text=True, encoding="utf-8", env=env)
    assert json.loads(r.stdout)["systemMessage"].startswith("AI Audit Trail:")
    assert run(repo, "init", "--no-git-hook").returncode == 0
    (repo / "b.py").write_text("y = 2\n")
    sh("git add -A && git commit -qm second", repo)
    assert run(repo, "create").returncode == 0
    assert "by ai-audit-trail " in run(repo, "report").stdout


@pytest.mark.parametrize("var", ["AI_AUDIT_TRAIL_QUIET", "TITAN_RECEIPTS_QUIET"])
def test_quiet_env_new_and_legacy_names(repo, tmp_path, var):
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDECODE" and not k.startswith(("CLAUDE_", "TITAN_RECEIPTS_", "AI_AUDIT_TRAIL_"))}
    env.update(CLAUDECODE="1", CLAUDE_PLUGIN_DATA=str(tmp_path / "data"), **{var: "1"})
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"},
               "tool_response": {"stdout": "[main 1a2b3c4] x"}}
    r = subprocess.run([sys.executable, str(RECEIPT), "hook"], cwd=repo, input=json.dumps(payload),
                       capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0 and r.stdout.strip() == ""
