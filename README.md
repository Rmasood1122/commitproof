Works in Claude Code. To install, run these two commands in a Claude Code session:

```
/plugin marketplace add Rmasood1122/commitproof
/plugin install commitproof@commitproof
```

# CommitProof

[![CI](https://github.com/Rmasood1122/commitproof/actions/workflows/ci.yml/badge.svg)](https://github.com/Rmasood1122/commitproof/actions/workflows/ci.yml)

**An AI audit trail for your commits.** Know which commits AI wrote, and
prove the record wasn't rewritten.

Teams using Claude Code get asked two questions:

1. **"How much of this did the AI write?"** `/ai-history` answers in seconds
   from the git history you already have. No setup, no key, writes nothing.
2. **"Can you prove that record hasn't been edited since?"** `/receipt-init`
   gives every commit from then on a tamper-evident receipt: hash-chained,
   signed, verifiable offline. `/receipt-report` turns the chain into a
   change-control report you can give a SOC 2, HIPAA or PCI auditor as
   supporting evidence.

## Try it in 30 seconds

```
/plugin marketplace add Rmasood1122/commitproof
/plugin install commitproof@commitproof
```

Then, in any repository:

```
/ai-history
```

```markdown
| | commits | lines added |
|---|---|---|
| Scanned (non-merge) | 7 | 749 |
| With a Claude trailer | 4 (57%) | 605 (81%) |

## By author

| author | commits | with a Claude trailer |
|---|---|---|
| Dana Lee <dana@example.com> | 3 | 0 (0%) |
| Priya Nair <priya@example.com> | 2 | 2 (100%) |
| Sam Ortiz <sam@example.com> | 2 | 2 (100%) |
```

([full sample](docs/sample-ai-history.md), from a demo repo.) It reads the
`Co-Authored-By: Claude …` and `Claude-Session:` trailers Claude Code already
puts on commits (and the Linux kernel's `Assisted-by: Claude:…` form), so it labels itself **unsigned**: a starting estimate, not
evidence. Trailers are plain text and history can be rewritten. That gap is
what receipts close.

## Make it evidence

Open Claude Code **inside the repository you want receipts for**:

```
/receipt-init                    # one-time: signing key (gitignored), vendored verifier, git post-commit hook
git commit -m "…"                # every commit from now on is receipted, human or AI
/verify-chain                    # walks the chain offline; exit 0 means intact
/receipt-report --badge docs/ai-audit-badge.svg
```

`/receipt-report` writes the evidence document: verification result first,
then AI-assisted share by author, month and recorder, and the models and
Claude Code versions recorded. **[See a sample report](docs/sample-report.md).**

Each receipt is one small JSON file in `.titan/attestations/`:

```jsonc
{
  "commit": { "sha": "629fca04…", "subject": "feat: add handler",
              "author": "Dev <dev@example.com>", "committed_at": "2026-10-03T07:32:14-04:00" },
  "files": [ { "path": "app.py", "status": "M", "sha256": "bc16d440…" } ],
  "diff_sha256": "e95b93b0…",
  "provenance": { "ai_assisted": true, "basis": ["commit-trailers", "claude-code-hook"],
                  "models": ["claude-opus-5-5"], "claude_code_version": "2.1.299",
                  "session_id": "7f3a…", "transcript": { "lines": 412, "content_sha256": "2ef9732e…" } },
  "prev_receipt_hash": "b9f069af…",
  "receipt_hash": "c41d0e7b…",
  "signature": "80265ea9…"
}
```

Edit any recorded field (flip one `ai_assisted` flag) or delete a receipt from
the middle of the chain, and `/verify-chain` fails and names the receipt.

## Put it on your README

`--badge` writes a self-contained SVG (no badge service, nothing phones home)
and prints the README line:

![AI-assisted: 50% · chain verified](docs/badge-verified.svg) &nbsp;
![AI-assisted: 54% of commits · unsigned](docs/badge-unsigned.svg)

The badge can't say more than the check behind it. It says **chain verified**
only when the chain is intact and every signature checks out, **structure
only** without the key, **verification FAILED** with no percentage if anything
was altered, and **unsigned** when it comes from `/ai-history`.

## Commands

| Command | What it does |
|---|---|
| `/ai-history` | Share of commits and lines added with a Claude trailer, by author and month, from git history. No setup, writes nothing, unsigned. `--since`, `--json`, `--badge`. |
| `/receipt-init` | Generates the signing key (gitignored; init refuses if git tracks it), vendors the verifier into `.titan/tools/`, installs a git `post-commit` hook. `--no-git-hook` to skip the hook. |
| `/receipt` | Writes a signed, chained receipt for HEAD by hand. One per commit; re-runs are no-ops. |
| `/verify-chain` | Walks the whole chain offline: structure and every signature. Any tamper exits 1 and names the receipt. `--structure-only` checks without the key and says signatures were not checked. Ends with an `ANCHOR` line: how many receipts are committed **and pushed**. |
| `/receipt-report` | Markdown evidence: verification result, AI-assisted share by recorder / author / month, models and Claude Code versions recorded, and the limits footer. `--out`, `--badge`. |

## Two hooks, full coverage

| Commit made… | Receipted by | `ai_assisted` | Extra detail |
|---|---|---|---|
| in a Claude Code session | plugin `PostToolUse` hook | `true` (basis: `claude-code-hook`, plus trailers if present) | session id, model(s), Claude Code version, transcript hash, tool-use id |
| from your own terminal | git `post-commit` hook (defers inside Claude Code) | from `Co-Authored-By`/`Claude-Session` trailers; otherwise `false` | author, timestamp |

Neither hook can break a commit: an uninitialized repo is a silent no-op
(plus a one-time notice naming `/receipt-init`; `COMMITPROOF_QUIET=1`
turns it off), and the git hook always exits 0. Commit `.titan/attestations/`
and `.titan/tools/`, never `.titan/key`. Git hooks aren't cloned, so each
teammate runs `python3 .titan/tools/receipt.py install-hook` once per clone
(`python` or `py` on Windows).

## How it fits with git-ai

[git-ai](https://github.com/git-ai-project/git-ai) does line-level AI blame
across many coding agents. Use it for that. CommitProof answers the
question an auditor asks next: can you prove this record wasn't edited after
the fact? It does that with hash-chained, signed receipts you verify offline,
and a report built as change-control evidence. The two work side by side.

## Verify in CI

```yaml
- uses: Rmasood1122/commitproof@v1.3.2
  with:
    key: ${{ secrets.TITAN_KEY }}       # omit for structure-only verification
    report: docs/ai-change-receipts.md  # optional
```

Without the key the action verifies chain structure and content hashes and
says plainly that signatures were not checked. The key is written only for
the step and removed after. The action verifies with **its own pinned
verifier**, never the `.titan/tools/receipt.py` in the repo under audit: the
party who could alter the receipts also controls that copy. Pin a ref you
trust. `allow_repo_verifier: true` runs the repo's copy for the rare
compatibility case and warns that the result is self-reported.

## What a receipt proves

**Proves:** the recorded content (file hashes, diff hash, author, provenance
claims) is unchanged since signing, and the receipts form one unbroken ordered
chain, under a key your team controls.

<details>
<summary><strong>Does not prove</strong>: read before writing a compliance claim</summary>

- **Who held the key.** HMAC is a shared secret; anyone with `.titan/key` can
  produce valid signatures. Asymmetric signing and external timestamping live
  in the upstream [titan-gate](https://github.com/Rmasood1122/titan-gate) engine.
- **That anyone reviewed the change**, or that it was good.
- **That provenance is true.** `ai_assisted`, model, version, session and
  transcript hash are recorded claims: trailers from the commit message and
  what the Claude Code hook observed locally. The chain proves they weren't
  edited afterwards, not that they were accurate when written.
- **Anything about un-receipted commits.** Coverage is as good as hook
  installation; the report counts only receipted commits.
- **Ordering to anyone but you** until `.titan/attestations/` is committed and
  pushed. Every pushed clone then holds an independent copy a rewrite would
  have to chase down, and `/verify-chain` reports how much is pushed.

A fresh clone has the receipts but not the gitignored key: `/verify-chain`
still runs the full structural walk there, then says `SIGNATURES NOT CHECKED`
and exits 2. Share the key out-of-band with whoever must verify signatures.
The bundled `receipt-integrity` skill keeps compliance language inside these
lines, because a receipt system that overclaims is worse than none.
</details>

## What it runs and touches

- **Plugin hook (`PostToolUse`, every Bash tool call).** Starts
  `core/py.sh`, which runs `core/receipt.py hook` under the first Python 3.10+
  it finds. It reads the hook's JSON from stdin and exits unless the command
  was a successful `git commit`. In a repo without receipts it shows the
  one-time setup notice and records that it did in the plugin's data folder
  (a hash of the repo path, nothing inside your repo).
- **When it writes a receipt** (receipts on, commit made): runs read-only git
  commands, hashes the changed files, and reads the Claude Code session
  transcript named in the hook payload to record model names, the Claude
  Code version, its line count and sha256. Transcript content is never copied
  into the receipt. The session id comes from the hook payload or a
  `Claude-Session:` commit trailer; no session-id environment variable is
  read. Writes one JSON file under `.titan/attestations/`.
- **`/receipt-init`:** creates `.titan/key` and adds it to `.gitignore`,
  copies `receipt.py`, `badge.py`, `canonical.py` and `chain_state.py` into
  `.titan/tools/`, and installs or appends to `.git/hooks/post-commit`.
  Nothing else in your repo changes.
- **`/ai-history`, `/verify-chain`, `/receipt-report`:** read-only, apart
  from the `--out` or `--badge` file you name.
- **Network:** none. No telemetry, no package installs, no service.

## Requirements and privacy

Claude Code, git, and Python 3.10+ on PATH as `python3`, `python` or `py`.
Stdlib only: no packages, no network, no service, nothing phones home
([PRIVACY.md](PRIVACY.md)). CI runs the full suite, every tamper path
included, on Ubuntu and Windows.

## Formerly Titan Receipts

Same tool, new name (1.3.0). To switch an existing install:

```
/plugin uninstall titan-receipts@titan-receipts-marketplace
/plugin marketplace remove titan-receipts-marketplace
/plugin marketplace add Rmasood1122/commitproof
/plugin install commitproof@commitproof
```

Existing `.titan/` chains keep verifying unchanged. Re-run
`python3 .titan/tools/receipt.py install-hook` in each clone to pick up the
updated git hook. `TITAN_RECEIPTS_QUIET` still works.

## Provenance

The canonicalization and chain-walk rules are vendored byte-compatible from
[titan-gate](https://github.com/Rmasood1122/titan-gate), whose receipt engine
adds Ed25519 signing, RFC-3161 timestamping and Merkle roots. This plugin is
its lightweight attestation profile, `change-attestation/v1`. Related:
[eval-conductor](https://github.com/Rmasood1122/eval-conductor) and
[proof-gate](https://github.com/Rmasood1122/proof-gate) by the same author.

## License

MIT
