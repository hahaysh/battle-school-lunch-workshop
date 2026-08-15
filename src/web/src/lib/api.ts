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

export async function getRandomSchools() {
  return getJson<{ items: School[]; totalCount: number }>("/api/schools/random", {});
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

export interface AnalysisArea {
  key: string;
  name: string;
  score: number;
  weight: number;
  evidence: string[];
}

export interface SchoolAnalysis {
  school: Pick<School, "schoolCode" | "schoolName">;
  totalScore: number;
  areas: AnalysisArea[];
}

export interface AnalysisResult {
  schools: SchoolAnalysis[];
  winner: string;
  summary: string;
  qualityGate: { passed: boolean; warnings: string[] };
}

export interface AnalysisProgress {
  type: "RUN_STARTED" | "STEP_STARTED" | "STEP_FINISHED" | "RUN_FINISHED" | "RUN_ERROR";
  name?: string;
  message?: string;
  result?: AnalysisResult;
}

export async function streamAnalysis(
  input: {
    schools: Pick<School, "officeCode" | "schoolCode" | "schoolName">[];
    date: string;
    prompt: string;
  },
  onProgress: (event: AnalysisProgress) => void,
) {
  let response: Response;
  try {
    response = await fetch("/agent/agui", {
      method: "POST",
      headers: { Accept: "text/event-stream", "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  } catch {
    throw new ApiError("분석 서버 연결을 확인한 뒤 다시 시도해 주세요.", "NETWORK_ERROR");
  }
  if (!response.ok || !response.body) {
    const body = (await response.json().catch(() => ({}))) as ErrorBody;
    throw new ApiError(body.error?.message ?? "분석을 시작하지 못했습니다.", body.error?.code);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const event of events) {
      const line = event.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;
      try {
        onProgress(JSON.parse(line.slice(5).trim()) as AnalysisProgress);
      } catch {
        // Ignore keep-alive frames and malformed provider events.
      }
    }
    if (done) break;
  }
}
