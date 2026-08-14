import { FormEvent, useMemo, useState } from "react";
import {
  Button,
  Card,
  FluentProvider,
  Input,
  MessageBar,
  MessageBarBody,
  Spinner,
  webLightTheme,
} from "@fluentui/react-components";
import { ApiError, getMeals, Meal, School, searchSchools } from "./lib/api";
import "./styles.css";

type Step = 1 | 2 | 3;

function dateInputValue(date: Date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function defaultDates() {
  const start = new Date();
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  return { from: dateInputValue(start), to: dateInputValue(end) };
}

function validateRange(from: string, to: string): string {
  if (!from || !to) return "시작일과 종료일을 모두 선택해 주세요.";
  const start = new Date(`${from}T00:00:00`);
  const end = new Date(`${to}T00:00:00`);
  if (end < start) return "종료일은 시작일 이후여야 합니다.";
  const inclusiveDays = Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1;
  if (inclusiveDays > 31) return "조회 기간은 최대 31일입니다.";
  return "";
}

function datesBetween(from: string, to: string) {
  const dates: string[] = [];
  const current = new Date(`${from}T00:00:00`);
  const end = new Date(`${to}T00:00:00`);
  while (current <= end) {
    dates.push(dateInputValue(current));
    current.setDate(current.getDate() + 1);
  }
  return dates;
}

const koreanDate = new Intl.DateTimeFormat("ko-KR", {
  month: "long",
  day: "numeric",
  weekday: "short",
  timeZone: "Asia/Seoul",
});

function MealCard({ date, meal }: { date: string; meal?: Meal }) {
  return (
    <Card className={`meal-card ${meal ? "" : "meal-card--empty"}`}>
      <h3>{koreanDate.format(new Date(`${date}T00:00:00+09:00`))}</h3>
      {meal ? (
        <>
          <ul aria-label={`${date} 메뉴`}>
            {meal.dishes.map((dish, index) => <li key={`${dish}-${index}`}>{dish}</li>)}
          </ul>
          <p className="calorie">{meal.calorie || "열량 정보 없음"}</p>
          {meal.origin && <details><summary>원산지 정보</summary><p>{meal.origin}</p></details>}
        </>
      ) : (
        <p>급식 없음</p>
      )}
    </Card>
  );
}

export default function App() {
  const defaults = useMemo(defaultDates, []);
  const [step, setStep] = useState<Step>(1);
  const [query, setQuery] = useState("");
  const [schools, setSchools] = useState<School[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [school, setSchool] = useState<School | null>(null);
  const [fromDate, setFromDate] = useState(defaults.from);
  const [toDate, setToDate] = useState(defaults.to);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  async function onSearch(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (value.length < 2) {
      setError("2자 이상 입력해 주세요.");
      return;
    }
    setLoading(true);
    setError("");
    setSearched(true);
    try {
      const result = await searchSchools(value);
      setSchools(result.items);
      setTotalCount(result.totalCount);
    } catch (reason) {
      setSchools([]);
      setError(reason instanceof Error ? reason.message : "학교를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function onMeals(event: FormEvent) {
    event.preventDefault();
    if (!school) return;
    const rangeError = validateRange(fromDate, toDate);
    if (rangeError) {
      setError(rangeError);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await getMeals(school, fromDate, toDate);
      setMeals(result.items);
      setStep(3);
    } catch (reason) {
      if (reason instanceof ApiError && reason.code === "INVALID_SCHOOL") {
        setSchool(null);
        setMeals([]);
        setSchools([]);
        setSearched(false);
        setStep(1);
        setError("학교 정보를 다시 선택해 주세요.");
        return;
      }
      setError(reason instanceof Error ? reason.message : "급식 정보를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  function chooseSchool(selected: School) {
    setSchool(selected);
    setMeals([]);
    setError("");
    setStep(2);
  }

  const mealByDate = new Map(meals.map((meal) => [meal.date, meal]));

  return (
    <FluentProvider theme={webLightTheme}>
    <>
      <header className="hero">
        <div className="hero__inner">
          <span className="eyebrow">오늘의 학교 식탁</span>
          <h1>급식 배틀</h1>
          <p>학교를 찾고, 원하는 기간의 중식 메뉴를 한눈에 확인하세요.</p>
        </div>
      </header>
      <main>
        <ol className="steps" aria-label="조회 단계">
          {["학교 찾기", "기간 선택", "급식 확인"].map((label, index) => (
            <li key={label} aria-current={step === index + 1 ? "step" : undefined}
              className={step >= index + 1 ? "active" : ""}>
              <span>{index + 1}</span>{label}
            </li>
          ))}
        </ol>

        {school && step > 1 && (
          <aside className="selected" aria-label="선택한 학교">
            <div><small>선택한 학교</small><strong>{school.schoolName}</strong>
              <span>{school.officeName} · {school.schoolKind}</span></div>
            <Button type="button" appearance="subtle" className="text-button" onClick={() => {
              setStep(1); setError(""); setMeals([]);
            }}>학교 변경</Button>
          </aside>
        )}

        <section className="panel" aria-labelledby={`step-${step}-title`}>
          {step === 1 && (
            <>
              <div className="section-heading">
                <span className="number">01</span>
                <div><h2 id="step-1-title">학교를 찾아보세요</h2>
                  <p>학교 이름을 2자 이상 입력해 주세요.</p></div>
              </div>
              <form className="search-form" onSubmit={onSearch}>
                <label htmlFor="school-name">학교 이름</label>
                <div className="field-row">
                  <Input id="school-name" value={query}
                    onChange={(event) => { setQuery(event.target.value); setError(""); }}
                    placeholder="예: 배틀초등학교" autoComplete="off" />
                  <Button type="submit" appearance="primary" disabled={loading || query.trim().length < 2}>학교 검색</Button>
                </div>
                {query.length > 0 && query.trim().length < 2 &&
                  <p className="hint">2자 이상 입력해 주세요.</p>}
              </form>
              {loading && <div className="status" role="status"><Spinner size="tiny" /> 학교를 찾고 있어요…</div>}
              {error && <div role="alert" className="alert"><MessageBar intent="error"><MessageBarBody>{error}
                <Button appearance="secondary" type="button" onClick={() => void onSearch({ preventDefault() {} } as FormEvent)}>다시 시도</Button>
              </MessageBarBody></MessageBar></div>}
              {!loading && searched && !error && schools.length === 0 &&
                <p className="empty">검색 결과가 없습니다. 학교 이름을 다시 확인해 주세요.</p>}
              {schools.length > 0 && (
                <div className="results">
                  <div className="results__heading"><h3>검색 결과</h3><span>{totalCount}개 학교</span></div>
                  {totalCount > schools.length &&
                    <p className="notice">검색 결과가 많습니다. 더 구체적으로 입력해 주세요.</p>}
                  <ul className="school-list">
                    {schools.map((item) => (
                      <li key={`${item.officeCode}-${item.schoolCode}`}>
                        <Button appearance="subtle" type="button" onClick={() => chooseSchool(item)}>
                          <strong>{item.schoolName}</strong>
                          <span>{item.schoolKind} · {item.officeName}</span>
                          <small>{item.address}</small>
                          <b aria-hidden="true">선택 →</b>
                        </Button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {step === 2 && (
            <>
              <div className="section-heading">
                <span className="number">02</span>
                <div><h2 id="step-2-title">조회 기간을 선택하세요</h2>
                  <p>최대 31일까지 중식 메뉴를 확인할 수 있어요.</p></div>
              </div>
              <form onSubmit={onMeals}>
                <div className="date-grid">
                  <label>시작일<Input aria-label="시작일" type="date" value={fromDate}
                    onChange={(event) => { setFromDate(event.target.value); setError(""); }} /></label>
                  <span aria-hidden="true">→</span>
                  <label>종료일<Input aria-label="종료일" type="date" value={toDate} min={fromDate}
                    onChange={(event) => { setToDate(event.target.value); setError(""); }} /></label>
                </div>
                {error && <div role="alert" className="alert"><MessageBar intent="error"><MessageBarBody>{error}
                  <Button appearance="secondary" type="button" onClick={() => void onMeals({ preventDefault() {} } as FormEvent)}>다시 시도</Button>
                </MessageBarBody></MessageBar></div>}
                {loading && <div className="status" role="status"><Spinner size="tiny" /> 급식 정보를 불러오고 있어요…</div>}
                <div className="actions">
                  <Button type="button" appearance="secondary" className="secondary" onClick={() => setStep(1)}>이전</Button>
                  <Button type="submit" appearance="primary" disabled={loading}>급식 조회</Button>
                </div>
              </form>
            </>
          )}

          {step === 3 && (
            <>
              <div className="section-heading result-heading">
                <span className="number">03</span>
                <div><h2 id="step-3-title">중식 메뉴를 확인하세요</h2>
                  <p>{fromDate} ~ {toDate}</p></div>
                <Button type="button" appearance="secondary" className="secondary" onClick={() => {
                  setStep(2); setError("");
                }}>기간 변경</Button>
              </div>
              {meals.length === 0 ? (
                <div className="empty">
                  <strong>선택한 기간에 급식 정보가 없습니다.</strong>
                  <p>방학이나 휴일일 수 있어요. 다른 기간을 선택해 보세요.</p>
                </div>
              ) : (
                <div className="meal-grid">
                  {datesBetween(fromDate, toDate).map((date) =>
                    <MealCard key={date} date={date} meal={mealByDate.get(date)} />)}
                </div>
              )}
            </>
          )}
        </section>
      </main>
      <footer>NEIS 학교 급식 정보를 바탕으로 제공합니다.</footer>
    </>
    </FluentProvider>
  );
}
