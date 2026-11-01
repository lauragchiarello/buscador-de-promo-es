#!/usr/bin/env bash
# Start no Render: API + frontend compilado no mesmo serviço, na porta definida pelo Render.
set -euo pipefail
cd backend
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8010}" --proxy-headers --forwarded-allow-ips="*"
