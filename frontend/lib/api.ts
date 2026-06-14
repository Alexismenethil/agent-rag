// Cliente HTTP hacia el backend FastAPI.
// Identidad en MVP por header X-User-Id (usuario de desarrollo fijo).
// Contrato canónico: docs/DECISIONES.md (ADR-004); campos de dominio en español.

import type {
  ConsultaRequest,
  ConsultaResponse,
  DocumentListItem,
  DocumentStatusResponse,
  DocumentUploadResponse,
  Health,
  SessionDetailResponse,
  SessionListItem,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Usuario de desarrollo: coincide con DEV_USER_ID del .env del repo.
export const DEV_USER_ID =
  process.env.NEXT_PUBLIC_DEV_USER_ID ?? "00000000-0000-0000-0000-000000000001";

/** Error de API con código HTTP y mensaje legible en español. */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function authHeaders(extra?: HeadersInit): HeadersInit {
  return { "X-User-Id": DEV_USER_ID, ...extra };
}

async function parseError(res: Response): Promise<never> {
  let detail = `HTTP ${res.status}`;
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") detail = data.detail;
    else if (Array.isArray(data?.detail) && data.detail[0]?.msg) detail = data.detail[0].msg;
  } catch {
    /* respuesta sin cuerpo JSON */
  }
  throw new ApiError(res.status, detail);
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    ...init,
    headers: authHeaders(init?.headers),
  });
  if (!res.ok) return parseError(res);
  return res.json() as Promise<T>;
}

// --- Salud ---
export async function getHealth(): Promise<Health> {
  return getJson<Health>("/health");
}

// --- Documentos ---
export async function listDocuments(): Promise<DocumentListItem[]> {
  return getJson<DocumentListItem[]>("/documents");
}

export async function getDocumentStatus(docId: string): Promise<DocumentStatusResponse> {
  return getJson<DocumentStatusResponse>(`/documents/${docId}`);
}

/**
 * Sube un PDF con progreso de transferencia. Usamos XMLHttpRequest porque
 * `fetch` aún no expone progreso de subida de forma fiable.
 */
export function uploadDocument(
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<DocumentUploadResponse> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/documents`);
    xhr.setRequestHeader("X-User-Id", DEV_USER_ID);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(event.loaded / event.total);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as DocumentUploadResponse);
        } catch {
          reject(new ApiError(xhr.status, "Respuesta de subida ilegible"));
        }
      } else {
        let detail = `HTTP ${xhr.status}`;
        try {
          const data = JSON.parse(xhr.responseText);
          if (typeof data?.detail === "string") detail = data.detail;
        } catch {
          /* sin cuerpo */
        }
        reject(new ApiError(xhr.status, detail));
      }
    };
    xhr.onerror = () => reject(new ApiError(0, "No se pudo conectar con el servidor"));
    xhr.send(form);
  });
}

/** URL del PDF servido por el backend (para el visor). Incluye el header vía proxy del visor. */
export function documentFileUrl(docId: string): string {
  return `${API_URL}/documents/${docId}/file`;
}

// --- Consulta ---
export async function postQuery(body: ConsultaRequest): Promise<ConsultaResponse> {
  return getJson<ConsultaResponse>("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// --- Sesiones ---
export async function listSessions(): Promise<SessionListItem[]> {
  return getJson<SessionListItem[]>("/sessions");
}

export async function getSession(sessionId: string): Promise<SessionDetailResponse> {
  return getJson<SessionDetailResponse>(`/sessions/${sessionId}`);
}
