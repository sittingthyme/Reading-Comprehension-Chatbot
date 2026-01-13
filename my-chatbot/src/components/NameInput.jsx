import React, { useEffect, useState } from "react";

export default function NameInput({ onSubmit }) {
  const [name, setName] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("userName");
    if (saved && saved.trim()) setName(saved);
  }, []);

  const handleSubmit = () => {
    const trimmed = name.trim();
    if (!trimmed) return;

    localStorage.setItem("userName", trimmed);
    onSubmit(trimmed);
  };

  return (
    <div className="name-input-screen">
      <div className="name-input-header minimal">
        <h1 className="hero-title">Agente de Compreensão de Leitura</h1>
        <p className="hero-sub">Bem-vindo!</p>
      </div>

      <div className="name-input-center">
        <div className="name-card flat">
          <input
            id="username"
            className="name-input name-input-underline"
            type="text"
            value={name}
            autoFocus
            onChange={(e) => setName(e.target.value)}
            placeholder="Escreve o teu nome..."
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
          <button
            className="outline-gradient-btn"
            onClick={handleSubmit}
            disabled={!name.trim()}
          >
            Continuar
          </button>
        </div>
      </div>
    </div>
  );
}
