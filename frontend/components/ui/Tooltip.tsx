"use client";

// Tooltip ligero con animación, accesible (aria-describedby). Aparece al hover/focus.
// Restyle "clean premium": tarjeta blanca, borde hairline, sombra suave.

import { AnimatePresence, motion } from "framer-motion";
import { useId, useState } from "react";

export function Tooltip({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span aria-describedby={open ? id : undefined} className="inline-flex">
        {children}
      </span>
      <AnimatePresence>
        {open && (
          <motion.span
            role="tooltip"
            id={id}
            initial={{ opacity: 0, y: 4, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 2, scale: 0.98 }}
            transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
            className="pointer-events-none absolute bottom-[calc(100%+8px)] left-1/2 z-50 -translate-x-1/2 whitespace-nowrap rounded-xl border border-border bg-white px-2.5 py-1.5 text-[0.78rem] font-medium text-ink shadow-[var(--shadow-card)]"
          >
            {label}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
