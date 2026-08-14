# AGENTS.md

이 문서는 현재 저장소에서 작업하는 AI 코딩 에이전트를 위한 가이드입니다.
제품 요구사항은 `PRD.md`, 기술 결정과 시스템 구조는 `TRD.md`를 우선합니다.
워크숍의 후속 단계에 해당하는 MCP·Agent·데이터베이스 코드는 아직 이 저장소에
구현되어 있지 않으므로, 실제 파일과 스크립트를 기준으로 작업합니다.

## 1. 프로젝트 개요

NEIS 공개 API에서 학교 기본 정보와 중식 급식 정보를 조회하는 풀스택 앱입니다.
프런트엔드는 React·TypeScript·Vite·Fluent UI, 백엔드는 FastAPI·httpx로 구성됩니다.

- 급식 조회는 중식(`MMEAL_SC_CODE=2`)만 사용합니다.
- 브라우저는 NEIS API를 직접 호출하지 않고 백엔드의 `/api/*`만 호출합니다.
- 학교 검색은 이름 2자 이상, 페이지 크기 1~100으로 제한합니다.
- 급식 날짜 범위는 양끝 날짜를 포함해 최대 31일입니다.
- API 키와 내부 설정은 환경 변수 또는 배포 시크릿으로만 주입합니다.

## 2. 디렉터리 구조

```text
/
├── .github/              이슈·PR 템플릿, CODEOWNERS, CI
├── AGENTS.md             AI 코딩 에이전트 작업 지침
├── PRD.md                제품 요구사항
├── TRD.md                기술 요구사항
├── openapi.json          워크숍에서 사용하는 NEIS API 명세 원본
├── docker-compose.yml    API·웹 컨테이너 오케스트레이션
├── scripts/              로컬 Compose 실행 스크립트
├── data/                 명세 작성용 원본 데이터
├── docs/                 워크숍 단계별 문서
└── src/
    ├── openapi.json      프런트엔드·백엔드 내부 API 계약
    ├── api/              FastAPI 백엔드와 pytest 테스트
    ├── web/              React·Vite·Fluent UI 프런트엔드
    └── e2e/              Playwright 브라우저 테스트
```

### 백엔드 (`src/api/`)

- `app/main.py`: FastAPI 앱, lifespan, CORS, 라우터 및 공통 오류 핸들러
- `app/config.py`: `.env`와 환경 변수를 읽는 `pydantic-settings` 설정
- `app/neis_client.py`: NEIS 비동기 HTTP 클라이언트, 재시도 및 응답 정규화
- `app/schemas.py`: API 요청·응답 Pydantic 모델
- `app/main_errors.py`: 클라이언트 오류 타입
- `app/routers/schools.py`: `/api/schools` 학교 검색
- `app/routers/meals.py`: `/api/meals` 중식 조회 및 날짜 검증
- `app/routers/health.py`: `/api/health` 상태 확인
- `tests/unit/`: 날짜·메뉴 정규화와 도메인 규칙 테스트
- `tests/integration/`: FastAPI 라우터와 모킹한 NEIS HTTP 통합 테스트

### 프런트엔드 (`src/web/`)

- `src/App.tsx`: 학교 검색 → 기간 선택 → 급식 확인 3단계 화면과 상태 관리
- `src/lib/api.ts`: 백엔드 `/api/*` 호출 및 `ApiError` 변환
- `src/styles.css`: 화면 스타일
- `src/test/`: Vitest·React Testing Library·MSW 테스트 설정
- `Dockerfile`, `nginx.conf`: Vite 빌드 결과를 비특권 Nginx로 제공

### E2E (`src/e2e/`)

- `tests/lunch-flow.spec.ts`: 학교 검색, 기간 선택, 급식 확인 및 날짜 범위 검증
- `playwright.config.ts`: Chromium 프로젝트, `BASE_URL`, 선택적 개발 서버 설정

## 3. 도구와 환경

| 영역 | 요구 도구 |
| --- | --- |
| 백엔드 | Python 3.12+, `uv`, FastAPI, httpx, pytest, respx |
| 프런트엔드 | Node.js 20.19+ 또는 22.13+, npm, React, Vite, TypeScript |
| E2E | Playwright, Chromium |
| 실행·배포 | Docker Desktop, Docker Compose |

루트 `.env.example`을 `.env`로 복사하고 `NEIS_API_KEY`를 설정합니다. `.env`,
API 키와 기타 시크릿은 커밋하거나 로그·명령 기록에 출력하지 않습니다.
백엔드 설정은 다음 환경 변수를 지원합니다.

- `NEIS_API_KEY`: NEIS API 인증 키
- `NEIS_BASE_URL`: 기본값 `https://open.neis.go.kr/hub`
- `NEIS_TIMEOUT_SECONDS`: 기본값 10초, 최대 30초
- `NEIS_MAX_RETRIES`: 기본값 2회, 최대 5회
- `CORS_ORIGINS`: 쉼표로 구분한 허용 오리진 목록, 기본값 `http://localhost:3000`

## 4. 설치·실행·검증 명령

### Docker Compose로 전체 앱 실행

저장소 루트에서 실행합니다.

```powershell
.\scripts\run.ps1
docker compose down
```

