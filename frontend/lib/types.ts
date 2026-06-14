// Tipos del contrato de la API (ADR-004). Campos de dominio en español, igual
// que el backend. Mantener sincronizado con backend/app/schemas.py.

export type Modo = "estricto" | "ampliado";

export type DocumentStatus =
  | "pending"
  | "parsing"
  | "chunking"
  | "embedding"
  | "indexing"
  | "ready"
  | "failed";

export type Role = "user" | "assistant" | "system";

// --- Salud ---
export type Health = { status: "ok" | "degraded"; db: "ok" | "down" };

// --- Documentos ---
export interface DocumentUploadResponse {
  doc_id: string;
  status: DocumentStatus;
}

export interface DocumentListItem {
  doc_id: string;
  titulo: string | null;
  filename: string;
  status: DocumentStatus;
  num_paginas: number | null;
  created_at: string;
}

export interface DocumentStatusResponse {
  doc_id: string;
  status: DocumentStatus;
  progress: number; // [0, 1]
  num_paginas: number | null;
  error_msg: string | null;
}

// --- Consulta / citas ---
export interface Cita {
  marcador: number;
  chunk_id: string | null;
  doc_id: string;
  pagina: number;
  seccion: string | null;
  offset_inicio: number;
  offset_fin: number;
  snippet: string;
  texto_afirmacion: string;
}

export interface ConsultaRequest {
  doc_id: string;
  pregunta: string;
  modo?: Modo;
  session_id?: string | null;
  top_k?: number;
}

export interface ConsultaResponse {
  message_id: string;
  session_id: string;
  respuesta: string;
  citas: Cita[];
  informacion_ampliada: string | null;
  groundedness: number;
  modelo: string;
}

// --- Sesiones / historial ---
export interface SessionListItem {
  session_id: string;
  doc_id: string | null;
  titulo: string | null;
  modo_default: Modo;
  created_at: string;
  updated_at: string;
}

export interface MessageItem {
  message_id: string;
  role: Role;
  contenido: string;
  modo: Modo | null;
  groundedness: number | null;
  modelo: string | null;
  citas: Cita[];
  created_at: string;
}

export interface SessionDetailResponse {
  session_id: string;
  doc_id: string | null;
  titulo: string | null;
  modo_default: Modo;
  created_at: string;
  updated_at: string;
  mensajes: MessageItem[];
}

// Etiquetas amables para cada estado de ingesta (en español).
export const STATUS_LABEL: Record<DocumentStatus, string> = {
  pending: "En cola",
  parsing: "Leyendo el PDF",
  chunking: "Dividiendo en fragmentos",
  embedding: "Generando embeddings",
  indexing: "Construyendo el índice",
  ready: "Listo",
  failed: "Error",
};

// Progreso aproximado por etapa, para la barra mientras llega `progress` real.
export const STATUS_PROGRESS: Record<DocumentStatus, number> = {
  pending: 0.05,
  parsing: 0.25,
  chunking: 0.45,
  embedding: 0.65,
  indexing: 0.85,
  ready: 1,
  failed: 1,
};
