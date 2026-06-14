"use client";

// Muestra el avance de la ingesta con etapas animadas, haciendo polling al
// backend. Maneja con amabilidad el caso 'failed' con error_msg='needs_ocr'.
// Restyle "clean premium": tarjeta blanca, lista de etapas con check lucide.

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Check, CheckCircle2, Loader2 } from "lucide-react";
import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { useIngestionStatus } from "@/lib/hooks/useIngestionStatus";
import type { DocumentStatus } from "@/lib/types";
import { STATUS_LABEL } from "@/lib/types";
import { cn } from "@/lib/utils";

const STAGES: DocumentStatus[] = [
  "pending",
  "parsing",
  "chunking",
  "embedding",
  "indexing",
  "ready",
];

export function IngestionTracker({
  docId,
  fileName,
  onReady,
  onRetry,
  onOpen,
}: {
  docId: string;
  fileName: string;
  onReady: () => void;
  onRetry: () => void;
  onOpen: () => void;
}) {
  const { status, progress, numPaginas, errorMsg, isTerminal } =
    useIngestionStatus(docId);

  // Avisa al padre cuando termina con éxito (puede autonavegar al visor).
  useEffect(() => {
    if (status === "ready") {
      const t = setTimeout(onReady, 650);
      return () => clearTimeout(t);
    }
  }, [status, onReady]);

  const failed = status === "failed";
  const ready = status === "ready";
  const needsOcr = failed && (errorMsg ?? "").toLowerCase().includes("needs_ocr");
  const currentIndex = status ? STAGES.indexOf(status) : 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex min-h-[300px] flex-col justify-center rounded-[1.75rem] border border-border bg-white p-8 shadow-soft"
      aria-live="polite"
    >
      <div className="mb-6 flex items-center gap-3.5">
        <StatusGlyph failed={failed} ready={ready} />
        <div className="min-w-0">
          <h3 className="text-[1.05rem] font-semibold tracking-tight text-ink">
            {failed
              ? needsOcr
                ? "Necesita OCR"
                : "No se pudo procesar"
              : ready
                ? "Documento listo"
                : "Procesando documento…"}
          </h3>
          <p className="truncate text-sm text-ink-muted">
            {fileName}
            {numPaginas ? ` · ${numPaginas} págs.` : ""}
          </p>
        </div>
      </div>

      {failed ? (
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl bg-surface-muted px-4 py-3.5 text-[0.85rem] leading-relaxed text-ink-soft"
          >
            {needsOcr ? (
              <>
                Este PDF parece <strong className="text-ink">escaneado</strong> (sin capa de texto).
                En esta versión solo trabajamos con PDFs que ya contienen texto seleccionable. El
                reconocimiento óptico (OCR) llega en una versión posterior.
              </>
            ) : (
              <>Ocurrió un problema durante la ingesta. {errorMsg ? `(${errorMsg})` : ""}</>
            )}
          </motion.div>
        </AnimatePresence>
      ) : (
        <>
          {/* Barra de progreso global. */}
          <div
            className="h-2 overflow-hidden rounded-full bg-surface-muted"
            role="progressbar"
            aria-valuenow={Math.round(progress * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <motion.div
              animate={{ width: `${Math.max(4, progress * 100)}%` }}
              transition={{ type: "spring", stiffness: 120, damping: 24 }}
              className={cn(
                "h-full rounded-full",
                ready ? "bg-ok" : "bg-gradient-to-r from-primary to-cyan",
              )}
            />
          </div>

          {/* Lista de etapas. */}
          <ul className="mt-5 flex flex-col gap-2.5">
            {STAGES.slice(0, 5).map((stage, i) => {
              const done = currentIndex > i || ready;
              const active = status === stage;
              return (
                <li
                  key={stage}
                  className={cn(
                    "flex items-center gap-3 text-[0.85rem]",
                    done || active ? "text-ink" : "text-ink-muted",
                    active ? "font-semibold" : "font-medium",
                  )}
                >
                  <StageDot done={done} active={active} />
                  {STATUS_LABEL[stage]}
                </li>
              );
            })}
          </ul>
        </>
      )}

      <div className="mt-6 flex gap-2.5">
        {ready && <Button onClick={onOpen}>Abrir documento</Button>}
        {(failed || isTerminal) && (
          <Button variant="ghost" onClick={onRetry}>
            Subir otro PDF
          </Button>
        )}
      </div>
    </motion.div>
  );
}

function StageDot({ done, active }: { done: boolean; active: boolean }) {
  return (
    <span
      className={cn(
        "grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full",
        done ? "bg-primary" : active ? "border-[1.5px] border-primary bg-primary-soft" : "bg-surface-muted",
      )}
    >
      {done ? (
        <Check className="h-2.5 w-2.5 text-white" strokeWidth={3.5} aria-hidden />
      ) : active ? (
        <motion.span
          animate={{ scale: [1, 0.6, 1] }}
          transition={{ repeat: Infinity, duration: 1.1, ease: "easeInOut" }}
          className="h-[7px] w-[7px] rounded-full bg-primary"
        />
      ) : null}
    </span>
  );
}

function StatusGlyph({ failed, ready }: { failed: boolean; ready: boolean }) {
  return (
    <span
      className={cn(
        "grid h-12 w-12 shrink-0 place-items-center rounded-[1rem]",
        failed
          ? "bg-down/10 text-down"
          : ready
            ? "bg-ok/15 text-ok"
            : "bg-primary-soft text-primary",
      )}
    >
      {failed ? (
        <AlertTriangle className="h-[22px] w-[22px]" aria-hidden />
      ) : ready ? (
        <CheckCircle2 className="h-[22px] w-[22px]" aria-hidden />
      ) : (
        <Loader2 className="h-[22px] w-[22px] animate-spin" aria-hidden />
      )}
    </span>
  );
}
