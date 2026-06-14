// Cliente HTTP mínimo hacia el backend FastAPI.
// En V1+ los tipos se generan desde el OpenAPI (lib/api/types.gen.ts) con `make openapi`.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Health = { status: "ok" | "degraded"; db: "ok" | "down" };

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
