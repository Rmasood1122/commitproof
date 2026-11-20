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

## P2 — Strip (branch v2-candidate)

### Gate 2.1: only allowed file types are tracked

- Time (UTC): 2026-11-20T12:00:45Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git ls-files | grep -Ev '\.(md|txt|json|ya?ml|png|jpe?g|gif|webp|ico)$' | grep -Ev '^(LICENSE|\.gitignore|\.claude-plugin/icon\.svg)$'
```

Raw output:

```text
(no output)
```

### Gate 2.2: no tracked file starts with #!

- Time (UTC): 2026-11-20T12:00:46Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 123)

Command:

```sh
git ls-files | xargs grep -l '^#!'
```

Raw output:

```text
(no output)
```

### Gate 2.3: no dynamic-context lines, allowed-tools, credential names or installs

- Time (UTC): 2026-11-20T12:00:46Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -nE '!`|allowed-tools|TOKEN|SECRET|API_KEY|getenv|environ|pip install|npx|uvx|curl |marketplace add'
```

Raw output:

```text
(no output)
```

### Gate 2.4: no file over 256 KiB

- Time (UTC): 2026-11-20T12:00:46Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 0)

Command:

```sh
find . -size +256k -not -path './.git/*'
```

Raw output:

```text
(no output)
```

### Gate 2.5: (stricter) .claude-plugin holds only plugin.json and the icon

- Time (UTC): 2026-11-20T12:00:46Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `exact:.claude-plugin/icon.svg\n.claude-plugin/plugin.json`
- Result: **PASS** (exit 0)

Command:

```sh
git ls-files .claude-plugin
```

Raw output:

```text
.claude-plugin/icon.svg
.claude-plugin/plugin.json
```

### Gate 2.6: (stricter) no credential, secret, key or env-var words, any letter case

- Time (UTC): 2026-11-20T12:00:47Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -niE 'token|secret|api[_-]?key|passw|credential|\benv\b|environ|getenv|\$[A-Z_]{2,}|\$\{|CLAUDE_PLUGIN_ROOT|\bkey\b|\.titan'
```

Raw output:

```text
(no output)
```

### Gate 2.7: (stricter) no install commands of any package manager

- Time (UTC): 2026-11-20T12:00:47Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -niE '\b(npm|pip3?|brew|apt(-get)?|winget|choco|cargo|go|gem|uv) +install|/plugin +install|npx|uvx|curl |wget '
```

Raw output:

```text
(no output)
```

### Gate 2.8: (stricter) UTF-8 only, no NUL bytes, no CR in committed blobs

- Time (UTC): 2026-11-20T12:00:48Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git ls-files -z | xargs -0 -n1 sh -c 'iconv -f UTF-8 -t UTF-8 "$0" > /dev/null 2>&1 || echo "not UTF-8: $0"'
git ls-files -z | xargs -0 grep -lP '\x00'
git grep -lI $'\r' HEAD
```

Raw output:

```text
(no output)
```

### Gate 2.9: (stricter) plugin.json fields exact; no hooks, userConfig, mcpServers or lsp

- Time (UTC): 2026-11-20T12:00:48Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 0)

Command:

```sh
python - <<'PY'
import json
m = json.load(open('.claude-plugin/plugin.json', encoding='utf-8'))
want = {'name': 'titan-receipts', 'displayName': 'Titan Receipts', 'version': '2.0.0',
        'privacyPolicyUrl': 'https://github.com/Rmasood1122/commitproof/blob/main/PRIVACY.md',
        'icon': './.claude-plugin/icon.svg'}
for k, v in want.items():
    if m.get(k) != v:
        print('wrong', k, repr(m.get(k)))
if m.get('author', {}).get('email') != 'rmasood112224@gmail.com':
    print('wrong author.email')
bad_kw = [k for k in m.get('keywords', []) if any(b in k.lower() for b in ('soc2', 'soc-2', 'hipaa', 'pci', 'tamper'))]
if bad_kw:
    print('banned keywords', bad_kw)
for k in ('hooks', 'userConfig', 'mcpServers', 'lspServers', 'lsp', 'agents', 'outputStyles', 'monitors'):
    if k in m:
        print('forbidden field', k)
PY
```

Raw output:

```text
(no output)
```

### Gate 2 control: every check fails on a throwaway repository with planted violations

The throwaway repository at `scratchpad/control-bad` holds:
- a `#!` script and a `#!` line in Markdown
- `` !`…` ``, a `TOKEN` name, "api key", `npm install` and `${HOME}` in Markdown
- a 300 KB file
- `marketplace.json`
- a CRLF file, a Latin-1 file and a NUL byte
- a plugin.json with the wrong name and a `hooks` field

The first control run showed that `grep -lP '\x00'` cannot see NUL bytes, because GNU grep treats NUL as a line end in binary files. Check 8 now uses `tr`/`cmp`. Gate 2 was re-run below as 2r, and 2r supersedes the 2.8 entry above. Control log (expected: all 9 FAIL):

#### Control C.1: only allowed file types are tracked

- Time (UTC): 2026-11-20T12:01:46Z
- Checkout: main @ 71dd686 (clean)
- Pass rule: `empty`
- Result: **FAIL** (exit 0)

Command:

```sh
git ls-files | grep -Ev '\.(md|txt|json|ya?ml|png|jpe?g|gif|webp|ico)$' | grep -Ev '^(LICENSE|\.gitignore|\.claude-plugin/icon\.svg)$'
```

Raw output:

```text
run.sh
```

#### Control C.2: no tracked file starts with #!

