// selectionScreen.jsx
import React from "react";

export default function SelectionScreen({ onChoose }) {
  return (
    <div className="mode-select-container clean">
      {/* corner decorations */}
      <span className="corner tl" aria-hidden="true"></span>
      <span className="corner tr" aria-hidden="true"></span>
      <span className="corner bl" aria-hidden="true"></span>
      <span className="corner br" aria-hidden="true"></span>

      {/* header */}
      <header className="select-header">
        <h1 className="hero-title">Welcome to your reading adventure</h1>
        <p className="hero-sub">Choose a system</p>
      </header>

      {/* big pill buttons */}
      <div className="select-stack">
        <button
          className="select-pill select-pill--primary"
          onClick={() => onChoose("personalized")}
          aria-label="Choose Personalized AI System"
        >
          <ChatIcon className="pill-icon" />
          <span>Personalized AI System</span>
        </button>

        <button
          className="select-pill select-pill--secondary"
          onClick={() => onChoose("default")}
          aria-label="Choose Generic AI System"
        >
          <ChatIcon className="pill-icon" variant="secondary" />
          <span>Generic AI System</span>
        </button>
      </div>
    </div>
  );
}

/* Small inline SVG icon */
function ChatIcon({ className, variant }) {
  const stroke =
    variant === "secondary" ? "url(#grad-warm)" : "url(#grad-cool)";
  return (
    <svg
      className={className}
      width="40"
      height="40"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="grad-cool" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3b82f6" />
          <stop offset="1" stopColor="#22c55e" />
        </linearGradient>
        <linearGradient id="grad-warm" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ef4444" />
          <stop offset="1" stopColor="#f59e0b" />
        </linearGradient>
      </defs>
      <path
        d="M4 12a5 5 0 015-5h6a5 5 0 010 10h-1.2l-2.6 2.4c-.7.64-1.2.29-1.2-.5v-1.9H9a5 5 0 01-5-5Z"
        stroke={stroke}
        strokeWidth="1.6"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M8 10h6M8 13h8"
        stroke={stroke}
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}
