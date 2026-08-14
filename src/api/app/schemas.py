from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class School(ApiModel):
    office_code: str = Field(alias="officeCode")
    office_name: str = Field(alias="officeName")
    school_code: str = Field(alias="schoolCode")
    school_name: str = Field(alias="schoolName")
    school_kind: str = Field(alias="schoolKind")
    address: str


class SchoolList(ApiModel):
    items: list[School]
    total_count: int = Field(alias="totalCount", ge=0)


class Meal(ApiModel):
    date: date
    meal_type: str = Field(alias="mealType")
    dishes: list[str]
    calorie: str
    origin: str


class MealList(ApiModel):
    items: list[Meal]


class Health(ApiModel):
    status: str


class ErrorDetail(ApiModel):
    code: str
    message: str


class ErrorResponse(ApiModel):
    error: ErrorDetail

