#!/usr/bin/env bash
# Descarga los pesos a ./models (NO se versionan; ver .gitignore).
# Placeholder de V0: los modelos se necesitan a partir de V1 (embeddings) / V2 (reranker) / V3 (voz).
set -euo pipefail

MODELS_DIR="${MODELS_DIR:-./models}"
mkdir -p "$MODELS_DIR/voices" "$MODELS_DIR/whisper" "$MODELS_DIR/.hf_cache"

echo "Directorio de modelos: $MODELS_DIR"
echo
echo "Pendiente por versión:"
echo "  V1  Embeddings BGE-m3        -> se descarga solo al primer uso (HF cache en \$HF_HOME)"
echo "  V2  Reranker BGE-reranker-v2-m3 -> idem"
echo "  V3  Voz Piper (es_ES-*.onnx)  -> descargar desde el repo de voces de Piper a $MODELS_DIR/voices"
echo "  V3  faster-whisper (base)     -> se descarga solo al primer uso a $MODELS_DIR/whisper"
echo
echo "Por ahora no hay nada obligatorio que descargar para V0. Edita este script en V1+."
