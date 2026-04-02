import React, { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const STUDY_LOGIN_CODE_KEY = "studyLoginCode";

function formatLoginCodeForDisplay(code) {
  if (!code) return "";
  const c = String(code).replace(/\s|-/g, "").toUpperCase();
  return c.replace(/(.{5})/g, "$1-").replace(/-$/, "");
}

export default function EnrollmentGate({ onEnrolled }) {
  const [loginCode, setLoginCode] = useState(
    () => localStorage.getItem(STUDY_LOGIN_CODE_KEY) || ""
  );
  // New participants: "Primeira vez" first. If we already stored a return code, open "Já estive aqui".
  const [mode, setMode] = useState(() =>
    localStorage.getItem(STUDY_LOGIN_CODE_KEY) ? "return" : "first"
  ); // return | first
  const [code, setCode] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [pin, setPin] = useState("");
  const [pinConfirm, setPinConfirm] = useState("");
  const [loginPin, setLoginPin] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [registeredInfo, setRegisteredInfo] = useState(null);

  const submitFirstTime = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/study/register/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enrollmentCode: code.trim(),
          displayName: displayName.trim(),
          pin: pin.trim(),
          pinConfirm: pinConfirm.trim(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error || "Não foi possível registar.");
        return;
      }
      if (data.loginCode) {
        localStorage.setItem(STUDY_LOGIN_CODE_KEY, data.loginCode);
      }
      setRegisteredInfo({
        loginCode: data.loginCode,
        authToken: data.authToken,
      });
    } catch {
      setError("Não foi possível ligar ao servidor.");
    } finally {
      setBusy(false);
    }
  };

  const submitReturn = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/study/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          loginCode: loginCode.trim(),
          pin: loginPin.trim(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error || "Código ou PIN incorretos.");
        return;
      }
      if (data.loginCode) {
        localStorage.setItem(STUDY_LOGIN_CODE_KEY, data.loginCode);
      }
      onEnrolled(data.authToken);
    } catch {
      setError("Não foi possível ligar ao servidor.");
    } finally {
      setBusy(false);
    }
  };

  if (registeredInfo) {
    return (
      <div className="study-enroll">
        <h1 className="hero-title xl">Guarda estes dados</h1>
        <p className="hero-sub">
          Usa o <strong>código</strong> e o <strong>PIN</strong> da próxima vez em &quot;Já estive aqui&quot;.
        </p>
        <div className="enroll-success-card">
          <p className="enroll-success-label">O teu código de regresso</p>
          <p className="enroll-success-code" aria-live="polite">
            {formatLoginCodeForDisplay(registeredInfo.loginCode)}
          </p>
          <p className="hero-sub">
            Anota também o PIN que escolheste (não o mostramos de novo).
          </p>
        </div>
        <button
          type="button"
          className="study-primary-btn"
          onClick={() => onEnrolled(registeredInfo.authToken)}
        >
          Entrar no estudo
        </button>
      </div>
    );
  }

  return (
    <div className="study-enroll">
      <h1 className="hero-title xl">Entrar no estudo</h1>
      <div className="enroll-mode-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "return"}
          className={`enroll-tab ${mode === "return" ? "enroll-tab-active" : ""}`}
          onClick={() => {
            setMode("return");
            setError("");
          }}
        >
          Já estive aqui
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "first"}
          className={`enroll-tab ${mode === "first" ? "enroll-tab-active" : ""}`}
          onClick={() => {
            setMode("first");
            setError("");
          }}
        >
          Primeira vez
        </button>
      </div>

      {mode === "return" ? (
        <form
          key="enroll-return"
          onSubmit={submitReturn}
          className="enroll-form"
          autoComplete="on"
        >
          <p className="hero-sub enroll-mode-hint">
            Introduz o código que recebeste e o teu PIN.
          </p>
          <label htmlFor="study-return-login-code">
            Código de regresso
            <input
              id="study-return-login-code"
              name="study-return-login-code"
              className="enroll-field-input"
              value={loginCode}
              onChange={(e) => setLoginCode(e.target.value)}
              autoComplete="username"
              inputMode="text"
              autoCapitalize="characters"
            />
          </label>
          <label htmlFor="study-return-pin">
            PIN
            <input
              id="study-return-pin"
              name="study-return-pin"
              className="enroll-field-input"
              type="password"
              value={loginPin}
              onChange={(e) => setLoginPin(e.target.value)}
              autoComplete="current-password"
              inputMode="numeric"
            />
          </label>
          {error ? <p className="enroll-error">{error}</p> : null}
          <button type="submit" className="study-primary-btn" disabled={busy}>
            {busy ? "A entrar…" : "Entrar"}
          </button>
        </form>
      ) : (
        <form
          key="enroll-first"
          onSubmit={submitFirstTime}
          className="enroll-form"
          autoComplete="off"
        >
          <p className="hero-sub enroll-mode-hint">
            Usa o <strong>código de inscrição</strong> que o estudo te deu (folheto ou investigador).
            <span className="enroll-hint-secondary">
              {" "}
              Não é o código que aparece depois de te registares — esse serve só em &quot;Já estive
              aqui&quot;.
            </span>
          </p>
          <label htmlFor="study-enrollment-code">
            Código de inscrição ao estudo
            <input
              id="study-enrollment-code"
              name="study-enrollment-code"
              className="enroll-field-input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoComplete="off"
              required
            />
          </label>
          <label htmlFor="study-enroll-display-name">
            Nome (opcional)
            <input
              id="study-enroll-display-name"
              name="study-enroll-display-name"
              className="enroll-field-input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="name"
            />
          </label>
          <label htmlFor="study-enroll-pin">
            PIN (4–6 algarismos)
            <input
              id="study-enroll-pin"
              name="study-enroll-pin"
              className="enroll-field-input"
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              autoComplete="new-password"
              inputMode="numeric"
              minLength={4}
              maxLength={6}
              required
            />
          </label>
          <label htmlFor="study-enroll-pin-confirm">
            Confirmar PIN
            <input
              id="study-enroll-pin-confirm"
              name="study-enroll-pin-confirm"
              className="enroll-field-input"
              type="password"
              value={pinConfirm}
              onChange={(e) => setPinConfirm(e.target.value)}
              autoComplete="new-password"
              inputMode="numeric"
              minLength={4}
              maxLength={6}
              required
            />
          </label>
          {error ? <p className="enroll-error">{error}</p> : null}
          <button type="submit" className="study-primary-btn" disabled={busy}>
            {busy ? "A criar conta…" : "Criar e continuar"}
          </button>
        </form>
      )}
    </div>
  );
}
