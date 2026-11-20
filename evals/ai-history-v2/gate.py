"""Run one release gate and append its evidence to the release log.

Usage:
  python gate.py LOG GATE_ID TITLE RULE CWD COMMAND

  RULE  empty            the command must print nothing (stdout and stderr)
        exact:<text>     the output, with CRLF line endings read as LF and
                         trailing newlines dropped, must equal <text>
        contains:<text>  the output must contain <text>
        exit0            the command must exit 0

The command runs in Git Bash (on other systems, bash) as a script file, in
CWD, with stdout and stderr merged in order. The log entry records the UTC
time, the branch and commit of CWD, the pass rule, the result, the exact
command and its raw output. Exit 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def bash_exe() -> str:
    for cand in (r"C:\Program Files\Git\bin\bash.exe", shutil.which("bash")):
        if cand and Path(cand).exists() and "System32" not in cand:
            return cand
    raise SystemExit("no POSIX bash found (Git Bash on Windows)")


def bash_env() -> dict:
    env = dict(os.environ)
    usr = Path(bash_exe()).parent.parent / "usr" / "bin"
    if usr.exists():  # POSIX find/sort/awk ahead of Windows find.exe/sort.exe
        env["PATH"] = str(usr) + os.pathsep + env.get("PATH", "")
    return env


def checkout(cwd: Path) -> str:
    def g(*a: str) -> str:
        r = subprocess.run(["git", *a], cwd=cwd, capture_output=True)
        return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else ""
    branch, sha = g("rev-parse", "--abbrev-ref", "HEAD"), g("rev-parse", "--short", "HEAD")
    if not sha:
        return f"{cwd} (not a git checkout)"
    dirty = g("status", "--porcelain")
    state = "clean" if not dirty else f"{len(dirty.splitlines())} uncommitted change(s)"
    return f"{branch} @ {sha} ({state})"


def fence(text: str) -> str:
    ticks = "```"
    while ticks in text:
        ticks += "`"
    return ticks


def main() -> int:
    log, gate_id, title, rule, cwd, command = sys.argv[1:7]
    cwd_p = Path(cwd).resolve()
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8", newline="\n") as fh:
        fh.write(command + "\n")
        script = fh.name
    try:
        r = subprocess.run([bash_exe(), script], cwd=cwd_p, env=bash_env(), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    finally:
        os.unlink(script)
    out = r.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    norm = out.rstrip("\n")
    if rule == "empty":
        ok = out == ""
    elif rule == "exit0":
        ok = r.returncode == 0
    elif rule.startswith("exact:"):
        ok = norm == rule[len("exact:"):].replace("\\n", "\n")
    elif rule.startswith("contains:"):
        ok = rule[len("contains:"):] in out
    else:
        raise SystemExit(f"unknown rule {rule!r}")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = "PASS" if ok else "FAIL"
    shown_rule = rule.replace("\n", "\\n")
    body = out if out else "(no output)\n"
    if not body.endswith("\n"):
        body += "\n"
    entry = (f"### Gate {gate_id}: {title}\n\n"
             f"- Time (UTC): {stamp}\n"
             f"- Checkout: {checkout(cwd_p)}\n"
             f"- Pass rule: `{shown_rule}`\n"
             f"- Result: **{result}** (exit {r.returncode})\n\n"
             f"Command:\n\n{fence(command)}sh\n{command}\n{fence(command)}\n\n"
             f"Raw output:\n\n{fence(body)}text\n{body}{fence(body)}\n\n")
    with open(log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(entry)
    print(entry)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
