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
  await page.getByRole("button", { name: "급식 조회" }).click();
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
  await page.getByRole("button", { name: "급식 조회" }).click();
  await expect(page.getByRole("alert")).toContainText("최대 31일");
});

