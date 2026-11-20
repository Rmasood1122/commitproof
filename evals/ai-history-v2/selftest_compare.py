"""Offline self-test of compare.py: synthetic transcripts that must pass and
ones that must fail with a given label. No model calls, no cost.

Usage: python selftest_compare.py PLUGIN_DIR FIXTURES_DIR
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from block_check import blocks, render_layout  # noqa: E402
from compare import EMPTY, NOREPO, load_run, score  # noqa: E402
from fixtures import isolated_env  # noqa: E402
from golden import golden  # noqa: E402


def transcript(answer: str, tools: list[tuple[str, dict]], init: dict) -> str:
    evs = [{"type": "system", "subtype": "init", "model": "test-model", **init}]
    for name, inp in tools:
        evs.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}})
    evs.append({"type": "result", "result": answer, "total_cost_usd": 0.0, "usage": {}, "is_error": False})
    return "\n".join(json.dumps(e) for e in evs)


def main(plugin: Path, fixtures: Path) -> int:
    env = isolated_env(fixtures / "_git")
    step1, step2, step2b = blocks(plugin)
    shipped = [step1, step2, step2b]
    gc = golden(fixtures / "c", env=env)
    good = render_layout(gc)
    init_ok = {"plugins": [{"name": "titan-receipts", "path": str(plugin)}]}
    bash_ok = [("Bash", {"command": step1}), ("Bash", {"command": step2})]
    norepo_ok = "\n".join(NOREPO) + "\n\n```sh\n" + step2 + "```\n"
    state = {"status": "", "refs": "x", "config_sha256": None, "files": []}
    cases = [
        # (name, case, fixture, answer, tools, init, expected label or "" for pass)
        ("c good", "fixtures", "c", good, bash_ok, init_ok, ""),
        ("c good, plugin via slash_commands", "fixtures", "c", good, bash_ok,
         {"slash_commands": ["titan-receipts:ai-history"]}, ""),
        ("c wrong total", "fixtures", "c", good.replace("| Commits | 16 | 7 |", "| Commits | 16 | 8 |"), bash_ok,
         init_ok, "wrong-number"),
        ("c thousands separator", "fixtures", "c", good.replace("| 409 |", "| 4,09 |"), bash_ok, init_ok,
         "wrong-number"),
        ("c percentage", "fixtures", "c", good.replace("| Commits | 16 | 7 |", "| Commits | 16 | 7 (44%) |"),
         bash_ok, init_ok, "policy"),
        ("c missing month row", "fixtures", "c", good.replace("| 2026-10 | 4 | 2 |\n", ""), bash_ok, init_ok,
         "missing-row"),
        ("c preamble before first line", "fixtures", "c", "Here is the estimate.\n\n" + good, bash_ok, init_ok,
         "format"),
        ("c old label", "fixtures", "c", good.replace("With a Claude or LLM trailer", "With a Claude trailer"),
         bash_ok, init_ok, "format"),
        ("c no source line", "fixtures", "c", good.replace("Numbers copied from the git output above; "
                                                           "git did the counting.", ""), bash_ok, init_ok, "format"),
        ("c banned word", "fixtures", "c", good + "\nThis proves nothing.", bash_ok, init_ok, "policy"),
        ("c email shown", "fixtures", "c", good.replace("| Dana Lee |", "| Dana Lee <dana@example.com> |"),
         bash_ok, init_ok, "policy"),
        ("c extra bash", "fixtures", "c", good, bash_ok + [("Bash", {"command": "git log -p | head"})], init_ok,
         "tool-misuse"),
        ("c write tool", "fixtures", "c", good, bash_ok + [("Write", {"file_path": "x"})], init_ok, "tool-misuse"),
        ("c wrong plugin path", "fixtures", "c", good, bash_ok,
         {"plugins": [{"name": "titan-receipts", "path": str(Path(tempfile.gettempdir()))}]}, "plugin"),
        ("c plugin missing", "fixtures", "c", good, bash_ok, {"plugins": [{"name": "other", "path": "x"}]},
         "plugin"),
        ("f empty good", "fixtures", "f", EMPTY, [("Bash", {"command": step1})], init_ok, ""),
        ("f empty with table", "fixtures", "f", EMPTY + "\n| a | b |", [("Bash", {"command": step1})], init_ok,
         "format"),
        ("norepo good", "norepo", None, norepo_ok, [("Bash", {"command": step1})], init_ok, ""),
        ("norepo edited block", "norepo", None, norepo_ok.replace("head -n 15", "head -n 20"), [], init_ok,
         "format"),
        ("norepo counted anyway", "norepo", None, norepo_ok + "\n| Commits | 3 | 1 |", [], init_ok, "format"),
        ("paste good", "paste", "c", good, [], init_ok, ""),
        ("nl good", "nl", "c", good, [("Skill", {"skill": "titan-receipts:ai-history"})] + bash_ok, init_ok, ""),
        ("nl no skill", "nl", "c", good, bash_ok, init_ok, "trigger"),
    ]
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, case, fx, answer, tools, init, want) in enumerate(cases):
            p = Path(tmp) / f"{i}.jsonl"
            p.write_text(transcript(answer, tools, init), encoding="utf-8")
            meta = {"tag": name, "case": case, "fixture": fx, "exit": 0, "state_before": state, "state_after": state}
            expect = golden(fixtures / fx, env=env) if fx else None
            errs = score(load_run(p), meta, expect, plugin, step2, shipped)
            ok = (not errs) if not want else any(e.startswith(want) for e in errs)
            bad += not ok
            print(f"{'ok ' if ok else 'BAD'} {name}: want {want or 'pass'}; got {errs or 'pass'}")
    print(f"compare self-test: {'PASS' if not bad else f'FAIL ({bad})'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
