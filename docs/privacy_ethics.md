# Privacidad y ética

Hoy el corpus son libros/PDFs académicos sin datos personales, pero el **destino del proyecto es el
cribado de anemia infantil**, donde se procesarán datos de salud de menores. La arquitectura se diseña ya
con estos principios para que la transición sea inmediata y defendible ante un comité de ética. Este
documento es la base del capítulo de ética de la tesis.

- **Minimización de datos.** Solo se almacena lo imprescindible para la función: texto del documento +
  metadatos de posición para citar. No se infieren ni guardan atributos sensibles innecesarios.
- **Separación de ejes como garantía de privacidad.** Mantener **grounding** (contenido del documento) y
  **personalización** (perfil del estudiante) en subsistemas separados implica que el perfil no se mezcla
  con el corpus ni se filtra; al LLM solo se envía lo estrictamente necesario.
- **Consentimiento informado.** El usuario acepta explícitamente que sus PDFs se procesan y almacenan,
  con explicación de qué se guarda, para qué y por cuánto tiempo. En la versión clínica futura:
  consentimiento del tutor/apoderado para datos de menores, conforme a la **Ley N.º 29733** (Protección de
  Datos Personales, Perú) y su reglamento, y a los principios de la normativa MINSA.
- **Anonimización / seudonimización.** Identificar a los sujetos por un identificador opaco (`user_id`/
  `patient_id` UUID), nunca por nombre en tablas de contenido. Los logs no registran el texto íntegro de
  los documentos (`ANONYMIZE_LOGS=true`): solo identificadores y métricas.
- **Retención y derecho al borrado.** Política explícita (`DATA_RETENTION_DAYS`) con purga automática de
  `data/uploads/` y derivados (chunks, embeddings). Operación de borrado total a petición
  (`DELETE /documents/{id}` → chunks/embeddings; las citas conservan su `snippet` denormalizado pero pierden
  el `chunk_id`), alineada con el derecho de supresión.
- **Soberanía y procesamiento offline.** La voz es 100% local (Piper/faster-whisper) y la interfaz de LLM
  es intercambiable hacia un modelo local (Qwen2.5/Llama 3.x). Documentar qué datos salen del entorno en
  cada modo (Claude en la nube vs. local) — clave para el escenario clínico con menores.
- **Transparencia y no alucinación.** Los dos modos (estricto con cita exacta; ampliado etiquetado aparte)
  y la verificación de fidelidad (groundedness) son salvaguardas éticas: el sistema no presenta información
  no respaldada como si viniera del documento. En contexto clínico, una afirmación médica inventada es un
  daño potencial.
- **Seguridad de acceso (producción).** Autenticación, TLS en tránsito, cifrado en reposo de la BD,
  mínimo privilegio en credenciales, `CORS_ORIGINS` restringido. Claves y contraseñas como secretos
  (nunca en el repo; ver `.env`/`.gitignore` y el hook `detect-secrets`).
- **Trazabilidad / auditoría.** El historial permite auditar qué se respondió y con qué evidencia (qué
  chunks/citas) — útil tanto para la evaluación con RAGAS como para la rendición de cuentas en uso clínico.