- Time (UTC): 2026-11-20T12:01:46Z
- Checkout: main @ 71dd686 (clean)
- Pass rule: `empty`
- Result: **FAIL** (exit 0)

Command:

```sh
git ls-files | xargs grep -l '^#!'
```

Raw output:

```text
run.sh
tool.md
```

#### Control C.3: no dynamic-context lines, allowed-tools, credential names or installs

- Time (UTC): 2026-11-20T12:01:46Z
- Checkout: main @ 71dd686 (clean)
- Pass rule: `empty`
- Result: **FAIL** (exit 0)

Command:

```sh
git grep -nE '!`|allowed-tools|TOKEN|SECRET|API_KEY|getenv|environ|pip install|npx|uvx|curl |marketplace add'
```

Raw output:

```text
a.md:1:Use !`git status` here. Set GITHUB_TOKEN. Your api key. Run npm install foo. Path ${HOME}.
```

#### Control C.4: no file over 256 KiB

- Time (UTC): 2026-11-20T12:01:46Z
- Checkout: main @ 71dd686 (clean)
- Pass rule: `empty`
- Result: **FAIL** (exit 0)

Command:

```sh
find . -size +256k -not -path './.git/*'
```

Raw output:

```text
./big.txt
```

#### Control C.5: (stricter) .claude-plugin holds only plugin.json and the icon

- Time (UTC): 2026-11-20T12:01:47Z
- Checkout: main @ 71dd686 (clean)
- Pass rule: `exact:.claude-plugin/icon.svg\n.claude-plugin/plugin.json`
- Result: **FAIL** (exit 0)

Command:

```sh
git ls-files .claude-plugin
```

Raw output:

```text
.claude-plugin/icon.svg
.claude-plugin/marketplace.json
.claude-plugin/plugin.json
```

#### Control C.6: (stricter) no credential, secret, key or env-var words, any letter case

- Time (UTC): 2026-11-20T12:01:47Z
- Checkout: main @ 71dd686 (clean)
- Pass rule: `empty`
- Result: **FAIL** (exit 0)

Command:

```sh
git grep -niE 'token|secret|api[_-]?key|passw|credential|\benv\b|environ|getenv|\$[A-Z_]{2,}|\$\{|CLAUDE_PLUGIN_ROOT|\bkey\b|\.titan'
```

Raw output:

```text
a.md:1:Use !`git status` here. Set GITHUB_TOKEN. Your api key. Run npm install foo. Path ${HOME}.
tool.md:1:#!/usr/bin/env python3
```

#### Control C.7: (stricter) no install commands of any package manager

- Time (UTC): 2026-11-20T12:01:47Z
- Checkout: main @ 71dd686 (clean)
- Pass rule: `empty`
- Result: **FAIL** (exit 0)

Command:

```sh
git grep -niE '\b(npm|pip3?|brew|apt(-get)?|winget|choco|cargo|go|gem|uv) +install|/plugin +install|npx|uvx|curl |wget '
```

Raw output:

```text
a.md:1:Use !`git status` here. Set GITHUB_TOKEN. Your api key. Run npm install foo. Path ${HOME}.
```

#### Control C.8: (stricter) UTF-8 only, no NUL bytes, no CR in committed blobs

- Time (UTC): 2026-11-20T12:01:49Z
- Checkout: main @ 71dd686 (clean)
- Pass rule: `empty`
- Result: **FAIL** (exit 0)

Command:

```sh
git ls-files -z | xargs -0 -n1 sh -c 'iconv -f UTF-8 -t UTF-8 "$0" > /dev/null 2>&1 || echo "not UTF-8: $0"'
git ls-files -z | xargs -0 -n1 sh -c 'tr -d "\\000" < "$0" | cmp -s - "$0" || echo "NUL byte: $0"'
git grep -lI $'\r' HEAD
```

Raw output:

```text
not UTF-8: latin1.md
NUL byte: zerobyte.txt
HEAD:crlf.md
```

#### Control C.9: (stricter) plugin.json fields exact; no hooks, userConfig, mcpServers or lsp

- Time (UTC): 2026-11-20T12:01:50Z
- Checkout: main @ 71dd686 (clean)
- Pass rule: `empty`
- Result: **FAIL** (exit 0)

Command:

```sh
python - <<'PY'
import json
m = json.load(open('.claude-plugin/plugin.json', encoding='utf-8'))
want = {'name': 'titan-receipts', 'displayName': 'Titan Receipts', 'version': '2.0.0',
        'privacyPolicyUrl': 'https://github.com/Rmasood1122/commitproof/blob/main/PRIVACY.md',
        'icon': './.claude-plugin/icon.svg'}
for k, v in want.items():
    if m.get(k) != v:
        print('wrong', k, repr(m.get(k)))
if m.get('author', {}).get('email') != 'rmasood112224@gmail.com':
    print('wrong author.email')
bad_kw = [k for k in m.get('keywords', []) if any(b in k.lower() for b in ('soc2', 'soc-2', 'hipaa', 'pci', 'tamper'))]
if bad_kw:
    print('banned keywords', bad_kw)
for k in ('hooks', 'userConfig', 'mcpServers', 'lspServers', 'lsp', 'agents', 'outputStyles', 'monitors'):
    if k in m:
        print('forbidden field', k)
PY
```

Raw output:

```text
wrong name 'commitproof'
wrong displayName None
wrong version None
wrong privacyPolicyUrl None
wrong icon None
wrong author.email
forbidden field hooks
```

### Gate 2r: Gate 2 re-run with the fixed NUL check

### Gate 2r.1: only allowed file types are tracked

- Time (UTC): 2026-11-20T12:02:00Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git ls-files | grep -Ev '\.(md|txt|json|ya?ml|png|jpe?g|gif|webp|ico)$' | grep -Ev '^(LICENSE|\.gitignore|\.claude-plugin/icon\.svg)$'
```

