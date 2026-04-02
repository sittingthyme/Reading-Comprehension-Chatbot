import React, { useState } from "react";
import "./styles/App.css";

import SelectionScreen from "./components/SelectionScreen.jsx";
import NameInput from "./components/NameInput.jsx";
import CharacterSelection from "./components/CharacterSelection.jsx";
import Chat from "./components/Chat.jsx";
import EnrollmentGate from "./components/EnrollmentGate.jsx";
import StudySessionDashboard from "./components/StudySessionDashboard.jsx";

const STUDY_GATING = import.meta.env.VITE_STUDY_GATING !== "false";

export default function App() {
  const [studyToken, setStudyToken] = useState(() =>
    localStorage.getItem("studyAuthToken")
  );

  const [mode, setMode] = useState("select");
  const [username, setUsername] = useState(null);
  const [selectedCharacter, setSelectedCharacter] = useState(null);

  const resetToModeSelect = () => {
    setSelectedCharacter(null);
    setMode("select");
    setUsername(null);
  };

  if (STUDY_GATING) {
    if (!studyToken) {
      return (
        <div className="app-container">
          <EnrollmentGate
            onEnrolled={(token) => {
              localStorage.setItem("studyAuthToken", token);
              setStudyToken(token);
            }}
          />
        </div>
      );
    }
    return (
      <div className="app-container">
        <StudySessionDashboard
          authToken={studyToken}
          onLogout={() => {
            localStorage.removeItem("studyAuthToken");
            setStudyToken(null);
          }}
        />
      </div>
    );
  }

  return (
    <div className="app-container">
      {mode === "select" ? (
        <SelectionScreen
          onChoose={(choice) => {
            if (choice === "personalized") setMode("name");
            else setMode("default");
          }}
        />
      ) : mode === "name" ? (
        <NameInput
          onSubmit={(name) => {
            setUsername(name);
            setMode("personalized");
          }}
        />
      ) : mode === "default" ? (
        <>
          <Chat selectedCharacter="default" username={null} />
          <div className="toolbar">
            <button className="change-character" onClick={resetToModeSelect}>
              Voltar
            </button>
          </div>
        </>
      ) : !selectedCharacter ? (
        <>
          <CharacterSelection onSelect={(key) => setSelectedCharacter(key)} />
          <div className="toolbar">
            <button className="change-character" onClick={resetToModeSelect}>
              Voltar
            </button>
          </div>
        </>
      ) : (
        <Chat selectedCharacter={selectedCharacter} username={username} />
      )}
    </div>
  );
}
