from datetime import date

import pytest

from app.repository import AnalysisRepository
from app.schemas import AnalysisResult, AreaScore, QualityGate, SchoolAnalysis


def result() -> AnalysisResult:
    return AnalysisResult(
        schools=[
            SchoolAnalysis(
                school={"officeCode": "J10", "schoolCode": "1", "schoolName": "A"},
                totalScore=80,
                areas=[
                    AreaScore(key="nutrition", name="영양 균형", score=4, weight=35, evidence=["근거"])
                ],
            ),
            SchoolAnalysis(
                school={"officeCode": "J10", "schoolCode": "2", "schoolName": "B"},
                totalScore=80,
                areas=[
                    AreaScore(key="nutrition", name="영양 균형", score=4, weight=35, evidence=["근거"])
                ],
            ),
        ],
        winner="동점",
        summary="비교 결과입니다.",
        qualityGate=QualityGate(passed=True),
    )


@pytest.mark.integration
def test_analysis_is_saved_and_retrieved_with_schools_and_agent_results(tmp_path):
    repository = AnalysisRepository(str(tmp_path / "analyses.db"))
    repository.initialize()

    analysis_id = repository.save(date(2026, 8, 17), "비교", result())

    saved = repository.get(analysis_id)
    assert saved is not None
    assert saved["date"] == "2026-08-17"
    assert [school["school"]["schoolName"] for school in saved["schools"]] == ["A", "B"]
    assert saved["schools"][0]["areas"][0]["score"] == 4
    assert saved["winner"] == "동점"
    assert saved["summary"] == "비교 결과입니다."


@pytest.mark.integration
def test_failed_save_rolls_back_the_entire_analysis(tmp_path):
    repository = AnalysisRepository(str(tmp_path / "analyses.db"))
    repository.initialize()
    invalid = result()
    invalid.schools[1].school.pop("officeCode")

    with pytest.raises(KeyError):
        repository.save(date(2026, 8, 17), "비교", invalid)

    assert repository.get(1) is None