Raw output:

```text
(no output)
```

### Gate 2r.2: no tracked file starts with #!

- Time (UTC): 2026-11-20T12:02:00Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 123)

Command:

```sh
git ls-files | xargs grep -l '^#!'
```

Raw output:

```text
(no output)
```

### Gate 2r.3: no dynamic-context lines, allowed-tools, credential names or installs

- Time (UTC): 2026-11-20T12:02:00Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -nE '!`|allowed-tools|TOKEN|SECRET|API_KEY|getenv|environ|pip install|npx|uvx|curl |marketplace add'
```

Raw output:

```text
(no output)
```

### Gate 2r.4: no file over 256 KiB

- Time (UTC): 2026-11-20T12:02:01Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 0)

Command:

```sh
find . -size +256k -not -path './.git/*'
```

Raw output:

```text
(no output)
```

### Gate 2r.5: (stricter) .claude-plugin holds only plugin.json and the icon

- Time (UTC): 2026-11-20T12:02:01Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `exact:.claude-plugin/icon.svg\n.claude-plugin/plugin.json`
- Result: **PASS** (exit 0)

Command:

```sh
git ls-files .claude-plugin
```

Raw output:

```text
.claude-plugin/icon.svg
.claude-plugin/plugin.json
```

### Gate 2r.6: (stricter) no credential, secret, key or env-var words, any letter case

- Time (UTC): 2026-11-20T12:02:01Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -niE 'token|secret|api[_-]?key|passw|credential|\benv\b|environ|getenv|\$[A-Z_]{2,}|\$\{|CLAUDE_PLUGIN_ROOT|\bkey\b|\.titan'
```

Raw output:

```text
(no output)
```

### Gate 2r.7: (stricter) no install commands of any package manager

- Time (UTC): 2026-11-20T12:02:02Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -niE '\b(npm|pip3?|brew|apt(-get)?|winget|choco|cargo|go|gem|uv) +install|/plugin +install|npx|uvx|curl |wget '
```

Raw output:

```text
(no output)
```

### Gate 2r.8: (stricter) UTF-8 only, no NUL bytes, no CR in committed blobs

- Time (UTC): 2026-11-20T12:02:03Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git ls-files -z | xargs -0 -n1 sh -c 'iconv -f UTF-8 -t UTF-8 "$0" > /dev/null 2>&1 || echo "not UTF-8: $0"'
git ls-files -z | xargs -0 -n1 sh -c 'tr -d "\\000" < "$0" | cmp -s - "$0" || echo "NUL byte: $0"'
git grep -lI $'\r' HEAD
```

Raw output:

```text
(no output)
```

### Gate 2r.9: (stricter) plugin.json fields exact; no hooks, userConfig, mcpServers or lsp

- Time (UTC): 2026-11-20T12:02:03Z
- Checkout: v2-candidate @ da7f79c (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 0)

Command:

```sh
python - <<'PY'
import json
m = json.load(open('.claude-plugin/plugin.json', encoding='utf-8'))
want = {'name': 'titan-receipts', 'displayName': 'Titan Receipts', 'version': '2.0.0',
        'privacyPolicyUrl': 'https://github.com/Rmasood1122/commitproof/blob/main/PRIVACY.md',
        'icon': './.claude-plugin/icon.svg'}
for k, v in want.items():
    if m.get(k) != v:
        print('wrong', k, repr(m.get(k)))
if m.get('author', {}).get('email') != 'rmasood112224@gmail.com':
    print('wrong author.email')
bad_kw = [k for k in m.get('keywords', []) if any(b in k.lower() for b in ('soc2', 'soc-2', 'hipaa', 'pci', 'tamper'))]
if bad_kw:
    print('banned keywords', bad_kw)
for k in ('hooks', 'userConfig', 'mcpServers', 'lspServers', 'lsp', 'agents', 'outputStyles', 'monitors'):
    if k in m:
        print('forbidden field', k)
PY
```

Raw output:

```text
(no output)
```

## P3 — Command, skill, trailer reference (branch v2-candidate)

### Gate 3.1-3.4: layer 1: command = skill text; fixtures a-h, 2b emails, hostile config and two real repos equal the golden oracle

- Time (UTC): 2026-11-20T12:06:02Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `contains:layer 1: PASS`
- Result: **FAIL** (exit 1)

Command:

```sh
cd /c/Users/rmaso/code/Rmasood1122/commitproof/evals/ai-history-v2 && python fixtures.py "$(cygpath -w '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/fx')" > /dev/null && python block_check.py "$(cygpath -w '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/wt-v2')" "$(cygpath -w '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/fx')" --real "$(cygpath -w /c/Users/rmaso/code/Rmasood1122/commitproof)" "$(cygpath -w /c/Users/rmaso/code/Rmasood1122/appealforge)"
```

Raw output:

