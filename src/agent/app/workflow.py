import asyncio
from collections.abc import Awaitable, Callable

from .mcp_client import McpLunchClient
from .rubric import AREAS, Evaluation, evaluate_area, to_area_score, weighted_total
from .schemas import AnalysisRequest, AnalysisResult, QualityGate, SchoolAnalysis

try:  # The adapter is optional for deterministic/offline test execution.
    from agent_framework import Concurrent, Sequential  # type: ignore
except ImportError:  # pragma: no cover - exercised only when package is unavailable
    Concurrent = Sequential = None

Progress = Callable[[str, str], Awaitable[None]]


async def run_analysis(
    request: AnalysisRequest,
    meals_client: McpLunchClient,
    progress: Progress | None = None,
) -> AnalysisResult:
    async def notify(name: str, message: str) -> None:
        if progress:
            await progress(name, message)

    # Concurrent: MCP fetch and the four independent rubric evaluators have no
    # shared mutable state. Sequential: the quality gate runs after all evidence.
    await notify("mcp", "MCP 서버에서 두 학교의 중식 데이터를 조회하고 있어요…")
    meals = await asyncio.gather(*(meals_client.get_meals(school, request.date) for school in request.schools))
    if any(not items for items in meals):
        raise ValueError("두 학교 모두 선택한 날짜의 중식 데이터가 있어야 분석할 수 있습니다.")

    async def evaluate_school(school, school_meals) -> SchoolAnalysis:
        await notify("evaluators", f"{school.schoolName}의 4개 평가자를 병렬 실행하고 있어요…")
        evaluations: list[Evaluation] = list(await asyncio.gather(*(
            asyncio.to_thread(evaluate_area, key, school_meals) for key, _, _ in AREAS
        )))
        return SchoolAnalysis(
            school={
                "officeCode": school.officeCode,
                "schoolCode": school.schoolCode,
                "schoolName": school.schoolName,
            },
            totalScore=weighted_total(evaluations),
            areas=[to_area_score(evaluation) for evaluation in evaluations],
        )

    # Concurrent orchestration: both schools and all four area evaluators are
    # independent and receive only the normalized MCP data.
    school_results = list(await asyncio.gather(*(
        evaluate_school(school, school_meals)
        for school, school_meals in zip(request.schools, meals)
    )))

    await notify("quality-gate", "최종 품질 게이트에서 근거와 모순을 확인하고 있어요…")
    warnings: list[str] = []
    expected_keys = {key for key, _, _ in AREAS}
    for result in school_results:
        actual_keys = {area.key for area in result.areas}
        if actual_keys != expected_keys:
            warnings.append(f"{result.school['schoolName']}의 평가 영역이 루브릭과 일치하지 않습니다.")
        if any(not area.evidence for area in result.areas):
            warnings.append(f"{result.school['schoolName']}의 일부 평가에 근거가 없습니다.")
    scores = [school.totalScore for school in school_results]
    if scores[0] == scores[1]:
        winner = "동점"
    else:
        winner_index = scores.index(max(scores))
        loser_index = 1 - winner_index
        winner = (
            f"{school_results[winner_index].school['schoolName']} 승리, "
            f"{school_results[loser_index].school['schoolName']} 패자"
        )
    summary = f"{winner}입니다. 애플리케이션이 결정론적으로 계산한 총점은 {scores[0]:.1f}점과 {scores[1]:.1f}점입니다."
    await notify("done", "분석이 완료되었습니다.")
    return AnalysisResult(
        schools=school_results,
        winner=winner,
        summary=summary,
        qualityGate=QualityGate(passed=not warnings, warnings=warnings),
    )
