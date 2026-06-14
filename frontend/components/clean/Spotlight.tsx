"use client";

// Spotlight que sigue el cursor (solo puntero de ratón). Resplandor azul suave.

import { useRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Spotlight({
  children,
  className,
  glow = "rgba(10,132,255,0.12)",
}: {
  children: ReactNode;
  className?: string;
  glow?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  function onMove(e: React.PointerEvent<HTMLDivElement>) {
    if (e.pointerType !== "mouse") return;
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${e.clientX - r.left}px`);
    el.style.setProperty("--my", `${e.clientY - r.top}px`);
  }

  return (
    <div
      ref={ref}
      onPointerMove={onMove}
      style={{ "--glow": glow } as React.CSSProperties}
      className={cn("group relative", className)}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        style={{
          background:
            "radial-gradient(16rem 16rem at var(--mx,50%) var(--my,50%), var(--glow), transparent 62%)",
        }}
      />
      <div className="relative z-10 flex h-full flex-col">{children}</div>
    </div>
  );
}
