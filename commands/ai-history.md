---
description: How much of this repo did Claude help write? An estimate from commit trailers (unsigned), by author and by month, from read-only git commands. No setup; writes nothing.
---

This command takes no arguments. If any were given, say in one line that they were ignored, then continue.

## Rules

- Run only the commands in steps 1, 2 and 2b, exactly as written, with a bash or zsh shell tool (on Windows, Git Bash). They only read git history. If no such shell tool is available here, go to step 4.
- Git does the counting. Copy every number exactly as printed. Never count, add, subtract, round or estimate a number yourself, and never show a number that is not in the output.
- Show author names only. Show emails only if the user asks for them; then run step 2b and use its two lists in place of the author lists of step 2.
- Never show commit messages, commit hashes or links taken from commit messages.
- Which trailers count, and why: the ai-history skill's reference/trailers.md.

## Step 1: is there a repository?

```sh
git rev-parse --is-inside-work-tree
git rev-parse --verify -q HEAD
git rev-parse --is-shallow-repository
```

- If the first command does not print `true` (no repository, or no git), go to step 4. If git reports "dubious ownership", say in one line that git declined to read this folder because of who owns it, change no git setting, and go to step 4.
- If the second command prints nothing, reply `No commits yet - nothing to count.` and stop.
- If the third command prints `true`, put `Shallow clone: only the history fetched to this machine was counted.` on the second line of the answer.

## Step 2: count

Run this block as one command, exactly as written. If it fails, quote its first error line and stop. If it has not finished after 10 minutes, say the history is too large to count here and stop.

```sh
echo "commits_all $(git rev-list --count --no-merges HEAD)"
echo "commits_claude $(git rev-list --count --no-merges -i -E --grep='^((co-authored-by|assisted-by)[[:space:]]*:[[:space:]]*claude([^[:alpha:]]|$)|assisted-by[[:space:]]*:[[:space:]]*llm[[:space:]]*$|claude-session[[:space:]]*:)' HEAD)"
echo "lines_all $(git -c log.showRoot=true -c log.showSignature=false log --no-merges --no-relative -M --no-textconv --numstat --format= HEAD | awk -F'\t' '$1 ~ /^[0-9]+$/ { s += $1 } END { printf "%.0f\n", s }')"
echo "lines_claude $(git -c log.showRoot=true -c log.showSignature=false log --no-merges --no-relative -M --no-textconv --numstat --format= -i -E --grep='^((co-authored-by|assisted-by)[[:space:]]*:[[:space:]]*claude([^[:alpha:]]|$)|assisted-by[[:space:]]*:[[:space:]]*llm[[:space:]]*$|claude-session[[:space:]]*:)' HEAD | awk -F'\t' '$1 ~ /^[0-9]+$/ { s += $1 } END { printf "%.0f\n", s }')"
echo "authors_all $(git shortlog -s --no-merges HEAD | wc -l)"
echo "== authors_all (top 15)"; git shortlog -s -n --no-merges HEAD | head -n 15
echo "== authors_claude"; git shortlog -s -n --no-merges -i -E --grep='^((co-authored-by|assisted-by)[[:space:]]*:[[:space:]]*claude([^[:alpha:]]|$)|assisted-by[[:space:]]*:[[:space:]]*llm[[:space:]]*$|claude-session[[:space:]]*:)' HEAD
echo "== months_all (last 12)"; git -c log.showSignature=false log --no-merges --date=format:%Y-%m --format=%cd HEAD | sort | uniq -c | tail -n 12
echo "== months_claude (last 12)"; git -c log.showSignature=false log --no-merges -i -E --grep='^((co-authored-by|assisted-by)[[:space:]]*:[[:space:]]*claude([^[:alpha:]]|$)|assisted-by[[:space:]]*:[[:space:]]*llm[[:space:]]*$|claude-session[[:space:]]*:)' --date=format:%Y-%m --format=%cd HEAD | sort | uniq -c | tail -n 12
```

## Step 2b: emails, only if the user asks for them

```sh
echo "== authors_all (top 15)"; git shortlog -s -n -e --no-merges HEAD | head -n 15
echo "== authors_claude"; git shortlog -s -n -e --no-merges -i -E --grep='^((co-authored-by|assisted-by)[[:space:]]*:[[:space:]]*claude([^[:alpha:]]|$)|assisted-by[[:space:]]*:[[:space:]]*llm[[:space:]]*$|claude-session[[:space:]]*:)' HEAD
```

## Step 3: answer in this layout

Write the answer as Markdown, not inside a code block. Fill each angle bracket from the step 2 output:
- Add one author row for each line under `authors_all (top 15)`, in that order. Take the second column from the same name under `authors_claude`, or `0` if the name is not there.
- Add one month row for each line under `months_all (last 12)`, oldest first. Take the second column from `months_claude`, or `0`.
- Copy numbers with no separators.

```text
Estimate from commit trailers (unsigned)

Non-merge commits reachable from HEAD.

| | All commits | With a Claude or LLM trailer |
|---|---|---|
| Commits | <commits_all> | <commits_claude> |
| Lines added | <lines_all> | <lines_claude> |

By author: <authors_all> authors, up to 15 shown

| Author | Commits | With a Claude or LLM trailer |
|---|---|---|
| <name> | <count> | <count with a Claude or LLM trailer> |

By month (commit date): up to the 12 latest months with commits

| Month | Commits | With a Claude or LLM trailer |
|---|---|---|
| <YYYY-MM> | <count> | <count with a Claude or LLM trailer> |

What this does not show
- Which lines Claude typed: this counts whole commits that carry a Claude or LLM trailer, and the lines added in them.
- Commits where trailers were switched off or removed: they count as without a Claude or LLM trailer.
- Squash merges: if the squashed message dropped the trailers, that work counts as without a Claude or LLM trailer.

Numbers copied from the git output above; git did the counting.
```

Describe the result only as an estimate from commit trailers, for example "commits with a Claude or LLM trailer". Add no percentage, ratio, multiplier or other claim about the code.

## Step 4: no repository

Reply with exactly this text, then the step 2 block, exactly as written, in a `sh` code block:

```text
I can't see a git repository here, so I can't count yet. Two ways to get the answer:
1. Open the repository in Claude Code or Cowork and ask again, or run /titan-receipts:ai-history there.
2. In a terminal inside the repository (macOS or Linux, or Git Bash on Windows), run the commands below and paste the output here.
```

When the user pastes output:
- If it has the lines from `commits_all` through `== months_claude (last 12)`, answer with step 3 using only the pasted numbers.
- If it shows an error instead, quote the first error line and stop.
- If it is anything else, for example raw `git log` output, don't count it. Ask for the output of the commands above.