```text
Traceback (most recent call last):
  File "C:\Users\rmaso\code\Rmasood1122\commitproof\evals\ai-history-v2\fixtures.py", line 300, in <module>
    for name, path in build_all(target, sys.argv[2] if len(sys.argv) > 2 else "abcdefgh").items():
                      ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\rmaso\code\Rmasood1122\commitproof\evals\ai-history-v2\fixtures.py", line 292, in build_all
    shutil.rmtree(path)
    ~~~~~~~~~~~~~^^^^^^
  File "C:\Users\rmaso\AppData\Local\Programs\Python\Python313\Lib\shutil.py", line 790, in rmtree
    return _rmtree_unsafe(path, onexc)
  File "C:\Users\rmaso\AppData\Local\Programs\Python\Python313\Lib\shutil.py", line 629, in _rmtree_unsafe
    onexc(os.unlink, fullname, err)
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\rmaso\AppData\Local\Programs\Python\Python313\Lib\shutil.py", line 625, in _rmtree_unsafe
    os.unlink(fullname)
    ~~~~~~~~~^^^^^^^^^^
PermissionError: [WinError 5] Access is denied: 'C:\\Users\\rmaso\\AppData\\Local\\Temp\\claude\\74486e4faaf2f9ee\\deb1bc2b-013f-4645-9174-a879297d0526\\scratchpad\\fx\\a\\.git\\objects\\04\\fd6e2ff91e4fcd4ce2e85f5d681a1e15aeccc9'
```

### Gate 3.5: claude plugin validate on the plugin checkout

- Time (UTC): 2026-11-20T12:06:03Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `contains:Validation passed`
- Result: **PASS** (exit 0)

Command:

```sh
claude plugin validate .
```

Raw output:

```text
Validating plugin manifest: C:\Users\rmaso\AppData\Local\Temp\claude\74486e4faaf2f9ee\deb1bc2b-013f-4645-9174-a879297d0526\scratchpad\wt-v2\.claude-plugin\plugin.json

Provides:

  ❯ skills: titan-receipts:ai-history
  ❯ commands: titan-receipts:ai-history

Hosts not read for: skills (1), commands (1)

Plugin directory checks for C:\Users\rmaso\AppData\Local\Temp\claude\74486e4faaf2f9ee\deb1bc2b-013f-4645-9174-a879297d0526\scratchpad\wt-v2. The plugin directory is the catalog that plugins are submitted to; this is a subset of what it runs.

✘ Found 1 problem the plugin directory refuses a submission for:

  ❯ README.md: README missing (README_MISSING). This plugin has no README.md. People who install it and the directory's automated review read the README to learn what it does; the first line of a README in the plugin folder also stands in as the listing summary when plugin.json has no description.
    Fix: Add a README.md to the plugin folder describing what the plugin does, how to use it, and any setup it needs, in at least 40 words. A README at the repository root also counts for a plugin in a sub-folder.

These plugin directory checks do not change the result below. To fail on problems the directory refuses a submission for, run this command with --profile directory.

The directory also runs a safety scan and a policy review that this command does not.

✔ Validation passed
```

> Gate 3.1-3.4 attempt 1 failed in the harness, not the plugin. `fixtures.py` could not delete the previous fixtures because git object files are read-only on Windows. Fixed with `rm_tree` (chmod, then delete), and the gate commands moved into `layer1.sh`. Attempt 2 follows.

### Gate 3.1-3.4 (attempt 2): layer 1: command = skill text; fixtures a-h, 2b emails, hostile config and two real repos equal the golden oracle

- Time (UTC): 2026-11-20T12:07:01Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `contains:layer 1: PASS`
- Result: **PASS** (exit 0)

Command:

```sh
bash /c/Users/rmaso/code/Rmasood1122/commitproof/evals/ai-history-v2/layer1.sh '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/wt-v2' '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/fx' /c/Users/rmaso/code/Rmasood1122/commitproof /c/Users/rmaso/code/Rmasood1122/appealforge
```

Raw output:

```text
method text identical in command and skill: PASS
a: step 1 + block: commits 12/0 lines 138/0 authors 3 months 3: PASS
a: step 2b (emails) equals golden: PASS
b: step 1 + block: commits 10/10 lines 185/185 authors 2 months 2: PASS
b: step 2b (emails) equals golden: PASS
c: step 1 + block: commits 16/7 lines 409/141 authors 3 months 3: PASS
c: step 2b (emails) equals golden: PASS
d: step 1 + block: commits 12/6 lines 114/53 authors 2 months 3: PASS
d: step 2b (emails) equals golden: PASS
e: step 1 + block: commits 10/8 lines 65/47 authors 2 months 1: PASS
e: step 2b (emails) equals golden: PASS
f: empty repository, step 1 prints true, nothing, false: PASS  ['true', 'false']
g: step 1 + block: commits 5000/1750 lines 127500/42000 authors 20 months 12: PASS
g: step 2b (emails) equals golden: PASS
h: step 1 + block: commits 8/3 lines 70/20 authors 2 months 3: PASS
h: step 2b (emails) equals golden: PASS
hostile config (log.showRoot=false, diff.relative=true, run in data/) equals golden(c): PASS
control: plain git log under that config gives a different lines total: PASS  plain=200 block=409
real repo commitproof: commits 40/40 lines 6612/6612 authors 3: PASS
real repo appealforge: commits 143/126 lines 70523/47466 authors 4: PASS
layer 1: PASS
```

### Gate 3g: Gate 2 re-run on the P3 tree

### Gate 3g.1: only allowed file types are tracked

