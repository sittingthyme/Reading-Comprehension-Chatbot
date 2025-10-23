import React from "react";
import { characters } from "../data/characters";

export default function CharacterSelection({ onSelect }) {
  return (
    <div className="character-selection-screen">
      {/* corner decorations */}
      <span className="corner tl" aria-hidden="true"></span>
      <span className="corner tr" aria-hidden="true"></span>
      <span className="corner bl" aria-hidden="true"></span>
      <span className="corner br" aria-hidden="true"></span>

      {/* content */}
      <div className="character-selection-content">
        <div className="character-selection-header">
          <h1 className="hero-title">Escolhe o teu personagem</h1>
          <p className="hero-sub">Com quem queres conversar?</p>
        </div>

        <div className="character-grid">
          {Object.entries(characters).map(([key, c]) => (
            <button
              key={key}
              className="character-card image-only"
              onClick={() => onSelect(key)}
              aria-label={`Select ${c.name}`}
              title={c.name}
            >
              {c.image && (
                <img
                  src={c.image}
                  alt={c.name}
                  className="character-image large"
                  loading="lazy"
                />
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
