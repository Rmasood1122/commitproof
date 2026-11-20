# /ai-history 2.0.0 evals

Release tests for CommitProof 2.0.0's `/ai-history`, which ships as Markdown on branch `v2-candidate`. They live here on `engine` because they are code. Python 3.10+ stdlib, git, and Git Bash on Windows.

## What is checked

- **Layer 1, deterministic and free (`block_check.py`).** It runs the shipped git commands exactly as written in every fixture and compares each number with `golden.py`. It also checks that the method text in `commands/ai-history.md` and `skills/ai-history/SKILL.md` is identical, and runs the `--since` path once.
- **Layer 2, with the model (`run_claude.py` + `compare.py`).** It runs `claude -p "/ai-history"` with the exported plugin, 3 fresh sessions per fixture, 24 runs. Every number in each answer is compared by code with `golden.py`. Each run is also checked for:
  - the first line;
  - the three "does not show" bullets;
  - no email, link, percentage, multiplier or banned word;
  - only read-only tools, with Bash running only the shipped commands;
  - the fixture unchanged afterwards.

  The gate is 24/24, and the Wilson 95% interval is printed alongside.
- **The oracle (`golden.py`).** It decides "has a Claude trailer" with a Python regex and does every sum and grouping in Python. It is independent of the shipped `git --grep`, `awk` and `sort | uniq` pipeline.

## Fixtures (`fixtures.py`)

Fixtures are deterministic: fixed names and dates, an empty global git config, and no system config.

| | Repository | Pins down |
|---|---|---|
| a | no trailers; a binary file; "Generated with Claude Code" in a body | 0 Claude commits; body text is not a trailer |
| b | every commit has a Claude trailer, four are session links | no links in the answer |
| c | two `--no-ff` merges with trailers; Claudette and Jean-Claude co-authors; a pure rename | merges skipped; name boundary; rename adds 0 |
| d | `Assisted-by:` only, incl. `LLM`, `GitHub Copilot`, `Anthropic Claude` | only values starting with Claude count |
| e | lowercase, no space, tab, space before colon, CRLF, indented trailer, body-quoted trailer | letter case and spacing |
| f | empty repository | "No commits yet" |
| g | 5,000 commits, 20 authors, 30 months | top-15 authors, last 12 months, scale |
| h | squash merges, rebase across a month, cherry-pick, amend | squash and rebase behaviour |

## Run

From a checkout of `engine`, with the plugin exported from `v2-candidate`:

```sh
git archive v2-candidate | tar -x -C /tmp/plugin-v2
python evals/ai-history-v2/fixtures.py /tmp/fx
python evals/ai-history-v2/block_check.py /tmp/plugin-v2 /tmp/fx            # layer 1
python evals/ai-history-v2/run_claude.py /tmp/plugin-v2 /tmp/fx /tmp/runs   # layer 2: 24 model runs, costs money
python evals/ai-history-v2/compare.py /tmp/plugin-v2 /tmp/fx /tmp/runs      # score
```

`run_claude.py` refuses to start while an installed commitproof or titan-receipts plugin is enabled. Each run is capped at $1 with `--max-budget-usd`.
