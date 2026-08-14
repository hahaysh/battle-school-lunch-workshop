$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker가 설치되어 있지 않습니다. Docker Desktop을 먼저 설치해 주세요."
}

docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose를 사용할 수 없습니다. Docker Desktop을 실행해 주세요."
}

if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
    Write-Warning ".env.example을 .env로 복사했습니다. 실제 NEIS_API_KEY를 설정하면 급식 조회가 가능합니다."
}

docker compose up --build
