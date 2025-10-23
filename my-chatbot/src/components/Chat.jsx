import React, { useState, useRef, useLayoutEffect, useCallback } from "react";
import { defaultCharacter, characters } from "../data/characters";

export default function Chat({ selectedCharacter, username }) {
  const persona =
    selectedCharacter === "default" ? defaultCharacter : characters[selectedCharacter];

  const initial = username
    ? persona.initialMessage.replace("{username}", username)
    : persona.initialMessage;

  const [messages, setMessages] = useState([{ from: "bot", text: initial }]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const listRef = useRef(null);
  const endRef = useRef(null);

  // strong scroll-to-bottom
  const scrollToBottom = useCallback(() => {
    endRef.current?.scrollIntoView({ block: "end" });
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "auto" });
    requestAnimationFrame(() => {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    });
  }, []);

  useLayoutEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  const toLLMHistory = (msgs) =>
    (msgs || []).map((m) => ({
      role: m.from === "user" ? "user" : "assistant",
      content: m.text,
    }));

  const sendMessage = async () => {
    const value = input.trim();
    if (!value) return;

    const userMsg = { from: "user", text: value };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const payload = {
        message: userMsg.text,
        character: selectedCharacter,
        username,
        history: toLLMHistory(messages.slice(-8)),
      };

      const res = await fetch("http://localhost:8000/api/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Request failed");

      const { reply } = await res.json();
      setMessages((msgs) => [...msgs, { from: "bot", text: reply }]);
    } catch (_e) {
      setMessages((msgs) => [
        ...msgs,
        { from: "bot", text: "Desculpa, ocorreu um erro. Tenta novamente." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const prettyName =
    selectedCharacter?.charAt(0).toUpperCase() + selectedCharacter?.slice(1);

  return (
    <div className="chat-screen">
      {/* decorative corners */}
      <span className="corner tl" aria-hidden="true"></span>
      <span className="corner tr" aria-hidden="true"></span>
      <span className="corner bl" aria-hidden="true"></span>
      <span className="corner br" aria-hidden="true"></span>

      {/* header */}
      <header className="chat-hero">
        <h1 className="hero-title xl">Vamos explorar um mundo de histórias!</h1>
        <p className="hero-sub">
          A conversar com {selectedCharacter === "default" ? "Reading Coach" : prettyName}
        </p>
      </header>

      {/* messages */}
      <div className="chat-body">
        <div className="messages" ref={listRef}>
          {messages.map((m, i) => {
            const isBot = m.from === "bot";
            return (
              <div key={i} className={`msg-row ${isBot ? "left" : "right"}`}>
                <div className={`name-label ${isBot ? "left" : "right"}`}>
                  {isBot ? persona.name : username || "Tu"}
                  {!isBot && <span className="name-emoji" aria-hidden></span>}
                </div>

                {isBot ? (
                  <div className="avatar-circle bot-avatar" aria-hidden>
                    {persona.image && (
                      <img src={persona.image} alt={persona.name} className="avatar-img" />
                    )}
                  </div>
                ) : (
                  <div className="avatar-circle user-avatar" aria-hidden>
                    <span className="user-avatar-text">
                      {username?.[0]?.toUpperCase() || "🙂"}
                    </span>
                  </div>
                )}

                <div className={`bubble ${isBot ? "bot" : "user"}`}>{m.text}</div>
              </div>
            );
          })}

          {isLoading && (
            <div className="msg-row left">
              <div className="name-label left">{persona.name}</div>
              <div className="avatar-circle bot-avatar" aria-hidden>
                {persona.image && (
                  <img src={persona.image} alt={persona.name} className="avatar-img" />
                )}
              </div>
              <div className="bubble bot">
                <em>...</em>
              </div>
            </div>
          )}

          {/* scroll anchor */}
          <div ref={endRef} />
        </div>
      </div>

      {/* input */}
      <div className="input-wrap">
        <input
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !isLoading && sendMessage()}
          placeholder="Escreve aqui..."
          disabled={isLoading}
        />
        <button
          className="send-btn"
          onClick={sendMessage}
          disabled={isLoading}
          aria-label="Enviar"
          title="Enviar"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M5 12L3 4l18 8-18 8 2-8 10-0"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
