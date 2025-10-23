import React, { useState } from "react";
import "./styles/App.css";

import SelectionScreen from "./components/SelectionScreen.jsx";
import NameInput from "./components/NameInput.jsx";
import CharacterSelection from "./components/CharacterSelection.jsx";
import Chat from "./components/Chat.jsx";

export default function App() {
  // modes: 'select' | 'name' | 'default' | 'personalized' | 'chat'
  const [mode, setMode] = useState("select");
  const [username, setUsername] = useState(null);
  const [selectedCharacter, setSelectedCharacter] = useState(null);

  const resetToModeSelect = () => {
    setSelectedCharacter(null);
    setMode("select");
    setUsername(null);
  };

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