- Time (UTC): 2026-11-20T12:07:09Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git ls-files | grep -Ev '\.(md|txt|json|ya?ml|png|jpe?g|gif|webp|ico)$' | grep -Ev '^(LICENSE|\.gitignore|\.claude-plugin/icon\.svg)$'
```

Raw output:

```text
(no output)
```

### Gate 3g.2: no tracked file starts with #!

- Time (UTC): 2026-11-20T12:07:09Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 123)

Command:

```sh
git ls-files | xargs grep -l '^#!'
```

Raw output:

```text
(no output)
```

### Gate 3g.3: no dynamic-context lines, allowed-tools, credential names or installs

- Time (UTC): 2026-11-20T12:07:09Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -nE '!`|allowed-tools|TOKEN|SECRET|API_KEY|getenv|environ|pip install|npx|uvx|curl |marketplace add'
```

Raw output:

```text
(no output)
```

### Gate 3g.4: no file over 256 KiB

- Time (UTC): 2026-11-20T12:07:09Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 0)

Command:

```sh
find . -size +256k -not -path './.git/*'
```

Raw output:

```text
(no output)
```

### Gate 3g.5: (stricter) .claude-plugin holds only plugin.json and the icon

- Time (UTC): 2026-11-20T12:07:10Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `exact:.claude-plugin/icon.svg\n.claude-plugin/plugin.json`
- Result: **PASS** (exit 0)

Command:

```sh
git ls-files .claude-plugin
```

Raw output:

```text
.claude-plugin/icon.svg
.claude-plugin/plugin.json
```

### Gate 3g.6: (stricter) no credential, secret, key or env-var words, any letter case

- Time (UTC): 2026-11-20T12:07:10Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -niE 'token|secret|api[_-]?key|passw|credential|\benv\b|environ|getenv|\$[A-Z_]{2,}|\$\{|CLAUDE_PLUGIN_ROOT|\bkey\b|\.titan'
```

Raw output:

```text
(no output)
```

### Gate 3g.7: (stricter) no install commands of any package manager

- Time (UTC): 2026-11-20T12:07:10Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -niE '\b(npm|pip3?|brew|apt(-get)?|winget|choco|cargo|go|gem|uv) +install|/plugin +install|npx|uvx|curl |wget '
```

Raw output:

```text
(no output)
```

### Gate 3g.8: (stricter) UTF-8 only, no NUL bytes, no CR in committed blobs

- Time (UTC): 2026-11-20T12:07:12Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git ls-files -z | xargs -0 -n1 sh -c 'iconv -f UTF-8 -t UTF-8 "$0" > /dev/null 2>&1 || echo "not UTF-8: $0"'
git ls-files -z | xargs -0 -n1 sh -c 'tr -d "\\000" < "$0" | cmp -s - "$0" || echo "NUL byte: $0"'
git grep -lI $'\r' HEAD
```

Raw output:

```text
(no output)
```

### Gate 3g.9: (stricter) plugin.json fields exact; no hooks, userConfig, mcpServers or lsp

- Time (UTC): 2026-11-20T12:07:12Z
- Checkout: v2-candidate @ 80b0cb7 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 0)

Command:

```sh
python - <<'PY'
import json
m = json.load(open('.claude-plugin/plugin.json', encoding='utf-8'))
want = {'name': 'titan-receipts', 'displayName': 'Titan Receipts', 'version': '2.0.0',
        'privacyPolicyUrl': 'https://github.com/Rmasood1122/commitproof/blob/main/PRIVACY.md',
        'icon': './.claude-plugin/icon.svg'}
for k, v in want.items():
    if m.get(k) != v:
        print('wrong', k, repr(m.get(k)))
if m.get('author', {}).get('email') != 'rmasood112224@gmail.com':
    print('wrong author.email')
bad_kw = [k for k in m.get('keywords', []) if any(b in k.lower() for b in ('soc2', 'soc-2', 'hipaa', 'pci', 'tamper'))]
if bad_kw:
    print('banned keywords', bad_kw)
for k in ('hooks', 'userConfig', 'mcpServers', 'lspServers', 'lsp', 'agents', 'outputStyles', 'monitors'):
    if k in m:
        print('forbidden field', k)
PY
```

Raw output:

```text
(no output)
```

## P4 — Docs and the finished tree (branch v2-candidate)

### Gate 4g.1: only allowed file types are tracked

- Time (UTC): 2026-11-20T12:08:29Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git ls-files | grep -Ev '\.(md|txt|json|ya?ml|png|jpe?g|gif|webp|ico)$' | grep -Ev '^(LICENSE|\.gitignore|\.claude-plugin/icon\.svg)$'
```

Raw output:

```text
(no output)
```

### Gate 4g.2: no tracked file starts with #!

- Time (UTC): 2026-11-20T12:08:29Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 123)

Command:

```sh
git ls-files | xargs grep -l '^#!'
```

Raw output:

```text
(no output)
```

### Gate 4g.3: no dynamic-context lines, allowed-tools, credential names or installs

- Time (UTC): 2026-11-20T12:08:30Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -nE '!`|allowed-tools|TOKEN|SECRET|API_KEY|getenv|environ|pip install|npx|uvx|curl |marketplace add'
```

Raw output:

```text
(no output)
```

### Gate 4g.4: no file over 256 KiB

- Time (UTC): 2026-11-20T12:08:30Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 0)

Command:

```sh
find . -size +256k -not -path './.git/*'
```

Raw output:

```text
(no output)
```

### Gate 4g.5: (stricter) .claude-plugin holds only plugin.json and the icon

- Time (UTC): 2026-11-20T12:08:30Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `exact:.claude-plugin/icon.svg\n.claude-plugin/plugin.json`
- Result: **PASS** (exit 0)

Command:

```sh
git ls-files .claude-plugin
```

Raw output:

```text
.claude-plugin/icon.svg
.claude-plugin/plugin.json
```

### Gate 4g.6: (stricter) no credential, secret, key or env-var words, any letter case

- Time (UTC): 2026-11-20T12:08:30Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -niE 'token|secret|api[_-]?key|passw|credential|\benv\b|environ|getenv|\$[A-Z_]{2,}|\$\{|CLAUDE_PLUGIN_ROOT|\bkey\b|\.titan'
```

