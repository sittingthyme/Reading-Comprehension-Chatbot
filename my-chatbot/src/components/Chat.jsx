import React, {
  useState,
  useRef,
  useLayoutEffect,
  useCallback,
  useEffect,
} from "react";
import { defaultCharacter, characters } from "../data/characters";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

if (import.meta.env.DEV) {
  console.log("API URL:", API_URL);
}

function mapApiMessagesToState(rows) {
  return (rows || []).map((m) => ({
    from: m.sender === "user" ? "user" : "bot",
    text: m.content ?? "",
  }));
}

export default function Chat({
  selectedCharacter,
  username,
  studyContext = null,
  onStudyLocked,
  onRequestEndSession: _onRequestEndSession,
}) {
  const persona =
    selectedCharacter === "default"
      ? defaultCharacter
      : characters[selectedCharacter] || defaultCharacter;

  const initial = username
    ? persona.initialMessage.replace("{username}", username)
    : persona.initialMessage;

  const [messages, setMessages] = useState(() => {
    if (studyContext?.initialMessages?.length) {
      return mapApiMessagesToState(studyContext.initialMessages);
    }
    return [{ from: "bot", text: initial }];
  });
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const [conversationId, setConversationId] = useState(
    studyContext?.conversationId || null
  );

  const [secondsUntilLock, setSecondsUntilLock] = useState(null);

  const listRef = useRef(null);
  const endRef = useRef(null);
  const lockEmittedRef = useRef(false);

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

      const headers = { "Content-Type": "application/json" };
      if (studyContext?.authToken) {
        headers.Authorization = `Bearer ${studyContext.authToken}`;
      }

      try {
        const res = await fetch(`${API_URL}/api/save-message/`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            conversationId,
            sender,
            content,
            meta,
          }),
        });
        if (res.status === 403) {
          const d = await res.json().catch(() => ({}));
          if (d.sessionLocked && !lockEmittedRef.current) {
            lockEmittedRef.current = true;
            onStudyLocked?.(d.lockReason || "time_cap");
          }
        }
      } catch (err) {
        console.error("Failed to save message:", err);
      }
    },
    [conversationId, studyContext?.authToken, onStudyLocked]
  );

  useEffect(() => {
    if (studyContext?.conversationId) {
      setConversationId(studyContext.conversationId);
      if (studyContext.initialMessages?.length) {
        setMessages(mapApiMessagesToState(studyContext.initialMessages));
      }
    }
  }, [studyContext?.conversationId, studyContext?.initialMessages]);

  useEffect(() => {
    let cancelled = false;

    async function startConversation() {
      if (studyContext?.conversationId) {
        return;
      }

      try {
        const res = await fetch(`${API_URL}/api/start-conversation/`, {
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
            setConversationId("local-only");
          }
          return;
        }

        const data = await res.json();
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
  }, [selectedCharacter, username, studyContext?.conversationId]);

  useEffect(() => {
    lockEmittedRef.current = false;
  }, [studyContext?.studySessionId]);

  useEffect(() => {
    if (!studyContext?.sessionStartedAtISO || !studyContext?.maxSessionMinutes) {
      setSecondsUntilLock(null);
      return;
    }
    const capSec = studyContext.maxSessionMinutes * 60;
    const tick = () => {
      const start = new Date(studyContext.sessionStartedAtISO).getTime();
      if (Number.isNaN(start)) {
        setSecondsUntilLock(null);
        return;
      }
      const elapsed = (Date.now() - start) / 1000;
      const left = Math.max(0, Math.floor(capSec - elapsed));
      setSecondsUntilLock(left);
      if (left <= 0 && !lockEmittedRef.current) {
        lockEmittedRef.current = true;
        onStudyLocked?.("time_cap");
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [
    studyContext?.sessionStartedAtISO,
    studyContext?.maxSessionMinutes,
    onStudyLocked,
  ]);

  useEffect(() => {
    if (!studyContext?.authToken || !studyContext?.studySessionId) return;

    const ping = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        const res = await fetch(`${API_URL}/api/study/session/heartbeat/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${studyContext.authToken}`,
          },
          body: JSON.stringify({
            studySessionId: studyContext.studySessionId,
            activeDeltaSeconds: 45,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (data.sessionLocked && !lockEmittedRef.current) {
          lockEmittedRef.current = true;
          onStudyLocked?.(data.lockReason || "time_cap");
        }
      } catch {
        /* ignore */
      }
    };

    const id = setInterval(ping, 45000);
    ping();
    return () => clearInterval(id);
  }, [studyContext?.authToken, studyContext?.studySessionId, onStudyLocked]);

  const sendMessage = async () => {
    const value = input.trim();
    if (!value || isLoading || !conversationId) return;
    if (
      studyContext &&
      secondsUntilLock !== null &&
      secondsUntilLock <= 0
    ) {
      if (!lockEmittedRef.current) {
        lockEmittedRef.current = true;
        onStudyLocked?.("time_cap");
      }
      return;
    }

    const userMsg = { from: "user", text: value };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput("");
    setIsLoading(true);

    saveMessageToBackend("user", userMsg.text);

    try {
      const nextMessages = [...messages, userMsg];
      const payload = {
        message: userMsg.text,
        character: selectedCharacter,
        userName: username,
        history: toLLMHistory(nextMessages.slice(-8)),
      };
      if (studyContext?.studySessionId) {
        payload.studySessionId = studyContext.studySessionId;
      }

      const headers = { "Content-Type": "application/json" };
      if (studyContext?.authToken) {
        headers.Authorization = `Bearer ${studyContext.authToken}`;
      }

      const res = await fetch(`${API_URL}/api/chat/`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      const raw = await res.json().catch(() => ({}));
      if (raw.sessionLocked) {
        if (!lockEmittedRef.current) {
          lockEmittedRef.current = true;
          onStudyLocked?.(raw.lockReason || "time_cap");
        }
        setIsLoading(false);
        return;
      }

      if (!res.ok) throw new Error("Request failed");

      const { reply } = raw;
      const botMsg = { from: "bot", text: reply };

      setMessages((msgs) => [...msgs, botMsg]);

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

  const chKey = selectedCharacter || "default";
  const prettyName =
    chKey.charAt(0).toUpperCase() + chKey.slice(1);

  const inputLocked =
    isLoading ||
    !conversationId ||
    (studyContext &&
      secondsUntilLock !== null &&
      secondsUntilLock <= 0);

  const inputDisabled = inputLocked;

  const warnFifteen =
    studyContext &&
    secondsUntilLock !== null &&
    secondsUntilLock > 0 &&
    secondsUntilLock <= 300;

  return (
    <div className="chat-screen">
      <span className="corner tl" aria-hidden="true"></span>
      <span className="corner tr" aria-hidden="true"></span>
      <span className="corner bl" aria-hidden="true"></span>
      <span className="corner br" aria-hidden="true"></span>

      <header className="chat-hero">
        <h1 className="hero-title xl">Vamos explorar um mundo de histórias!</h1>
        <p className="hero-sub">
          A conversar com{" "}
          {selectedCharacter === "default" ? "Reading Coach" : prettyName}
        </p>
        {studyContext && secondsUntilLock !== null ? (
          <p className={`session-timer ${warnFifteen ? "session-timer-warn" : ""}`}>
            Tempo restante: {Math.floor(secondsUntilLock / 60)}:
            {String(secondsUntilLock % 60).padStart(2, "0")}
            {warnFifteen ? " — brevemente termina o tempo da sessão" : ""}
          </p>
        ) : null}
      </header>

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

          <div ref={endRef} />
        </div>
      </div>

      <div className="input-wrap">
        <input
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) =>
            e.key === "Enter" && !inputDisabled && sendMessage()
          }
          placeholder={
            !conversationId
              ? "A preparar a conversa..."
              : inputLocked && studyContext
                ? "Tempo da sessão terminou."
                : "Escreve aqui..."
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
