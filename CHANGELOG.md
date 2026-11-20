# Changelog

## 2.0.0 — 2026-11-20

The plugin now does one thing: `/ai-history`, an estimate from commit trailers (unsigned) of how much of a repository Claude helped write, by author and by month. It ships as Markdown only. The plugin name stays `titan-receipts`.

### Removed, and why

Version 1.x needed Python, a setup step and hooks, so it could not run in many of the places it was installed. The Claude plugin directory accepts no hooks from unverified publishers and no program files in community plugins. 2.0.0 removes:

- Signed receipts: `/receipt-init`, `/receipt`, `/receipt-report`, `/verify-chain` and the receipt-integrity skill, with the signing step and everything that created or checked receipts.
- All plugin hooks, and the setup of a git post-commit hook.
- The Python engine and its tests, the GitHub Action, badges, `--json`, `--badge` and `--since`.
- The plugin's own marketplace file. Install from the Claude plugin directory.

### Changed

- `/ai-history` is now a set of read-only git commands that Claude runs, given in full in the README. Git does the counting, and Claude copies the numbers. Python is no longer needed.
- New `ai-history` skill: Claude answers "how much of this repo did Claude help write?" without the slash command. With no repository open, it says so and offers two ways to get the answer.
- A trailer now counts when its value starts with the word Claude, or when an `Assisted-by:` line has exactly the value `LLM`. 1.x matched "claude" or "anthropic" anywhere in the value.
- Output shows counts only, no percentages, so every number comes straight from a git command.

### Where 1.x lives

On branch `engine` and tag `v1.3.3-final` in this repository, with its full history, tests and changelog.

### If you used 1.x receipts

Repositories where you ran `/receipt-init` keep the git post-commit hook and the files that 1.x added. 2.0.0 does not read, run or remove them. To stop the hook, delete the block marked `titan-receipts post-commit hook` or `commitproof post-commit hook` from `.git/hooks/post-commit`.
