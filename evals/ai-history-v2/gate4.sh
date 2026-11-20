# Gate 4: docs and the finished tree. Usage: bash gate4.sh PREFIX PLUGIN_CHECKOUT FIXTURES_DIR LOG
# Exit status: the number of failed checks.
set -u
prefix=$1; wt=$2; fx=$3; log=$4
here=$(cd "$(dirname "$0")" && pwd)
where=$(cygpath -w "$here"); wfx=$(cygpath -w "$fx")
fails=0
gate() { python "$here/gate.py" "$log" "$1" "$2" "$3" "$wt" "$4" > /dev/null || { fails=$((fails + 1)); echo "FAIL: $1 $2"; }; }

gate "$prefix.1" "no banned wording in shipped files (any letter case, nothing masked)" empty \
"git grep -niE 'compliant|certif|\\bproofs?\\b|\\bproves?\\b|tamper|audit-ready|audit trail|soc ?2|hipaa|\\bpci\\b|reviewed|\\b[0-9]+(\\.[0-9]+)?x\\b'"

gate "$prefix.2" "README has at least 40 words outside code blocks" contains:'README words outside code: PASS' \
"python - <<'PY'
import re
t = open('README.md', encoding='utf-8').read()
prose = re.sub(r'(?ms)^\`\`\`.*?^\`\`\`', ' ', t)
n = len(prose.split())
print('README words outside code: ' + ('PASS' if n >= 40 else 'FAIL') + ' (' + str(n) + ')')
PY"

gate "$prefix.3" "the tree is exactly the target tree" \
'exact:.claude-plugin/icon.svg\n.claude-plugin/plugin.json\n.gitignore\nCHANGELOG.md\nLICENSE\nPRIVACY.md\nREADME.md\ncommands/ai-history.md\nskills/ai-history/SKILL.md\nskills/ai-history/reference/trailers.md' \
"git ls-files"

gate "$prefix.4" "layer 1 again with README: its blocks equal the command's, and every number equals the golden oracle" \
contains:'layer 1: PASS' \
"bash '$here/layer1.sh' '$wt' '$fx' /c/Users/rmaso/code/Rmasood1122/commitproof /c/Users/rmaso/code/Rmasood1122/appealforge"

gate "$prefix.5" "the README sample is fixture c's golden answer, rendered by code" \
contains:'README sample matches: True' \
"python - '$where' '$wfx' <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from block_check import render_layout
from fixtures import isolated_env
from golden import golden
fx = Path(sys.argv[2])
want = '\\n'.join(('> ' + l) if l else '>' for l in render_layout(golden(fx / 'c', env=isolated_env(fx / '_git'))).splitlines())
print('README sample matches:', want in open('README.md', encoding='utf-8').read().replace('\\r\\n', '\\n'))
PY"

gate "$prefix.6" "claude plugin validate (default)" contains:'Validation passed' \
"claude plugin validate ."

gate "$prefix.7" "claude plugin validate --strict --profile directory (stricter than spec)" exit0 \
"claude plugin validate . --strict --profile directory"
exit $fails
