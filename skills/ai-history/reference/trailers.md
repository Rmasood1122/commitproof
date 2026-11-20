# Which trailers count

A commit counts as "with a Claude or LLM trailer" when any line of its message matches one of the rules below. Letter case doesn't matter, and spaces or tabs are allowed on either side of the colon.

| Line starts with | Counts when the value | Usually written by |
|---|---|---|
| `Co-Authored-By:` | starts with the word Claude, e.g. `Claude <noreply@anthropic.com>`, `Claude Opus 5.5 <...>`, `claude[bot] <...>` | Claude Code; GitHub spells it `Co-authored-by:` |
| `Assisted-by:` | starts with the word Claude, e.g. `Claude:claude-opus-5-5 coccinelle` | the Linux kernel form `Assisted-by: AGENT:MODEL` |
| `Assisted-by:` | is exactly `LLM`, with nothing after it | projects that record AI help without naming a model |
| `Claude-Session:` | has any value; it is counted and never shown | Claude Code, as a link to the session |

"Starts with the word Claude" means `Claude` followed by a character that is not a letter, or by the end of the line. So `Claudette` doesn't count.

An `Assisted-by: LLM` trailer names no model, so a commit counted through it may not involve Claude at all. That is why the column says "Claude or LLM".

## Not counted, and why

- `Assisted-by: LLMs`, `Assisted-by: LLM:gpt-4o` and any other value that is not exactly `LLM`: they name another model, or something other than the generic label.
- `Assisted-by: GitHub Copilot`, `Assisted-by: Anthropic Claude` and any other value that doesn't start with Claude. Counting values that don't name Claude first would overstate Claude's share.
- `Co-Authored-By: Jean-Claude ...`: the value doesn't start with Claude.
- A trailer indented with a space: git itself doesn't read that as a trailer.
- "Generated with Claude Code" and other body text: not trailers.

## Known miscounts

- A human co-author whose first name is Claude counts.
- A message that quotes a trailer at the start of a body line counts, even outside the trailer block.
- Merge commits are skipped, with any trailer on them.
- A squash merge keeps only the squashed message. If it dropped the trailers, the work counts as without.
- Rebased, amended and cherry-picked commits are dated by their new commit date.
