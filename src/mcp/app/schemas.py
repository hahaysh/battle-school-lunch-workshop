import datetime

from pydantic import BaseModel, ConfigDict, Field


class McpModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class School(McpModel):
    office_code: str = Field(alias="officeCode", description="시도교육청코드")
    office_name: str = Field(alias="officeName", description="시도교육청명")
    school_code: str = Field(alias="schoolCode", description="표준학교코드")
    school_name: str = Field(alias="schoolName", description="학교명")
    school_kind: str = Field(alias="schoolKind", description="학교종류명")
    address: str = Field(description="학교 도로명 주소")


class SchoolSearchResult(McpModel):
    items: list[School] = Field(description="검색된 학교 목록")
    total_count: int = Field(alias="totalCount", ge=0, description="전체 검색 결과 수")
    message: str = Field(default="", description="결과가 없을 때 사용자에게 전달할 안내 문구")


class Meal(McpModel):
    meal_date: datetime.date = Field(alias="date", description="급식 일자")
    meal_type: str = Field(alias="mealType", description="급식 종류(중식)")
    dishes: list[str] = Field(description="메뉴 목록")
    calorie: str = Field(description="칼로리 정보")
    origin: str = Field(description="원산지 정보")


class MealResult(McpModel):
    items: list[Meal] = Field(description="날짜순으로 정렬된 중식 급식 목록")
    message: str = Field(default="", description="결과가 없을 때 사용자에게 전달할 안내 문구")
