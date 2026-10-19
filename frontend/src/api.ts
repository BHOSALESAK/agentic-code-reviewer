import type { Fixture, Health, Preview } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: { message?: string } } | null;
    throw new Error(payload?.error?.message ?? "The API could not complete the request.");
  }
  return response.json() as Promise<T>;
}

export const getHealth = () => request<Health>("/api/v1/health");
export const getFixtures = () => request<Fixture[]>("/api/v1/fixtures");
export const previewPullRequest = (payload: { fixture_id?: string; reference?: string }) =>
  request<Preview>("/api/v1/pull-requests/preview", { method: "POST", body: JSON.stringify(payload) });
