"use client";

// Header "glass premium": transparente arriba, se condensa en una isla glass
// con esquinas pill al hacer scroll (curva cubic-bezier(0.16,1,0.3,1)).
// Conserva el sondeo de salud del backend en vivo y el slot `right`.

import Link from "next/link";
import { FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

export function TopBar({ right }: { right?: React.ReactNode }) {
  const [db, setDb] = useState<"ok" | "down" | "loading">("loading");
  const [scrolled, setScrolled] = useState(false);

  // Sondeo de salud del backend (lógica conservada tal cual).
  useEffect(() => {
    let alive = true;
    const check = () =>
      getHealth()
        .then((h) => alive && setDb(h.db === "ok" ? "ok" : "down"))
        .catch(() => alive && setDb("down"));
    check();
    const id = setInterval(check, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  // Condensa el header al hacer scroll. La app desplaza dentro de un contenedor
  // anidado (<main>), así que escuchamos en fase de captura para detectarlo.
  useEffect(() => {
    const onScroll = (e: Event) => {
      const t = e.target;
      const top =
        t instanceof HTMLElement
          ? t.scrollTop
          : (document.scrollingElement?.scrollTop ?? window.scrollY);
      setScrolled(top > 16);
    };
    window.addEventListener("scroll", onScroll, { capture: true, passive: true });
    return () => window.removeEventListener("scroll", onScroll, { capture: true } as EventListenerOptions);
  }, []);

  return (
    <header className="sticky top-0 z-40">
      <div
        className={cn(
          "transition-[padding] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
          scrolled ? "px-3 pt-2.5 sm:px-5" : "px-0 pt-0",
        )}
      >
        <div
          className={cn(
            "relative mx-auto flex items-center justify-between transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
            scrolled
              ? "glass h-[54px] max-w-5xl rounded-full border border-border/70 px-3.5 shadow-[0_2px_10px_rgba(20,24,31,0.05),0_18px_44px_-18px_rgba(20,24,31,0.18)] sm:px-4"
              : "h-[64px] max-w-7xl border border-transparent bg-white/60 px-5 backdrop-blur-md lg:px-8",
          )}
        >
          <Link
            href="/"
            aria-label="Agente RAG inicio"
            className="inline-flex items-center gap-2.5 rounded-xl transition-transform duration-300 hover:scale-[1.02] active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
          >
            <span
              className={cn(
                "flex items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-cyan text-white shadow-[0_12px_28px_-12px_rgba(10,132,255,0.7)] transition-transform duration-500",
                scrolled ? "h-8 w-8" : "h-9 w-9",
              )}
            >
              <FileText className="h-[18px] w-[18px]" strokeWidth={1.9} aria-hidden />
            </span>
            <span className="flex items-baseline gap-1.5">
              <span className="text-[1.05rem] font-extrabold tracking-tight text-ink">
                Agente RAG
              </span>
              <span className="hidden text-[0.8rem] font-medium text-ink-muted sm:inline">
                explica-PDF
              </span>
            </span>
          </Link>

          <div className="flex items-center gap-3 sm:gap-4">
            {right}
            <span
              title={`Backend ${db}`}
              className="inline-flex items-center gap-2 text-[0.78rem] font-medium text-ink-muted"
            >
              <span
                className={cn(
                  "h-2 w-2 rounded-full",
                  db === "ok" && "bg-ok shadow-[0_0_0_3px_rgba(52,199,89,0.18)]",
                  db === "down" && "bg-down",
                  db === "loading" && "bg-warn",
                )}
              />
              <span className="hidden sm:inline">Backend</span>
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
