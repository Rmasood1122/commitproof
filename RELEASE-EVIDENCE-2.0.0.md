# Release evidence: titan-receipts 2.0.0

Every gate of the 2.0.0 release. The plan was approved on 2026-11-20 and lives at `~/.claude/plans/pasted-content-id-e7ea-role-you-immutable-codd.md`. Each entry gives the exact command, its raw output, the pass rule, the result and a UTC timestamp. The entries are written by `evals/ai-history-v2/gate.py`. A gate without raw output has not passed. CRLF line endings in the output are logged as LF.

- Repository: Rmasood1122/commitproof (directory listing "Titan Receipts", plugin name `titan-receipts`)
- Starting point: `main` at `56c563fd6618c5e429657d52b55364627da96908` (v1.3.3)
- Tools: git 2.56.1.windows.1, Claude Code 2.1.329, Git Bash on Windows 11, Python 3.13.5 (evals only)
- Decisions taken before the run:
  - D1: the 2026-11-19 attempt is archived as local tags `archive/engine-2026-11-19` and `archive/v2-candidate-2026-11-19`.
  - D2: the no-repo path gives the same step-2 block.
  - D3: `Assisted-by: LLM` counts only as that exact value, labelled "With a Claude or LLM trailer".
  - D4: the displayName stays "Titan Receipts".
- Superseded: the 2026-11-19 attempt (base `973bfa0`, plugin name "commitproof") and its evidence log, kept at `archive/engine-2026-11-19:RELEASE-EVIDENCE-2.0.0.md`.

## P1 — Archive

### Gate 1a: engine, v2-candidate and v1.3.3-final point at main HEAD

- Time (UTC): 2026-11-20T11:59:32Z
- Checkout: engine @ 56c563f (2 uncommitted change(s))
- Pass rule: `exact:56c563fd6618c5e429657d52b55364627da96908\n56c563fd6618c5e429657d52b55364627da96908\n56c563fd6618c5e429657d52b55364627da96908\n56c563fd6618c5e429657d52b55364627da96908`
- Result: **PASS** (exit 0)

Command:

```sh
git rev-parse main engine v2-candidate 'v1.3.3-final^{commit}'
```

Raw output:

```text
56c563fd6618c5e429657d52b55364627da96908
56c563fd6618c5e429657d52b55364627da96908
56c563fd6618c5e429657d52b55364627da96908
56c563fd6618c5e429657d52b55364627da96908
```

### Gate 1b: the 2026-11-19 attempt is archived, not lost

- Time (UTC): 2026-11-20T11:59:32Z
- Checkout: engine @ 56c563f (2 uncommitted change(s))
- Pass rule: `exact:9c5f81c P5: log layer-1 gates 5.1-5.3 (all pass); layer 2 waiting for go\n641566a P4: 2.0.0 docs and manifests (Gate 4)`
- Result: **PASS** (exit 0)

Command:

```sh
git log -1 --format='%h %s' archive/engine-2026-11-19 && git log -1 --format='%h %s' archive/v2-candidate-2026-11-19
```

Raw output:

```text
9c5f81c P5: log layer-1 gates 5.1-5.3 (all pass); layer 2 waiting for go
641566a P4: 2.0.0 docs and manifests (Gate 4)
```

