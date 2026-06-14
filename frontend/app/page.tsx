"use client";

import { useEffect, useState } from "react";
import { getHealth, type Health, API_URL } from "@/lib/api";

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setError(String(e)));
  }, []);

  const dbOk = health?.db === "ok";

  return (
    <main>
      <h1>Agente RAG sobre documentos</h1>
      <p className="muted">
        Explica un PDF citando el punto exacto. Proyecto antecedente para dominar RAG. Estado: <code>V0</code>.
      </p>

      <div className="card">
        <div className="badge">
          <span className={`dot ${dbOk ? "ok" : "down"}`} />
          Backend{" "}
          {error
            ? "no disponible"
            : health
              ? `${health.status} · BD ${health.db}`
              : "consultando…"}
        </div>
        <p className="muted" style={{ marginBottom: 0 }}>
          API: <code>{API_URL}</code>
          {error ? (
            <>
              {" "}
              — ¿levantaste el backend? <code>make up</code>
            </>
          ) : null}
        </p>
      </div>

      <div className="card">
        <strong>Siguiente:</strong> V1 — subir un PDF y responder citando página + fragmento exacto.
        <br />
        <span className="muted">Ver el roadmap en docs/PLAN.md.</span>
      </div>
    </main>
  );
}
