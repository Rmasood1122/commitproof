> **Sample.** Real output of `/receipt-report`, run on a demo repository with made-up commits and authors (`payments-api`). Yours appears once receipts are on: `/receipt-init`, commit as usual, then `/receipt-report`.

# AI-assisted change receipts — payments-api

Generated 2026-10-20 14:19 UTC by commitproof 1.3.0 from `.titan/attestations/`.

## Verification

- Chain structure (single unbroken line from GENESIS, content hashes recomputed): **intact**
- Signatures (HMAC-SHA256 under the repo key): **all valid**

## Summary

| | count | share |
|---|---|---|
| Receipted commits | 6 | |
| AI-assisted (per recorded basis) | 3 | 50% |
| Not AI-assisted | 3 | 50% |

## By recorder

| recorder | receipts |
|---|---|
| claude-code-hook | 3 |
| git-post-commit | 3 |

## By author

| author | commits | AI-assisted |
|---|---|---|
| Sam Ortiz <sam@example.com> | 2 | 2 (100%) |
| Dana Lee <dana@example.com> | 2 | 0 (0%) |
| Priya Nair <priya@example.com> | 1 | 1 (100%) |
| CI <ci@example.com> | 1 | 0 (0%) |

## By month

| month | commits | AI-assisted |
|---|---|---|
| 2026-10 | 6 | 3 (50%) |

## Tooling recorded

- model `claude-opus-5-5`: 3 receipt(s)
- model `claude-sonnet-5-5`: 3 receipt(s)
- Claude Code `2.1.299`: 3 receipt(s)

## What this report proves — and does not

Each receipt records a commit's changed-file hashes, diff hash, author, and provenance claims, hash-chained to the previous receipt and HMAC-signed. An intact chain with valid signatures means the recorded history has not been altered since signing, under a key the team controls. It does **not** prove who held the key (HMAC is a shared secret), that any change was reviewed, or that the AI-assistance claims are true — `ai_assisted` comes from commit trailers and from the Claude Code hook that wrote the receipt, and model/version/transcript fields are what that tool observed locally. Commits made outside both the Claude Code hook and the git post-commit hook have no receipt and are not counted.
