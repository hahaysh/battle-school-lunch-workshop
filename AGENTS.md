# AGENTS.md

이 문서는 AI 코딩 에이전트가 이 저장소에서 작업할 때 따라야 할 규칙과 명령을
정리한 가이드입니다. 제품 요구사항은 `PRD.md`, 시스템 구조와 구현 결정은
`TRD.md`를 기준으로 합니다.

## 1. 프로젝트 개요

NEIS 학교기본정보 및 급식식단정보 API를 사용하는 풀스택 급식 조회 앱입니다.
프런트엔드는 React + TypeScript, 백엔드는 FastAPI이며, MCP와 멀티 에이전트
분석 서비스를 함께 제공합니다.

- 급식은 중식(`MMEAL_SC_CODE=2`)으로 조회합니다.
- 브라우저는 NEIS API를 직접 호출하지 않고 백엔드의 `/api/*`만 호출합니다.
- `src/openapi.json`은 백엔드와 MCP 도구가 공유하는 단일 API 계약입니다.
- API 키와 AI 서비스 자격 증명은 환경 변수 또는 배포 시크릿으로만 주입합니다.

## 2. 디렉터리 구조

```text
/
├── .github/       이슈·PR 템플릿, CODEOWNERS, CI
├── AGENTS.md      AI 코딩 에이전트 작업 지침
├── PRD.md         제품 요구사항
├── TRD.md         기술 요구사항
├── openapi.json   NEIS API 명세 원본
├── apphost.mts    로컬·Azure 서비스 오케스트레이션
├── docker-compose.yml
└── src/
    ├── api/       FastAPI 백엔드
    ├── web/       React + Vite + TypeScript 프런트엔드
    ├── mcp/       OpenAPI 기반 MCP 서버
    ├── agent/     멀티 에이전트 분석 서비스
    └── e2e/       Playwright 엔드투엔드 테스트
```

### 백엔드 (`src/api/`)

- `app/main.py`: FastAPI 앱, CORS, lifespan 및 라우터 등록
- `app/config.py`: `pydantic-settings` 기반 환경 설정
- `app/neis_client.py`: `httpx` 비동기 NEIS 클라이언트
- `app/schemas.py`: 요청·응답 Pydantic 모델
- `app/routers/`: 학교·급식·상태 확인 API 라우터
- `tests/`: pytest 단위·통합 테스트

### 프런트엔드 (`src/web/`)

- `src/pages/`: 학교 조회와 급식 분석 페이지
- `src/components/`: 화면 컴포넌트
- `src/lib/api.ts`: 백엔드 `/api/*` 호출 래퍼
- `src/test/`: Vitest, React Testing Library, MSW 테스트 인프라

### MCP·Agent·E2E

- `src/mcp/`: `openapi.json`을 읽어 MCP 도구를 등록하고 NEIS 호출을 중계합니다.
- `src/agent/`: MCP 데이터를 이용해 전문 에이전트를 실행하고 결과를 종합합니다.
- `src/e2e/`: Playwright 브라우저 테스트와 테스트 설정을 보관합니다.

## 3. 도구와 런타임

| 영역 | 도구 |
| --- | --- |
| Python 서비스 | Python 3.12+, `uv`, FastAPI, pytest |
| Web | Node.js 20.19+ 또는 22.13+, npm, React, Vite, TypeScript |
| 테스트 | Vitest + React Testing Library + MSW, pytest + respx, Playwright |
| 오케스트레이션 | Docker Compose, Aspire CLI |
| 배포 | Azure CLI, Docker |

저장소 루트의 `.env`에 `NEIS_API_KEY`를 설정합니다. `.env` 파일과 실제 키는
커밋하거나 로그·명령 기록에 출력하지 않습니다.

## 4. 설치·실행·검증 명령

### 전체 애플리케이션

```bash
npm install
docker compose up --build
docker compose down
```

개발 오케스트레이션을 사용하는 경우 다음 명령을 사용합니다.

```bash
npm run dev
aspire stop
```

### 백엔드

```bash
cd src/api
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run pytest -m unit
uv run pytest -m integration
```

### 프런트엔드

```bash
cd src/web
npm install
npm run dev
npm run build
npm run lint
npm test
npm run test:coverage
```

