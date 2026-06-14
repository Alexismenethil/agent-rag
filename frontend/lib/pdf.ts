"use client";

// Configuración del worker de pdf.js para react-pdf (v9 → pdfjs-dist v4).
// Importar este módulo (con efecto secundario) antes de usar <Document/>.
//
// El worker se sirve como asset estático desde /public para evitar problemas de
// bundling. El script copia el .mjs (ver follow_ups: paso "copiar worker"):
//   cp node_modules/pdfjs-dist/build/pdf.worker.min.mjs public/pdf.worker.min.mjs
// Alternativa CDN documentada abajo si no se quiere copiar el asset.

import { pdfjs } from "react-pdf";

// react-pdf re-exporta la versión de pdfjs-dist que usa internamente.
// Usamos esa misma versión para el worker (debe coincidir exactamente).
const PDFJS_VERSION = pdfjs.version;

// Worker servido localmente desde /public (preferido: 100% offline).
const LOCAL_WORKER = "/pdf.worker.min.mjs";

// Respaldo por CDN, por si el asset local no se copió en la instalación.
const CDN_WORKER = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDFJS_VERSION}/build/pdf.worker.min.mjs`;

pdfjs.GlobalWorkerOptions.workerSrc =
  process.env.NEXT_PUBLIC_PDF_WORKER_SRC ?? LOCAL_WORKER;

// Si en algún despliegue prefieres CDN, exporta NEXT_PUBLIC_PDF_WORKER_SRC con CDN_WORKER.
export { CDN_WORKER, PDFJS_VERSION };

// Opciones para el visor: ubicación de cMaps y fuentes estándar (acentos/CJK).
export const PDF_OPTIONS = {
  cMapUrl: `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDFJS_VERSION}/cmaps/`,
  cMapPacked: true,
  standardFontDataUrl: `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDFJS_VERSION}/standard_fonts/`,
} as const;
