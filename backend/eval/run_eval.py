"""Runner de evaluación RAGAS (V2).

STUB (V0): define la interfaz del comando único de evaluación. La implementación (cargar el set
gold, ejecutar el pipeline RAG sobre cada pregunta, calcular faithfulness / answer_relevancy /
context_precision / context_recall, persistir en eval_runs/eval_results y reportar) llega en V2.

Uso (cuando esté implementado):
    python -m eval.run_eval --gold eval/datasets/gold_v1.jsonl

Gates de aprobación (ver docs/PLAN.md): faithfulness >= 0.85 y context_recall >= 0.80.
OJO: distinto del umbral de runtime GROUNDEDNESS_THRESHOLD (=0.6). Son medidas diferentes.
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluación RAGAS del agente RAG")
    parser.add_argument("--gold", default="eval/datasets/gold_v1.jsonl", help="Set gold (JSONL)")
    parser.add_argument("--nombre", default="baseline", help="Etiqueta del run (baseline_vN)")
    args = parser.parse_args()

    print(f"[eval] gold={args.gold} nombre={args.nombre}", file=sys.stderr)
    print("[eval] No implementado todavía (llega en V2). Ver docs/PLAN.md.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
