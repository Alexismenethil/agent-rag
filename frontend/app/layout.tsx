import type { Metadata, Viewport } from "next";
import type { CSSProperties } from "react";
import "./globals.css";
import { ToastProvider } from "@/components/ui/Toaster";

export const metadata: Metadata = {
  title: "Agente RAG — explica-PDF con cita exacta",
  description:
    "Sube un PDF y pregunta: el agente responde citando la página y el fragmento exacto.",
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  width: "device-width",
  initialScale: 1,
};

// Stack de tipografía Inter + fuentes del sistema (offline-safe; no depende de
// next/font/google para no romper el build sin red).
const FONT_STACK =
  '"Inter", "SF Pro Display", "SF Pro Text", "Helvetica Neue", "Segoe UI Variable Display", system-ui, sans-serif';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body
        className="font-sans antialiased"
        style={{ "--font-clean": FONT_STACK } as CSSProperties}
      >
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
