"use client";

// Chip de cita [n]. Clicable: navega el visor a la página y resalta el snippet.
// Cuando está activo (cita seleccionada) usa el color de acento.
// Restyle "clean premium": pill azul suave, activo azul sólido.

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function CitationChip({
  marcador,
  active,
  disabled,
  asStatic,
  onClick,
}: {
  marcador: number;
  active: boolean;
  disabled?: boolean;
  asStatic?: boolean; // sin press-scale (para la lista de fuentes)
  onClick: () => void;
}) {
  const inner = (
    <>
      <span className="mr-px text-[10px] opacity-70">[</span>
      {marcador}
      <span className="ml-px text-[10px] opacity-70">]</span>
    </>
  );

  const className = cn(
    "inline-flex h-[19px] min-w-[22px] items-center justify-center rounded-md px-1.5 align-baseline text-[0.72rem] font-bold leading-none transition-colors duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]",
    active ? "bg-primary text-white" : "bg-primary-soft text-primary",
    disabled && "opacity-40",
    !asStatic && "mx-px",
  );

  if (asStatic) {
    return (
      <span className={cn(className, "shrink-0")} aria-hidden>
        {inner}
      </span>
    );
  }

  return (
    <motion.button
      type="button"
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      aria-label={`Ir a la cita ${marcador}`}
      whileHover={disabled ? undefined : { y: -1 }}
      whileTap={disabled ? undefined : { scale: 0.9 }}
      transition={{ type: "spring", stiffness: 500, damping: 28 }}
      className={cn(className, disabled ? "cursor-default" : "cursor-pointer")}
    >
      {inner}
    </motion.button>
  );
}
