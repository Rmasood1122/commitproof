# Layer 2, attempt 1: 20/24 (Wilson 95% [0.641, 0.933])

- Plugin: `v2-candidate` @ `1bc3aa3`
- Model: claude-opus-5-5
- Cost: $3.13 for 24 runs, plus the $0.135 probe (`probe-c-1.jsonl`, PASS)

Every number in all 24 answers matched the golden oracle. The four misses are all wording:

| Run | Label | What the answer did |
|---|---|---|
| c-1 | format: bold | First line written as `**Estimate from commit trailers (unsigned)**`; "What this does not show" also bolded |
| e-1 | format: paraphrase | Source line reworded to "Git did the counting; every number above is copied from its output."; second line and bullets reworded |
| e-2 | format: paraphrase | Source line reworded to "All numbers are copied from git's output; I did no counting myself."; bullets reworded |
| h-3 | format: paraphrase | Source line reworded to "Every number is copied from the git output above. Git did the counting."; second line and bullets reworded |

**Root cause.** Step 3 said "answer in this layout" and "fill each angle bracket", but it never said that the lines outside the angle brackets are fixed text.

**Fix (instruction only; the scorer is unchanged).** Step 3 now says: copy every line of the layout word for word, as plain text (no bold, no headings, no added or reworded lines), and change only the angle brackets. All 24 runs are re-run as attempt 2.
