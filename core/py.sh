#!/bin/sh
# usage: sh py.sh SCRIPT [ARGS...]
# Run SCRIPT under the first Python 3.10+ on PATH, passing its exit code
# through. `python3` alone is not enough: Windows' classic python.org
# installer ships python.exe and py.exe but no python3.exe, and the
# WindowsApps python3.exe alias only prints a Microsoft Store message — so
# `python3 … || true` made the plugin fail silently there. The probe runs
# with stdin closed, leaving the hook payload on stdin for the real run.
# Callers pass SCRIPT explicitly so no path parsing happens here (on Windows
# CLAUDE_PLUGIN_ROOT may hold backslashes).
for py in python3 python py; do
  if "$py" -c 'import sys; sys.exit(sys.version_info < (3, 10))' </dev/null >/dev/null 2>&1; then
    exec "$py" "$@"
  fi
done
echo "ai-audit-trail: needs Python 3.10+ on PATH as python3, python or py — none found" >&2
exit 127
