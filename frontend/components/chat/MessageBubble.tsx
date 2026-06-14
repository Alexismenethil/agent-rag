"use client";

// Burbuja de mensaje. Para el asistente, transforma los marcadores [n] del texto
// en chips clicables que navegan el visor a la cita. Renderiza también la lista
// de fuentes y (si llega) la información ampliada etiquetada aparte.
// Restyle "clean premium": usuario azul, asistente blanco con borde hairline.

import { motion } from "framer-motion";
import { Fragment, useMemo } from "react";
import type { Cita, Role } from "@/lib/types";
import { truncate } from "@/lib/textMatch";
import { CitationChip } from "@/components/chat/CitationChip";
import { cn } from "@/lib/utils";

export interface ChatMessage {
  id: string;
  role: Role;
  contenido: string;
  citas: Cita[];
  informacion_ampliada?: string | null;
  groundedness?: number | null;
  modelo?: string | null;
  pending?: boolean;
}

export function MessageBubble({
  message,
  activeCitaKey,
  onCitaClick,
}: {
  message: ChatMessage;
  activeCitaKey: number | null;
  onCitaClick: (cita: Cita) => void;
}) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 320, damping: 30 }}
      className={cn("flex", isUser ? "justify-end" : "justify-start")}
    >
      <div
        className={cn(
          "rounded-[1.125rem] px-4 text-[0.9rem] leading-relaxed shadow-soft",
          isUser
            ? "max-w-[82%] rounded-br-md bg-primary py-2.5 text-white"
            : "max-w-[94%] rounded-bl-md border border-border bg-white py-3 text-ink",
        )}
      >
        {isUser ? (
          <span className="whitespace-pre-wrap">{message.contenido}</span>
        ) : (
          <AssistantBody
            message={message}
            activeCitaKey={activeCitaKey}
            onCitaClick={onCitaClick}
          />
        )}
      </div>
    </motion.div>
  );
}

function AssistantBody({
  message,
  activeCitaKey,
  onCitaClick,
}: {
  message: ChatMessage;
  activeCitaKey: number | null;
  onCitaClick: (cita: Cita) => void;
}) {
  const byMarcador = useMemo(() => {
    const map = new Map<number, Cita>();
    for (const c of message.citas) map.set(c.marcador, c);
    return map;
  }, [message.citas]);

  // Divide el texto por marcadores [n] e intercala chips inline.
  const parts = useMemo(() => renderWithMarkers(message.contenido), [message.contenido]);

  return (
    <div>
      <p className="m-0 whitespace-pre-wrap">
        {parts.map((part, i) =>
          part.type === "text" ? (
            <Fragment key={i}>{part.value}</Fragment>
          ) : (
            <CitationChip
              key={i}
              marcador={part.marcador}
              active={activeCitaKey === part.marcador}
              disabled={!byMarcador.has(part.marcador)}
              onClick={() => {
                const cita = byMarcador.get(part.marcador);
                if (cita) onCitaClick(cita);
              }}
            />
          ),
        )}
      </p>

      {message.informacion_ampliada ? (
        <div className="mt-3 rounded-xl border-l-[3px] border-warn bg-warm-soft px-3.5 py-2.5 text-[0.82rem] text-ink-soft">
          <div className="mb-1 text-[0.68rem] font-bold uppercase tracking-[0.04em] text-warm-dark">
            Fuera del documento
          </div>
          {message.informacion_ampliada}
        </div>
      ) : null}

      {/* Fuentes (lista de citas). */}
      {message.citas.length > 0 && (
        <div className="mt-3 flex flex-col gap-1.5">
          <div className="text-[0.68rem] font-bold uppercase tracking-[0.04em] text-ink-muted">
            Fuentes
          </div>
          {message.citas.map((c) => (
            <button
              key={c.marcador}
              onClick={() => onCitaClick(c)}
              className="flex items-start gap-2.5 rounded-lg px-1 py-1 text-left text-[0.78rem] leading-snug text-ink-soft transition-colors hover:bg-surface-muted"
            >
              <CitationChip
                marcador={c.marcador}
                active={activeCitaKey === c.marcador}
                onClick={() => onCitaClick(c)}
                asStatic
              />
              <span>
                <strong className="text-ink">
                  pág. {c.pagina}
                  {c.seccion ? ` · ${c.seccion}` : ""}
                </strong>
                <br />
                <span className="text-ink-muted">{truncate(c.snippet, 120)}</span>
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Pie con metadatos del modelo / fidelidad. */}
      {(message.modelo || typeof message.groundedness === "number") && (
        <div className="mt-2.5 flex items-center gap-3 text-[0.68rem] text-ink-muted">
          {typeof message.groundedness === "number" && (
            <span title="Fidelidad de la respuesta a las fuentes">
              fidelidad {Math.round(message.groundedness * 100)}%
            </span>
          )}
          {message.modelo && <span>· {message.modelo}</span>}
        </div>
      )}
    </div>
  );
}

type Part =
  | { type: "text"; value: string }
  | { type: "cita"; marcador: number };

// Divide el texto en fragmentos y marcadores [n] (uno o varios juntos).
function renderWithMarkers(text: string): Part[] {
  const parts: Part[] = [];
  const re = /\[(\d+)\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ type: "text", value: text.slice(last, m.index) });
    parts.push({ type: "cita", marcador: Number(m[1]) });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ type: "text", value: text.slice(last) });
  return parts;
}
