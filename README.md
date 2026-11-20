# Titan Receipts

How much of this repo did Claude help write? This plugin answers from the git history you already have: an estimate from commit trailers (unsigned), by author and by month. There is one command and nothing to set up:

```
/ai-history
```

It's for developers and team leads who write code with Claude and want a number they can trace back to git. The plugin's name is `titan-receipts`, so the full command is `/titan-receipts:ai-history`. You can also just ask Claude "how much of this repo did Claude help write?". Install it from the Claude plugin directory.

## What you get

A sample from one of the test repositories used for this release. The answer was rendered by code from that repository's git history:

> Estimate from commit trailers (unsigned)
>
> Non-merge commits reachable from HEAD.
>
> | | All commits | With a Claude or LLM trailer |
> |---|---|---|
> | Commits | 16 | 7 |
> | Lines added | 409 | 141 |
>
> By author: 3 authors, up to 15 shown
>
> | Author | Commits | With a Claude or LLM trailer |
> |---|---|---|
> | Dana Lee | 6 | 1 |
> | Priya Nair | 5 | 4 |
> | Sam Ortiz | 5 | 2 |
>
> By month (commit date): up to the 12 latest months with commits
>
> | Month | Commits | With a Claude or LLM trailer |
> |---|---|---|
> | 2026-09 | 7 | 3 |
> | 2026-10 | 4 | 2 |
> | 2026-11 | 5 | 2 |
>
> What this does not show
> - Which lines Claude typed: this counts whole commits that carry a Claude or LLM trailer, and the lines added in them.
> - Commits where trailers were switched off or removed: they count as without a Claude or LLM trailer.
> - Squash merges: if the squashed message dropped the trailers, that work counts as without a Claude or LLM trailer.
>
> Numbers copied from the git output above; git did the counting.

## How it counts

A commit counts as "with a Claude or LLM trailer" when a line of its message starts with `Co-Authored-By: Claude`, `Assisted-by: Claude`, `Assisted-by: LLM` (that exact value) or `Claude-Session:`, in any letter case. Merge commits are skipped. Git does the counting. `awk`, `sort`, `uniq`, `head`, `tail` and `wc` only total or trim git's output, and Claude copies the numbers into the tables without doing any arithmetic. Full rules and known miscounts: [skills/ai-history/reference/trailers.md](skills/ai-history/reference/trailers.md).

## Exactly what it runs, reads, writes and sends

**Runs:** the commands below and nothing else. Claude Code shows each command before it runs, and asks first according to your permission settings.

Step 1, is there a repository:

```sh
git rev-parse --is-inside-work-tree
git rev-parse --verify -q HEAD
git rev-parse --is-shallow-repository
```

Step 2, the counts:

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

Only if you ask for emails:

```sh
echo "== authors_all (top 15)"; git shortlog -s -n -e --no-merges HEAD | head -n 15
echo "== authors_claude"; git shortlog -s -n -e --no-merges -i -E --grep='^((co-authored-by|assisted-by)[[:space:]]*:[[:space:]]*claude([^[:alpha:]]|$)|assisted-by[[:space:]]*:[[:space:]]*llm[[:space:]]*$|claude-session[[:space:]]*:)' HEAD
```

- **Reads:** the git history of the repository you have open: commit messages (git searches them for trailers; they are never shown), author names, commit dates and per-file counts of added lines. Author emails are read only if you ask for them. Git also reads its usual settings and the repository's `.mailmap` file.
- **Writes:** nothing. No files, no git settings, no hooks.
- **Sends:** nothing. The plugin makes no network calls and has no server, account, analytics or telemetry. Like any command Claude runs, the output (counts, author names, months) becomes part of your Claude conversation.
- **Without a repository** (for example in a Claude chat), it says so and offers two ways forward: open the repository in Claude Code or Cowork, or run the same commands yourself and paste the output.

## Limits

- An estimate from unsigned commit trailers. Anyone can add, remove or rewrite a trailer.
- It counts commits that carry a Claude or LLM trailer and the lines added in them, not which lines Claude typed.
- Commits where trailers were switched off or removed count as without a Claude or LLM trailer.
- An `Assisted-by: LLM` trailer names no model, so those commits may not involve Claude at all.
- Squash merges keep only the squashed message.
- Months use the commit date, so rebased commits move to the month of the rebase.
- Shallow clones count only the history that was fetched.
- One person under two names shows as two authors unless `.mailmap` merges them.
- Needs git 2.28 or later and a POSIX shell (bash or zsh). On Windows, that is Git Bash, which comes with Git for Windows.
- Very long histories can take minutes, because git reads every commit's changes to count lines.

## Earlier versions

Versions 1.x also wrote signed receipts through hooks and a Python engine. 2.0.0 removed them; see [CHANGELOG.md](CHANGELOG.md).

Source and issues: https://github.com/Rmasood1122/commitproof · License: MIT
