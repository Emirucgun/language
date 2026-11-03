// Tarayıcı yalnızca kendi origin'ine konuşur; Next /api/* isteklerini FastAPI'ye yönlendirir.
// Tipler FastAPI şemasından üretilir: `npm run gen:api`.
import type { components } from "./api-types";

export type Schemas = components["schemas"];
export type Me = Schemas["Me"];
export type FeedbackView = Schemas["FeedbackView"];
export type ShownError = Schemas["ShownError"];
export type WritingTask = Schemas["WritingTask"];
export type SessionView = Schemas["SessionView"];
export type ActivityView = Schemas["ActivityView"];
export type ChoiceView = Schemas["ChoiceView"];
export type AnswerResult = Schemas["AnswerResult"];

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function detailMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return status >= 500 ? "Sunucuya ulaşılamadı, biraz sonra tekrar dene." : "İstek geçersiz.";
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 204) return undefined as T;
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, detailMessage(data, res.status));
  return data as T;
}

export const api = {
  me: () => request<Me>("GET", "/api/auth/me"),
  requestLogin: (body: Schemas["LoginRequest"]) =>
    request<{ ok: boolean }>("POST", "/api/auth/request", body),
  verifyLogin: (token: string) => request<Me>("POST", "/api/auth/verify", { token }),
  logout: () => request<void>("POST", "/api/auth/logout"),
  consent: (body: Schemas["ConsentRequest"]) =>
    request<Me>("POST", "/api/onboarding/consent", body),
  goals: (body: Schemas["GoalSet"]) => request<Me>("POST", "/api/onboarding/goals", body),
  writingTask: () => request<WritingTask>("GET", "/api/practice/writing-task"),
  feedback: (body: Schemas["WritingRequest"]) =>
    request<FeedbackView>("POST", "/api/feedback", body),
  rewrite: (feedbackId: number, text: string, activityId?: number) =>
    request<Schemas["RewriteResult"]>("POST", `/api/feedback/${feedbackId}/rewrite`, {
      text,
      activity_id: activityId ?? null,
    }),
  placement: () => request<Schemas["PlacementView"]>("GET", "/api/onboarding/placement"),
  placementAnswer: (body: Schemas["PlacementAnswer"]) =>
    request<void>("POST", "/api/onboarding/placement/answer", body),
  placementComplete: () =>
    request<Schemas["PlacementResult"]>("POST", "/api/onboarding/placement/complete"),
  curriculum: () => request<Schemas["CurriculumView"]>("GET", "/api/curriculum"),
  sessionToday: () => request<SessionView>("GET", "/api/session/today"),
  answer: (activityId: number, body: Schemas["AnswerRequest"]) =>
    request<AnswerResult>("POST", `/api/activities/${activityId}/answer`, body),
  event: (body: Schemas["ClientEvent"]) => request<Schemas["Recorded"]>("POST", "/api/events", body),
};

// Onam metninin sürümü sunucudakiyle aynı olmalı (app/config.py: consent_version).
export const CONSENT_VERSION = "2026-11-v1";
