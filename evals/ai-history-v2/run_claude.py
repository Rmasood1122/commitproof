"""Layer 2: run /ai-history through `claude -p`, N times per case, and save
each transcript. Scoring is compare.py's job.

Usage:
  python run_claude.py PLUGIN_DIR FIXTURES_DIR RUNS_DIR [--mode fixtures|norepo|paste|nl]
                       [--runs 3] [--only abcdefgh] [--command /titan-receipts:ai-history]

Modes:
  fixtures  /titan-receipts:ai-history in a fresh copy of each fixture (the gated 24 runs)
  norepo    /titan-receipts:ai-history in an empty folder that is not a repository
  paste     a natural message pasting fixture c's step-2 output, in an empty non-repo folder
  nl        "How much of this repo did Claude help write?" in a copy of fixture c

Each run gets a fresh working directory and a fresh session. The working
directory's git state is recorded before and after, so compare.py can check
the run changed nothing. Spending is capped per run with --max-budget-usd;
tools that write or reach the network are disallowed. The user's own
~/.claude/CLAUDE.md still loads (excluding it needs --bare, which needs an
API key), which makes these runs stricter, not looser.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from block_check import blocks, run_sh  # noqa: E402
from fixtures import isolated_env, rm_tree  # noqa: E402

ALLOWED = ["Bash", "Read", "Glob", "Grep", "Skill"]
DISALLOWED = ["Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Agent", "PowerShell"]
NL_PROMPT = "How much of this repo did Claude help write?"
PASTE_PROMPT = ("I can't open my repository here, so I ran the ai-history commands from the Titan Receipts "
                "plugin in a terminal inside it. Here is the output:\n\n```\n{out}```")


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


def not_in_a_repo(path: Path) -> None:
    r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, capture_output=True)
    if r.returncode == 0:
        raise SystemExit(f"{path} is inside a git repository; the no-repo cases would be invalid")


def git_state(repo: Path) -> dict:
    def g(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=repo, capture_output=True).stdout.decode("utf-8", "replace")
    cfg = repo / ".git" / "config"
    return {"status": g("status", "--porcelain", "--untracked-files=all"),
            "refs": g("for-each-ref", "--format=%(refname) %(objectname)") + g("rev-parse", "HEAD"),
            "config_sha256": hashlib.sha256(cfg.read_bytes()).hexdigest() if cfg.exists() else None,
            "files": sorted(str(p.relative_to(repo)) for p in repo.rglob("*") if ".git" not in p.parts)}


def run_one(plugin: Path, work: Path, runs_dir: Path, tag: str, prompt: str, case: str, expect_fixture: str | None,
            timeout: int) -> dict:
    before = git_state(work)
    cmd = [claude_exe(), "-p", prompt, "--plugin-dir", str(plugin),
           "--output-format", "stream-json", "--verbose", "--max-turns", "10", "--max-budget-usd", "1",
           "--strict-mcp-config", "--no-session-persistence",
           "--allowedTools", *ALLOWED, "--disallowedTools", *DISALLOWED]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=work, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
        rc, out, err = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as exc:
        rc, out, err = "timeout", exc.stdout or b"", exc.stderr or b""
    meta = {"tag": tag, "case": case, "fixture": expect_fixture, "prompt": prompt, "exit": rc,
            "seconds": round(time.time() - t0, 1), "workdir": str(work), "plugin": str(plugin),
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
    ap.add_argument("--mode", default="fixtures", choices=["fixtures", "norepo", "paste", "nl"])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--only", default="abcdefgh")
    ap.add_argument("--command", default="/titan-receipts:ai-history")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    no_shadowing_install()
    plugin, fixtures, runs_dir = a.plugin.resolve(), a.fixtures.resolve(), a.runs_dir.resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    not_in_a_repo(runs_dir)
    cases: list[tuple[str, str, str | None, str]] = []  # (tag, source fixture or '', expected fixture, prompt)
    if a.mode == "fixtures":
        cases = [(f"{name}-{n}", name, name, a.command) for name in a.only for n in range(1, a.runs + 1)]
    elif a.mode == "norepo":
        cases = [(f"norepo-{n}", "", None, a.command) for n in range(1, a.runs + 1)]
    elif a.mode == "paste":
        _, block, _ = blocks(plugin)
        rc, out = run_sh(block, fixtures / "c", isolated_env(fixtures / "_git"))
        assert rc == 0, out
        cases = [(f"paste-{n}", "", "c", PASTE_PROMPT.format(out=out.replace("\r\n", "\n")))
                 for n in range(1, a.runs + 1)]
    elif a.mode == "nl":
        cases = [(f"nl-{n}", "c", "c", NL_PROMPT) for n in range(1, a.runs + 1)]
    for tag, source, expect, prompt in cases:
        work = runs_dir / "work" / tag
        rm_tree(work)
        if source:
            shutil.copytree(fixtures / source, work)
        else:
            work.mkdir(parents=True)
            not_in_a_repo(work)
        m = run_one(plugin, work, runs_dir, tag, prompt, a.mode, expect, a.timeout)
        print(f"{m['tag']}: exit {m['exit']} in {m['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
