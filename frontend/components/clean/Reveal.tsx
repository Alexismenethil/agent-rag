"use client";

// Reveal-on-scroll (una sola vez). Bajo prefers-reduced-motion el CSS muestra
// todo de inmediato (ver globals.css), por lo que nunca oculta contenido.

import { useEffect, useRef, useState, type ElementType, type ReactNode } from "react";

type RevealProps = {
  children: ReactNode;
  as?: ElementType;
  delay?: number;
  variant?: "up" | "scale";
  className?: string;
};

export function Reveal({ children, as, delay = 0, variant = "up", className }: RevealProps) {
  const Tag = (as ?? "div") as ElementType;
  const ref = useRef<HTMLElement | null>(null);
  const [show, setShow] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (typeof IntersectionObserver === "undefined") {
      setShow(true);
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShow(true);
            io.disconnect();
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -10% 0px" },
    );

    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <Tag
      ref={ref}
      data-reveal={variant}
      data-show={show ? "true" : "false"}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
      className={className}
    >
      {children}
    </Tag>
  );
}
