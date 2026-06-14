"use client";

// Zona de subida drag & drop con estados animados:
// idle → hover → subiendo (progreso real) → procesando (polling de ingesta) →
// listo / error. El estado de ingesta refleja status pending|parsing|chunking|
// embedding|indexing|ready|failed haciendo polling a GET /documents/{id}.
// Restyle "clean premium": tarjeta blanca con borde dashed hairline, halo azul.

import { AnimatePresence, motion } from "framer-motion";
import { Loader2, UploadCloud } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { ApiError, uploadDocument } from "@/lib/api";
import { useToast } from "@/components/ui/Toaster";
import { IngestionTracker } from "@/components/upload/IngestionTracker";
import { cn } from "@/lib/utils";

type Phase = "idle" | "uploading";

export function Dropzone({
  onReady,
}: {
  onReady: (docId: string) => void;
}) {
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const [docId, setDocId] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>("");

  const reset = useCallback(() => {
    setPhase("idle");
    setProgress(0);
    setDocId(null);
    setFileName("");
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const startUpload = useCallback(
    async (file: File) => {
      if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
        toast.error("Solo se admiten archivos PDF.");
        return;
      }
      setFileName(file.name);
      setPhase("uploading");
      setProgress(0);
      try {
        const res = await uploadDocument(file, setProgress);
        setDocId(res.doc_id);
      } catch (e) {
        const msg =
          e instanceof ApiError
            ? e.status === 409
              ? "Este documento ya fue subido."
              : e.message
            : "No se pudo subir el archivo.";
        toast.error(msg);
        reset();
      }
    },
    [reset, toast],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) startUpload(file);
    },
    [startUpload],
  );

  // Vista de procesamiento/ingesta (sustituye la zona mientras hay un docId).
  if (docId) {
    return (
      <IngestionTracker
        docId={docId}
        fileName={fileName}
        onReady={() => onReady(docId)}
        onRetry={reset}
        onOpen={() => onReady(docId)}
      />
    );
  }

  const busy = phase === "uploading";

  return (
    <motion.div
      layout
      onDragOver={(e) => {
        e.preventDefault();
        if (!busy) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={busy ? undefined : onDrop}
      onClick={() => !busy && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (!busy && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label="Subir un PDF: arrastra o haz clic para elegir un archivo"
      aria-busy={busy}
      animate={{ scale: dragging ? 1.01 : 1 }}
      transition={{ type: "spring", stiffness: 320, damping: 26 }}
      className={cn(
        "relative grid min-h-[300px] place-items-center overflow-hidden rounded-[1.75rem] border border-dashed bg-white p-12 text-center transition-[border-color,box-shadow] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2",
        busy ? "cursor-default" : "cursor-pointer",
        dragging
          ? "border-primary shadow-[var(--shadow-lift)]"
          : "border-border-strong shadow-soft hover:border-ink/25 hover:shadow-card",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) startUpload(file);
        }}
      />

      {/* Halo de acento al arrastrar. */}
      <AnimatePresence>
        {dragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(420px 220px at 50% 40%, rgba(10,132,255,0.12), transparent 70%)",
            }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {busy ? (
          <motion.div
            key="uploading"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="w-full max-w-sm"
          >
            <IconBadge>
              <Loader2 className="h-7 w-7 animate-spin" aria-hidden />
            </IconBadge>
            <h3 className="mt-5 text-lg font-semibold tracking-tight text-ink">Subiendo…</h3>
            <p className="mt-1 truncate text-sm text-ink-muted">{fileName}</p>
            <ProgressBar value={progress} />
            <p className="mt-2 text-[0.8rem] font-medium tabular-nums text-ink-muted">
              {Math.round(progress * 100)}%
            </p>
          </motion.div>
        ) : (
          <motion.div
            key="idle"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            <motion.div
              animate={{ y: dragging ? -4 : 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <IconBadge>
                <UploadCloud className="h-8 w-8" strokeWidth={1.8} aria-hidden />
              </IconBadge>
            </motion.div>
            <h3 className="mt-5 text-xl font-semibold tracking-tight text-ink">
              {dragging ? "Suelta para subir" : "Arrastra tu PDF aquí"}
            </h3>
            <p className="mt-2 text-[0.95rem] text-ink-soft">
              o <span className="font-semibold text-primary">haz clic</span> para elegir un archivo
            </p>
            <p className="mt-4 text-[0.8rem] text-ink-muted">
              Solo PDF con texto · se procesa de forma privada
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function IconBadge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-grid h-16 w-16 place-items-center rounded-[1.25rem] bg-primary-soft text-primary">
      {children}
    </span>
  );
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div
      className="mt-5 h-2 overflow-hidden rounded-full bg-surface-muted"
      role="progressbar"
      aria-valuenow={Math.round(value * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <motion.div
        animate={{ width: `${Math.max(2, value * 100)}%` }}
        transition={{ type: "spring", stiffness: 200, damping: 30 }}
        className="h-full rounded-full bg-gradient-to-r from-primary to-cyan"
      />
    </div>
  );
}
