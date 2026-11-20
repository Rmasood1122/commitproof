# /ai-history 2.0.0 evals

These are the release tests for titan-receipts 2.0.0's `/ai-history`, which ships as Markdown on branch `v2-candidate`. They live here on `engine` because they are code. They need Python 3.10+ (stdlib only), git, and Git Bash on Windows.

## What is checked

- **Gates (`gate.py`, `gate2.sh`, `gate4.sh`).** Each check runs in Git Bash and is appended to `RELEASE-EVIDENCE-2.0.0.md` with:
  - the exact command
  - its raw output
  - the pass rule and the result
  - the UTC time
  - the branch and commit

  `gate2.sh` covers the directory's file and content rules. A control run on a repository with planted violations makes sure every check can fail. `gate4.sh` covers the docs, the tree, wording and `claude plugin validate --strict --profile directory`.
- **Layer 1: deterministic and free (`block_check.py`, run by `layer1.sh`).**
  - It runs the shipped git blocks exactly as written in every fixture and compares each number with `golden.py`, including step 2b (emails).
  - It checks that the method text in `commands/ai-history.md` and `skills/ai-history/SKILL.md` is identical, and that the README's command blocks are byte-identical to the command's.
  - Hostile config: a copy of fixture c with `log.showRoot=false` and `diff.relative=true`, run from a subdirectory, must still match. A control shows that plain git gives a different number there.
  - With `--real`, it also checks real repositories.
- **Layer 2: with the model (`run_claude.py` + `compare.py`).**
  - The gated runs are `claude -p "/titan-receipts:ai-history"` with the plugin checkout: 3 fresh sessions per fixture, 24 runs.
  - The extra modes are:
    - `norepo`: an empty folder
    - `paste`: a message that pastes fixture c's step-2 output
    - `nl`: "How much of this repo did Claude help write?" in fixture c
  - Every number in each answer is compared by code with `golden.py`. Each run is also checked for:
    - the first line, the three table headers, the three "does not show" bullets and the source line;
    - no email, link, percentage, multiplier or banned word;
    - only read-only tools, with Bash running only the shipped lines;
    - the working directory unchanged afterwards;
    - the plugin under test loaded from the checkout.
  - The gate is 24/24. The Wilson 95% interval is printed alongside: a perfect 24/24 gives [0.862, 1.000].
  - `selftest_compare.py` checks the scorer offline with synthetic transcripts that must pass or fail.
- **The oracle (`golden.py`).** It decides "has a Claude or LLM trailer" with a Python regex, and does every sum, grouping and ranking in Python. It is independent of the shipped `git --grep`, `shortlog`, `awk` and `sort | uniq` pipeline.

## Fixtures (`fixtures.py`)

Fixtures are deterministic: fixed names and dates, an empty global git config, and no system config.

| | Repository | Pins down |
|---|---|---|
| a | no trailers; a binary file; "Generated with Claude Code" in a body | 0 counted commits; body text is not a trailer |
| b | every commit has a Claude trailer, four are session links | no links in the answer |
| c | two `--no-ff` merges with trailers; Claudette and Jean-Claude co-authors; a pure rename | merges skipped; name boundary; rename adds 0 |
| d | `Assisted-by:` only: Claude values, `LLM` (plain, CRLF, lowercase with spaces), `LLM:gpt-4o`, `LLMs`, `GitHub Copilot`, `Anthropic Claude` | only values starting with Claude, or exactly LLM, count |
| e | lowercase, no space, tab, space before colon, CRLF, indented trailer, body-quoted trailer | letter case and spacing |
| f | empty repository | "No commits yet" |
| g | 5,000 commits, 20 authors, 30 months | top-15 authors, last 12 months, scale |
| h | squash merges, rebase across a month, cherry-pick, amend | squash and rebase behaviour |

## Run

From a checkout of `engine`, with a worktree of `v2-candidate` at `$WT`:

```sh
bash evals/ai-history-v2/layer1.sh "$WT" /tmp/fx                          # layer 1 (builds fixtures)
python evals/ai-history-v2/selftest_compare.py "$WT" /tmp/fx              # scorer self-test
python evals/ai-history-v2/run_claude.py "$WT" /tmp/fx /tmp/runs          # layer 2: 24 model runs, costs money
python evals/ai-history-v2/run_claude.py "$WT" /tmp/fx /tmp/runs --mode norepo   # extras: norepo, paste, nl
python evals/ai-history-v2/compare.py "$WT" /tmp/fx /tmp/runs             # score
```

`run_claude.py` refuses to start in two cases:
- an installed commitproof or titan-receipts plugin is enabled;
- the runs folder is inside a git repository.

Each run is capped at $1 with `--max-budget-usd`. Your own `~/.claude/CLAUDE.md` still loads, because excluding it needs `--bare`, which needs an API key. That makes the runs stricter, not looser.
