import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agente RAG — explica-PDF con cita exacta",
  description: "Proyecto antecedente para dominar el ecosistema RAG.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