Raw output:

```text
(no output)
```

### Gate 4g.7: (stricter) no install commands of any package manager

- Time (UTC): 2026-11-20T12:08:31Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -niE '\b(npm|pip3?|brew|apt(-get)?|winget|choco|cargo|go|gem|uv) +install|/plugin +install|npx|uvx|curl |wget '
```

Raw output:

```text
(no output)
```

### Gate 4g.8: (stricter) UTF-8 only, no NUL bytes, no CR in committed blobs

- Time (UTC): 2026-11-20T12:08:33Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git ls-files -z | xargs -0 -n1 sh -c 'iconv -f UTF-8 -t UTF-8 "$0" > /dev/null 2>&1 || echo "not UTF-8: $0"'
git ls-files -z | xargs -0 -n1 sh -c 'tr -d "\\000" < "$0" | cmp -s - "$0" || echo "NUL byte: $0"'
git grep -lI $'\r' HEAD
```

Raw output:

```text
(no output)
```

### Gate 4g.9: (stricter) plugin.json fields exact; no hooks, userConfig, mcpServers or lsp

- Time (UTC): 2026-11-20T12:08:33Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 0)

Command:

```sh
python - <<'PY'
import json
m = json.load(open('.claude-plugin/plugin.json', encoding='utf-8'))
want = {'name': 'titan-receipts', 'displayName': 'Titan Receipts', 'version': '2.0.0',
        'privacyPolicyUrl': 'https://github.com/Rmasood1122/commitproof/blob/main/PRIVACY.md',
        'icon': './.claude-plugin/icon.svg'}
for k, v in want.items():
    if m.get(k) != v:
        print('wrong', k, repr(m.get(k)))
if m.get('author', {}).get('email') != 'rmasood112224@gmail.com':
    print('wrong author.email')
bad_kw = [k for k in m.get('keywords', []) if any(b in k.lower() for b in ('soc2', 'soc-2', 'hipaa', 'pci', 'tamper'))]
if bad_kw:
    print('banned keywords', bad_kw)
for k in ('hooks', 'userConfig', 'mcpServers', 'lspServers', 'lsp', 'agents', 'outputStyles', 'monitors'):
    if k in m:
        print('forbidden field', k)
PY
```

Raw output:

```text
(no output)
```

### Gate 4.1: no banned wording in shipped files (any letter case, nothing masked)

- Time (UTC): 2026-11-20T12:08:34Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `empty`
- Result: **PASS** (exit 1)

Command:

```sh
git grep -niE 'compliant|certif|\bproofs?\b|\bproves?\b|tamper|audit-ready|audit trail|soc ?2|hipaa|\bpci\b|reviewed|\b[0-9]+(\.[0-9]+)?x\b'
```

Raw output:

```text
(no output)
```

### Gate 4.2: README has at least 40 words outside code blocks

- Time (UTC): 2026-11-20T12:08:34Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `contains:README words outside code: PASS`
- Result: **FAIL** (exit 0)

Command:

````sh
python - <<'PY'
import re
t = open('README.md', encoding='utf-8').read()
prose = re.sub(r'(?ms)^```.*?^```', ' ', t)
n = len(prose.split())
print('README words outside code:', n, 'PASS' if n >= 40 else 'FAIL')
PY
````

Raw output:

```text
README words outside code: 805 PASS
```

### Gate 4.3: the tree is exactly the target tree

- Time (UTC): 2026-11-20T12:08:34Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `exact:.claude-plugin/icon.svg\n.claude-plugin/plugin.json\n.gitignore\nCHANGELOG.md\nLICENSE\nPRIVACY.md\nREADME.md\ncommands/ai-history.md\nskills/ai-history/SKILL.md\nskills/ai-history/reference/trailers.md`
- Result: **PASS** (exit 0)

Command:

```sh
git ls-files
```

Raw output:

```text
.claude-plugin/icon.svg
.claude-plugin/plugin.json
.gitignore
CHANGELOG.md
LICENSE
PRIVACY.md
README.md
commands/ai-history.md
skills/ai-history/SKILL.md
skills/ai-history/reference/trailers.md
```

### Gate 4.4: layer 1 again with README: its blocks equal the command's, and every number equals the golden oracle

- Time (UTC): 2026-11-20T12:09:06Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `contains:layer 1: PASS`
- Result: **PASS** (exit 0)

Command:

```sh
bash '/c/Users/rmaso/code/Rmasood1122/commitproof/evals/ai-history-v2/layer1.sh' '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/wt-v2' '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/fx' /c/Users/rmaso/code/Rmasood1122/commitproof /c/Users/rmaso/code/Rmasood1122/appealforge
```

Raw output:

