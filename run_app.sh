#!/usr/bin/env bash
set -euo pipefail

main() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "找不到 python3，請先安裝 Python 3 再執行此腳本。" >&2
    exit 1
  fi

  if [ ! -d "venv" ]; then
    python3 -m venv venv
  fi

  # shellcheck source=/dev/null
  source venv/bin/activate

  python -m pip install --upgrade pip
  pip install -r requirements.txt

  uvicorn backend.main:app --host 0.0.0.0 --port 8000
}

main "$@"
