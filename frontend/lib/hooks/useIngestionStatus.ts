"use client";

// Hace polling a GET /documents/{id} hasta que el estado sea 'ready' o 'failed'.
// Devuelve el último estado conocido y un progreso suavizado para la UI.

import { useEffect, useRef, useState } from "react";
import { getDocumentStatus } from "@/lib/api";
import type { DocumentStatus, DocumentStatusResponse } from "@/lib/types";
import { STATUS_PROGRESS } from "@/lib/types";

const TERMINAL: DocumentStatus[] = ["ready", "failed"];
const POLL_MS = 1200;

export interface IngestionState {
  status: DocumentStatus | null;
  progress: number; // [0, 1]
  numPaginas: number | null;
  errorMsg: string | null;
  isTerminal: boolean;
}

export function useIngestionStatus(docId: string | null): IngestionState {
  const [state, setState] = useState<IngestionState>({
    status: null,
    progress: 0,
    numPaginas: null,
    errorMsg: null,
    isTerminal: false,
  });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!docId) return;
    let cancelled = false;

    async function poll() {
      if (cancelled || !docId) return;
      try {
        const data: DocumentStatusResponse = await getDocumentStatus(docId);
        if (cancelled) return;
        const isTerminal = TERMINAL.includes(data.status);
        // Si el backend no envía progreso fiable, usamos el aproximado por etapa.
        const progress =
          data.progress && data.progress > 0
            ? data.progress
            : (STATUS_PROGRESS[data.status] ?? 0);
        setState({
          status: data.status,
          progress,
          numPaginas: data.num_paginas,
          errorMsg: data.error_msg,
          isTerminal,
        });
        if (!isTerminal) {
          timer.current = setTimeout(poll, POLL_MS);
        }
      } catch {
        // Reintenta con margen; la ingesta puede tardar en aparecer.
        if (!cancelled) timer.current = setTimeout(poll, POLL_MS * 2);
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [docId]);

  return state;
}
