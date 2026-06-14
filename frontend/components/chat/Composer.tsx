"use client";

// Caja de entrada con textarea autoajustable (autosize) y envío con Enter
// (Shift+Enter inserta salto de línea). Botón de envío con press-scale.
// Restyle "clean premium": contenedor blanco con borde hairline, botón pill azul.

import { motion } from "framer-motion";
import { ArrowUp } from "lucide-react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export function Composer({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  // Autosize del textarea.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(160, el.scrollHeight)}px`;
  }, [value]);

  const submit = useCallback(() => {
    const t = value.trim();
    if (!t || disabled) return;
    onSend(t);
    setValue("");
  }, [value, disabled, onSend]);

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div className="flex items-end gap-2 rounded-[1.125rem] border border-border bg-white py-2 pl-3.5 pr-2 shadow-soft transition-colors focus-within:border-border-strong">
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={1}
        placeholder="Escribe tu pregunta…"
        aria-label="Escribe tu pregunta"
        disabled={disabled}
        className="max-h-40 flex-1 resize-none border-none bg-transparent py-1.5 text-[0.9rem] leading-relaxed text-ink outline-none placeholder:text-ink-muted"
      />
      <motion.button
        type="button"
        onClick={submit}
        disabled={!canSend}
        aria-label="Enviar pregunta"
        whileHover={canSend ? { y: -1 } : undefined}
        whileTap={canSend ? { scale: 0.92 } : undefined}
        transition={{ type: "spring", stiffness: 500, damping: 28 }}
        className={cn(
          "grid h-[38px] w-[38px] shrink-0 place-items-center rounded-full transition-colors",
          canSend
            ? "cursor-pointer bg-primary text-white shadow-[0_8px_22px_-6px_rgba(10,132,255,0.5)]"
            : "cursor-not-allowed bg-surface-muted text-ink-muted",
        )}
      >
        <ArrowUp className="h-[18px] w-[18px]" strokeWidth={2.4} aria-hidden />
      </motion.button>
    </div>
  );
}
