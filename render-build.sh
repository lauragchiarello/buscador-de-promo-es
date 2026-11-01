#!/usr/bin/env bash
# Build no Render (serviço "Python 3"): instala o backend e compila o frontend.
set -euo pipefail

pip install --upgrade pip
pip install -r backend/requirements.txt

if command -v npm >/dev/null 2>&1; then
  echo "Compilando o frontend (Node $(node --version))..."
  (cd frontend && npm ci --no-fund --no-audit && npm run build)
else
  echo "ERRO: npm não encontrado no ambiente de build; o frontend não foi compilado." >&2
  exit 1
fi
