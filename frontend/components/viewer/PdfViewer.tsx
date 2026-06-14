"use client";

// Visor de PDF (react-pdf / pdf.js). Carga el documento desde
// GET /documents/{id}/file enviando el header X-User-Id. Navega suavemente a una
// página y resalta el snippet de una cita dentro de la capa de texto (ADR-003:
// localización por texto, no por coordenadas).
//
// IMPORTANTE: la lógica de carga, resaltado por texto (customTextRenderer /
// fragmentMatchesSnippet), registro de páginas y navegación se conserva intacta.
// Solo cambia la presentación.

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Document, Page } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import { PDF_OPTIONS } from "@/lib/pdf";
import { DEV_USER_ID, documentFileUrl } from "@/lib/api";
import { fragmentMatchesSnippet } from "@/lib/textMatch";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";

export interface HighlightTarget {
  // Identificador para reaccionar a clics repetidos en la misma cita.
  key: number;
  pagina: number;
  snippet: string;
}

interface PdfViewerProps {
  docId: string;
  highlight: HighlightTarget | null;
  onPageCount?: (n: number) => void;
}

// Cabeceras para que pdf.js incluya la identidad al pedir el PDF.
const FILE_HEADERS = { "X-User-Id": DEV_USER_ID };

export function PdfViewer({ docId, highlight, onPageCount }: PdfViewerProps) {
  const [numPages, setNumPages] = useState(0);
  const [width, setWidth] = useState(680);
  const [error, setError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const fileUrl = useMemo(() => documentFileUrl(docId), [docId]);
  const file = useMemo(
    () => ({ url: fileUrl, httpHeaders: FILE_HEADERS }),
    [fileUrl],
  );

  // Ajusta el ancho del render al contenedor (responsive, nítido).
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 680;
      setWidth(Math.min(900, Math.max(320, Math.floor(w - 8))));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const onLoad = useCallback(
    ({ numPages: n }: { numPages: number }) => {
      setNumPages(n);
      onPageCount?.(n);
    },
    [onPageCount],
  );

  // Navega a la página objetivo cuando cambia la cita seleccionada.
  useEffect(() => {
    if (!highlight) return;
    const node = pageRefs.current.get(highlight.pagina);
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [highlight]);

  const registerPage = useCallback((pagina: number, node: HTMLDivElement | null) => {
    if (node) pageRefs.current.set(pagina, node);
    else pageRefs.current.delete(pagina);
  }, []);

  if (error) {
    return (
      <div className="grid h-full place-items-center p-8 text-center">
        <div>
          <p className="mb-1.5 font-semibold text-ink">No se pudo cargar el PDF</p>
          <p className="mb-4 text-[0.85rem] text-ink-muted">
            Verifica que el documento esté disponible en el servidor.
          </p>
          <Button variant="ghost" size="sm" onClick={() => setError(false)}>
            Reintentar
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex h-full flex-col items-center gap-6 overflow-y-auto bg-surface-muted px-6 pb-16 pt-5"
    >
      <Document
        file={file}
        onLoadSuccess={onLoad}
        onLoadError={() => setError(true)}
        options={PDF_OPTIONS}
        loading={<ViewerSkeleton width={width} />}
        error={<span />}
      >
        {Array.from({ length: numPages }, (_, i) => {
          const pagina = i + 1;
          const isTarget = highlight?.pagina === pagina;
          return (
            <PageBlock
              key={pagina}
              pagina={pagina}
              width={width}
              snippet={isTarget ? highlight!.snippet : null}
              highlightKey={isTarget ? highlight!.key : null}
              register={registerPage}
            />
          );
        })}
      </Document>
    </div>
  );
}

function PageBlock({
  pagina,
  width,
  snippet,
  highlightKey,
  register,
}: {
  pagina: number;
  width: number;
  snippet: string | null;
  highlightKey: number | null;
  register: (pagina: number, node: HTMLDivElement | null) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    register(pagina, ref.current);
    return () => register(pagina, null);
  }, [pagina, register]);

  // Renderizador de texto personalizado: marca con clase los spans que forman
  // parte del snippet citado (resaltado por texto, robusto a coordenadas).
  const textRenderer = useCallback(
    (item: { str: string }) => {
      if (!snippet) return item.str;
      if (fragmentMatchesSnippet(item.str, snippet)) {
        return `<mark class="cita-highlight">${escapeHtml(item.str)}</mark>`;
      }
      return item.str;
    },
    [snippet],
  );

  return (
    <div ref={ref} className="relative scroll-mt-4" data-pagina={pagina}>
      {/* Etiqueta de número de página. */}
      <span className="absolute -left-0.5 top-2 -translate-x-full px-1.5 py-0.5 text-[0.69rem] font-semibold tabular-nums text-ink-muted">
        {pagina}
      </span>

      <Page
        pageNumber={pagina}
        width={width}
        renderTextLayer
        renderAnnotationLayer={false}
        customTextRenderer={snippet ? textRenderer : undefined}
        loading={<Skeleton width={width} height={width * 1.3} radius={14} />}
      />

      {/* Destello de acento sobre la página objetivo. */}
      <AnimatePresence>
        {highlightKey !== null && (
          <motion.div
            key={highlightKey}
            initial={{ opacity: 0.9 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 1.1, ease: "easeOut" }}
            aria-hidden
            className="pointer-events-none absolute inset-0 rounded-[14px]"
            style={{
              boxShadow: "0 0 0 3px #0a84ff, 0 0 32px rgba(10,132,255,0.35)",
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function ViewerSkeleton({ width }: { width: number }) {
  return (
    <div className="flex flex-col gap-6">
      {[0, 1].map((i) => (
        <Skeleton key={i} width={width} height={width * 1.3} radius={14} />
      ))}
    </div>
  );
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
