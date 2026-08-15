import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import App from "./App";
import { server } from "./test/server";

function analysisSchools() {
  return Array.from({ length: 10 }, (_, index) => ({
    officeCode: "J10",
    officeName: "경기도교육청",
    schoolCode: `${index + 1}`,
    schoolName: `분석학교${index + 1}`,
    schoolKind: "고등학교",
    address: "경기도",
  }));
}

test("학교 검색부터 급식 결과까지 조회한다", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.type(screen.getByLabelText("학교 이름"), "배틀");
  await user.click(screen.getByRole("button", { name: "학교 검색" }));
  await user.click(await screen.findByRole("button", { name: /배틀초등학교/ }));

  await user.clear(screen.getByLabelText("시작일"));
  await user.type(screen.getByLabelText("시작일"), "2026-08-17");
  await user.clear(screen.getByLabelText("종료일"));
  await user.type(screen.getByLabelText("종료일"), "2026-08-17");
  await user.click(screen.getByRole("button", { name: "급식 조회" }));

  expect(await screen.findByText("기장밥")).toBeInTheDocument();
  expect(screen.getByText("812.3 Kcal")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "기간 변경" })).toBeInTheDocument();
});

test("빈 검색 결과와 잘못된 날짜 범위를 안내한다", async () => {
  server.use(http.get("/api/schools", () => HttpResponse.json({ items: [], totalCount: 0 })));
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("학교 이름"), "없는학교");
  await user.click(screen.getByRole("button", { name: "학교 검색" }));
  expect(await screen.findByText(/검색 결과가 없습니다/)).toBeInTheDocument();
});

test("API 오류 메시지와 재시도 수단을 표시한다", async () => {
  server.use(http.get("/api/schools", () =>
    HttpResponse.json({ error: { code: "UPSTREAM_ERROR", message: "학교를 불러오지 못했습니다." } }, { status: 502 })));
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("학교 이름"), "배틀");
  await user.click(screen.getByRole("button", { name: "학교 검색" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("학교를 불러오지 못했습니다.");
  expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
});

test("급식 조회 오류를 재시도하고 잘못된 학교는 검색 단계로 되돌린다", async () => {
  let mealAttempts = 0;
  server.use(http.get("/api/meals", () => {
    mealAttempts += 1;
    if (mealAttempts === 1) {
      return HttpResponse.json(
        { error: { code: "UPSTREAM_ERROR", message: "급식 정보를 불러오지 못했습니다." } },
        { status: 502 },
      );
    }
    return HttpResponse.json({
      items: [{
        date: "2026-08-17",
        mealType: "중식",
        dishes: ["재시도 성공"],
        calorie: "700 Kcal",
        origin: "",
      }],
    });
  }));

  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("학교 이름"), "배틀");
  await user.click(screen.getByRole("button", { name: "학교 검색" }));
  await user.click(await screen.findByRole("button", { name: /배틀초등학교/ }));
  await user.click(screen.getByRole("button", { name: "급식 조회" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("급식 정보를 불러오지 못했습니다.");
  await user.click(screen.getByRole("button", { name: "다시 시도" }));
  expect(await screen.findByText("재시도 성공")).toBeInTheDocument();

  server.use(http.get("/api/meals", () => HttpResponse.json(
    { error: { code: "INVALID_SCHOOL", message: "학교 정보를 확인할 수 없습니다." } },
    { status: 400 },
  )));
  await user.click(screen.getByRole("button", { name: "기간 변경" }));
  await user.click(screen.getByRole("button", { name: "급식 조회" }));
  expect(await screen.findByRole("heading", { name: "학교를 찾아보세요" })).toBeInTheDocument();
  expect(screen.getByText("학교 정보를 다시 선택해 주세요.")).toBeInTheDocument();
});

test("급식 분석 페이지에서 두 학교를 선택하고 수정한 프롬프트를 전송한다", async () => {
  server.use(
    http.get("/api/schools/random", () => HttpResponse.json({ items: analysisSchools(), totalCount: 10 })),
    http.post("/agent/agui", async ({ request }) => {
      const body = await request.json() as { prompt: string };
      expect(body.prompt).toBe("수정한 분석 요청");
      const result = {
        schools: analysisSchools().slice(0, 2).map((school) => ({
          school: { schoolCode: school.schoolCode, schoolName: school.schoolName },
          totalScore: 80,
          areas: [
            { key: "nutrition", name: "영양 균형", score: 4, weight: 35, evidence: ["식품군 근거"] },
            { key: "health", name: "건강성", score: 4, weight: 25, evidence: ["부담 신호 근거"] },
            { key: "quality", name: "식재료·메뉴 품질", score: 3, weight: 20, evidence: ["메뉴 근거"] },
            { key: "evidence", name: "데이터 충분성·근거 신뢰도", score: 5, weight: 20, evidence: ["필드 근거"] },
          ],
        })),
        winner: "동점",
        summary: "동점입니다.",
        qualityGate: { passed: true, warnings: [] },
      };
      const payload = [
        `data: ${JSON.stringify({ type: "RUN_STARTED", message: "시작" })}\n\n`,
        `data: ${JSON.stringify({ type: "RUN_FINISHED", result })}\n\n`,
      ].join("");
      return new HttpResponse(payload, { headers: { "Content-Type": "text/event-stream" } });
    }),
  );
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: "급식 분석" }));
  expect(await screen.findByText("분석학교1")).toBeInTheDocument();
  await user.click(screen.getAllByLabelText(/분석학교1/)[0]);
  await user.click(screen.getByLabelText(/^분석학교2/));
  const prompt = screen.getByLabelText("분석 프롬프트");
  await user.clear(prompt);
  await user.type(prompt, "수정한 분석 요청");
  await user.click(screen.getByRole("button", { name: "분석 전송" }));
  expect(await screen.findByText("동점")).toBeInTheDocument();
  expect(screen.getAllByText("80.0점")).toHaveLength(2);
});
