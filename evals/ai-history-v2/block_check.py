"""Layer 1: run the shipped git commands exactly as written and compare
every number with golden.py. No model involved, no cost.

Usage: python block_check.py PLUGIN_DIR FIXTURES_DIR [--real REPO ...]

Checks, each printed with PASS/FAIL:
1. The method text (from "## Rules" to the end of step 4) is the same in
   commands/ai-history.md and skills/ai-history/SKILL.md; if README.md
   exists, its sh blocks are byte-identical to the command's sh blocks.
2. In every fixture: step 1, then the step-2 block, compared number by number
   with golden.py; the step-2b block (emails), compared with golden.py.
3. Hostile config: a copy of fixture c with log.showRoot=false and
   diff.relative=true, run from a subdirectory, must still equal golden(c).
4. --real REPO: the block against golden.py on real repositories, under the
   user's own git config (read-only).
Exit 0 only when every check passes.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fixtures import isolated_env, rm_tree  # noqa: E402
from golden import golden  # noqa: E402

LABEL = "With a Claude or LLM trailer"
KEYS = ("commits_all", "commits_claude", "lines_all", "lines_claude", "authors_all", "authors", "months")


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def method(md: str) -> str:
    """'## Rules' up to (not including) '## Limits', without trailing blank lines."""
    start = md.index("\n## Rules\n") + 1
    end = md.find("\n## Limits\n", start)
    return (md[start:] if end < 0 else md[start:end + 1]).rstrip("\n")


def sh_blocks(md: str) -> list[str]:
    return re.findall(r"^```sh\n(.*?)^```$", md, flags=re.S | re.M)


def blocks(plugin: Path) -> tuple[str, str, str]:
    """Step 1, step 2 and step 2b blocks of the command file."""
    b = sh_blocks(text(plugin / "commands" / "ai-history.md"))
    assert len(b) == 3, f"expected 3 sh blocks in the command, found {len(b)}"
    assert b[1].startswith('echo "commits_all ') and b[2].startswith('echo "== authors_all'), "unexpected block order"
    return b[0], b[1], b[2]


def bash_exe() -> str:
    for cand in (r"C:\Program Files\Git\bin\bash.exe", shutil.which("bash")):
        if cand and Path(cand).exists() and "System32" not in cand:
            return cand
    raise SystemExit("no POSIX bash found (Git Bash on Windows)")


def run_sh(script: str, cwd: Path, env: dict | None) -> tuple[int, str]:
    env = dict(env if env is not None else os.environ)
    git_usr = Path(bash_exe()).parent.parent / "usr" / "bin"
    if git_usr.exists():  # POSIX sort/uniq/awk/head, not Windows sort.exe
        env["PATH"] = str(git_usr) + os.pathsep + env.get("PATH", "")
    r = subprocess.run([bash_exe(), "-c", script], cwd=cwd, env=env, capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


def parse_block(out: str) -> dict:
    """Parse labelled output: 'key N' totals, then '== list' sections whose
    lines are 'N<space or tab>value' (uniq -c and shortlog -s)."""
    res: dict = {"lists": {}}
    section = None
    for line in out.replace("\r\n", "\n").splitlines():
        if line.startswith("== "):
            section = line[3:].split(" ")[0]
            res["lists"][section] = {}
        elif section is None:
            key, _, val = line.partition(" ")
            res[key] = int(val.strip())
        elif line.strip():
            m = re.match(r"^\s*(\d+)[ \t](.*)$", line)
            if not m:
                raise ValueError(f"unparsed line in {section}: {line!r}")
            res["lists"][section][m.group(2)] = int(m.group(1))
    return res


def as_golden_shape(p: dict) -> dict:
    """What a correct step-3 answer would show, built only from block output."""
    L = p["lists"]
    return {
        "commits_all": p["commits_all"], "commits_claude": p["commits_claude"],
        "lines_all": p["lines_all"], "lines_claude": p["lines_claude"], "authors_all": p["authors_all"],
        "authors": {a: [n, L["authors_claude"].get(a, 0)] for a, n in L["authors_all"].items()},
        "months": {m: [n, L["months_claude"].get(m, 0)] for m, n in L["months_all"].items()},
    }


def project(g: dict) -> dict:
    return {k: g[k] for k in KEYS}


def emails_shape(p: dict) -> dict:
    L = p["lists"]
    return {"top": L["authors_all"], "claude": L["authors_claude"]}


def emails_golden(g: dict) -> dict:
    return {"top": {a: v[0] for a, v in g["authors"].items()}, "claude": g["authors_claude_all"]}


def render_layout(g: dict) -> str:
    """The step-3 layout filled in by code (used for the README sample)."""
    out = ["Estimate from commit trailers (unsigned)", "",
           "Non-merge commits reachable from HEAD.", "",
           f"| | All commits | {LABEL} |", "|---|---|---|",
           f"| Commits | {g['commits_all']} | {g['commits_claude']} |",
           f"| Lines added | {g['lines_all']} | {g['lines_claude']} |", "",
           f"By author: {g['authors_all']} authors, up to 15 shown", "",
           f"| Author | Commits | {LABEL} |", "|---|---|---|"]
    out += [f"| {a} | {n} | {c} |" for a, (n, c) in g["authors"].items()]
    out += ["", "By month (commit date): up to the 12 latest months with commits", "",
            f"| Month | Commits | {LABEL} |", "|---|---|---|"]
    out += [f"| {m} | {n} | {c} |" for m, (n, c) in g["months"].items()]
    out += ["", "What this does not show",
            "- Which lines Claude typed: this counts whole commits that carry a Claude or LLM trailer, "
            "and the lines added in them.",
            "- Commits where trailers were switched off or removed: they count as without a Claude or LLM trailer.",
            "- Squash merges: if the squashed message dropped the trailers, that work counts as without a "
            "Claude or LLM trailer.",
            "", "Numbers copied from the git output above; git did the counting."]
    return "\n".join(out)


def check(label: str, ok: bool, detail: str = "") -> int:
    print(f"{label}: {'PASS' if ok else 'FAIL'}{('  ' + detail) if detail else ''}")
    return 0 if ok else 1


def run_block(block: str, repo: Path, env: dict | None, cwd: Path | None = None) -> tuple[int, dict | None, str]:
    rc, out = run_sh(block, cwd or repo, env)
    try:
        return rc, parse_block(out), out
    except (ValueError, KeyError) as exc:
        return rc, None, out + f"\n[parse error: {exc}]"


def main(argv: list[str]) -> int:
    plugin, fixtures = Path(argv[0]), Path(argv[1])
    real = [Path(p) for p in argv[argv.index("--real") + 1:]] if "--real" in argv else []
    env = isolated_env(fixtures / "_git")
    failures = 0
    cmd_md, skill_md = text(plugin / "commands" / "ai-history.md"), text(plugin / "skills" / "ai-history" / "SKILL.md")
    failures += check("method text identical in command and skill", method(cmd_md) == method(skill_md))
    step1, block, block2b = blocks(plugin)
    readme = plugin / "README.md"
    if readme.exists():
        failures += check("README sh blocks byte-identical to the command's", sh_blocks(text(readme)) == [step1, block, block2b])

    for name in "abcdefgh":
        repo = fixtures / name
        rc, out1 = run_sh(step1, repo, env)
        expect = golden(repo, env=env)
        if expect["empty"]:
            lines = out1.replace("\r\n", "\n").splitlines()
            failures += check(f"{name}: empty repository, step 1 prints true, nothing, false",
                              lines == ["true", "false"], repr(lines))
            continue
        ok1 = out1.replace("\r\n", "\n").splitlines() == ["true", git_head(repo, env), "false"]
        rc, parsed, out = run_block(block, repo, env)
        got = as_golden_shape(parsed) if parsed else None
        ok = rc == 0 and ok1 and got == project(expect)
        failures += check(f"{name}: step 1 + block: commits {expect['commits_all']}/{expect['commits_claude']} "
                          f"lines {expect['lines_all']}/{expect['lines_claude']} authors {expect['authors_all']} "
                          f"months {len(expect['months'])}", ok)
        if not ok:
            print("  expected:", project(expect), "\n  got:     ", got, "\n  raw:\n" + out)
        rc, parsed, out = run_block(block2b, repo, env)
        eg = emails_golden(golden(repo, env=env, emails=True))
        ok = rc == 0 and parsed is not None and emails_shape(parsed) == eg
        failures += check(f"{name}: step 2b (emails) equals golden", ok)
        if not ok:
            print("  expected:", eg, "\n  raw:\n" + out)

    # Hostile config: copy of fixture c, config that would change the counts, run from a subdirectory.
    hostile = fixtures / "_hostile_c"
    rm_tree(hostile)
    shutil.copytree(fixtures / "c", hostile)
    for k, v in (("log.showRoot", "false"), ("diff.relative", "true")):
        subprocess.run(["git", "config", k, v], cwd=hostile, env=env, check=True)
    rc, parsed, out = run_block(block, hostile, env, cwd=hostile / "data")
    expect = project(golden(fixtures / "c", env=env))
    ok = rc == 0 and parsed is not None and as_golden_shape(parsed) == expect
    failures += check("hostile config (log.showRoot=false, diff.relative=true, run in data/) equals golden(c)", ok)
    if not ok:
        print("  expected:", expect, "\n  raw:\n" + out)
    # Control: without the block's overrides, the same config does change the count.
    rc, plain = run_sh("git log --no-merges -M --no-textconv --numstat --format= HEAD | "
                       "awk -F'\\t' '$1 ~ /^[0-9]+$/ { s += $1 } END { printf \"%.0f\\n\", s }'", hostile / "data", env)
    failures += check("control: plain git log under that config gives a different lines total",
                      plain.strip() != str(expect["lines_all"]), f"plain={plain.strip()} block={expect['lines_all']}")

    for repo in real:
        rc, parsed, out = run_block(block, repo, None)
        expect = project(golden(repo))
        ok = rc == 0 and parsed is not None and as_golden_shape(parsed) == expect
        failures += check(f"real repo {repo.name}: commits {expect['commits_all']}/{expect['commits_claude']} "
                          f"lines {expect['lines_all']}/{expect['lines_claude']} authors {expect['authors_all']}", ok)
        if not ok:
            print("  expected:", expect, "\n  raw:\n" + out)

    print(f"layer 1: {'PASS' if not failures else f'FAIL ({failures})'}")
    return 1 if failures else 0


def git_head(repo: Path, env: dict) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, env=env, capture_output=True).stdout.decode().strip()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
