> **Sample.** Real output of `/ai-history`, run on a demo repository with made-up commits and authors (`payments-api`). Run it on your own repo: no setup, a few seconds.

# How much of payments-api did Claude help write?

Read from the commit trailers already in this repo's git history (`Co-Authored-By: Claude …`, `Claude-Session:`). No setup, no key, nothing written — and **unsigned**: a starting estimate, not evidence.

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

## By month

| month | commits | with a Claude trailer |
|---|---|---|
| 2026-06 | 1 | 0 (0%) |
| 2026-07 | 2 | 1 (50%) |
| 2026-08 | 2 | 2 (100%) |
| 2026-09 | 2 | 1 (50%) |

## What this does and doesn't tell you

It counts commits whose message carries a Claude trailer, and the lines added in those commits — not which lines Claude typed. Trailers are plain text: anyone can add or delete them, and history can be rewritten. Claude-assisted commits whose trailer was dropped (or squash-merged without it) count as not AI-assisted. A starting estimate, not evidence.

**Make it evidence from here on:** `/receipt-init` gives every new commit a hash-chained, signed receipt, so a later rewrite of this record shows up in `/verify-chain`.
