// App.jsx
import React, { useState } from 'react';
import './App.css';
import SelectionScreen from './selectionScreen.jsx';
import { SPONGEBOB_IMG, PO_IMG, KRATOS_IMG, NARUTO_IMG, PETER_IMG,
  ELSA_IMG, GERONIMO_IMG, HERMIONE_IMG, RAVEN_IMG, SAKURA_IMG, SONIC_IMG, 
  MASTER_IMG, LUZ_IMG, NATHAN_IMG, ANNABETH_IMG} from './images';

// Add a neutral "default" option used when mode === "default"
const defaultCharacter = {
  name: 'Reading Coach',
  description: 'A neutral, focused guide for reading and comprehension.',
  initialMessage:
    'Hi! I’m your reading coach. Ask me questions about the text, and I’ll help with hints, summaries, and questions.',
  image: null,
};

const characters = {
  // --- existing characters (unchanged) ---
  spongebob: {
    name: 'SpongeBob SquarePants',
    description: 'The optimistic and energetic sea sponge from Bikini Bottom',
    initialMessage: 'Hi there, buddy! Ready to have some fun under the sea?',
    image: SPONGEBOB_IMG,
  },
  po: {
    name: 'Po',
    description: 'The cheerful, food-loving panda who rises to become the Dragon Warrior',
    initialMessage: 'Hey there! I’m Po—the Dragon Warrior! Ready to train, protect the Valley of Peace, and share some dumplings along the way?',
    image: PO_IMG,
  },
  kratos: {
    name: 'Kratos',
    description: 'The God of War, a formidable Spartan warrior burdened by his tragic past and now navigating the realms of Norse mythology in search of redemption.',
    initialMessage: 'I am Kratos, Ghost of Sparta. Speak your question, mortal, and I will answer with the strength of a god.',
    image: KRATOS_IMG,
  },
  naruto: {
    name: 'Naruto',
    description: 'A determined shinobi from the Hidden Leaf who never gives up on his dream of becoming Hokage.',
    initialMessage: 'Hey there! Believe it! I’m Naruto Uzumaki! Ready to train hard, protect my friends, and master the Rasengan together?',
    image: NARUTO_IMG,
  },
  peterParker: {
    name: 'Peter Parker',
    description: 'A witty high-school photographer turned superhero who balances life and responsibility as Spider-Man.',
    initialMessage: 'Hey! I’m Peter Parker—your friendly neighborhood Spider-Man. Ready to swing into action?',
    image: PETER_IMG,
  },
  elsa: {
    name: 'Elsa',
    description: 'The ice queen of Arendelle who learns to embrace her magical powers and her true self.',
    initialMessage: 'Hello, I’m Queen Elsa of Arendelle. How may I help you today?',
    image: ELSA_IMG,
  },
  geronimo: {
    name: 'Geronimo Stilton',
    description: 'A mild-mannered mouse journalist and editor of The Rodent’s Gazette, always eager for a thrilling adventure.',
    initialMessage: 'Buongiorno! I’m Geronimo Stilton—editor, journalist, and adventurer extraordinaire. Ready to uncover a whisker-twitching tale together?',
    image: GERONIMO_IMG,
  },
  hermione: {
    name: 'Hermione Granger',
    description: 'A brilliant Gryffindor witch who values knowledge, logic, and loyalty.',
    initialMessage: 'Hello! I’m Hermione Granger. How can I help you master your magical studies today?',
    image: HERMIONE_IMG,
  },
  raven: {
    name: 'Raven',
    description: 'A reserved empath and sorceress balancing her human compassion with her demonic heritage.',
    initialMessage: 'I am Raven. Speak carefully and I will listen.',
    image: RAVEN_IMG,
  },
  sakura: {
    name: 'Sakura',
    description: 'A skilled medical-nin and powerhouse of Team 7, known for her intelligence, compassion, and inner strength.',
    initialMessage: 'Hi there! I’m Sakura Haruno. Ready to learn some healing ninjutsu or sharpen your combat skills together?',
    image: SAKURA_IMG,
  },
  sonic: {
    name: 'Sonic',
    description: 'The fastest hedgehog alive, known for his speed, confidence, and heroic heart.',
    initialMessage: 'Hey there! I’m Sonic the Hedgehog—gotta go fast! Ready for an adventure?',
    image: SONIC_IMG,
  },
  masterChief: {
    name: 'Master Chief',
    description: 'A legendary Spartan-II supersoldier defending humanity against the Covenant and beyond.',
    initialMessage: 'Spartan, mission briefing incoming. How can I assist you today?',
    image: MASTER_IMG,
  },
  luzNoceda: {
    name: 'Luz Noceda',
    description: 'A curious and imaginative human girl who learns magic in the Boiling Isles and follows her dreams fearlessly.',
    initialMessage: 'Hey there! I’m Luz Noceda—ready to explore magic, make new friends, and have an adventure?',
    image: LUZ_IMG,
  },
  nathanDrake: {
    name: 'Nathan Drake',
    description: 'A charismatic treasure hunter with a sharp wit and a knack for getting into (and out of) perilous situations.',
    initialMessage: 'Hey there! I’m Nathan Drake—ready to hunt some treasure and survive another adventure?',
    image: NATHAN_IMG,
  },
  annabethChase: {
    name: 'Annabeth Chase',
    description: 'The brave daughter of Athena, known for her wisdom, courage, and leadership among demigods.',
    initialMessage: 'Hello, I’m Annabeth Chase. How can I help you navigate strategy, myth, or life at Camp Half-Blood today?',
    image: ANNABETH_IMG,
  },
};

