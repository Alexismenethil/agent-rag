"use client";

// Página principal. Dos modos: (1) bienvenida con subida + lista de documentos;
// (2) vista de trabajo (visor + chat) cuando hay un documento seleccionado.

import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, FileText, Sparkles } from "lucide-react";
import { useCallback, useState } from "react";
import { TopBar } from "@/components/TopBar";
import { Dropzone } from "@/components/upload/Dropzone";
import { DocumentList } from "@/components/DocumentList";
import { Workspace } from "@/components/Workspace";
import { Reveal } from "@/components/clean/Reveal";
import { Button } from "@/components/ui/Button";

export default function Home() {
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleReady = useCallback((docId: string) => {
    setRefreshKey((k) => k + 1);
    setActiveDocId(docId);
  }, []);

  const handleSelect = useCallback((docId: string) => {
    setActiveDocId(docId);
  }, []);

  const backToHome = useCallback(() => {
    setActiveDocId(null);
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="flex h-[100dvh] flex-col">
      <TopBar
        right={
          activeDocId ? (
            <Button variant="subtle" size="sm" onClick={backToHome}>
              <ChevronLeft className="h-[15px] w-[15px]" aria-hidden />
              Documentos
            </Button>
          ) : undefined
        }
      />

      <main className="relative min-h-0 flex-1">
        <AnimatePresence mode="wait">
          {activeDocId ? (
            <motion.div
              key="workspace"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="h-full"
            >
              <Workspace docId={activeDocId} onClose={backToHome} />
            </motion.div>
          ) : (
            <motion.div
              key="landing"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ type: "spring", stiffness: 280, damping: 30 }}
              className="bg-hero h-full overflow-y-auto"
            >
              <Landing onReady={handleReady} onSelect={handleSelect} refreshKey={refreshKey} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

function Landing({
  onReady,
  onSelect,
  refreshKey,
}: {
  onReady: (docId: string) => void;
  onSelect: (docId: string) => void;
  refreshKey: number;
}) {
  return (
    <div className="mx-auto max-w-5xl px-6 pb-20 pt-[clamp(28px,6vw,72px)]">
      {/* Hero. */}
      <Reveal className="mb-12 text-center">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-white/80 px-3.5 py-1.5 text-[0.8rem] font-semibold text-primary shadow-soft backdrop-blur">
          <Sparkles className="h-[14px] w-[14px]" aria-hidden />
          Respuestas con cita exacta
        </span>
        <h1 className="font-display mx-auto mt-6 max-w-3xl text-balance text-[clamp(32px,5.4vw,52px)] font-semibold text-ink">
          Pregúntale a tu PDF.{" "}
          <span className="text-gradient">Te responde con la cita exacta.</span>
        </h1>
        <p className="text-pretty mx-auto mt-5 max-w-xl text-[clamp(15px,2.2vw,18px)] leading-8 text-ink-soft">
          Sube un documento y obtén respuestas fundamentadas: cada afirmación enlaza a su página y
          fragmento literal, resaltado en el visor.
        </p>
      </Reveal>

      {/* Subida + documentos. */}
      <div className="grid grid-cols-1 items-start gap-5 md:grid-cols-[minmax(0,1fr)_300px]">
        <Reveal variant="scale">
          <Dropzone onReady={onReady} />
        </Reveal>

        <Reveal delay={90}>
          <aside className="rounded-[1.5rem] border border-border bg-white p-5 shadow-soft">
            <div className="mb-3 flex items-center gap-2 px-1">
              <FileText className="h-4 w-4 text-ink-muted" aria-hidden />
              <span className="text-[0.72rem] font-bold uppercase tracking-[0.06em] text-ink-muted">
                Tus documentos
              </span>
            </div>
            <DocumentList selectedId={null} refreshKey={refreshKey} onSelect={onSelect} />
          </aside>
        </Reveal>
      </div>
    </div>
  );
}
