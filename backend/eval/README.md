# Evaluación (RAGAS)

Ubicación y comando **canónicos** (ver `docs/DECISIONES.md` ADR-006):

```bash
python -m eval.run_eval --gold eval/datasets/gold_v1.jsonl   # o: make eval
```

## Set gold (`datasets/gold_v1.jsonl`)

30-50 preguntas con respuesta y **evidencia esperada**. La evidencia se identifica por un id
**estable** —`doc_sha256 + chunk_index + offset_inicio/offset_fin`— **no** por el UUID de la
ingesta (que cambia al recrear la BD). Así el gold sobrevive a reconstruir el entorno.

Formato por línea (JSON):

```json
{
  "id": "q001",
  "doc_sha256": "<sha256 del PDF semilla>",
  "pregunta": "¿Cuál es la dosis recomendada de hierro para la prevención?",
  "ground_truth": "La respuesta esperada, parafraseable.",
  "modo": "estricto",
  "evidencia": [
    { "chunk_index": 42, "pagina": 7, "offset_inicio": 1820, "offset_fin": 1944,
      "snippet_esperado": "fragmento literal que debería citarse" }
  ]
}
```

## Métricas (gate de versión)

| Métrica | Qué mide | Gate |
|---|---|---|
| `faithfulness` | La respuesta se apoya de verdad en lo recuperado (anti-alucinación). | ≥ 0.85 |
| `answer_relevancy` | La respuesta responde lo que se preguntó. | (reportar) |
| `context_precision` | Los chunks recuperados son pertinentes. | (reportar) |
| `context_recall` | Se recuperó la evidencia necesaria. | ≥ 0.80 |
| *precisión de cita* | El `snippet` citado contiene realmente la afirmación. | (reportar) |
| *latencia* | Tiempo de respuesta por pregunta. | (reportar) |

Los `eval_runs`/`eval_results` se persisten en la BD para comparar *baselines* entre versiones
(`baseline_v2`, `baseline_v3`, …).
