from datetime import date

from pydantic import BaseModel, Field, field_validator


class SchoolInput(BaseModel):
    officeCode: str = Field(min_length=2, max_length=4)
    schoolCode: str = Field(min_length=1)
    schoolName: str = Field(min_length=1)


class Meal(BaseModel):
    date: date
    mealType: str = "중식"
    dishes: list[str] = Field(default_factory=list)
    calorie: str = ""
    origin: str = ""


class AnalysisRequest(BaseModel):
    schools: list[SchoolInput]
    date: date
    prompt: str = Field(min_length=1, max_length=4000)

    @field_validator("schools")
    @classmethod
    def exactly_two_schools(cls, value: list[SchoolInput]) -> list[SchoolInput]:
        if len(value) != 2 or (
            value[0].officeCode,
            value[0].schoolCode,
        ) == (
            value[1].officeCode,
            value[1].schoolCode,
        ):
            raise ValueError("정확히 서로 다른 2개의 학교를 선택해 주세요.")
        return value


class AreaScore(BaseModel):
    key: str
    name: str
    score: int = Field(ge=1, le=5)
    weight: int = Field(ge=0, le=100)
    evidence: list[str]


class SchoolAnalysis(BaseModel):
    school: dict[str, str]
    totalScore: float
    areas: list[AreaScore]


class QualityGate(BaseModel):
    passed: bool
    warnings: list[str] = []


class AnalysisResult(BaseModel):
    schools: list[SchoolAnalysis]
    winner: str
    summary: str
    qualityGate: QualityGate