`run.ps1`은 Docker와 Compose를 확인하고 `.env`가 없으면 `.env.example`을
복사한 뒤 `docker compose up --build`를 실행합니다. 웹은
`http://localhost:3000`, API는 `http://localhost:8000`에서 제공됩니다.

셸 스크립트가 필요한 환경에서는 다음을 사용합니다.

```bash
bash ./scripts/run.sh
```

### 루트 npm 스크립트

루트에는 의존성이 없으며 하위 디렉터리 명령을 위임합니다.

```powershell
npm run dev:web
npm run build
npm run test:web
npm run test:e2e
```

### 백엔드

```powershell
cd src/api
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run pytest -m unit
uv run pytest -m integration
```

### 프런트엔드

```powershell
cd src/web
npm ci
npm run dev
npm run build
npm run lint
npm test
npm run test:coverage
```

### E2E

```powershell
cd src/e2e
npm ci
npx playwright install chromium
$env:PLAYWRIGHT_START_SERVER = "true"
npm test
```

기본 E2E 대상은 `http://localhost:3000`이며, 다른 실행 중인 앱을 검증할 때는
`BASE_URL`로 재정의합니다. 테스트는 `/api/schools`와 `/api/meals`를
Playwright에서 모킹하므로 실제 NEIS·AI 서비스에 연결하지 않습니다.

## 5. 코딩 규칙

- 프런트엔드에서 `fetch`를 직접 사용하지 말고 `src/lib/api.ts`를 사용합니다.
- 백엔드의 외부 HTTP 호출은 `NeisClient`(`app/neis_client.py`)를 통해서만 수행합니다.
- API 라우터는 `app/routers/`에 추가하고, 요청·응답은 Pydantic 모델로 정의합니다.
- API 필드명과 쿼리 파라미터는 `src/openapi.json` 계약과 일치시킵니다.
  Python 내부 snake_case 필드는 Pydantic alias로 외부 camelCase를 유지합니다.
- NEIS 응답은 클라이언트 계층에서 정규화하고, 메뉴의 알레르기 번호와 HTML
  줄바꿈을 제거한 뒤 날짜순으로 반환합니다.
- 사용자에게 노출되는 API 오류는 `{ "error": { "code", "message" } }` 형식을
  사용합니다. NEIS 응답 본문·인증 정보·내부 예외를 그대로 반환하지 않습니다.
- 새 Python 의존성은 `src/api`에서 `uv add`, 새 JavaScript 의존성은 해당
  패키지 디렉터리에서 `npm install`로 추가하고 잠금 파일을 갱신합니다.
  잠금 파일을 수동 편집하지 않습니다.
- 생성물과 캐시(`dist/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`)는
  직접 수정하거나 커밋하지 않습니다.
- Docker 이미지의 non-root 사용자와 Nginx 비특권 포트를 유지합니다.

## 6. 테스트 원칙

| 계층 | 위치 | 도구 | 외부 경계 |
| --- | --- | --- | --- |
| API 단위 | `src/api/tests/unit/` | pytest | 외부 I/O 없음 |
| API 통합 | `src/api/tests/integration/` | pytest + respx | NEIS HTTP 모킹 |
| Web | `src/web/src/**/*.test.*` | Vitest + RTL + MSW | `/api/*` 모킹 |
| E2E | `src/e2e/tests/` | Playwright | `/api/*` 라우팅 모킹 |

- 순수 함수와 날짜 범위·오류 변환 같은 비즈니스 규칙을 우선 테스트합니다.
- 성공 응답뿐 아니라 잘못된 검색어, 잘못된 학교 코드, 잘못된 날짜 범위,
  upstream 오류·타임아웃의 안전한 오류 응답을 검증합니다.
- 실제 NEIS API, API 키, Azure 또는 모델 엔드포인트에 접근하는 테스트를
  만들지 않습니다.
- 새 pytest 마커는 `src/api/pyproject.toml`의 `markers`에 등록합니다.

## 7. Git·PR 규칙

- 작업 전 `git branch --show-current`와 `git status --short`로 상태를 확인합니다.
- 논리적으로 독립된 변경은 별도 커밋으로 나눕니다.
- 커밋 메시지는 변경 목적을 간결하게 설명합니다.
- PR은 `.github/PULL_REQUEST_TEMPLATE.md`의 구조를 그대로 사용하고 변경 요약과
  검증한 명령을 기록합니다.
- 관련 없는 변경사항을 되돌리거나 커밋에 섞지 않습니다.

## 8. 보안 및 운영 가드레일

- `.env`, API 키, 토큰, 인증서와 기타 시크릿을 커밋하지 않습니다.
- 시크릿을 소스 코드, 테스트 fixture, URL, 오류 메시지 또는 로그에 포함하지
  않습니다.
- 프런트엔드에 `NEIS_API_KEY`나 내부 서비스 URL을 전달하지 않습니다.
- CORS 허용 목록은 `CORS_ORIGINS` 설정으로 관리하며 전체 오리진 허용을 기본값으로
  두지 않습니다.
- API는 허용된 GET 메서드와 `Accept`·`Content-Type` 헤더만 CORS에 허용합니다.
- 생성된 OpenAPI 문서나 Docker 산출물을 임의로 수정하지 않습니다. API 계약이나
  배포 동작을 바꿀 때는 원본 명세·소스·Docker 설정을 함께 검토합니다.