```text
method text identical in command and skill: PASS
README sh blocks byte-identical to the command's: PASS
a: step 1 + block: commits 12/0 lines 138/0 authors 3 months 3: PASS
a: step 2b (emails) equals golden: PASS
b: step 1 + block: commits 10/10 lines 185/185 authors 2 months 2: PASS
b: step 2b (emails) equals golden: PASS
c: step 1 + block: commits 16/7 lines 409/141 authors 3 months 3: PASS
c: step 2b (emails) equals golden: PASS
d: step 1 + block: commits 12/6 lines 114/53 authors 2 months 3: PASS
d: step 2b (emails) equals golden: PASS
e: step 1 + block: commits 10/8 lines 65/47 authors 2 months 1: PASS
e: step 2b (emails) equals golden: PASS
f: empty repository, step 1 prints true, nothing, false: PASS  ['true', 'false']
g: step 1 + block: commits 5000/1750 lines 127500/42000 authors 20 months 12: PASS
g: step 2b (emails) equals golden: PASS
h: step 1 + block: commits 8/3 lines 70/20 authors 2 months 3: PASS
h: step 2b (emails) equals golden: PASS
hostile config (log.showRoot=false, diff.relative=true, run in data/) equals golden(c): PASS
control: plain git log under that config gives a different lines total: PASS  plain=200 block=409
real repo commitproof: commits 41/41 lines 7928/7928 authors 3: PASS
real repo appealforge: commits 143/126 lines 70523/47466 authors 4: PASS
layer 1: PASS
```

### Gate 4.5: the README sample is fixture c's golden answer, rendered by code

- Time (UTC): 2026-11-20T12:09:06Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `contains:README sample matches: True`
- Result: **PASS** (exit 0)

Command:

```sh
python - 'C:\Users\rmaso\code\Rmasood1122\commitproof\evals\ai-history-v2' 'C:\Users\rmaso\AppData\Local\Temp\claude\74486e4faaf2f9ee\deb1bc2b-013f-4645-9174-a879297d0526\scratchpad\fx' <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from block_check import render_layout
from fixtures import isolated_env
from golden import golden
fx = Path(sys.argv[2])
want = '\n'.join(('> ' + l) if l else '>' for l in render_layout(golden(fx / 'c', env=isolated_env(fx / '_git'))).splitlines())
print('README sample matches:', want in open('README.md', encoding='utf-8').read().replace('\r\n', '\n'))
PY
```

Raw output:

```text
README sample matches: True
```

### Gate 4.6: claude plugin validate (default)

- Time (UTC): 2026-11-20T12:09:07Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `contains:Validation passed`
- Result: **PASS** (exit 0)

Command:

```sh
claude plugin validate .
```

Raw output:

```text
Validating plugin manifest: C:\Users\rmaso\AppData\Local\Temp\claude\74486e4faaf2f9ee\deb1bc2b-013f-4645-9174-a879297d0526\scratchpad\wt-v2\.claude-plugin\plugin.json

Provides:

  ❯ skills: titan-receipts:ai-history
  ❯ commands: titan-receipts:ai-history

Hosts not read for: skills (1), commands (1)

Plugin directory checks for C:\Users\rmaso\AppData\Local\Temp\claude\74486e4faaf2f9ee\deb1bc2b-013f-4645-9174-a879297d0526\scratchpad\wt-v2. The plugin directory is the catalog that plugins are submitted to; this is a subset of what it runs.

✔ These checks found nothing to report

The directory also runs a safety scan and a policy review that this command does not.

ℹ Advice (does not change the verdict):

  ❯ C:\Users\rmaso\AppData\Local\Temp\claude\74486e4faaf2f9ee\deb1bc2b-013f-4645-9174-a879297d0526\scratchpad\wt-v2\README.md: This README has no line that installs "titan-receipts" from a marketplace. Add the install line, which works in one step on Claude Code 2.1.275 or later. Validate the folder that holds its marketplace.json to have <owner>/<repo> filled in, and the name its marketplace lists it under.
      /plugin install titan-receipts --marketplace <owner>/<repo>

✔ Validation passed
```

### Gate 4.7: claude plugin validate --strict --profile directory (stricter than spec)

- Time (UTC): 2026-11-20T12:09:08Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `exit0`
- Result: **PASS** (exit 0)

Command:

```sh
claude plugin validate . --strict --profile directory
```

Raw output:

```text
Validating plugin manifest: C:\Users\rmaso\AppData\Local\Temp\claude\74486e4faaf2f9ee\deb1bc2b-013f-4645-9174-a879297d0526\scratchpad\wt-v2\.claude-plugin\plugin.json

Provides:

  ❯ skills: titan-receipts:ai-history
  ❯ commands: titan-receipts:ai-history

Hosts not read for: skills (1), commands (1)

Plugin directory checks for C:\Users\rmaso\AppData\Local\Temp\claude\74486e4faaf2f9ee\deb1bc2b-013f-4645-9174-a879297d0526\scratchpad\wt-v2. The plugin directory is the catalog that plugins are submitted to; this is a subset of what it runs.

✔ These checks found nothing to report

The directory also runs a safety scan and a policy review that this command does not.

ℹ Advice (does not change the verdict):

  ❯ C:\Users\rmaso\AppData\Local\Temp\claude\74486e4faaf2f9ee\deb1bc2b-013f-4645-9174-a879297d0526\scratchpad\wt-v2\README.md: This README has no line that installs "titan-receipts" from a marketplace. Add the install line, which works in one step on Claude Code 2.1.275 or later. Validate the folder that holds its marketplace.json to have <owner>/<repo> filled in, and the name its marketplace lists it under.
      /plugin install titan-receipts --marketplace <owner>/<repo>

✔ Validation passed
```

> Gate 4.2 attempt 1 failed in the gate itself. The script printed `805 PASS` and the rule looked for `: PASS`. The README had 805 words outside code, against a minimum of 40. The print now puts the verdict first. Attempt 2 follows.

### Gate 4.2 (attempt 2): README has at least 40 words outside code blocks

- Time (UTC): 2026-11-20T12:09:21Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `contains:README words outside code: PASS`
- Result: **PASS** (exit 0)

Command:

