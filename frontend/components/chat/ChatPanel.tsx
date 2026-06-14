"use client";

// Panel de chat: historial de mensajes, indicador de "pensando", caja de entrada
// con autosize y selector de modo. Llama a POST /query y propaga las citas.
// Restyle "clean premium": cabecera hairline, estado vacío con sugerencias pill.

import { AnimatePresence, motion } from "framer-motion";
import { MessageSquare } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, postQuery } from "@/lib/api";
import type { Cita, Modo } from "@/lib/types";
import { useToast } from "@/components/ui/Toaster";
import { ModeSelector } from "@/components/chat/ModeSelector";
import { MessageBubble, type ChatMessage } from "@/components/chat/MessageBubble";
import { Composer } from "@/components/chat/Composer";

const SUGGESTIONS = [
  "¿De qué trata este documento?",
  "Resume las ideas principales.",
  "¿Cuál es la conclusión?",
];

export function ChatPanel({
  docId,
  onCitaSelect,
  activeCitaKey,
}: {
  docId: string;
  onCitaSelect: (cita: Cita) => void;
  activeCitaKey: number | null;
}) {
  const toast = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [modo, setModo] = useState<Modo>("estricto");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [thinking, setThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Reinicia la conversación al cambiar de documento.
  useEffect(() => {
    setMessages([]);
    setSessionId(null);
  }, [docId]);

  // Autoscroll al final cuando llegan mensajes.
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, thinking]);

  const send = useCallback(
    async (pregunta: string) => {
      const trimmed = pregunta.trim();
      if (!trimmed || thinking) return;

      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        contenido: trimmed,
        citas: [],
      };
      setMessages((prev) => [...prev, userMsg]);
      setThinking(true);

      try {
        const res = await postQuery({
          doc_id: docId,
          pregunta: trimmed,
          modo,
          session_id: sessionId,
          top_k: 8,
        });
        setSessionId(res.session_id);
        setMessages((prev) => [
          ...prev,
          {
            id: res.message_id,
            role: "assistant",
            contenido: res.respuesta,
            citas: res.citas,
            informacion_ampliada: res.informacion_ampliada,
            groundedness: res.groundedness,
            modelo: res.modelo,
          },
        ]);
      } catch (e) {
        const msg =
          e instanceof ApiError ? e.message : "No se pudo obtener la respuesta.";
        toast.error(msg);
        // Marca el último mensaje del usuario como fallido visualmente quitándolo no;
        // mejor dejamos el mensaje y mostramos toast (puede reintentar escribiendo).
      } finally {
        setThinking(false);
      }
    },
    [docId, modo, sessionId, thinking, toast],
  );

  const empty = messages.length === 0;

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Cabecera del chat. */}
      <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-3.5">
        <span className="text-[0.95rem] font-semibold tracking-tight text-ink">Conversación</span>
        <ModeSelector value={modo} onChange={setModo} />
      </div>

      {/* Historial. */}
      <div
        ref={scrollRef}
        className={cnScroll(empty)}
      >
        {empty ? (
          <EmptyState onPick={send} disabled={thinking} />
        ) : (
          messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              activeCitaKey={activeCitaKey}
              onCitaClick={onCitaSelect}
            />
          ))
        )}

        <AnimatePresence>{thinking && <ThinkingBubble />}</AnimatePresence>
      </div>

      {/* Entrada. */}
      <div className="shrink-0 px-4 pb-4 pt-3">
        <Composer onSend={send} disabled={thinking} />
      </div>
    </div>
  );
}

function cnScroll(empty: boolean) {
  return [
    "flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto",
    empty ? "p-0" : "px-[18px] py-5",
  ].join(" ");
}

function EmptyState({
  onPick,
  disabled,
}: {
  onPick: (q: string) => void;
  disabled: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-1 flex-col items-center justify-center gap-2 px-6 py-8 text-center"
    >
      <div className="mb-2 grid h-14 w-14 place-items-center rounded-[1.25rem] bg-primary-soft text-primary">
        <MessageSquare className="h-6 w-6" strokeWidth={1.8} aria-hidden />
      </div>
      <h3 className="text-[1.05rem] font-semibold tracking-tight text-ink">
        Pregunta sobre tu documento
      </h3>
      <p className="mb-2.5 max-w-xs text-[0.84rem] leading-relaxed text-ink-soft">
        Cada respuesta cita la página y el fragmento exacto. Haz clic en una cita para verla
        resaltada en el PDF.
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((s, i) => (
          <motion.button
            key={s}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 * i }}
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.97 }}
            disabled={disabled}
            onClick={() => onPick(s)}
            className="rounded-full border border-border bg-white px-3.5 py-2 text-[0.8rem] font-medium text-ink-soft shadow-soft transition-colors hover:border-border-strong hover:text-ink"
          >
            {s}
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}

function ThinkingBubble() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="flex justify-start"
    >
      <div className="flex items-center gap-1.5 rounded-[1.125rem] rounded-bl-md border border-border bg-white px-4 py-3.5 shadow-soft">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
            transition={{ repeat: Infinity, duration: 1, delay: i * 0.15 }}
            className="h-1.5 w-1.5 rounded-full bg-ink-muted"
          />
        ))}
      </div>
    </motion.div>
  );
}
