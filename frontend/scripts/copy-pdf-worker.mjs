// Copia el worker de pdf.js a public/ para servirlo localmente (100% offline).
// Se ejecuta tras `npm install` (postinstall). La versión del worker debe
// coincidir con la de pdfjs-dist que usa react-pdf.

import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");

const candidates = [
  "node_modules/pdfjs-dist/build/pdf.worker.min.mjs",
  "node_modules/pdfjs-dist/build/pdf.worker.mjs",
];

const dest = resolve(root, "public/pdf.worker.min.mjs");

try {
  const src = candidates.map((c) => resolve(root, c)).find((p) => existsSync(p));
  if (!src) {
    console.warn(
      "[pdf-worker] No se encontró pdf.worker en pdfjs-dist; el visor usará el CDN de respaldo.",
    );
    process.exit(0);
  }
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(src, dest);
  console.log("[pdf-worker] Worker copiado a public/pdf.worker.min.mjs");
} catch (err) {
  // No bloquear la instalación: el visor tiene respaldo por CDN.
  console.warn("[pdf-worker] No se pudo copiar el worker:", err?.message ?? err);
  process.exit(0);
}
