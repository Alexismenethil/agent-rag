from uuid import UUID

from app.grounding import RESPUESTA_NO_ENCONTRADO, calcular_groundedness, resolver_citas
from app.retrieval.vector import ChunkRecuperado


def _chunk(texto: str) -> ChunkRecuperado:
    return ChunkRecuperado(
        chunk_id=UUID("11111111-1111-1111-1111-111111111111"),
        doc_id=UUID("22222222-2222-2222-2222-222222222222"),
        chunk_index=0,
        texto=texto,
        pagina=2,
        pagina_fin=2,
        seccion="Prueba",
        seccion_path=["Prueba"],
        offset_inicio=100,
        offset_fin=100 + len(texto),
        score=0.9,
    )


def test_resolver_citas_localiza_snippet_y_offsets_globales():
    chunk = _chunk("El umbral de hemoglobina para anemia es 11.0 g/dL.")
    respuesta = "El umbral de hemoglobina para anemia es 11.0 g/dL [1]."

    citas = resolver_citas(respuesta, [chunk])

    assert len(citas) == 1
    cita = citas[0]
    assert cita.localizado is True
    assert cita.snippet == "El umbral de hemoglobina para anemia es 11.0 g/dL"
    assert cita.offset_inicio == 100
    assert cita.offset_fin == 100 + len(cita.snippet)
    assert cita.pagina == 2


def test_groundedness_penaliza_afirmaciones_sin_marcador():
    chunk = _chunk("El umbral de hemoglobina para anemia es 11.0 g/dL.")
    respuesta = (
        "El documento trata sobre cribado no invasivo. "
        "El umbral de hemoglobina para anemia es 11.0 g/dL [1]."
    )
    citas = resolver_citas(respuesta, [chunk])

    assert calcular_groundedness(respuesta, citas) == 0.5


def test_resolver_citas_usa_match_normalizado_antes_de_fuzzy():
    chunk = _chunk(
        "El umbral de hemoglobina\n"
        "de la OMS para anemia en ninos de 6 a 59 meses es 11.0 g/dL."
    )
    respuesta = (
        "El umbral de hemoglobina de la OMS para anemia en niños de 6 a 59 meses "
        "es 11.0 g/dL [1]."
    )

    citas = resolver_citas(respuesta, [chunk])

    assert len(citas) == 1
    assert citas[0].localizado is True
    assert citas[0].snippet.endswith("11.0 g/dL")
    assert "\n" in citas[0].snippet


def test_groundedness_no_da_credito_a_cita_no_localizada():
    chunk = _chunk("Este fragmento no contiene la afirmación de la respuesta.")
    respuesta = "El umbral de hemoglobina para anemia es 11.0 g/dL [1]."
    citas = resolver_citas(respuesta, [chunk])

    assert len(citas) == 1
    assert citas[0].localizado is False
    assert calcular_groundedness(respuesta, citas) == 0.0


def test_groundedness_no_encontrado_es_fiel():
    assert calcular_groundedness(RESPUESTA_NO_ENCONTRADO, []) == 1.0
