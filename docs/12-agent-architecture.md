# 분석 에이전트 아키텍처

이슈 #9의 분석 서비스(`src/agent`)는 **Microsoft Agent Framework의 Python
패키지**를 사용한다. 모델 연동은 Microsoft Foundry를 선택했으며,
`FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_API_KEY`, `FOUNDRY_MODEL`을 배포 시
주입할 수 있다. 테스트와 로컬 개발에서는 모델 호출 없이 동일한 결정론적
루브릭 계산기를 사용한다.

## 워크플로우

1. `McpLunchClient`가 기존 MCP 서버의 `get_lunch_meals` 도구를 호출한다.
2. `Concurrent` 단계에서 영양 균형, 건강성, 식재료·메뉴 품질,
   데이터 충분성·근거 신뢰도 평가자를 병렬 실행한다.
3. `Sequential` 품질 게이트가 네 결과의 근거와 누락을 확인한다.
4. 총점은 애플리케이션의 결정론적 계산기가 100점으로 환산한다. 품질 게이트나
   모델은 점수를 변경할 수 없다.

`/agui`는 AG-UI 호환 SSE 이벤트(`RUN_STARTED`, `STEP_FINISHED`,
`RUN_FINISHED`, `RUN_ERROR`)를 내보낸다. DevUI는 다음 명령으로 같은 앱의
워크플로우를 관찰할 수 있다.

```powershell
cd src/agent
uv run devui app --port 8091 --host 127.0.0.1 --no-open
```

비밀값은 `.env` 또는 배포 시크릿으로만 제공하며 저장소에는 포함하지 않는다.
