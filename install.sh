#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Python 3 is required. In Ubuntu run: sudo apt-get update && sudo apt-get install python3' >&2
  exit 2
fi
exec python3 "$ROOT/tools/install.py" "$@"
