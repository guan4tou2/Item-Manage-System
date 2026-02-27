#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="${ROOT_DIR}/.venv313/bin/python"

if [ ! -x "${VENV_PY}" ]; then
  echo "Missing virtualenv python: ${VENV_PY}"
  exit 1
fi

export FLASK_APP=app

"${VENV_PY}" -m flask db downgrade -1
"${VENV_PY}" -m flask db upgrade
"${VENV_PY}" -m flask db current

echo "Rollback verify completed"
