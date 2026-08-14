import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const server = setupServer(
  http.get("/api/schools", () =>
    HttpResponse.json({
      items: [{
        officeCode: "J10",
        officeName: "경기도교육청",
        schoolCode: "7530575",
        schoolName: "배틀초등학교",
        schoolKind: "초등학교",
        address: "경기도 성남시",
      }],
      totalCount: 1,
    })),
  http.get("/api/meals", () =>
    HttpResponse.json({
      items: [{
        date: "2026-08-17",
        mealType: "중식",
        dishes: ["기장밥", "미역국"],
        calorie: "812.3 Kcal",
        origin: "쌀 : 국내산",
      }],
    })),
);

