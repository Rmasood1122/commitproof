"""Golden values for /ai-history, computed by code.

This path is independent of the shipped commands. It reads each commit's
message and numstat once, decides "has a Claude or LLM trailer" with a
Python regex, and does every sum, grouping and ranking in Python. It shares
only git's own definitions with the shipped block:
- which commits are reachable (--no-merges)
- the author name and email after .mailmap (%aN, %aE)
- the commit month (%cd)
- per-file line counts (numstat with -M --no-textconv)

Usage: python golden.py REPO [--emails]   -> prints JSON
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# The rule from skills/ai-history/reference/trailers.md, written independently
# of the shipped git ERE:
# - a line starting with Co-Authored-By: or Assisted-by: whose value starts
#   with the word Claude;
# - an Assisted-by: line whose value is exactly LLM;
# - any Claude-Session: line.
TRAILER = re.compile(r"^(?:co-authored-by|assisted-by)[ \t]*:[ \t]*claude(?![a-z])"
                     r"|^assisted-by[ \t]*:[ \t]*llm[ \t\r]*$"
                     r"|^claude-session[ \t]*:",
                     re.IGNORECASE | re.MULTILINE)
TOP_AUTHORS, LAST_MONTHS = 15, 12


def git(repo: Path, *args: str, env: dict | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, env=env)
    if r.returncode:
        raise RuntimeError(r.stderr.decode("utf-8", "replace"))
    return r.stdout.decode("utf-8")


def has_commits(repo: Path, env: dict | None = None) -> bool:
    r = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"], cwd=repo, capture_output=True, env=env)
    return r.returncode == 0 and bool(r.stdout.strip())


def golden(repo: Path, env: dict | None = None, emails: bool = False) -> dict:
    if not has_commits(repo, env):
        return {"empty": True}
    who = "%aN <%aE>" if emails else "%aN"
    meta = git(repo, "log", "--no-merges", "--date=format:%Y-%m", f"--format=%H%x00{who}%x00%cd%x00%B%x01",
               "HEAD", env=env)
    commits = {}
    for rec in meta.split("\x01"):
        rec = rec.lstrip("\n")
        if not rec:
            continue
        sha, author, month, body = rec.split("\x00", 3)
        commits[sha] = {"author": author, "month": month, "claude": bool(TRAILER.search(body)), "lines": 0}
    stat = git(repo, "log", "--no-merges", "-M", "--no-textconv", "--numstat", "--format=%x02%H", "HEAD", env=env)
    sha = None
    for line in stat.splitlines():
        if line.startswith("\x02"):
            sha = line[1:]
            continue
        cols = line.split("\t")
        if sha and len(cols) >= 3 and cols[0].isdigit():
            commits[sha]["lines"] += int(cols[0])

    rows = list(commits.values())
    by_author, by_author_c = Counter(r["author"] for r in rows), Counter(r["author"] for r in rows if r["claude"])
    by_month, by_month_c = Counter(r["month"] for r in rows), Counter(r["month"] for r in rows if r["claude"])

    ranked = sorted(by_author.items(), key=lambda kv: -kv[1])
    if len(ranked) > TOP_AUTHORS and ranked[TOP_AUTHORS - 1][1] == ranked[TOP_AUTHORS][1]:
        raise ValueError("tie at the top-15 author boundary; the expected rows would be ambiguous")
    top = ranked[:TOP_AUTHORS]
    months = sorted(by_month)[-LAST_MONTHS:]
    return {
        "empty": False,
        "commits_all": len(rows),
        "commits_claude": sum(r["claude"] for r in rows),
        "lines_all": sum(r["lines"] for r in rows),
        "lines_claude": sum(r["lines"] for r in rows if r["claude"]),
        "authors_all": len(by_author),
        "authors": {name: [n, by_author_c.get(name, 0)] for name, n in top},
        "months": {m: [by_month[m], by_month_c.get(m, 0)] for m in months},
        "authors_claude_all": dict(by_author_c),
    }


if __name__ == "__main__":
    print(json.dumps(golden(Path(sys.argv[1]), emails="--emails" in sys.argv[2:]), indent=2))
