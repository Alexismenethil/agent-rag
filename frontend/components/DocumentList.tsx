"use client";

// Lista de documentos del usuario con estado, skeletons y estado vacío.
// Reveal escalonado de la lista. Restyle "clean premium".

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, FileText } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { listDocuments } from "@/lib/api";
import type { DocumentListItem, DocumentStatus } from "@/lib/types";
import { STATUS_LABEL } from "@/lib/types";
import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";

export function DocumentList({
  selectedId,
  refreshKey,
  onSelect,
}: {
  selectedId: string | null;
  refreshKey: number; // cambiar para forzar recarga tras subir
  onSelect: (docId: string) => void;
}) {
  const [docs, setDocs] = useState<DocumentListItem[] | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await listDocuments();
      setDocs(data);
    } catch {
      setDocs([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  if (docs === null) {
    return (
      <div className="flex flex-col gap-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex flex-col gap-1.5 px-3 py-2.5">
            <Skeleton width="70%" height={13} />
            <Skeleton width="40%" height={10} />
          </div>
        ))}
      </div>
    );
  }

  if (docs.length === 0) {
    return (
      <p className="px-1 py-2 text-[0.8rem] leading-relaxed text-ink-muted">
        Aún no hay documentos. Sube un PDF para empezar.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-1">
      <AnimatePresence initial={false}>
        {docs.map((doc, i) => {
          const selected = doc.doc_id === selectedId;
          const ready = doc.status === "ready";
          return (
            <motion.li
              key={doc.doc_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.04, 0.3) }}
            >
              <button
                onClick={() => ready && onSelect(doc.doc_id)}
                disabled={!ready}
                aria-current={selected}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-2xl px-3 py-2.5 text-left transition-colors duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]",
                  ready ? "cursor-pointer" : "cursor-default",
                  selected ? "bg-primary-soft" : "hover:bg-surface-muted",
                )}
              >
                <DocGlyph status={doc.status} />
                <span className="min-w-0 flex-1">
                  <span
                    className={cn(
                      "block truncate text-[0.84rem]",
                      selected
                        ? "font-semibold text-primary-dark"
                        : "font-medium text-ink",
                    )}
                  >
                    {doc.titulo || doc.filename}
                  </span>
                  <span className="text-[0.72rem] text-ink-muted">
                    {ready
                      ? doc.num_paginas
                        ? `${doc.num_paginas} págs.`
                        : "Listo"
                      : STATUS_LABEL[doc.status]}
                  </span>
                </span>
              </button>
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ul>
  );
}

function DocGlyph({ status }: { status: DocumentStatus }) {
  const failed = status === "failed";
  const ready = status === "ready";
  return (
    <span
      className={cn(
        "grid h-8 w-8 shrink-0 place-items-center rounded-xl",
        failed
          ? "bg-down/10 text-down"
          : ready
            ? "bg-primary-soft text-primary"
            : "bg-surface-muted text-ink-muted",
      )}
    >
      {failed ? (
        <AlertTriangle className="h-[15px] w-[15px]" aria-hidden />
      ) : (
        <FileText className="h-[15px] w-[15px]" strokeWidth={1.8} aria-hidden />
      )}
    </span>
  );
}
