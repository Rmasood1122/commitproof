# Gate 2: the directory's file and content rules, run against a checkout of
# v2-candidate. Each check is logged by gate.py; every one must print nothing
# (or match exactly). Usage: bash gate2.sh PREFIX PLUGIN_CHECKOUT LOG
# Exit status: the number of failed checks.
set -u
prefix=$1; wt=$2; log=$3
here=$(cd "$(dirname "$0")" && pwd)
fails=0
gate() { python "$here/gate.py" "$log" "$1" "$2" "$3" "$wt" "$4" > /dev/null || { fails=$((fails + 1)); echo "FAIL: $1 $2"; }; }

# The spec's four checks, verbatim.
gate "$prefix.1" "only allowed file types are tracked" empty \
"git ls-files | grep -Ev '\.(md|txt|json|ya?ml|png|jpe?g|gif|webp|ico)\$' | grep -Ev '^(LICENSE|\.gitignore|\.claude-plugin/icon\.svg)\$'"
gate "$prefix.2" "no tracked file starts with #!" empty \
"git ls-files | xargs grep -l '^#!'"
gate "$prefix.3" "no dynamic-context lines, allowed-tools, credential names or installs" empty \
"git grep -nE '!\`|allowed-tools|TOKEN|SECRET|API_KEY|getenv|environ|pip install|npx|uvx|curl |marketplace add'"
gate "$prefix.4" "no file over 256 KiB" empty \
"find . -size +256k -not -path './.git/*'"

# Stricter extras (plan, 'Stricter extras').
gate "$prefix.5" "(stricter) .claude-plugin holds only plugin.json and the icon" \
'exact:.claude-plugin/icon.svg\n.claude-plugin/plugin.json' \
"git ls-files .claude-plugin"
gate "$prefix.6" "(stricter) no credential, secret, key or env-var words, any letter case" empty \
"git grep -niE 'token|secret|api[_-]?key|passw|credential|\\benv\\b|environ|getenv|\\\$[A-Z_]{2,}|\\\$\\{|CLAUDE_PLUGIN_ROOT|\\bkey\\b|\\.titan'"
gate "$prefix.7" "(stricter) no install commands of any package manager" empty \
"git grep -niE '\\b(npm|pip3?|brew|apt(-get)?|winget|choco|cargo|go|gem|uv) +install|/plugin +install|npx|uvx|curl |wget '"
gate "$prefix.8" "(stricter) UTF-8 only, no NUL bytes, no CR in committed blobs" empty \
"git ls-files -z | xargs -0 -n1 sh -c 'iconv -f UTF-8 -t UTF-8 \"\$0\" > /dev/null 2>&1 || echo \"not UTF-8: \$0\"'
git ls-files -z | xargs -0 -n1 sh -c 'tr -d \"\\\\000\" < \"\$0\" | cmp -s - \"\$0\" || echo \"NUL byte: \$0\"'
git grep -lI \$'\\r' HEAD"
gate "$prefix.9" "(stricter) plugin.json fields exact; no hooks, userConfig, mcpServers or lsp" empty \
"python - <<'PY'
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
PY"
exit $fails
