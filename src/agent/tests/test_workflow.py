from datetime import date

import pytest

from app.rubric import AREAS, weighted_total
from app.schemas import AnalysisRequest, Meal, SchoolInput
from app.workflow import run_analysis


class FakeMcpClient:
    async def get_meals(self, school: SchoolInput, day: date) -> list[Meal]:
        return [
            Meal(
                date=day,
                dishes=["현미밥", "된장국", "닭볶음", "나물무침", "김치"],
                calorie="700 Kcal",
                origin="쌀: 국내산",
            )
        ]


@pytest.mark.unit
def test_rubric_weights_sum_to_100_and_total_is_deterministic():
    assert sum(weight for _, _, weight in AREAS) == 100
    assert weighted_total([
        # All four 5-point areas must produce exactly 100 points.
        type("Evaluation", (), {"score": 5, "weight": weight})()
        for _, _, weight in AREAS
    ]) == 100.0


@pytest.mark.unit
def test_request_requires_two_distinct_school_identity_pairs():
    school = SchoolInput(officeCode="J10", schoolCode="1", schoolName="A")
    with pytest.raises(ValueError):
        AnalysisRequest(schools=[school, school], date=date(2026, 8, 17), prompt="분석")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analysis_runs_four_independent_areas_and_quality_gate():
    request = AnalysisRequest(
        schools=[
            SchoolInput(officeCode="J10", schoolCode="1", schoolName="A"),
            SchoolInput(officeCode="J10", schoolCode="2", schoolName="B"),
        ],
        date=date(2026, 8, 17),
        prompt="근거를 포함해 비교해 주세요.",
    )
    result = await run_analysis(request, FakeMcpClient())
    assert len(result.schools) == 2
    assert all(len(school.areas) == 4 for school in result.schools)
    assert all(school.totalScore == 80.0 for school in result.schools)
    assert result.winner == "동점"
    assert result.qualityGate.passed
