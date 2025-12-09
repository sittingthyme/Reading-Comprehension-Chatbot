import React, {
  useState,
  useRef,
  useLayoutEffect,
  useCallback,
  useEffect,
} from "react";
import { defaultCharacter, characters } from "../data/characters";

export default function Chat({ selectedCharacter, username }) {
  const persona =
    selectedCharacter === "default"
      ? defaultCharacter
      : characters[selectedCharacter];

  const initial = username
    ? persona.initialMessage.replace("{username}", username)
    : persona.initialMessage;

  const [messages, setMessages] = useState([{ from: "bot", text: initial }]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // conversation id returned by backend
  const [conversationId, setConversationId] = useState(null);

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

    const saveMessageToBackend = useCallback(
      async (sender, content) => {
        if (!conversationId || conversationId === "local-only") return;
    
        const text = content || "";
        const lower = text.toLowerCase();
    
        let meta = {};
    
        if (sender === "user") {
          const isQuestion = text.includes("?");
          const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
          const elaborated = wordCount >= 12; 
    
          const confusion_signal = /i don't know|idk|confused|stuck|lost|i'm not sure/.test(
            lower
          )
            ? "HIGH"
            : "NONE";
    
          const autonomy_signal = /let me try|i want to try|can i do it|i'll do it myself/.test(
            lower
          )
            ? "HIGH"
            : "NONE";
    
          meta = {
            role: "child",
            on_task: true, 
            elaborated,
            is_question: isQuestion,
            confusion_signal,
            autonomy_signal,
          };
        } else {
      
          const hasWarmEmoji = /❄️|✨|🌟|💖|💕|📚|😊|😀|🙂|🌈/.test(text);
          const hasChatter = /lol|haha|lmao|😂/.test(lower);
    
          let affect = "NEUTRAL";
          if (hasChatter) {
            affect = "OVER_SOCIAL";
          } else if (hasWarmEmoji) {
            affect = "WARM_SUPPORTIVE";
          }
    
          meta = {
            role: "agent",
            text_focus: "ON_TEXT",      
            stance: "RESPONSIVE",       
            ladder_step: "NUDGE",       
            affect,
          };
        }
    
        try {
          await fetch("http://localhost:8000/api/save-message/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              conversationId,
              sender,
              content,
              meta,
            }),
          });
        } catch (err) {
          console.error("Failed to save message:", err);
        }
      },
      [conversationId]
    );
    
  
  
  // start conversation when chat mounts
  useEffect(() => {
    let cancelled = false;
  
    async function startConversation() {
      try {
        const res = await fetch("http://localhost:8000/api/start-conversation/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            userName: username || "Anon",
            character: selectedCharacter || "default",
            initialMessage: initial,
          }),
        });
  
        if (!res.ok) {
          console.error("Failed to start conversation, status:", res.status);
          if (!cancelled) {
            // allow typing but don't try DB logging
            setConversationId("local-only");
          }
          return;
        }
  
        const data = await res.json();
        console.log("start-conversation data:", data);
  
        if (!cancelled) {
          setConversationId(data.conversationId);
          if (initial) {
            saveMessageToBackend("bot", initial);
          }
        }
      } catch (err) {
        console.error("Error starting conversation:", err);
        if (!cancelled) {
          setConversationId("local-only");
        }
      }
    }
  
    startConversation();
  
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCharacter, username]);

  const sendMessage = async () => {
    const value = input.trim();
    if (!value || isLoading || !conversationId) return;

    const userMsg = { from: "user", text: value };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput("");
    setIsLoading(true);

    // save user message (no need to await)
    saveMessageToBackend("user", userMsg.text);

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
      const botMsg = { from: "bot", text: reply };

      setMessages((msgs) => [...msgs, botMsg]);

      // save bot message
      saveMessageToBackend("bot", botMsg.text);
    } catch (_e) {
      const errMsg = {
        from: "bot",
        text: "Desculpa, ocorreu um erro. Tenta novamente.",
      };
      setMessages((msgs) => [...msgs, errMsg]);
      saveMessageToBackend("bot", errMsg.text);
    } finally {
      setIsLoading(false);
    }
  };

  const prettyName =
    selectedCharacter?.charAt(0).toUpperCase() + selectedCharacter?.slice(1);

  const inputDisabled = isLoading || !conversationId;

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
          A conversar com{" "}
          {selectedCharacter === "default" ? "Reading Coach" : prettyName}
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
                  {!isBot && (
                    <span className="name-emoji" aria-hidden></span>
                  )}
                </div>

                {isBot ? (
                  <div className="avatar-circle bot-avatar" aria-hidden>
                    {persona.image && (
                      <img
                        src={persona.image}
                        alt={persona.name}
                        className="avatar-img"
                      />
                    )}
                  </div>
                ) : (
                  <div className="avatar-circle user-avatar" aria-hidden>
                    <span className="user-avatar-text">
                      {username?.[0]?.toUpperCase() || "🙂"}
                    </span>
                  </div>
                )}

                <div className={`bubble ${isBot ? "bot" : "user"}`}>
                  {m.text}
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="msg-row left">
              <div className="name-label left">{persona.name}</div>
              <div className="avatar-circle bot-avatar" aria-hidden>
                {persona.image && (
                  <img
                    src={persona.image}
                    alt={persona.name}
                    className="avatar-img"
                  />
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
          onKeyDown={(e) =>
            e.key === "Enter" && !inputDisabled && sendMessage()
          }
          placeholder={
            !conversationId ? "A preparar a conversa..." : "Escreve aqui..."
          }
          disabled={inputDisabled}
        />
        <button
          className="send-btn"
          onClick={sendMessage}
          disabled={inputDisabled}
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
