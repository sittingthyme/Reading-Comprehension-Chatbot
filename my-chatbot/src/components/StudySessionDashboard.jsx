import React, { useState, useEffect, useCallback } from "react";
import { defaultCharacter, characters } from "../data/characters";
import NameInput from "./NameInput.jsx";
import CharacterSelection from "./CharacterSelection.jsx";
import Chat from "./Chat.jsx";
import PostSessionSurvey from "./PostSessionSurvey.jsx";
import CaiqPanasSurvey from "./CaiqPanasSurvey.jsx";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function studyFetch(path, authToken, options = {}) {
  const headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${authToken}`,
  };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  return fetch(`${API_URL}${path}`, { ...options, headers });
}

const STUDY_CHARACTER_KEY = "studySelectedCharacter";

function readStoredCharacterKey() {
  const k = localStorage.getItem(STUDY_CHARACTER_KEY);
  if (k && characters[k]) return k;
  return null;
}

function characterDisplayName(key) {
  if (!key) return "";
  const persona = key === "default" ? defaultCharacter : characters[key];
  return persona?.name || key;
}

export default function StudySessionDashboard({ authToken, onLogout }) {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [username, setUsername] = useState(
    () => localStorage.getItem("userName") || ""
  );
  const [selectedCharacter, setSelectedCharacter] = useState(readStoredCharacterKey);
  const [phase, setPhase] = useState("lobby"); // lobby | name | character | chat | survey | caiq
  const [playPayload, setPlayPayload] = useState(null);
  const [surveyCtx, setSurveyCtx] = useState(null);

  const loadProgress = useCallback(async () => {
    setErr("");
    const res = await studyFetch("/api/study/progress/", authToken);
    if (res.status === 401) {
      onLogout();
      return;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setErr(data.error || "Erro ao carregar progresso");
      return;
    }
    setProgress(data);
  }, [authToken, onLogout]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const res = await studyFetch("/api/study/progress/", authToken);
      if (cancelled) return;
      if (res.status === 401) {
        onLogout();
        return;
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErr(data.error || "Erro ao carregar progresso");
        setLoading(false);
        return;
      }
      setProgress(data);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [authToken, onLogout]);

  useEffect(() => {
    if (phase !== "chat" || !playPayload?.studySessionId) return;
    const onBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue =
        "Ainda tens de completar o questionário de leitura e o CAIQ-PANAS antes de saires.";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [phase, playPayload?.studySessionId]);

  const condition = progress?.condition;
  const personalized = condition === "personalized";
  const needCharacter =
    progress?.allowCharacterSelection && personalized;

  const beginStartFlow = () => {
    if (
      progress?.focusStatus === "in_progress" &&
      progress.readingQuestionnaireSubmitted &&
      !progress.caiqPanasSubmitted
    ) {
      setPhase("caiq");
      return;
    }
    if (needCharacter && !username?.trim()) {
      setPhase("name");
      return;
    }
    if (needCharacter && !selectedCharacter) {
      setPhase("character");
      return;
    }
    startSession();
  };

  const startSession = async () => {
    setErr("");
    const focusId = progress?.focusSessionId;
    if (!focusId) {
      setErr("Não há sessão disponível.");
      return;
    }

    if (needCharacter && !selectedCharacter) {
      setErr("Escolhe um personagem antes de começar.");
      setPhase("character");
      return;
    }

    const charKey = needCharacter
      ? selectedCharacter
      : progress?.defaultCharacter || "default";
    const persona =
      charKey === "default" ? defaultCharacter : characters[charKey];
    const initialRaw = username?.trim()
      ? persona.initialMessage.replace("{username}", username.trim())
      : persona.initialMessage;

    const res = await studyFetch("/api/study/session/start/", authToken, {
      method: "POST",
      body: JSON.stringify({
        studySessionId: focusId,
        userName: username?.trim() || "Participant",
        character: charKey,
        initialMessage: initialRaw,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setErr(data.error || "Não foi possível iniciar a sessão");
      return;
    }

    setPlayPayload({
      studySessionId: data.studySessionId,
      conversationId: data.conversationId,
      messages: data.messages || [],
      sessionStartedAt: data.sessionStartedAt,
      maxSessionMinutes: progress?.maxSessionMinutes ?? 20,
      slotIndex: progress?.focusSlotIndex ?? 1,
      character: data.character || charKey,
      userName: data.userName || username?.trim() || "Participant",
    });
    setPhase("chat");
  };

  const handleReadingQuestionnaireDone = () => {
    setPhase("caiq");
  };

  const handleCaiqDone = async () => {
    setPhase("lobby");
    setPlayPayload(null);
    setSurveyCtx(null);
    await loadProgress();
  };

  if (loading && !progress) {
    return (
      <div className="study-lobby">
        <p>A carregar…</p>
      </div>
    );
  }

  if (phase === "name") {
    return (
      <div className="study-lobby">
        <NameInput
          onSubmit={(name) => {
            setUsername(name);
            localStorage.setItem("userName", name);
            setPhase("character");
          }}
        />
        <div className="toolbar">
          <button type="button" className="study-secondary-btn" onClick={() => setPhase("lobby")}>
            Voltar
          </button>
        </div>
      </div>
    );
  }

  if (phase === "character") {
    return (
      <div className="study-lobby">
        <CharacterSelection
          onSelect={(key) => {
            setSelectedCharacter(key);
            localStorage.setItem(STUDY_CHARACTER_KEY, key);
            setPhase("lobby");
          }}
        />
        <div className="toolbar">
          <button type="button" className="study-secondary-btn" onClick={() => setPhase("lobby")}>
            Voltar
          </button>
        </div>
      </div>
    );
  }

  if (phase === "survey" && surveyCtx && playPayload) {
    return (
      <PostSessionSurvey
        authToken={authToken}
        studySessionId={playPayload.studySessionId}
        slotIndex={surveyCtx.slotIndex}
        endReason={surveyCtx.endReason}
        onDone={handleReadingQuestionnaireDone}
        onCancel={() => {
          setSurveyCtx(null);
          setPhase("chat");
        }}
      />
    );
  }

  if (phase === "caiq") {
    const sid = playPayload?.studySessionId || progress?.focusSessionId;
    if (!sid) {
      return (
        <div className="study-lobby">
          <p className="enroll-error">Sessão inválida. Volta ao painel.</p>
          <button type="button" className="study-secondary-btn" onClick={() => setPhase("lobby")}>
            Voltar
          </button>
        </div>
      );
    }
    return (
      <CaiqPanasSurvey
        authToken={authToken}
        studySessionId={sid}
        onDone={handleCaiqDone}
        onBack={() => setPhase("lobby")}
      />
    );
  }

  if (phase === "chat" && playPayload) {
    return (
      <>
        <Chat
          key={playPayload.studySessionId}
          selectedCharacter={playPayload.character}
          username={playPayload.userName}
          studyContext={{
            authToken,
            studySessionId: playPayload.studySessionId,
            conversationId: playPayload.conversationId,
            sessionStartedAtISO: playPayload.sessionStartedAt,
            maxSessionMinutes: playPayload.maxSessionMinutes,
            initialMessages: playPayload.messages,
          }}
          onStudyLocked={(reason) => {
            setSurveyCtx({
              slotIndex: playPayload.slotIndex,
              endReason: reason === "time_cap" ? "time_cap" : "inactive_timeout",
            });
            setPhase("survey");
          }}
          onRequestEndSession={() => {
            setSurveyCtx({
              slotIndex: playPayload.slotIndex,
              endReason: "explicit_exit",
            });
            setPhase("survey");
          }}
        />
        <div className="toolbar">
          <button
            type="button"
            className="study-secondary-btn"
            onClick={() => {
              setSurveyCtx({
                slotIndex: playPayload.slotIndex,
                endReason: "completed_content",
              });
              setPhase("survey");
            }}
          >
            Terminar sessão e questionários
          </button>
        </div>
      </>
    );
  }

  const focus = progress?.focusStatus;
  const canStart =
    progress?.focusSessionId &&
    (focus === "available" || focus === "in_progress");

  const personalizedReady =
    !needCharacter ||
    (Boolean(username?.trim()) && Boolean(selectedCharacter));

  const handleLogout = () => {
    localStorage.removeItem(STUDY_CHARACTER_KEY);
    localStorage.removeItem("studyLoginCode");
    onLogout();
  };

  let primaryButtonLabel = "Começar sessão";
  if (canStart) {
    if (
      focus === "in_progress" &&
      progress?.readingQuestionnaireSubmitted &&
      !progress?.caiqPanasSubmitted
    ) {
      primaryButtonLabel = "Continuar questionário CAIQ-PANAS";
    } else if (!needCharacter) {
      primaryButtonLabel =
        focus === "in_progress" ? "Continuar sessão" : "Começar sessão";
    } else if (!username?.trim()) {
      primaryButtonLabel = "Introduz o teu nome para continuar";
    } else if (!selectedCharacter) {
      primaryButtonLabel = "Escolhe um personagem para continuar";
    } else {
      primaryButtonLabel = characterDisplayName(selectedCharacter);
    }
  }

  return (
    <div className="study-lobby">
      <header className="chat-hero">
        <h1 className="hero-title xl">O teu progresso</h1>
        <p className="hero-sub">
          Condição: <strong>{condition}</strong>
          {progress?.releasedWeekIndex != null
            ? ` · Semana do estudo liberada: ${progress.releasedWeekIndex}`
            : null}
        </p>
      </header>

      {err ? <p className="enroll-error">{err}</p> : null}

      <ul className="session-list">
        {(progress?.sessions || []).map((s) => (
          <li
            key={s.id}
            className={
              s.id === progress?.focusSessionId ? "session-focus" : ""
            }
          >
            Semana {s.weekIndex} · Sessão {s.slotIndex}: <strong>{s.status}</strong>
          </li>
        ))}
      </ul>

      <div className="toolbar study-toolbar">
        {canStart ? (
          <button
            type="button"
            className="study-primary-btn"
            onClick={beginStartFlow}
          >
            {primaryButtonLabel}
          </button>
        ) : (
          <p className="hero-sub">
            {progress?.focusSessionId
              ? "Esta sessão não está disponível ainda."
              : progress?.message || "Sem sessões em curso."}
          </p>
        )}
        {needCharacter && personalizedReady ? (
          <button
            type="button"
            className="study-secondary-btn"
            onClick={() => setPhase(username?.trim() ? "character" : "name")}
          >
            Alterar nome ou personagem
          </button>
        ) : null}
        <button type="button" className="study-secondary-btn" onClick={handleLogout}>
          Sair (novo código)
        </button>
      </div>
    </div>
  );
}
