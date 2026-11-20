"""Score layer-2 runs by code: every number in Claude's answer against
golden.py, plus format, wording, tool-use and no-write checks.

Usage: python compare.py PLUGIN_DIR FIXTURES_DIR RUNS_DIR

A fixture / paste / nl run passes only if all of these hold:
  1 first line exact                      6 exactly 3 "does not show" bullets and the source line
  2 totals = golden                       7 no email, link, %, multiplier or banned word
  3 author rows = golden                  8 only read-only tools; Bash runs only shipped lines
  4 month rows = golden                   9 the working directory is unchanged
  5 three tables headed "With a Claude or LLM trailer"
                                          10 the plugin under test was loaded
nl runs must also invoke the ai-history skill. A norepo run must reply with
the step-4 text and the step-2 block, verbatim, and show no table.
Error labels: wrong-number, missing-row, format, policy, tool-misuse, trigger,
plugin, timeout, error. Prints a table and the Wilson 95% interval.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from block_check import blocks, text  # noqa: E402
from fixtures import isolated_env  # noqa: E402
from golden import golden  # noqa: E402

FIRST = "Estimate from commit trailers (unsigned)"
EMPTY = "No commits yet - nothing to count."
LABEL = "With a Claude or LLM trailer"
SOURCE = "Numbers copied from the git output above; git did the counting."
NOREPO = ["I can't see a git repository here, so I can't count yet. Two ways to get the answer:",
          "1. Open the repository in Claude Code or Cowork and ask again, or run /titan-receipts:ai-history there.",
          "2. In a terminal inside the repository (macOS or Linux, or Git Bash on Windows), "
          "run the commands below and paste the output here."]
BANNED = re.compile(r"compliant|certif|\bproofs?\b|\bproves?\b|tamper|audit-ready|audit trail|soc ?2|hipaa|\bpci\b"
                    r"|reviewed", re.I)
READ_ONLY_TOOLS = {"Bash", "Read", "Glob", "Grep", "Skill", "ToolSearch"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    denom = 1 + z * z / n
    return ((centre - margin) / denom, (centre + margin) / denom)


def load_run(path: Path) -> dict:
    run = {"result": None, "tools": [], "model": None, "cost": None, "usage": {}, "is_error": None, "init": {}}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            run["init"] = ev
            run["model"] = ev.get("model")
        elif ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []) or []:
                if block.get("type") == "tool_use":
                    run["tools"].append((block.get("name"), block.get("input", {})))
        elif ev.get("type") == "result":
            run["result"] = ev.get("result")
            run["cost"] = ev.get("total_cost_usd")
            run["usage"] = ev.get("usage") or {}
            run["is_error"] = ev.get("is_error")
    return run


def plugin_loaded(init: dict, plugin: Path) -> str:
    """'' if the plugin under test is loaded, else the reason."""
    plugins = init.get("plugins")
    if isinstance(plugins, list) and plugins:
        for p in plugins:
            if isinstance(p, dict) and p.get("name") == "titan-receipts":
                path = p.get("path") or ""
                if path and Path(path).resolve() != plugin.resolve():
                    return f"titan-receipts loaded from {path}, not the checkout under test"
                return ""
        return f"titan-receipts not in init plugins: {[p.get('name') for p in plugins if isinstance(p, dict)]}"
    cmds = init.get("slash_commands") or []
    if any("titan-receipts:ai-history" in str(c) for c in cmds):
        return ""
    return "init event lists neither the plugin nor its command"


def num(cell: str) -> int | str:
    """The cell as an integer; anything else (e.g. '141 (34%)') is kept as
    text so it can never equal a golden integer."""
    clean = cell.replace("*", "").replace("`", "").strip()
    return int(clean) if clean.isdigit() else clean


def cells(line: str) -> list[str]:
    return [c.strip().replace("**", "").replace("`", "") for c in line.strip().strip("|").split("|")]


def parse_answer(answer: str) -> dict:
    lines = [l.rstrip() for l in answer.replace("\r\n", "\n").split("\n")]

    def find(prefix: str) -> int:
        return next((i for i, l in enumerate(lines) if l.replace("**", "").lstrip("#> ").startswith(prefix)), -1)

    i_auth, i_month, i_not = find("By author"), find("By month"), find("What this does not show")
    got: dict = {"first": next((l for l in lines if l.strip()), "").strip(), "authors": {}, "months": {}}
    for line in lines[:i_auth if i_auth >= 0 else len(lines)]:
        if line.strip().startswith("|"):
            c = cells(line)
            if c[0] == "Commits":
                got["commits_all"], got["commits_claude"] = num(c[1]), num(c[2])
            elif c[0] == "Lines added":
                got["lines_all"], got["lines_claude"] = num(c[1]), num(c[2])
    if i_auth >= 0:
        m = re.search(r"By author:\s*([\d,]+)\s+authors", lines[i_auth].replace("**", ""))
        got["authors_all"] = num(m.group(1)) if m else None

    def table(a: int, b: int, header: str) -> dict:
        rows = {}
        for line in lines[a:b] if a >= 0 else []:
            if line.strip().startswith("|"):
                c = cells(line)
                if c[0] in (header, "") or set(c[0]) <= set("-: "):
                    continue
                rows[c[0]] = [num(c[1]), num(c[2])] if len(c) >= 3 else ["?", "?"]
        return rows

    got["authors"] = table(i_auth, i_month, "Author")
    got["months"] = table(i_month, i_not if i_not >= 0 else len(lines), "Month")
    bullets = 0
    for line in lines[i_not + 1:] if i_not >= 0 else []:
        if re.match(r"^\s*[-*] ", line):
            bullets += 1
        elif line.strip():
            break
    got["bullets"] = bullets
    got["headers"] = sum(1 for l in lines if l.strip().startswith("|") and cells(l)[-1] == LABEL)
    got["source"] = any(l.strip() == SOURCE for l in lines)
    return got


def allowed_bash(command: str, shipped: list[str]) -> str:
    """What is left of a Bash command after removing the shipped lines;
    harmless glue (cd into the run dir, separators, plain echo) is allowed.
    An empty string means the call ran only shipped commands."""
    rest = command.replace("\r\n", "\n")
    for line in sorted({ln for b in shipped for ln in b.splitlines()}, key=len, reverse=True):
        if line.strip():
            rest = rest.replace(line, "")
    rest = re.sub(r"(?m)^\s*cd\s+(\"[^\"]*\"|'[^']*'|\S+)\s*(&&|;)?", "", rest)
    rest = re.sub(r"echo\s+(\"[^\"$`>|]*\"|'[^'>|]*')", "", rest)
    rest = re.sub(r"2>&1|2>/dev/null|&&|\|\||;|\n", " ", rest)
    return rest.strip()


def without_shipped_blocks(answer: str, shipped_blocks: list[str]) -> str:
    """The answer with fenced blocks removed only where the block is exactly
    one of the shipped blocks (the no-repo reply repeats step 2 verbatim)."""
    def drop(m: re.Match) -> str:
        return "" if m.group(1) in shipped_blocks else m.group(0)
    return re.sub(r"```(?:sh|bash)?\n(.*?)```", drop, answer.replace("\r\n", "\n"), flags=re.S)


def policy_and_tools(run: dict, meta: dict, plugin: Path, shipped: list[str], answer: str) -> list[str]:
    errors = []
    answer = without_shipped_blocks(answer, shipped)
    for label, rx in (("email", r"[\w.+-]+@[\w-]+\.[\w.-]+"), ("link", r"https?://"), ("percent", r"%"),
                      ("multiplier", r"\b\d+(\.\d+)?x\b")):
        if re.search(rx, answer):
            errors.append(f"policy: {label} in answer")
    if BANNED.search(answer):
        errors.append(f"policy: banned word {BANNED.search(answer).group(0)!r}")
    for name, inp in run["tools"]:
        if name not in READ_ONLY_TOOLS:
            errors.append(f"tool-misuse: used {name}")
        elif name == "Bash":
            rest = allowed_bash(inp.get("command", ""), shipped)
            if rest:
                errors.append(f"tool-misuse: Bash ran more than the shipped commands: {rest[:120]!r}")
    if meta["state_before"] != meta["state_after"]:
        errors.append("tool-misuse: working directory changed")
    why = plugin_loaded(run["init"], plugin)
    if why:
        errors.append(f"plugin: {why}")
    return errors


def score_answer(got: dict, expect: dict) -> list[str]:
    errors = []
    if got["first"] != FIRST:
        errors.append(f"format: first line {got['first']!r}")
    for k in ("commits_all", "commits_claude", "lines_all", "lines_claude", "authors_all"):
        if got.get(k) != expect[k]:
            errors.append(f"wrong-number: {k} {got.get(k)} != {expect[k]}")
    for k in ("authors", "months"):
        if got[k] != expect[k]:
            kind = "missing-row" if set(got[k]) != set(expect[k]) else "wrong-number"
            errors.append(f"{kind}: {k} {got[k]} != {expect[k]}")
    if got["bullets"] != 3:
        errors.append(f"format: {got['bullets']} 'does not show' bullets")
    if got["headers"] != 3:
        errors.append(f"format: {got['headers']} table headers end with {LABEL!r}")
    if not got["source"]:
        errors.append("format: source line missing")
    return errors


def score(run: dict, meta: dict, expect: dict | None, plugin: Path, step2: str, shipped: list[str]) -> list[str]:
    if meta.get("exit") == "timeout":
        return ["timeout"]
    answer = run["result"]
    if answer is None or run["is_error"]:
        return [f"error: no result (exit {meta.get('exit')})"]
    errors = policy_and_tools(run, meta, plugin, shipped, answer)
    case = meta.get("case", "fixtures")
    if case == "norepo":
        lines = [l.rstrip() for l in answer.replace("\r\n", "\n").split("\n")]
        nonblank = [l.strip() for l in lines if l.strip()]
        if nonblank[:3] != NOREPO:
            errors.append(f"format: step-4 text differs: {nonblank[:3]!r}")
        fenced = re.findall(r"```(?:sh|bash)?\n(.*?)```", answer.replace("\r\n", "\n"), flags=re.S)
        if step2 not in fenced:
            errors.append("format: step-2 block not given verbatim")
        if re.search(r"(?m)^\s*\|", answer):
            errors.append("format: table shown with no repository")
        return errors
    try:
        got = parse_answer(answer)
    except (IndexError, ValueError, AttributeError) as exc:
        return errors + [f"format: answer could not be parsed ({exc})"]
    if expect["empty"]:
        if got["first"] != EMPTY:
            errors.append(f"format: first line {got['first']!r}")
        if "|" in answer:
            errors.append("format: table shown for an empty repository")
    else:
        errors += score_answer(got, expect)
    if case == "nl" and not any(n == "Skill" and "ai-history" in json.dumps(i) for n, i in run["tools"]):
        errors.append("trigger: the ai-history skill was not invoked")
    return errors


def main(plugin: Path, fixtures: Path, runs_dir: Path) -> int:
    env = isolated_env(fixtures / "_git")
    step1, step2, step2b = blocks(plugin)
    shipped = [step1, step2, step2b]
    expects: dict = {}
    rows, total, passed = [], 0, 0
    tokens = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
    cost = 0.0
    models = set()
    for meta_path in sorted(runs_dir.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        name = meta.get("fixture")
        if name and name not in expects:
            g = golden(fixtures / name, env=env)
            expects[name] = g
        run = load_run(runs_dir / f"{meta['tag']}.jsonl")
        errs = score(run, meta, expects.get(name), plugin, step2, shipped)
        total += 1
        passed += not errs
        u = run["usage"]
        tokens["input"] += u.get("input_tokens", 0) or 0
        tokens["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
        tokens["cache_write"] += u.get("cache_creation_input_tokens", 0) or 0
        tokens["output"] += u.get("output_tokens", 0) or 0
        cost += run["cost"] or 0.0
        models.add(run["model"])
        rows.append((meta["tag"], "PASS" if not errs else "FAIL", run["cost"], u.get("output_tokens"),
                     "; ".join(errs)))
    print("| run | result | cost USD | output tokens | errors |\n|---|---|---|---|---|")
    for tag, res, c, out, errs in rows:
        print(f"| {tag} | {res} | {c if c is None else round(c, 4)} | {out} | {errs} |")
    lo, hi = wilson(passed, total)
    print(f"\nexact runs: {passed}/{total}; Wilson 95% interval [{lo:.3f}, {hi:.3f}]")
    print(f"models: {sorted(m for m in models if m)}; tokens {tokens}; total cost USD {cost:.4f}")
    return 0 if total and passed == total else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])))
