export interface School {
  officeCode: string;
  officeName: string;
  schoolCode: string;
  schoolName: string;
  schoolKind: string;
  address: string;
}

export interface Meal {
  date: string;
  mealType: string;
  dishes: string[];
  calorie: string;
  origin: string;
}

interface ErrorBody {
  error?: { code?: string; message?: string };
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code = "UNKNOWN_ERROR",
  ) {
    super(message);
  }
}

async function getJson<T>(path: string, params: Record<string, string>): Promise<T> {
  const query = new URLSearchParams(params);
  let response: Response;
  try {
    response = await fetch(`${path}?${query.toString()}`, {
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new ApiError("네트워크 연결을 확인한 뒤 다시 시도해 주세요.", "NETWORK_ERROR");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ErrorBody;
    throw new ApiError(
      body.error?.message ?? "정보를 불러오지 못했습니다.",
      body.error?.code,
    );
  }
  return response.json() as Promise<T>;
}

export async function searchSchools(name: string) {
  return getJson<{ items: School[]; totalCount: number }>("/api/schools", {
    name,
    page: "1",
    size: "50",
  });
}

export async function getMeals(
  school: Pick<School, "officeCode" | "schoolCode">,
  fromDate: string,
  toDate: string,
) {
  return getJson<{ items: Meal[] }>("/api/meals", {
    officeCode: school.officeCode,
    schoolCode: school.schoolCode,
    fromDate,
    toDate,
  });
}
