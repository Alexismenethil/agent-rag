"use client";

// Barra fina de progreso de scroll, fija en el borde superior.
// Lee el scroll del contenedor indicado (la app usa scroll interno, no window).

import { useEffect, useState, type RefObject } from "react";

export function ScrollProgress({
  scrollRef,
}: {
  // Contenedor con scroll a observar. Si no se pasa, usa el documento.
  scrollRef?: RefObject<HTMLElement>;
}) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let raf = 0;
    const target: HTMLElement | null = scrollRef?.current ?? null;

    const update = () => {
      if (target) {
        const max = target.scrollHeight - target.clientHeight;
        setProgress(max > 0 ? Math.min(target.scrollTop / max, 1) : 0);
      } else {
        const doc = document.documentElement;
        const max = doc.scrollHeight - doc.clientHeight;
        setProgress(max > 0 ? Math.min(doc.scrollTop / max, 1) : 0);
      }
    };

    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(update);
    };

    update();
    const node: HTMLElement | Window = target ?? window;
    node.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);

    return () => {
      cancelAnimationFrame(raf);
      node.removeEventListener("scroll", onScroll as EventListener);
      window.removeEventListener("resize", onScroll);
    };
  }, [scrollRef]);

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-[2.5px]">
      <div className="scroll-progress h-full w-full" style={{ transform: `scaleX(${progress})` }} />
    </div>
  );
}
