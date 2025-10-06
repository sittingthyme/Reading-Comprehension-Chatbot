// selectionScreen.jsx
import React from "react";

export default function SelectionScreen({ onChoose }) {
  return (
    <div className="mode-select-container">
      <h2 style={{ textAlign: "center", marginBottom: 8 }}>
        Choose your experience
      </h2>

      <div className="mode-grid">
        <button
          className="mode-card"
          onClick={() => onChoose("default")}
          aria-label="Use default chatbot"
        >
          <h3>Default</h3>
          <p>A clean, neutral reading coach with no persona.</p>
        </button>

        <button
          className="mode-card"
          onClick={() => onChoose("personalized")}
          aria-label="Use personalized chatbot"
        >
          <h3>Personalized</h3>
          <p>Select a character and chat in their style.</p>
        </button>
      </div>
    </div>
  );
}