````sh
python - <<'PY'
import re
t = open('README.md', encoding='utf-8').read()
prose = re.sub(r'(?ms)^```.*?^```', ' ', t)
n = len(prose.split())
print('README words outside code: ' + ('PASS' if n >= 40 else 'FAIL') + ' (' + str(n) + ')')
PY
````

Raw output:

```text
README words outside code: PASS (805)
```

## P5 — Evals (harness on branch engine, plugin = worktree of v2-candidate)

### Gate 5.0: scorer self-test: synthetic transcripts pass or fail with the right label (no model calls)

- Time (UTC): 2026-11-20T12:13:07Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `contains:compare self-test: PASS`
- Result: **PASS** (exit 0)

Command:

```sh
python "$(cygpath -w /c/Users/rmaso/code/Rmasood1122/commitproof/evals/ai-history-v2/selftest_compare.py)" "$(cygpath -w '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/wt-v2')" "$(cygpath -w '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/fx')"
```

Raw output:

```text
ok  c good: want pass; got pass
ok  c good, plugin via slash_commands: want pass; got pass
ok  c wrong total: want wrong-number; got ['wrong-number: commits_claude 8 != 7']
ok  c thousands separator: want wrong-number; got ['wrong-number: lines_all 4,09 != 409']
ok  c percentage: want policy; got ['policy: percent in answer', 'wrong-number: commits_claude 7 (44%) != 7']
ok  c missing month row: want missing-row; got ["missing-row: months {'2026-09': [7, 3], '2026-11': [5, 2]} != {'2026-09': [7, 3], '2026-10': [4, 2], '2026-11': [5, 2]}"]
ok  c preamble before first line: want format; got ["format: first line 'Here is the estimate.'"]
ok  c old label: want format; got ["format: 0 table headers end with 'With a Claude or LLM trailer'"]
ok  c no source line: want format; got ['format: source line missing']
ok  c banned word: want policy; got ["policy: banned word 'proves'"]
ok  c email shown: want policy; got ['policy: email in answer', "missing-row: authors {'Dana Lee <dana@example.com>': [6, 1], 'Priya Nair': [5, 4], 'Sam Ortiz': [5, 2]} != {'Dana Lee': [6, 1], 'Priya Nair': [5, 4], 'Sam Ortiz': [5, 2]}"]
ok  c extra bash: want tool-misuse; got ["tool-misuse: Bash ran more than the shipped commands: 'git log -p | head'"]
ok  c write tool: want tool-misuse; got ['tool-misuse: used Write']
ok  c wrong plugin path: want plugin; got ['plugin: titan-receipts loaded from C:\\Users\\rmaso\\AppData\\Local\\Temp, not the checkout under test']
ok  c plugin missing: want plugin; got ["plugin: titan-receipts not in init plugins: ['other']"]
ok  f empty good: want pass; got pass
ok  f empty with table: want format; got ['format: table shown for an empty repository']
ok  norepo good: want pass; got pass
ok  norepo edited block: want format; got ['policy: percent in answer', 'format: step-2 block not given verbatim']
ok  norepo counted anyway: want format; got ['format: table shown with no repository']
ok  paste good: want pass; got pass
ok  nl good: want pass; got pass
ok  nl no skill: want trigger; got ['trigger: the ai-history skill was not invoked']
compare self-test: PASS
```

### Gate 5.1: layer 1 on the final v2-candidate (fixtures rebuilt)

- Time (UTC): 2026-11-20T12:13:45Z
- Checkout: v2-candidate @ 1bc3aa3 (clean)
- Pass rule: `contains:layer 1: PASS`
- Result: **PASS** (exit 0)

Command:

```sh
bash /c/Users/rmaso/code/Rmasood1122/commitproof/evals/ai-history-v2/layer1.sh '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/wt-v2' '/c/Users/rmaso/AppData/Local/Temp/claude/74486e4faaf2f9ee/deb1bc2b-013f-4645-9174-a879297d0526/scratchpad/fx' /c/Users/rmaso/code/Rmasood1122/commitproof /c/Users/rmaso/code/Rmasood1122/appealforge
```

Raw output:

```text
method text identical in command and skill: PASS
README sh blocks byte-identical to the command's: PASS
a: step 1 + block: commits 12/0 lines 138/0 authors 3 months 3: PASS
a: step 2b (emails) equals golden: PASS
b: step 1 + block: commits 10/10 lines 185/185 authors 2 months 2: PASS
b: step 2b (emails) equals golden: PASS
c: step 1 + block: commits 16/7 lines 409/141 authors 3 months 3: PASS
c: step 2b (emails) equals golden: PASS
d: step 1 + block: commits 12/6 lines 114/53 authors 2 months 3: PASS
d: step 2b (emails) equals golden: PASS
e: step 1 + block: commits 10/8 lines 65/47 authors 2 months 1: PASS
e: step 2b (emails) equals golden: PASS
f: empty repository, step 1 prints true, nothing, false: PASS  ['true', 'false']
g: step 1 + block: commits 5000/1750 lines 127500/42000 authors 20 months 12: PASS
g: step 2b (emails) equals golden: PASS
h: step 1 + block: commits 8/3 lines 70/20 authors 2 months 3: PASS
h: step 2b (emails) equals golden: PASS
hostile config (log.showRoot=false, diff.relative=true, run in data/) equals golden(c): PASS
control: plain git log under that config gives a different lines total: PASS  plain=200 block=409
real repo commitproof: commits 42/42 lines 8511/8511 authors 3: PASS
real repo appealforge: commits 143/126 lines 70523/47466 authors 4: PASS
layer 1: PASS
```

