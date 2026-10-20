# Changelog

## 1.3.0 — 2026-10-20

Renamed **Titan Receipts → CommitProof** (`commitproof`), with an answer
in the first minute. Installs were loading the plugin and producing nothing:
the only useful output came after `/receipt-init`, and on some Windows
machines the hooks could not run at all.

- **New: `/ai-history`.** "How much of this repo did Claude help write?" from
  the Claude trailers already in git history: commits and lines added, by
  author and month; `--since`, `--json`. Writes nothing, needs no key, and
  labels itself unsigned — a starting estimate, not evidence. The first-run
  notice and the skill now point to it.
- **New: `--badge FILE`** on `report` and `history`: a self-contained SVG and
  a README line linking back here. It says "chain verified" only when the
  chain is intact and every signature checks out, "structure only" without
  the key, "verification FAILED" with no share otherwise, and "unsigned" from
  trailers.
- **Fixed: hooks failed silently on Windows without `python3`.** The classic
  python.org installer ships `python.exe`/`py.exe` but no `python3.exe`, and
  the WindowsApps alias only prints a Store message. The plugin hook, the
  setup notice and the git post-commit hook now use the first Python 3.10+
  among `python3`, `python`, `py` (`core/py.sh`). Re-running `install-hook`
  upgrades a hook an older version wrote; `*.sh` is pinned to LF so an
  autocrlf clone cannot break the launcher.
- **Fixed: GitHub-style `Co-authored-by: Claude` counted as human.** Trailer
  keys are case-insensitive now, with one rule shared by receipts and history.
- **Fixed: Windows output encoding.** A piped stdout was cp1252, so dashes
  reached Claude Code as invalid UTF-8 and a non-Latin author name crashed
  `report`; `report --out` is now written as UTF-8. `--out` and `--badge`
  create missing folders.
- **Renamed** plugin, marketplace, action and messages to `commitproof`;
  the repo moves to `Rmasood1122/commitproof` (GitHub redirects the old
  URL). `.titan/` data paths are unchanged, so existing chains keep
  verifying; the old git-hook mark and `TITAN_RECEIPTS_QUIET` are still
  honoured. Switching an install: see the README's "Formerly Titan Receipts".
- README rebuilt around the two questions, with a real sample report and
  history output in `docs/` (from a demo repo, labelled as such).

## 1.2.0 — 2026-10-20

First-run fix. Directory stats showed thousands of plugin loads and zero
receipts: the hook ran on every Bash call, found no `.titan/key`, and exited
silently. Nobody was told the plugin needs a one-time `/receipt-init`.

- **New: one-time setup notice.** The first successful Claude-made commit in a
  repo without receipts shows the user a single line naming `/receipt-init`,
  and tells Claude not to run setup itself. Once per repo (recorded in the
  plugin's data dir, never in your repo); if that record can't be written the
  notice is skipped rather than repeated. `TITAN_RECEIPTS_QUIET=1` disables it.
  Commits still never break; an uninitialized repo still gets no files.
- **Changed: descriptions lead with the problem.** The skill now triggers on
  questions like "which commits did Claude write" and "SOC 2 change-control
  evidence", not only on the word "receipt"; it offers `/receipt-init` when the
  repo isn't set up. Manifest and marketplace copy rewritten the same way.

## 1.1.1 — 2026-10-05

Windows correctness. Found by making the test suite run on Windows for the
first time.

- **Fixed: receipts were platform-dependent on Windows.** `receipt.py` decoded
  git's output with the platform locale (cp1252 on Windows) instead of UTF-8.
  A non-ASCII filename (`café.py`) was recorded as `cafÃ©.py`, matched no
  file, and its content hash was silently dropped while `create` still
  exited 0 — the exact failure the `-z` parser exists to prevent, re-opened
  by decoding. `diff_sha256` for the same commit also differed between a
  receipt written on Windows and one written on Linux whenever the diff held
  a non-ASCII byte. All git calls now decode as UTF-8 explicitly. A new test
  compares the receipt's hashes against git's raw bytes with no text decoding
  at all, so this holds on every platform. Receipts already written on
  Windows for commits with non-ASCII paths or diffs attest the mangled
  values; they still verify (they are internally consistent) but do not match
  what Linux computes for that commit.
- **Tests run on Windows.** The suite's shell helpers used `shell=True`,
  which is cmd.exe on Windows — single quotes, `&&` chains and `VAR=x cmd`
  prefixes all broke, so 25 of 60 tests died at fixture setup and the suite
  could only be trusted on Linux. Helpers now run through a resolved POSIX
  shell (Git for Windows' bash; never System32's WSL launcher), paths fed to
  the shell use forward slashes, and the one NTFS-illegal filename case is
  skipped on Windows. CI now runs `windows-latest` alongside `ubuntu-latest`.

## 1.1.0 — 2026-10-03

Positioning: an audit trail for AI-written code, with the provenance auditors
actually ask about.

- **Provenance block** on every receipt: `ai_assisted` with its `basis`
  (commit trailers and/or the Claude Code hook), `recorder`, and — when
  written by the Claude Code hook — `session_id`, `tool_use_id`,
  `permission_mode`, `models` and `claude_code_version` read from the session
  transcript, plus the transcript's line count and sha256 at receipt time.
  All signed; flipping `ai_assisted` breaks verification. Environment is
  trusted only when `CLAUDECODE` is set.
- **Commit author and timestamp** recorded (`commit.author`, `commit.committed_at`).
- **Full coverage**: `init` vendors the verifier into `.titan/tools/` and
  installs a git `post-commit` hook, so human commits are receipted too
  (`ai_assisted: false`). The git hook defers inside Claude Code so the richer
  receipt wins; it never fails a commit. `install-hook` re-installs per clone;
  `init --no-git-hook` opts out.
- **`/receipt-report`**: markdown evidence — receipted commits, AI-assisted
  share, by recorder / author / month, models and tool versions, chain
  verification result, and a mandatory what-it-does-not-prove footer. v1.0
  receipts (no provenance) are reported as "unknown", never as human.
- **`verify --structure-only`**: chain + content hashes without the key, for
  CI clones that don't hold the secret; output states signatures were not checked.
- **GitHub Action** (`action.yml`): `uses: Rmasood1122/titan-gate-plugin@v1.1.0`
  with optional `key` secret and `report` path.
- README rewritten around the problem with a real receipt; limits in a
  collapsed section, expanded (coverage, recorded-claims). Skill updated to match.
- **Hook over-claim guard**: the PostToolUse hook now receipts only when the
  command was a real `git commit` (not `git log | grep commit`), the tool
  reported success, and HEAD is fresh — a failed commit in a Claude session
  can no longer receipt the human's existing HEAD as AI-assisted.
- `install-hook` refuses (exit 1, with instructions) when an existing
  post-commit hook is not a shell script, ends in `exit`/`exec`, or is
  husky-managed — never claims coverage it cannot deliver. `init` on an
  already-initialised repo now still vendors tools and installs the hook.
- Suite: 53 tests (was 25).

## 1.0.0

- Initial release: hash-chained HMAC receipts, fail-closed chain rules,
  PostToolUse auto-receipting, offline verification, receipt-integrity skill.
