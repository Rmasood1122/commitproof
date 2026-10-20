# Privacy

commitproof collects nothing.

- All commands run local Python (stdlib only) inside your own repository.
- No network calls, no telemetry, no accounts. Nothing leaves your machine.
- Receipts record git metadata your repo already contains (paths, hashes,
  commit trailers) and are written into your repo, under your control.
- The signing key is generated locally and gitignored; this plugin never
  transmits it anywhere.
- With SSH signing (`/receipt-init --ssh`), your SSH public key and git email
  are written to `.titan/allowed_signers` in your repo, for you to commit. Your
  private key is used only by your local `ssh-keygen`, by path; the plugin
  never reads, copies or sends it.

Questions: https://github.com/Rmasood1122/commitproof/issues
