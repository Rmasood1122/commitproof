# Layer 1 (free, no model): rebuild the 8 fixtures, then run the shipped
# blocks against the golden oracle, plus the hostile-config copy and two real
# repositories. Usage: bash layer1.sh PLUGIN_CHECKOUT FIXTURES_DIR [REAL_REPO ...]
set -e
here=$(cd "$(dirname "$0")" && pwd)
plugin=$1; fx=$2; shift 2
win() { cygpath -w "$1" 2>/dev/null || printf '%s' "$1"; }
python "$(win "$here/fixtures.py")" "$(win "$fx")" > /dev/null
real=()
for r in "$@"; do real+=("$(win "$r")"); done
if [ ${#real[@]} -gt 0 ]; then
  python "$(win "$here/block_check.py")" "$(win "$plugin")" "$(win "$fx")" --real "${real[@]}"
else
  python "$(win "$here/block_check.py")" "$(win "$plugin")" "$(win "$fx")"
fi
