import React, { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const CAIQ_VALUES = [
  { v: 1, label: "Discordo totalmente 😩" },
  { v: 2, label: "Discordo 🙁" },
  { v: 3, label: "Nem concordo nem discordo 😐" },
  { v: 4, label: "Concordo 🙂" },
  { v: 5, label: "Concordo totalmente 😄" },
];

export default function CaiqPanasSurvey({ authToken, studySessionId, onDone, onBack }) {
  const [def, setDef] = useState(null);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError("");
      try {
        const res = await fetch(
          `${API_URL}/api/study/session/survey-definition/?studySessionId=${encodeURIComponent(
            studySessionId
          )}`,
          { headers: { Authorization: `Bearer ${authToken}` } }
        );
        const data = await res.json().catch(() => ({}));
        if (cancelled) return;
        if (!res.ok) {
          setError(data.error || "Erro ao carregar o questionário.");
          return;
        }
        setDef(data);
        const init = {};
        (data.items || []).forEach((it) => {
          init[it.itemId] = null;
        });
        setAnswers(init);
      } catch {
        if (!cancelled) setError("Erro de rede.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authToken, studySessionId]);

  const setVal = (itemId, v) => {
    setAnswers((a) => ({ ...a, [itemId]: v }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    const missing = (def?.items || []).filter((it) => answers[it.itemId] == null);
    if (missing.length) {
      setError("Responde a todas as perguntas antes de enviar.");
      return;
    }
    setBusy(true);
    try {
      const body = {
        studySessionId,
        answers: (def.items || []).map((it) => ({
          itemId: it.itemId,
          value: answers[it.itemId],
        })),
      };
      const res = await fetch(`${API_URL}/api/study/session/caiq-panas/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error || "Erro ao guardar.");
        return;
      }
      onDone(data);
    } catch {
      setError("Erro de rede.");
    } finally {
      setBusy(false);
    }
  };

  if (!def && !error) {
    return (
      <div className="study-lobby">
        <p>A carregar o questionário…</p>
      </div>
    );
  }

  if (!def && error) {
    return (
      <div className="study-lobby">
        <p className="enroll-error">{error}</p>
        <button type="button" className="study-secondary-btn" onClick={onBack}>
          Voltar
        </button>
      </div>
    );
  }

  const caiqItems = (def.items || []).filter((it) => it.block === "caiq");
  const panasItems = (def.items || []).filter((it) => it.block === "panas");

  return (
    <div className="post-survey">
      <header className="chat-hero">
        <h1 className="hero-title">Questionário da sessão</h1>
        <p className="hero-sub">
          Completa este passo para terminar a sessão. O próximo desafio só desbloqueia depois
          de enviares tudo.
        </p>
      </header>

      {error ? <p className="enroll-error">{error}</p> : null}

      <form className="survey-form" onSubmit={submit}>
        <section className="caiq-block">
          <h2 className="hero-title">CAIQ</h2>
          <p className="hero-sub">{def.caiqInstruction}</p>
          <p className="likert-legend">{def.caiqScaleHeader}</p>
          <p className="likert-emoji-row" aria-hidden="true">
            {def.caiqRowEmojis}
          </p>
          {caiqItems.map((it) => (
            <fieldset key={it.itemId} className="likert-fieldset">
              <legend className="likert-question">{it.text}</legend>
              <div className="likert-scale" role="radiogroup" aria-labelledby={it.itemId}>
                {CAIQ_VALUES.map(({ v, label }) => (
                  <label key={v} className="likert-opt">
                    <input
                      type="radio"
                      name={it.itemId}
                      checked={answers[it.itemId] === v}
                      onChange={() => setVal(it.itemId, v)}
                    />
                    <span className="likert-opt-label">{label}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
        </section>

        <section className="panas-block">
          <h2 className="hero-title">PANAS</h2>
          <p className="hero-sub">{def.panasInstruction}</p>
          <p className="likert-legend">{def.panasScaleHeader}</p>
          {panasItems.map((it) => (
            <fieldset key={it.itemId} className="likert-fieldset">
              <legend className="likert-question">{it.text}</legend>
              <div className="likert-scale" role="radiogroup">
                {[1, 2, 3, 4, 5].map((v) => (
                  <label key={v} className="likert-opt">
                    <input
                      type="radio"
                      name={it.itemId}
                      checked={answers[it.itemId] === v}
                      onChange={() => setVal(it.itemId, v)}
                    />
                    {v}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
        </section>

        <div className="toolbar">
          <button type="submit" className="study-primary-btn" disabled={busy}>
            {busy ? "A enviar…" : "Enviar e terminar sessão"}
          </button>
          <button type="button" className="study-secondary-btn" onClick={onBack} disabled={busy}>
            Voltar
          </button>
        </div>
      </form>
    </div>
  );
}
