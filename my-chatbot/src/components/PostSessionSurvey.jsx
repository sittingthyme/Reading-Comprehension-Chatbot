import React, { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function LikertRow({ label, fieldId, value, onChange }) {
  return (
    <div className="likert-row">
      <span id={fieldId}>{label}</span>
      <div
        className="likert-scale likert-scale--inline"
        role="group"
        aria-labelledby={fieldId}
      >
        {[1, 2, 3, 4, 5].map((n) => (
          <label key={n} className="likert-opt">
            <input
              type="radio"
              name={fieldId}
              checked={value === n}
              onChange={() => onChange(n)}
            />
            {n}
          </label>
        ))}
      </div>
    </div>
  );
}

export default function PostSessionSurvey({
  authToken,
  studySessionId,
  slotIndex,
  endReason,
  onDone,
  onCancel,
}) {
  const [rapport, setRapport] = useState(3);
  const [closeness, setCloseness] = useState(3);
  const [flow, setFlow] = useState(3);
  const [comprehension, setComprehension] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (slotIndex === 3 && !comprehension.trim()) {
      setError("Por favor responde às perguntas de compreensão.");
      return;
    }
    setBusy(true);
    try {
      const body = {
        studySessionId,
        endReason: endReason || "completed_content",
        likert: { rapport, closeness, flow },
      };
      if (slotIndex === 3) {
        body.comprehension = {
          main_response: comprehension.trim(),
        };
      }
      const res = await fetch(`${API_URL}/api/study/session/reading-questionnaire/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error || "Erro ao guardar");
        return;
      }
      onDone(data);
    } catch {
      setError("Erro de rede.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="post-survey">
      <h2 className="hero-title">Antes de terminar</h2>
      <p className="hero-sub">Responde de forma honesta — não há respostas certas ou erradas.</p>
      <form onSubmit={submit} className="survey-form">
        <h3>Escala (1 = muito baixo, 5 = muito alto)</h3>
        <LikertRow fieldId="likert-rapport" label="Rapport" value={rapport} onChange={setRapport} />
        <LikertRow fieldId="likert-closeness" label="Proximidade" value={closeness} onChange={setCloseness} />
        <LikertRow fieldId="likert-flow" label="Fluxo" value={flow} onChange={setFlow} />

        {slotIndex === 3 ? (
          <>
            <h3>Compreensão de leitura</h3>
            <label>
              Descreve o que leste e o que percebeste do texto.
              <textarea
                className="survey-textarea"
                rows={5}
                value={comprehension}
                onChange={(e) => setComprehension(e.target.value)}
                required
              />
            </label>
          </>
        ) : null}

        {error ? <p className="enroll-error">{error}</p> : null}
        <div className="survey-actions">
          <button type="button" className="study-secondary-btn" onClick={onCancel}>
            Voltar
          </button>
          <button type="submit" className="study-primary-btn" disabled={busy}>
            {busy ? "A guardar…" : "Submeter"}
          </button>
        </div>
      </form>
    </div>
  );
}
