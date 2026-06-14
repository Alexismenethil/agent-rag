"use client";

// Selector de modo (estricto / ampliado). En V1 'ampliado' está deshabilitado
// con tooltip "Llega en V2". Indicador deslizante animado (layoutId).
// Restyle "clean premium": segmented control con pill azul suave.

import { motion } from "framer-motion";
import { Tooltip } from "@/components/ui/Tooltip";
import type { Modo } from "@/lib/types";
import { cn } from "@/lib/utils";

const OPTIONS: { value: Modo; label: string; enabled: boolean }[] = [
  { value: "estricto", label: "Estricto", enabled: true },
  { value: "ampliado", label: "Ampliado", enabled: false },
];

export function ModeSelector({
  value,
  onChange,
}: {
  value: Modo;
  onChange: (modo: Modo) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Modo de respuesta"
      className="inline-flex gap-0.5 rounded-full border border-border bg-surface-muted p-1"
    >
      {OPTIONS.map((opt) => {
        const active = value === opt.value;
        const button = (
          <button
            key={opt.value}
            role="radio"
            aria-checked={active}
            aria-disabled={!opt.enabled}
            disabled={!opt.enabled}
            onClick={() => opt.enabled && onChange(opt.value)}
            className={cn(
              "relative z-[1] rounded-full px-4 py-1.5 text-[0.8rem] font-semibold transition-colors",
              opt.enabled ? "cursor-pointer" : "cursor-not-allowed opacity-65",
              active ? "text-ink" : opt.enabled ? "text-ink-soft" : "text-ink-muted",
            )}
          >
            {active && (
              <motion.span
                layoutId="mode-pill"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
                className="absolute inset-0 -z-[1] rounded-full bg-white shadow-soft"
              />
            )}
            {opt.label}
          </button>
        );

        return opt.enabled ? (
          button
        ) : (
          <Tooltip key={opt.value} label="Llega en V2">
            {button}
          </Tooltip>
        );
      })}
    </div>
  );
}
