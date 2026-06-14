"use client";

// Vista de trabajo: visor de PDF a la izquierda y chat a la derecha. En móvil se
// apila (pestañas Documento / Chat). El clic en una cita navega y resalta el PDF.
// Restyle "clean premium": tarjetas blancas con borde hairline y sombra suave.

import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import type { Cita } from "@/lib/types";
import { ChatPanel } from "@/components/chat/ChatPanel";
import type { HighlightTarget } from "@/components/viewer/PdfViewer";
import { cn } from "@/lib/utils";

// El visor toca `window`/pdf.js: solo en cliente.
const PdfViewer = dynamic(
  () => import("@/components/viewer/PdfViewer").then((m) => m.PdfViewer),
  {
    ssr: false,
    loading: () => (
      <div className="grid h-full place-items-center">
        <span className="text-sm text-ink-muted">Cargando visor…</span>
      </div>
    ),
  },
);

type MobileTab = "doc" | "chat";

export function Workspace({
  docId,
  onClose,
}: {
  docId: string;
  onClose?: () => void;
}) {
  const [highlight, setHighlight] = useState<HighlightTarget | null>(null);
  const [activeCitaKey, setActiveCitaKey] = useState<number | null>(null);
  const [tab, setTab] = useState<MobileTab>("doc");
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 860px)");
    const apply = () => setIsMobile(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const onCitaSelect = useCallback(
    (cita: Cita) => {
      setActiveCitaKey(cita.marcador);
      setHighlight({ key: Date.now(), pagina: cita.pagina, snippet: cita.snippet });
      if (isMobile) setTab("doc");
    },
    [isMobile],
  );

  const viewer = (
    <PanelCard>
      <PdfViewer docId={docId} highlight={highlight} />
    </PanelCard>
  );

  const chat = (
    <PanelCard>
      <ChatPanel docId={docId} onCitaSelect={onCitaSelect} activeCitaKey={activeCitaKey} />
    </PanelCard>
  );

  if (isMobile) {
    return (
      <div className="flex h-full flex-col gap-3 bg-surface-muted p-3 pb-4">
        <div
          role="tablist"
          aria-label="Cambiar entre documento y chat"
          className="inline-flex self-center gap-0.5 rounded-2xl border border-border bg-white p-1 shadow-soft"
        >
          {(["doc", "chat"] as MobileTab[]).map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={cn(
                "relative z-[1] rounded-xl px-6 py-1.5 text-sm font-semibold transition-colors",
                tab === t ? "text-ink" : "text-ink-muted",
              )}
            >
              {tab === t && (
                <motion.span
                  layoutId="mobile-tab"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  className="absolute inset-0 -z-[1] rounded-xl bg-primary-soft"
                />
              )}
              {t === "doc" ? "Documento" : "Chat"}
            </button>
          ))}
        </div>
        <div className="min-h-0 flex-1">{tab === "doc" ? viewer : chat}</div>
      </div>
    );
  }

  return (
    <div className="grid h-full grid-cols-[minmax(0,1.25fr)_minmax(380px,1fr)] gap-4 bg-surface-muted p-4 pb-[18px]">
      <motion.div
        initial={{ opacity: 0, x: -12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ type: "spring", stiffness: 280, damping: 30 }}
        className="min-w-0"
      >
        {viewer}
      </motion.div>
      <motion.div
        initial={{ opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ type: "spring", stiffness: 280, damping: 30, delay: 0.05 }}
        className="min-w-0"
      >
        {chat}
      </motion.div>
    </div>
  );
}

function PanelCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-[1.5rem] border border-border bg-white shadow-card">
      {children}
    </div>
  );
}
