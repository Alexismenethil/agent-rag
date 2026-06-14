"use client";

// Botón de la app con el lenguaje "clean premium": pill, hover-lift,
// active-scale y sheen sweep en la variante rellena. Conserva la API previa
// (variants primary / ghost / subtle, sizes sm / md y todas las props de motion)
// para no romper a sus consumidores (page, IngestionTracker, PdfViewer).

import { motion, type HTMLMotionProps } from "framer-motion";
import { forwardRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "ghost" | "subtle";
type Size = "sm" | "md";

interface ButtonProps extends Omit<HTMLMotionProps<"button">, "ref" | "children"> {
  variant?: Variant;
  size?: Size;
  children?: ReactNode;
}

const base =
  "group relative isolate inline-flex items-center justify-center gap-2 overflow-hidden rounded-full font-semibold tracking-[-0.01em] whitespace-nowrap transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2";

const SIZES: Record<Size, string> = {
  sm: "h-9 px-4 text-[0.875rem]",
  md: "h-11 px-5 text-[0.95rem]",
};

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-primary text-white shadow-[0_8px_22px_-6px_rgba(10,132,255,0.5)] hover:bg-primary-dark hover:shadow-[0_14px_32px_-8px_rgba(10,132,255,0.55)]",
  ghost:
    "border border-border-strong bg-white/70 text-ink backdrop-blur hover:border-ink/20 hover:bg-white",
  subtle: "bg-surface-muted text-ink hover:bg-border",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", className, children, disabled, ...props },
  ref,
) {
  return (
    <motion.button
      ref={ref}
      disabled={disabled}
      whileHover={disabled ? undefined : { y: -2 }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      className={cn(base, SIZES[size], VARIANTS[variant], disabled && "pointer-events-none opacity-50", className)}
      {...props}
    >
      {variant === "primary" && <span aria-hidden className="sheen" />}
      {children}
    </motion.button>
  );
});
