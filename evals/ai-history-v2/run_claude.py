"""Layer 2: run /ai-history through `claude -p`, N times per fixture, and save
each transcript. Scoring is compare.py's job.

Usage:
  python run_claude.py PLUGIN_DIR FIXTURES_DIR RUNS_DIR [--runs 3] [--only abcdefgh]
                       [--command /ai-history]

Each run gets a fresh copy of the fixture as its working directory and a fresh
session. The fixture's git state is recorded before and after, so compare.py
can check the run changed nothing. Spending is capped per run with
--max-budget-usd; tools that write or reach the network are disallowed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ALLOWED = ["Bash", "Read", "Glob", "Grep"]
DISALLOWED = ["Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Agent"]


def claude_exe() -> str:
    exe = shutil.which("claude")
    if not exe:
        raise SystemExit("claude CLI not found on PATH")
    return exe


def no_shadowing_install() -> None:
    """Refuse to run if an installed commitproof / titan-receipts is enabled:
    its /ai-history could answer instead of the plugin under test."""
    out = subprocess.run([claude_exe(), "plugin", "list"], capture_output=True).stdout.decode("utf-8", "replace")
    for block in re.split(r"\n\s*\n", out):
        if re.search(r"commitproof|titan-receipts", block, re.I) and re.search(r"Status:\s*\S*\s*enabled", block, re.I):
            raise SystemExit("an installed commitproof/titan-receipts plugin is enabled; disable it first:\n" + block)


def git_state(repo: Path) -> dict:
    def g(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=repo, capture_output=True).stdout.decode("utf-8", "replace")
    cfg = repo / ".git" / "config"
    return {"status": g("status", "--porcelain", "--untracked-files=all"),
            "refs": g("for-each-ref", "--format=%(refname) %(objectname)") + g("rev-parse", "HEAD"),
            "config_sha256": hashlib.sha256(cfg.read_bytes()).hexdigest() if cfg.exists() else None}


def run_one(plugin: Path, fixture: Path, runs_dir: Path, tag: str, command: str, timeout: int) -> dict:
    work = runs_dir / "work" / tag
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(fixture, work)
    before = git_state(work)
    cmd = [claude_exe(), "-p", command, "--plugin-dir", str(plugin),
           "--output-format", "stream-json", "--verbose", "--max-turns", "8", "--max-budget-usd", "1",
           "--strict-mcp-config", "--no-session-persistence",
           "--allowedTools", *ALLOWED, "--disallowedTools", *DISALLOWED]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=work, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
        rc, out, err = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as exc:
        rc, out, err = "timeout", exc.stdout or b"", exc.stderr or b""
    meta = {"tag": tag, "fixture": fixture.name, "command": command, "exit": rc,
            "seconds": round(time.time() - t0, 1), "workdir": str(work),
            "state_before": before, "state_after": git_state(work), "argv": cmd[1:]}
    (runs_dir / f"{tag}.jsonl").write_bytes(out)
    (runs_dir / f"{tag}.stderr.txt").write_bytes(err)
    (runs_dir / f"{tag}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plugin", type=Path)
    ap.add_argument("fixtures", type=Path)
    ap.add_argument("runs_dir", type=Path)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--only", default="abcdefgh")
    ap.add_argument("--command", default="/ai-history")
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args()
    no_shadowing_install()
    a.runs_dir.mkdir(parents=True, exist_ok=True)
    for name in a.only:
        for n in range(1, a.runs + 1):
            m = run_one(a.plugin.resolve(), (a.fixtures / name).resolve(), a.runs_dir.resolve(),
                        f"{name}-{n}", a.command, a.timeout)
            print(f"{m['tag']}: exit {m['exit']} in {m['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
