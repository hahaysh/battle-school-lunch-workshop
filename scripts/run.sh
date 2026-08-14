#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker가 설치되어 있지 않습니다. Docker를 먼저 설치해 주세요." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose를 사용할 수 없습니다. Docker를 실행해 주세요." >&2
  exit 1
fi

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "경고: .env.example을 .env로 복사했습니다. 실제 NEIS_API_KEY를 설정하면 급식 조회가 가능합니다." >&2
fi

exec docker compose up --build
