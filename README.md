# Titan Receipts

[![CI](https://github.com/Rmasood1122/titan-gate-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/Rmasood1122/titan-gate-plugin/actions/workflows/ci.yml)

**An audit trail for AI-written code.** Every commit gets a tamper-evident
receipt — AI-assisted or not, which model, which Claude Code version, which
session, the file and diff hashes — hash-chained to the previous one,
HMAC-signed, and verifiable offline. One command turns the chain into the
compliance report your auditor asks for.

When someone asks *"which of these commits did the AI write, under what
tool, and can you prove this record hasn't been rewritten since?"*, most
teams have a process document. This gives you receipts.

```jsonc
// .titan/attestations/2026-10-03/74c11c58-….json  (abridged)
{
  "commit": { "sha": "629fca04…", "branch": "main", "subject": "feat: add handler",
              "author": "Dev <dev@example.com>", "committed_at": "2026-10-03T07:32:14-04:00" },
  "files": [ { "path": "app.py", "status": "M", "sha256": "bc16d440…" } ],
  "diff_sha256": "e95b93b0…",
  "provenance": {
    "ai_assisted": true,
    "basis": ["commit-trailers", "claude-code-hook"],
    "recorder": "claude-code-hook", "recorder_version": "1.2.0",
    "session_id": "7f3a…", "models": ["claude-sonnet-4-6"], "claude_code_version": "2.1.288",
    "transcript": { "lines": 412, "content_sha256": "2ef9732e…" }
  },
  "prev_receipt_hash": "GENESIS",
  "receipt_hash": "b9f069af…",
  "signature": "80265ea9…"
}
```

## Install

Requires [Claude Code](https://claude.com/claude-code), Python 3.10+, and git.
Nothing else — stdlib only, no packages, no network, no service, nothing
phones home.

```
/plugin marketplace add Rmasood1122/titan-gate-plugin
/plugin install titan-receipts@titan-receipts-marketplace
```

Or from your shell: `claude plugin marketplace add Rmasood1122/titan-gate-plugin &&
claude plugin install titan-receipts@titan-receipts-marketplace`. Confirm with
`/plugin list`; if `/receipt-init` isn't recognized, start a fresh session.

## First run

Open Claude Code **inside the repository you want receipts for**:

```
/receipt-init                    # one-time: signing key (gitignored), vendored verifier, git post-commit hook
git commit -m "…"                # every commit from now on is receipted — human or AI
/verify-chain                    # walks the chain offline; exit 0 means intact
/receipt-report                  # markdown evidence: AI-assisted share, by author/month, tooling, verification
```

Until you run `/receipt-init`, the plugin receipts nothing. The first time
Claude commits in a repo that isn't set up, you get a one-line notice saying
so — once per repo, never again, and it never sets anything up for you.
Set `TITAN_RECEIPTS_QUIET=1` to turn the notice off.

Receipts land in `.titan/attestations/`, the verifier in `.titan/tools/`.
Commit both; the key never. Git hooks aren't cloned, so each teammate runs
`python3 .titan/tools/receipt.py install-hook` once per clone.

## Commands

| Command | What it does |
|---|---|
| `/receipt-init` | Generates the signing key (gitignored — init refuses if git tracks it), vendors the verifier into `.titan/tools/`, installs a git `post-commit` hook. `--no-git-hook` to skip the hook. |
| `/receipt` | Writes a signed, chained receipt for HEAD by hand. One per commit; re-runs are no-ops. |
| `/verify-chain` | Walks the whole chain offline: structure + every signature. Any tamper = exit 1 naming the receipt. `--structure-only` checks chain and content hashes without the key and says signatures were not checked. Ends with an `ANCHOR` line: how many receipts are committed **and pushed**. |
| `/receipt-report` | Markdown report: receipted commits, AI-assisted share, by recorder / author / month, models and Claude Code versions recorded, chain verification result, and the limits footer. |

## Two hooks, full coverage

| Commit made… | Receipted by | `ai_assisted` | Extra detail |
|---|---|---|---|
| in a Claude Code session | plugin `PostToolUse` hook | `true` (basis: `claude-code-hook`, plus trailers if present) | session id, model(s), Claude Code version, transcript hash, tool-use id |
| from your own terminal | git `post-commit` hook (defers inside Claude Code) | from `Co-Authored-By`/`Claude-Session` trailers; otherwise `false` | author, timestamp |

Neither hook can break a commit: an uninitialized repo is a silent no-op,
and the git hook always exits 0. Commits made with neither hook installed
have no receipt — the report says so rather than counting them as human.

## Verify in CI

```yaml
- uses: Rmasood1122/titan-gate-plugin@v1.2.0
  with:
    key: ${{ secrets.TITAN_KEY }}       # omit for structure-only verification
    report: docs/ai-change-receipts.md  # optional
```

Without the key the action verifies chain structure and content hashes and
states plainly that signatures were not checked. The key is written only for
the step and removed after.

The action verifies with **its own pinned verifier** (the one at the ref you
pin `uses:` to), never the `.titan/tools/receipt.py` committed in the repo
under audit. That is the point: the party who could alter the receipts also
controls the vendored verifier, so letting it verify itself proves nothing.
Pin a ref you trust. The escape hatch `allow_repo_verifier: true` runs the
repo's own verifier for the rare canonicalization-compatibility case — it
emits a warning that the check is no longer independent, and you should treat
the result as self-reported.

## What a receipt proves — exactly, no more

**Proves:** the recorded content (file hashes, diff hash, author, provenance
claims) is unchanged since signing, and the receipts form one unbroken
ordered chain — under a key your team controls. Flip a single
`ai_assisted` flag and verification fails on that receipt.

<details>
<summary><strong>Does not prove</strong> — read before writing a compliance claim</summary>

- **Who held the key.** HMAC is a shared secret; anyone with `.titan/key`
  can produce valid signatures. Asymmetric signing and external timestamp
  anchoring are features of the upstream
  [titan-gate](https://github.com/Rmasood1122/titan-gate) engine, not this
  plugin.
- **That anyone reviewed the change**, or that it was good.
- **That provenance is true.** `ai_assisted`, model, version, session and
  transcript hash are **recorded claims**: trailers copied from the commit
  message, and what the Claude Code hook observed on the machine that made
  the commit. The chain proves they weren't edited afterwards, not that they
  were accurate when written.
- **Anything about un-receipted commits.** Coverage is as good as hook
  installation.
- **Ordering to anyone but you** until `.titan/attestations/` is committed
  and pushed. Because that distribution is the only defence against someone
  who holds the key, `/verify-chain` measures it: its closing `ANCHOR` line
  reports how many receipts are untracked, uncommitted, or
  committed-but-not-pushed. A chain that verifies but sits only on one
  machine is a claim, not evidence — every pushed clone then holds an
  independent copy that tampering would have to chase down.

### Verifying a clone that has no key

The key is gitignored and never travels with the repo, so a reviewer's fresh
clone has the receipts but not `.titan/key`. `/verify-chain` still runs the
full structural walk there — one unbroken chain from GENESIS, every stored
`receipt_hash` recomputed from content — and reports that result, then says
plainly `SIGNATURES NOT CHECKED` and exits 2. Structure proves the files are
internally consistent; only the key proves they were signed under it. Share
the key out-of-band with whoever needs to verify signatures.

The bundled `receipt-integrity` skill keeps compliance language inside these
lines, because a receipt system that overclaims is worse than none.
</details>

## Provenance

The canonicalization and chain-walk rules are vendored byte-compatible from
[titan-gate](https://github.com/Rmasood1122/titan-gate) (849 tests), whose
TRS receipt engine adds Ed25519 signing, RFC-3161 timestamping, Merkle
roots, and a scoring judge. This plugin is the lightweight attestation
profile of that system: `change-attestation/v1`, its own verifier, its own
tree. Suite: 53 tests, every tamper path seen failing. Related:
[eval-conductor](https://github.com/Rmasood1122/eval-conductor) — fail-closed
eval release gates by the same author.

## License

MIT
