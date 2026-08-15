import { expect, test } from "@playwright/test";

const school = {
  officeCode: "J10",
  officeName: "경기도교육청",
  schoolCode: "7530575",
  schoolName: "배틀초등학교",
  schoolKind: "초등학교",
  address: "경기도 성남시",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/schools?**", (route) =>
    route.fulfill({ json: { items: [school], totalCount: 1 } }));
  await page.route("**/api/meals?**", (route) =>
    route.fulfill({
      json: {
        items: [{
          date: "2026-08-17",
          mealType: "중식",
          dishes: ["기장밥", "미역국"],
          calorie: "812.3 Kcal",
          origin: "쌀 : 국내산",
        }],
      },
    }));
});

test("학교 검색, 기간 선택, 급식 확인과 이전 단계 이동", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("학교 이름").fill("배틀");
  await page.getByRole("button", { name: "학교 검색" }).click();
  await page.getByRole("button", { name: /배틀초등학교/ }).click();
  await page.getByLabel("시작일").fill("2026-08-17");
  await page.getByLabel("종료일").fill("2026-08-17");
  await page.locator("form button[type=submit]").click();
  await expect(page.getByText("기장밥")).toBeVisible();
  await page.getByRole("button", { name: "기간 변경" }).click();
  await expect(page.getByRole("heading", { name: "조회 기간을 선택하세요" })).toBeVisible();
});

test("31일 초과 범위를 브라우저에서 차단한다", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("학교 이름").fill("배틀");
  await page.getByRole("button", { name: "학교 검색" }).click();
  await page.getByRole("button", { name: /배틀초등학교/ }).click();
  await page.getByLabel("시작일").fill("2026-08-01");
  await page.getByLabel("종료일").fill("2026-09-01");
  await page.locator("form button[type=submit]").click();
  await expect(page.getByRole("alert")).toContainText("최대 31일");
});

test("급식 분석에서 정확히 두 학교를 선택하고 결과를 확인한다", async ({ page }) => {
  const schools = Array.from({ length: 10 }, (_, index) => ({
    ...school,
    schoolCode: `${index + 1}`,
    schoolName: `분석학교${index + 1}`,
  }));
  await page.route("**/api/schools/random**", (route) =>
    route.fulfill({ json: { items: schools, totalCount: 10 } }));
  await page.route("**/agent/agui", async (route) => {
    const result = {
      schools: schools.slice(0, 2).map((item) => ({
        school: { schoolCode: item.schoolCode, schoolName: item.schoolName },
        totalScore: 80,
        areas: [
          { key: "nutrition", name: "영양 균형", score: 4, weight: 35, evidence: ["근거"] },
          { key: "health", name: "건강성", score: 4, weight: 25, evidence: ["근거"] },
          { key: "quality", name: "식재료·메뉴 품질", score: 3, weight: 20, evidence: ["근거"] },
          { key: "evidence", name: "데이터 충분성·근거 신뢰도", score: 5, weight: 20, evidence: ["근거"] },
        ],
      })),
      winner: "동점",
      summary: "동점입니다.",
      qualityGate: { passed: true, warnings: [] },
    };
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: `data: ${JSON.stringify({ type: "RUN_FINISHED", result })}\n\n`,
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "급식 분석" }).click();
  await expect(page.getByText("분석학교1", { exact: true })).toBeVisible();
  await page.getByLabel(/분석학교1/).first().check();
  await page.getByLabel(/^분석학교2/).check();
  await expect(page.getByLabel("분석 프롬프트")).toBeVisible();
  await page.getByRole("button", { name: "분석 전송" }).click();
  await expect(page.getByText("동점", { exact: true })).toBeVisible();
});
