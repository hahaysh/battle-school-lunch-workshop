import { FormEvent, useEffect, useMemo, useState } from "react";
import { Button, Card, Checkbox, MessageBar, MessageBarBody, Spinner } from "@fluentui/react-components";
import { ApiError, AnalysisResult, getRandomSchools, School, streamAnalysis } from "./lib/api";

function inputDate(date: Date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function monthRange(offset: number) {
  const now = new Date();
  const first = new Date(now.getFullYear(), now.getMonth() + offset, 1);
  const last = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0);
  const maximum = offset === 0 && last > now ? now : last;
  return { min: inputDate(first), max: inputDate(maximum) };
}

function schoolKey(school: School) {
  return `${school.officeCode}-${school.schoolCode}`;
}

export default function AnalysisPage() {
  const [schools, setSchools] = useState<School[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [month, setMonth] = useState<0 | -1>(0);
  const [date, setDate] = useState(inputDate(new Date()));
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const range = useMemo(() => monthRange(month), [month]);

  useEffect(() => {
    setLoading(true);
    setError("");
    void getRandomSchools()
      .then((response) => {
        if (response.items.length !== 10) {
          throw new Error("분석에 사용할 학교 10개를 준비하지 못했습니다.");
        }
        setSchools(response.items);
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "학교를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const nextDate = new Date(`${date}T00:00:00`);
    const min = new Date(`${range.min}T00:00:00`);
    const max = new Date(`${range.max}T00:00:00`);
    if (nextDate < min || nextDate > max || Number.isNaN(nextDate.getTime())) setDate(range.max);
  }, [date, range]);

  useEffect(() => {
    if (selected.length === 2 && schools.length === 10) {
      const names = schools.filter((school) => selected.includes(schoolKey(school))).map((school) => school.schoolName);
      setPrompt(`${names.join("과 ")}의 ${date} 중식을 루브릭에 따라 비교 분석해 주세요. 근거가 있는 내용만 사용하고, 양쪽의 개선안을 제시해 주세요.`);
    }
  }, [date, schools, selected]);

  function toggleSchool(school: School) {
    const key = schoolKey(school);
    setSelected((current) => current.includes(key)
      ? current.filter((item) => item !== key)
      : current.length < 2 ? [...current, key] : current);
    setResult(null);
    setError("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (selected.length !== 2) {
      setError("정확히 2개의 학교를 선택해 주세요.");
      return;
    }
    const picked = schools.filter((school) => selected.includes(schoolKey(school)));
    setLoading(true);
    setError("");
    setResult(null);
    setStatus("분석을 시작하고 있습니다…");
    try {
      await streamAnalysis({ schools: picked, date, prompt }, (event) => {
        if (event.message) setStatus(event.message);
        if (event.result) setResult(event.result);
      });
      setStatus("");
    } catch (reason) {
      setError(reason instanceof ApiError || reason instanceof Error ? reason.message : "분석에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  const picked = schools.filter((school) => selected.includes(schoolKey(school)));
  return (
    <section className="panel analysis-panel" aria-labelledby="analysis-title">
      <div className="section-heading">
        <span className="number">AI</span>
        <div><h2 id="analysis-title">급식 분석</h2><p>무작위 학교 10개 중 2개의 같은 날 중식을 비교합니다.</p></div>
      </div>
      {error && <div role="alert" className="alert"><MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar></div>}
      {loading && !status && <div className="status" role="status"><Spinner size="tiny" /> 학교 후보를 준비하고 있어요…</div>}
      {schools.length === 10 && (
        <form onSubmit={submit}>
          <fieldset className="school-picker">
            <legend>학교 선택 <small>({selected.length}/2)</small></legend>
            <div className="analysis-school-grid">
              {schools.map((school) => (
                <Card key={schoolKey(school)} className="analysis-school">
                  <Checkbox
                    label={<><strong>{school.schoolName}</strong><small>{school.schoolKind} · {school.officeName}</small></>}
                    checked={selected.includes(schoolKey(school))}
                    disabled={!selected.includes(schoolKey(school)) && selected.length >= 2}
                    onChange={() => toggleSchool(school)}
                  />
                </Card>
              ))}
            </div>
          </fieldset>
          <div className="analysis-date">
            <label>분석 월
              <select aria-label="분석 월" value={month} onChange={(event) => setMonth(Number(event.target.value) as 0 | -1)}>
                <option value={0}>이번 달</option><option value={-1}>직전 달</option>
              </select>
            </label>
            <label>분석 날짜
              <input aria-label="분석 날짜" type="date" min={range.min} max={range.max} value={date}
                onChange={(event) => setDate(event.target.value)} />
            </label>
          </div>
          {picked.length === 2 && <label className="prompt-field">분석 프롬프트
            <textarea aria-label="분석 프롬프트" rows={5} value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          </label>}
          <div className="actions">
            <Button type="submit" appearance="primary" disabled={loading || selected.length !== 2 || !prompt.trim()}>분석 전송</Button>
          </div>
        </form>
      )}
      {status && <div className="status" role="status"><Spinner size="tiny" /> {status}</div>}
      {result && <AnalysisResultView result={result} />}
    </section>
  );
}

function AnalysisResultView({ result }: { result: AnalysisResult }) {
  return (
    <section className="analysis-result" aria-label="분석 결과">
      <h3>분석 결과</h3>
      <p className="winner">{result.winner}</p>
      <p>{result.summary}</p>
      <div className="analysis-results-grid">
        {result.schools.map((school) => (
          <Card key={school.school.schoolCode} className="analysis-score-card">
            <h4>{school.school.schoolName}</h4><strong>{school.totalScore.toFixed(1)}점</strong>
            <ul>{school.areas.map((area) => <li key={area.key}><b>{area.name} {area.score}/5</b><span>{area.evidence.join(" ")}</span></li>)}</ul>
          </Card>
        ))}
      </div>
      {!result.qualityGate.passed && <MessageBar intent="warning"><MessageBarBody>{result.qualityGate.warnings.join(" ")}</MessageBarBody></MessageBar>}
    </section>
  );
}
