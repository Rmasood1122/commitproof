"""v1.3: find a real Python instead of assuming `python3`.

Windows' classic python.org installer ships python.exe and py.exe but no
python3.exe, and the WindowsApps python3.exe alias only prints a Store
message. Both hooks ran `python3 … || true`, so on such a machine the plugin
hook, the setup notice and the git post-commit hook all failed silently —
installs that could never activate. These tests put a Store-style stub first
on PATH and require the real interpreter behind it to run."""
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from _shell import POSIX_SHELL, shell_argv, posix

PLUGIN = Path(__file__).resolve().parents[1]
LAUNCHER = PLUGIN / "core" / "py.sh"
RECEIPT = PLUGIN / "core" / "receipt.py"

STUB = "#!/bin/sh\necho 'Python was not found; run without arguments to install from the Microsoft Store' >&2\nexit 49\n"


def script(path: Path, body: str):
    path.write_text(body, newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture()
def fakebin(tmp_path):
    d = tmp_path / "bin"
    d.mkdir()
    script(d / "python3", STUB)
    script(d / "py", STUB)
    script(d / "python", f'#!/bin/sh\nexec {posix(Path(sys.executable))} "$@"\n')
    return d


def env_path(*dirs, keep_system=True):
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDECODE" and not k.startswith(("CLAUDE_", "TITAN_RECEIPTS_", "AI_AUDIT_TRAIL_"))}
    parts = [str(d) for d in dirs]
    if keep_system:
        parts.append(os.environ.get("PATH", ""))
    env["PATH"] = os.pathsep.join(parts)
    return env


def sh(cmd, cwd, env):
    return subprocess.run(shell_argv(cmd), cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", env=env)


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    e = env_path()
    for c in ("git init -q -b main", "git config user.email t@t", "git config user.name T"):
        assert sh(c, r, e).returncode == 0
    (r / "a.py").write_text("x = 1\n")
    assert sh("git add -A && git commit -qm first", r, e).returncode == 0
    return r


def launch(cwd, env, *args):
    if POSIX_SHELL is None:
        pytest.skip("needs a POSIX shell")
    return subprocess.run([POSIX_SHELL, str(LAUNCHER), str(RECEIPT), *args], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_launcher_skips_a_store_stub_and_runs_real_python(repo, fakebin):
    r = launch(repo, env_path(fakebin), "history", "--json")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["commits"] == 1


def test_launcher_passes_exit_codes_through(repo, fakebin):
    r = launch(repo, env_path(fakebin), "verify")
    assert r.returncode == 2      # nothing to verify: receipt.py's own usage error


def test_no_python_at_all_says_so_and_hook_command_still_exits_0(repo, tmp_path):
    only_stubs = tmp_path / "stubs"
    only_stubs.mkdir()
    for name in ("python3", "python", "py"):
        script(only_stubs / name, STUB)
    # stubs first; the shell's own dir so the hook's `sh` resolves
    env = env_path(only_stubs, Path(POSIX_SHELL or "/bin/sh").parent, keep_system=False)
    r = launch(repo, env, "history")
    assert r.returncode != 0
    assert "Python 3.10+" in r.stderr
    hook_cmd = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())[
        "hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    hook_cmd = hook_cmd.replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN.as_posix())
    r = subprocess.run([POSIX_SHELL, "-c", hook_cmd], cwd=repo, input="{}",
                       capture_output=True, text=True, env=env)
    assert "Python 3.10+" in r.stderr  # the launcher really ran, and said why
    assert r.returncode == 0           # a hook must never fail the tool call


def test_plugin_hook_runs_through_the_launcher():
    h = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
    cmd = h["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    assert "core/py.sh" in cmd and "core/receipt.py" in cmd and "python3 " not in cmd


def test_commands_run_through_the_launcher():
    for md in (PLUGIN / "commands").glob("*.md"):
        text = md.read_text(encoding="utf-8")
        assert 'core/py.sh" "${CLAUDE_PLUGIN_ROOT}/core/receipt.py"' in text, md
        assert 'python3 "${CLAUDE_PLUGIN_ROOT}' not in text, md


def test_git_post_commit_hook_skips_a_store_stub(repo, fakebin):
    """The git hook is what receipts human commits; it had the same bug."""
    e = env_path(fakebin)
    r = subprocess.run([sys.executable, str(RECEIPT), "init"], cwd=repo,
                       capture_output=True, text=True, env=e)
    assert r.returncode == 0, r.stderr
    (repo / "b.py").write_text("y = 2\n")
    r = sh("git add b.py && git commit -qm human", repo, e)
    assert r.returncode == 0, r.stderr
    receipts = list((repo / ".titan" / "attestations").rglob("*.json"))
    assert len(receipts) == 1, r.stderr


def test_outdated_whole_file_hook_is_upgraded(repo):
    """Re-running install-hook must replace a hook this tool wrote earlier
    (the python3-only one), not report 'already installed' and keep it."""
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    old = ("#!/bin/sh\n# titan-receipts post-commit hook — receipt EVERY commit\n"
           'python3 "$root/.titan/tools/receipt.py" create --auto || true\nexit 0\n')
    (hooks / "post-commit").write_text(old, newline="\n")
    r = subprocess.run([sys.executable, str(RECEIPT), "install-hook"], cwd=repo,
                       capture_output=True, text=True, env=env_path())
    assert r.returncode == 0, r.stdout + r.stderr
    assert "updated" in r.stdout
    assert "for py in python3 python py" in (hooks / "post-commit").read_text()


def test_shell_scripts_are_pinned_to_lf():
    """core.autocrlf=true on a Windows clone would turn py.sh into CRLF,
    and sh then fails on every line (`$'\r': command not found`)."""
    attrs = (PLUGIN / ".gitattributes").read_text()
    assert "*.sh text eol=lf" in attrs
    assert b"\r\n" not in LAUNCHER.read_bytes()
