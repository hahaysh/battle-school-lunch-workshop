import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import App from "./App";
import { server } from "./test/server";

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
