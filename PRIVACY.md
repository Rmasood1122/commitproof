# Privacy

Titan Receipts (plugin name `titan-receipts`) runs only when you use /ai-history, or when you ask Claude a question it answers with its ai-history skill.

- **Runs:** read-only git commands on the repository you have open, listed in full in the README.
- **Reads:** that repository's git history: commit messages (git searches them for trailers; they are not shown), author names, commit dates and per-file counts of added lines. Author emails are read only if you ask for them. Git also reads its usual settings and the repository's .mailmap file.
- **Writes:** nothing. No files, no git settings, no hooks.
- **Sends:** nothing. The plugin makes no network calls and has no server, account, analytics or telemetry. Like any command output in Claude, the results (counts, author names, months) become part of your Claude conversation.
- **Keeps:** nothing. The plugin stores no data between runs. Your conversation is kept according to your Claude account settings.
- **Pasted output:** if you run the commands yourself and paste the output into a chat, it is handled like any other message you send.

The plugin is a developer tool and is not directed at anyone under 18.

Questions: https://github.com/Rmasood1122/commitproof/issues