function CharacterSelection({ onSelect }) {
  return (
    <div className="character-selection">
      <h2>Choose a character to chat with:</h2>
      <hr />
      <div className="character-grid">
        {Object.entries(characters).map(([key, character]) => (
          <div 
            key={key} 
            className="character-card"
            onClick={() => onSelect(key)}
          >
            <h3>{character.name}</h3>
            <p>{character.description}</p>
            {character.image && (
              <img src={character.image} alt={character.name} className="character-image" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Chat({ selectedCharacter }) {
  // If default mode, use defaultCharacter data
  const persona =
    selectedCharacter === 'default'
      ? defaultCharacter
      : characters[selectedCharacter];

  const [messages, setMessages] = useState([
    { from: 'bot', text: persona.initialMessage },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // inside Chat component in App.jsx

  const toLLMHistory = (msgs) =>
    (msgs || []).map(m => ({
      role: m.from === 'user' ? 'user' : 'assistant',
      content: m.text,
    }));
  
  const sendMessage = async () => {
    if (!input.trim()) return;
  
    // 1) Build history from the *current* messages
    const historyPayload = toLLMHistory([...messages].slice(-8));
  
    const userMsg = { from: 'user', text: input };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput('');
    setIsLoading(true);
  
    try {
      const payload = {
        message: userMsg.text,
        character: selectedCharacter,   // "default" or persona key
        history: historyPayload,        // <-- make sure this is here
      };
  
      // 2) Debug log — verify in the console
      console.log('POST /api/chat payload ->', payload);
  
      const res = await fetch('http://localhost:8000/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
  
      if (!res.ok) throw new Error('Request failed');
      const { reply } = await res.json();
      setMessages((msgs) => [...msgs, { from: 'bot', text: reply }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages((msgs) => [
        ...msgs,
        { from: 'bot', text: 'Sorry, an error occurred. Please try again.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="character-header">
        <h2>Chatting with {persona.name}</h2>
      </div>
      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.from}`}>
            {m.text}
          </div>
        ))}
        {isLoading && (
          <div className="message bot">
            <em>...</em>
          </div>
        )}
      </div>
      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !isLoading && sendMessage()}
          placeholder="Type a message..."
          disabled={isLoading}
        />
        <button onClick={sendMessage} disabled={isLoading}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}

export default function App() {
  // "select" -> show SelectionScreen
  // "default" -> jump straight into Chat with default persona
  // "personalized" -> show CharacterSelection then Chat
  const [mode, setMode] = useState('select');
  const [selectedCharacter, setSelectedCharacter] = useState(null);

  const resetToModeSelect = () => {
    setSelectedCharacter(null);
    setMode('select');
  };

  return (
    <div className="app-container">
      <h1 style={{ textAlign: 'center' }}>Reading Comprehension Chatbot</h1>

      {mode === 'select' && (
        <SelectionScreen onChoose={setMode} />
      )}

      {mode === 'default' && (
        <>
          <Chat selectedCharacter="default" />
          <div className="toolbar">
            <button className="change-character" onClick={resetToModeSelect}>
              Back
            </button>
          </div>
        </>
      )}

      {mode === 'personalized' && (
        <>
          {!selectedCharacter ? (
            <>
              <CharacterSelection onSelect={setSelectedCharacter} />
              <div className="toolbar">
                <button className="change-character" onClick={resetToModeSelect}>
                  Back
                </button>
              </div>
            </>
          ) : (
            <>
              <Chat selectedCharacter={selectedCharacter} />
              <div className="toolbar">
                <button
                  className="change-character"
                  onClick={() => setSelectedCharacter(null)}
                >
                  Change Character
                </button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
