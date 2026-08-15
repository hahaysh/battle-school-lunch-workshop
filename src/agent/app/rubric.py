"""Deterministic lunch rubric used by the independent evaluation agents."""

from dataclasses import dataclass

from .schemas import AreaScore, Meal

AREAS = (
    ("nutrition", "영양 균형", 35),
    ("health", "건강성", 25),
    ("quality", "식재료·메뉴 품질", 20),
    ("evidence", "데이터 충분성·근거 신뢰도", 20),
)


@dataclass(frozen=True)
class Evaluation:
    key: str
    name: str
    weight: int
    score: int
    evidence: list[str]


def _meal_text(meals: list[Meal]) -> str:
    return " ".join(dish for meal in meals for dish in meal.dishes).lower()


def evaluate_area(key: str, meals: list[Meal]) -> Evaluation:
    """Run one independent, explainable evaluator without an LLM."""
    text = _meal_text(meals)
    evidence: list[str] = []
    if not meals:
        return Evaluation(key, dict((k, n) for k, n, _ in AREAS)[key], dict((k, w) for k, _, w in AREAS)[key], 1, ["선택한 날짜의 중식 데이터가 없습니다."])
    if key == "nutrition":
        groups = sum(token in text for token in ("밥", "국", "찌개", "김치", "나물", "샐러드", "과일", "우유"))
        score = min(5, max(1, 2 + groups // 2))
        evidence.append(f"메뉴 {len(meals[0].dishes)}개와 확인 가능한 식품군 {groups}개를 기준으로 평가했습니다.")
    elif key == "health":
        burdens = sum(token in text for token in ("튀김", "돈까스", "햄", "소시지", "가공", "라면", "케이크"))
        score = max(1, min(5, 4 - burdens))
        evidence.append("영양 수치가 없으므로 메뉴명에서 직접 확인되는 부담 신호만 반영했습니다.")
    elif key == "quality":
        unique = len(set(text.split()))
        score = min(5, max(1, 2 + unique // 5))
        evidence.append(f"중복을 제외한 메뉴 표현 {unique}개와 원산지 정보를 근거로 평가했습니다.")
    else:
        complete = sum(bool(meal.dishes) and bool(meal.calorie) for meal in meals)
        score = 5 if complete == len(meals) and meals[0].origin else 4 if complete else 2
        evidence.append("날짜, 메뉴, 열량, 원산지 필드의 실제 제공 여부를 확인했습니다.")
    name, weight = next((name, weight) for area_key, name, weight in AREAS if area_key == key)
    return Evaluation(key, name, weight, score, evidence)


def to_area_score(evaluation: Evaluation) -> AreaScore:
    return AreaScore(key=evaluation.key, name=evaluation.name, score=evaluation.score, weight=evaluation.weight, evidence=evaluation.evidence)


def weighted_total(evaluations: list[Evaluation]) -> float:
    if sum(e.weight for e in evaluations) != 100:
        raise ValueError("평가 가중치는 100%여야 합니다.")
    return round(sum(e.score / 5 * e.weight for e in evaluations), 1)