### MCP·Agent

```bash
cd src/mcp
uv sync --all-groups
uv run pytest

cd ../agent
uv sync --all-groups
uv run pytest
```

### E2E

```bash
cd src/e2e
npm install
npm test
npm run test:headed
npm run test:ui
```

Playwright 브라우저가 없으면 `npx playwright install chromium`을 먼저
실행합니다. 테스트는 실제 NEIS, MCP 또는 AI 서비스에 연결하지 않습니다.

## 5. 코딩 규칙

- 프런트엔드에서 `fetch`를 직접 사용하지 말고 `src/lib/api.ts` 래퍼를 통합니다.
- 백엔드 외부 HTTP 호출은 `neis_client.py`를 통해서만 수행합니다.
- API 요청·응답은 Pydantic 모델로 정의하고, 새 라우터는 `app/routers/`에 추가합니다.
- API와 MCP의 파라미터·응답은 `openapi.json` 계약과 일치해야 합니다. 스키마를
  코드에 중복 정의하지 않습니다.
- 새 의존성은 Python 패키지 디렉터리에서 `uv add`, JavaScript 패키지는 해당
  디렉터리에서 `npm install`로 추가하고 잠금 파일을 갱신합니다. 잠금 파일을
  수동 편집하지 않습니다.
- 생성 디렉터리와 빌드 산출물(`dist/`, 캐시, Compose 생성물)은 직접 수정하거나
  커밋하지 않습니다.
- 날짜 범위는 최대 31일로 제한합니다.

## 6. 테스트 원칙

| 계층 | 위치 | 도구 | 모킹 경계 |
| --- | --- | --- | --- |
| API 단위·통합 | `src/api/tests/` | pytest + respx | NEIS HTTP |
| Web 통합 | `src/web/src/**/*.test.*` | Vitest + RTL + MSW | `/api/*` |
| MCP | `src/mcp/tests/` | pytest + respx | NEIS HTTP |
| Agent | `src/agent/tests/` | pytest | MCP·AI 서비스 |
| E2E | `src/e2e/tests/` | Playwright | `/api/*`, `/agent` |

- 순수 함수와 실제 비즈니스 로직을 우선 테스트합니다.
- 프레젠테이션 전용 컴포넌트와 단순한 한 줄짜리 유틸에는 불필요한 테스트를
  추가하지 않습니다.
- 새 pytest 마커는 해당 `pyproject.toml`에 등록한 후 사용합니다.
- API 키, 실제 학교 API, Azure 또는 모델 엔드포인트에 접근하는 테스트를 만들지
  않습니다. 외부 경계에서 모킹하고 오류 응답도 검증합니다.

## 7. Git·PR 규칙

- 작업 전 `git branch --show-current`로 브랜치를 확인합니다.
- 논리적으로 독립된 변경은 별도 커밋으로 나눕니다.
- 커밋 메시지는 변경 목적을 간결하게 설명합니다.
- PR 작성 시 `.github/PULL_REQUEST_TEMPLATE.md`를 그대로 사용하고, 변경 요약과
  검증한 명령을 빠짐없이 기록합니다.
- PR은 반드시 `.github/PULL_REQUEST_TEMPLATE.md`를 사용해 작성합니다.
- 관련 없는 변경사항을 되돌리거나 커밋에 섞지 않습니다.

## 8. 보안 및 운영 가드레일

- `.env`, API 키, 토큰, 인증서와 기타 시크릿을 커밋하지 않습니다.
- 시크릿을 소스 코드, 테스트 fixture, URL, 에러 메시지 또는 로그에 포함하지
  않습니다.
- 프런트엔드에 `NEIS_API_KEY`나 내부 서비스 URL을 전달하지 않습니다.
- Docker 런타임의 non-root 사용자와 네트워크 격리를 디버깅 편의를 위해
  약화시키지 않습니다.
- CORS 허용 목록은 설정을 통해 관리하며 전체 오리진 허용을 기본값으로 두지
  않습니다.
- 생성된 OpenAPI 문서나 배포 파일을 임의로 수정하지 말고, 원본 명세나
  `apphost.mts`를 변경한 뒤 재생성합니다.
