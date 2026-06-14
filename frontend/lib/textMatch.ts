// Búsqueda robusta de substring para resaltar el snippet de una cita dentro de
// la capa de texto del PDF (ADR-003): normaliza espacios y acentos y tolera
// pequeñas diferencias de extracción entre el texto del backend y el del visor.

/** Normaliza para comparar: minúsculas, sin acentos, espacios colapsados. */
export function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "") // quita marcas diacríticas
    .replace(/\s+/g, " ")
    .trim();
}

/** Tokeniza en palabras normalizadas (>= 2 caracteres). */
export function tokens(text: string): string[] {
  return normalize(text)
    .split(/[^\p{L}\p{N}]+/u)
    .filter((t) => t.length >= 2);
}

/**
 * Decide si un fragmento de la capa de texto del PDF forma parte del snippet
 * citado. Estrategia tolerante: el snippet suele venir partido en muchos items
 * (`react-pdf` parte por glifos/líneas), así que comprobamos solapamiento de
 * tokens en ambas direcciones.
 */
export function fragmentMatchesSnippet(fragment: string, snippet: string): boolean {
  const f = normalize(fragment);
  if (!f) return false;
  const s = normalize(snippet);
  if (!s) return false;

  // Coincidencia directa de substring (caso ideal).
  if (s.includes(f) && f.length >= 2) return true;
  if (f.includes(s)) return true;

  // Solapamiento de tokens: el fragmento aporta palabras que están en el snippet.
  const fragTokens = tokens(fragment);
  if (fragTokens.length === 0) return false;
  const snippetSet = new Set(tokens(snippet));
  const shared = fragTokens.filter((t) => snippetSet.has(t)).length;
  // Al menos la mitad de los tokens del fragmento aparecen en el snippet.
  return shared > 0 && shared / fragTokens.length >= 0.5;
}

/** Recorta un snippet largo para mostrarlo en chips/tooltips. */
export function truncate(text: string, max = 160): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return clean.slice(0, max - 1).trimEnd() + "…";
}
