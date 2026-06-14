"use client";

// Botón "clean premium" (recipe del skill): pill, sheen sweep en variantes
// rellenas, hover-lift (-translate-y-0.5) y active-scale (0.97), foco visible.
// Componente presentacional nuevo, separado del Button de framer-motion existente.

import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "warm" | "navy" | "outline" | "ghost" | "white";
type Size = "sm" | "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-primary text-white shadow-[0_8px_22px_-6px_rgba(10,132,255,0.5)] hover:bg-primary-dark hover:shadow-[0_14px_32px_-8px_rgba(10,132,255,0.55)]",
  warm:
    "bg-warm text-white shadow-[0_8px_22px_-6px_rgba(255,149,0,0.5)] hover:bg-warm-dark hover:shadow-[0_14px_32px_-8px_rgba(255,149,0,0.55)]",
  navy: "bg-[#0d1b35] text-white shadow-[0_10px_26px_-8px_rgba(13,27,53,0.55)] hover:bg-[#16264a]",
  outline:
    "border border-border-strong bg-white/80 text-ink backdrop-blur hover:border-ink/20 hover:bg-white",
  ghost: "text-ink-soft hover:bg-ink/[0.05] hover:text-ink",
  white: "bg-white text-ink shadow-[0_12px_30px_-10px_rgba(0,0,0,0.4)] hover:bg-white/90",
};

const SIZES: Record<Size, string> = {
  sm: "h-9 gap-1.5 px-4 text-sm",
  md: "h-11 gap-2 px-5 text-[0.95rem]",
  lg: "h-[3.25rem] gap-2.5 px-7 text-[1.02rem]",
};

const base =
  "group relative isolate inline-flex items-center justify-center overflow-hidden rounded-full font-semibold tracking-[-0.01em] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap select-none";

const FILLED: ReadonlySet<Variant> = new Set(["primary", "warm", "navy"]);

interface CommonProps {
  variant?: Variant;
  size?: Size;
  className?: string;
  children: ReactNode;
}

export function CleanButton({
  variant = "primary",
  size = "md",
  className,
  type = "button",
  children,
  ...props
}: CommonProps & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type={type} className={cn(base, VARIANTS[variant], SIZES[size], className)} {...props}>
      {FILLED.has(variant) && <span aria-hidden className="sheen" />}
      {children}
    </button>
  );
}

export function CleanButtonLink({
  variant = "primary",
  size = "md",
  className,
  href,
  external,
  children,
}: CommonProps & { href: string; external?: boolean }) {
  const cls = cn(base, VARIANTS[variant], SIZES[size], className);
  const inner = (
    <>
      {FILLED.has(variant) && <span aria-hidden className="sheen" />}
      {children}
    </>
  );

  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={cls}>
        {inner}
      </a>
    );
  }

  return (
    <Link href={href} className={cls}>
      {inner}
    </Link>
  );
}
