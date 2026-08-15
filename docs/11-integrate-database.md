# 데이터베이스 연동하기

## 선택과 데이터 모델

SQLite 관계형 데이터베이스를 선택했습니다. 별도 서버 없이 로컬 개발과 단일
에이전트 컨테이너에서 사용할 수 있고, 트랜잭션과 외래 키로 분석 한 건의
원자적 저장을 보장하기 때문입니다. `data/analyses.db`에 다음 테이블을 만듭니다.

- `analyses`: 분석 일자, 요청 프롬프트, 승자·패자/동점 결과, 총평, 품질 게이트
- `schools`: 교육청 코드, 학교 코드, 학교명
- `analysis_schools`: 분석과 대상 학교의 연결
- `agent_results`: 학교별 평가 영역, 점수, 가중치, 근거

## 로컬 실행과 마이그레이션

`DATABASE_PATH` 환경 변수로 파일 경로를 지정할 수 있습니다. 별도 마이그레이션
도구 없이 애플리케이션 시작 시 `CREATE TABLE IF NOT EXISTS`로 현재 스키마를
생성합니다. 로컬에서는 `src/agent`에서 `DATABASE_PATH=./data/analyses.db`
를 설정하고 실행하면 됩니다. Compose는 `agent-data` named volume을
`/app/data`에 마운트합니다.

분석이 끝나면 `POST /agui`가 모든 데이터를 하나의 SQLite 트랜잭션으로 저장하고,
응답의 `result.analysisId`로 `GET /analyses/{analysis_id}`에서 학교 정보,
분석 일자, 네 평가자 결과와 점수, 총평 및 비교 결과를 다시 조회할 수 있습니다.
