"use client";

// Sistema de toasts (avisos) con animación. Provee un contexto `useToast`.
// Restyle "clean premium": tarjeta glass blanca, icono lucide por tipo.
// La API (toast / error / success) se conserva sin cambios.

import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

type ToastKind = "error" | "success" | "info";

interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastApi {
  toast: (message: string, kind?: ToastKind) => void;
  error: (message: string) => void;
  success: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

let counter = 0;

const ICONS: Record<ToastKind, typeof Info> = {
  error: AlertCircle,
  success: CheckCircle2,
  info: Info,
};

const ICON_COLOR: Record<ToastKind, string> = {
  error: "text-down",
  success: "text-ok",
  info: "text-primary",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message: string, kind: ToastKind = "info") => {
      const id = ++counter;
      setToasts((prev) => [...prev, { id, kind, message }]);
      setTimeout(() => remove(id), 4800);
    },
    [remove],
  );

  const api = useMemo<ToastApi>(
    () => ({
      toast: push,
      error: (m: string) => push(m, "error"),
      success: (m: string) => push(m, "success"),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="pointer-events-none fixed inset-x-0 bottom-6 z-[1000] flex flex-col items-center gap-2.5"
      >
        <AnimatePresence>
          {toasts.map((t) => {
            const Icon = ICONS[t.kind];
            return (
              <motion.div
                key={t.id}
                role={t.kind === "error" ? "alert" : "status"}
                initial={{ opacity: 0, y: 24, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 12, scale: 0.96 }}
                transition={{ type: "spring", stiffness: 420, damping: 32 }}
                onClick={() => remove(t.id)}
                className="glass pointer-events-auto flex max-w-md cursor-pointer items-center gap-2.5 rounded-2xl border border-border/70 px-4 py-3 text-sm font-medium text-ink shadow-[var(--shadow-lift)]"
              >
                <Icon className={`h-[18px] w-[18px] shrink-0 ${ICON_COLOR[t.kind]}`} aria-hidden />
                <span>{t.message}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast debe usarse dentro de <ToastProvider>");
  return ctx;
}
