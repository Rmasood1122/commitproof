"""v1.2: first-run notice. Installs without /receipt-init produced thousands of
silent hook runs and zero receipts — the hook no-oped on every commit and
nobody was told why. The first successful Claude-made commit in an
uninitialized repo now tells the user, ONCE per repo, how to turn receipts
on. Every "never" below is a test: never nag, never auto-init, never break
a commit, never create anything inside the user's repo."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from _shell import shell_argv

PLUGIN = Path(__file__).resolve().parents[1]
RECEIPT = PLUGIN / "core" / "receipt.py"

COMMIT_OK = {"tool_name": "Bash",
             "tool_input": {"command": "git commit -m 'feat: x'"},
             "tool_response": {"stdout": "[main 1a2b3c4] feat: x\n 1 file changed"}}


def env_with(data_dir, **extra):
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDECODE" and not k.startswith(("CLAUDE_", "TITAN_RECEIPTS_", "COMMITPROOF_"))}
    env.update(CLAUDECODE="1", CLAUDE_PLUGIN_DATA=str(data_dir))
    env.update(extra)
    return env


def hook(cwd, env, payload=COMMIT_OK):
    return subprocess.run([sys.executable, str(RECEIPT), "hook"], cwd=cwd,
                          capture_output=True, text=True, env=env,
                          input=json.dumps(payload))


def sh(cmd, cwd):
    r = subprocess.run(shell_argv(cmd), cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    sh("git init -q -b main && git config user.email t@t && git config user.name T", path)
    (path / "a.py").write_text("print('hi')\n")
    sh("git add -A && git commit -qm first", path)
    return path


def commit(repo: Path, name: str):
    (repo / name).write_text(name + "\n")
    sh(f"git add -A && git commit -qm {name}", repo)


def notice(stdout: str) -> dict | None:
    out = stdout.strip()
    if not out.startswith("{"):
        return None
    return json.loads(out)


@pytest.fixture()
def repo(tmp_path):
    return make_repo(tmp_path / "repo")


@pytest.fixture()
def data(tmp_path):
    return tmp_path / "plugin-data"


def test_uninitialized_commit_gets_one_notice_naming_receipt_init(repo, data):
    r = hook(repo, env_with(data))
    assert r.returncode == 0, r.stderr
    n = notice(r.stdout)
    assert n is not None, f"expected a JSON notice, got {r.stdout!r}"
    assert "/receipt-init" in n["systemMessage"]
    assert "/ai-history" in n["systemMessage"]   # value now, before any setup
    ctx = n["hookSpecificOutput"]
    assert ctx["hookEventName"] == "PostToolUse"
    assert "/receipt-init" in ctx["additionalContext"]
    # Claude must be told not to set it up on the user's behalf.
    assert "do not run" in ctx["additionalContext"].lower()


def test_notice_never_repeats_in_the_same_repo(repo, data):
    assert notice(hook(repo, env_with(data)).stdout) is not None
    commit(repo, "b.py")
    second = hook(repo, env_with(data))
    assert second.returncode == 0
    assert second.stdout.strip() == ""


def test_notice_is_per_repo(tmp_path, data):
    a = make_repo(tmp_path / "a")
    b = make_repo(tmp_path / "b")
    assert notice(hook(a, env_with(data)).stdout) is not None
    assert notice(hook(b, env_with(data)).stdout) is not None


def test_notice_creates_nothing_inside_the_repo(repo, data):
    before = sorted(p.name for p in repo.iterdir())
    hook(repo, env_with(data))
    assert sorted(p.name for p in repo.iterdir()) == before
    assert not (repo / ".titan").exists()


def test_initialized_repo_never_gets_the_notice(repo, data):
    subprocess.run([sys.executable, str(RECEIPT), "init", "--no-git-hook"],
                   cwd=repo, capture_output=True, text=True, check=True)
    commit(repo, "b.py")
    r = hook(repo, env_with(data))
    assert r.returncode == 0, r.stderr
    assert notice(r.stdout) is None
    assert "receipt:" in r.stdout          # the normal receipt still lands


def test_quiet_env_disables_the_notice(repo, data):
    r = hook(repo, env_with(data, TITAN_RECEIPTS_QUIET="1"))
    assert r.returncode == 0 and r.stdout.strip() == ""
    assert not data.exists()


def test_non_commit_bash_never_gets_the_notice(repo, data):
    r = hook(repo, env_with(data), {"tool_name": "Bash",
                                    "tool_input": {"command": "git log | grep commit"},
                                    "tool_response": {"stdout": ""}})
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_failed_commit_never_gets_the_notice(repo, data):
    r = hook(repo, env_with(data), {"tool_name": "Bash",
                                    "tool_input": {"command": "git commit -m x"},
                                    "tool_response": {"stdout": "nothing to commit, working tree clean"}})
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_unwritable_state_stays_silent_rather_than_nagging(repo, tmp_path):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x")                 # data dir path is a FILE: can't record
    for _ in range(2):
        r = hook(repo, env_with(blocker))
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == ""       # no record possible -> no notice at all


def test_falls_back_to_home_when_plugin_data_unset(repo, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    env = env_with(tmp_path / "unused", HOME=str(home), USERPROFILE=str(home))
    env.pop("CLAUDE_PLUGIN_DATA")
    assert notice(hook(repo, env).stdout) is not None
    assert (home / ".titan-receipts").exists()
    assert hook(repo, env).stdout.strip() == ""
