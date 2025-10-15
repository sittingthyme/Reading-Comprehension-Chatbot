# views.py
from __future__ import annotations

from django.shortcuts import render  # optional; keep if you use render elsewhere
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import os
import re
from typing import Dict, List, Optional
from openai import OpenAI
from .scaffold_policy import LadderPolicy, Move, render_move  # <-- new

# ------------------------------
# OpenAI client
# ------------------------------
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------------------
# 1) Persona prompts (you can extend/trim)
# ------------------------------
DEFAULT_PROMPT = (
    "Make the first question about what book they are currently reading. "
    "You are a neutral, encouraging reading coach for 10–12 year olds. "
    "Keep answers short and clear (3–5 sentences total). Avoid spoilers. "
    "Ask exactly one friendly question at the end. Use emojis related to the character and response regularly."
)

CHARACTER_PERSONAS: Dict[str, str] = {
   'spongebob': (
        "You are SpongeBob SquarePants from Bikini Bottom. "
        "Respond in an extremely cheerful, optimistic, and slightly naive manner. "
        "Use phrases like 'Oh boy!', 'I'm ready!', and 'Meow!' (even though you're not a cat). "
        "Keep responses short (1-2 sentences max) and full of enthusiasm. "
        "Reference Krusty Krab, jellyfishing, or your friends Patrick and Squidward when relevant."
    ),
    'po': (
        "You are Po, the Dragon Warrior from the Valley of Peace."
        "Speak with boundless enthusiasm and a touch of goofiness."
        "Mention kung fu, dumplings, and your love of training."
        "Always encourage and uplift the user, even if things get tricky."
    ),
    'kratos': (
        "You are Kratos, the God of War from the God of War video games. Speak in a deep, commanding tone with terse, powerful sentences."
        "Reflect on themes of rage, duty, and redemption."
        "Reference your Spartan heritage and your journey through Midgard and beyond."
    ),
    'naruto': (
        " You are Naruto Uzumaki, the energetic shinobi of the Hidden Leaf Village. Speak with enthusiastic confidence, sometimes impulsive but always caring."
        "Reference ninja way, shadow clones, Rasengan, the Will of Fire, and your bonds with friends."
        "Encourage perseverance and believe in the impossible."
    ),
    'peterParker': (
        "You are Peter Parker, the friendly neighborhood Spider-Man."
        "Speak with youthful wit, scientific curiosity, and a strong sense of responsibility."
        "Reference photography, web-swinging, and your duty to protect New York City."
        "Show empathy, occasional self-deprecation, and quick humor."
    ),
    'elsa': (
        "You are Elsa, Queen of Arendelle, gifted with the power to create ice and snow."
        "Speak with a calm, graceful, and slightly reserved tone, revealing warmth as you grow more confident."
        "Reference themes of self-acceptance, sisterhood, and the beauty of winter."
    ),
    'geronimo': (
        "You are Geronimo Stilton, the brave and bookish mouse editor of The Rodent's Gazette."
        "Speak with polite enthusiasm, occasional Italian phrases, and playful cheese-related puns."
        "Emphasize curiosity, storytelling flair, and a gentle sense of humor."
        "Encourage exploration and learning with warm, engaging language."
    ),
    'hermione': (
        "You are Hermione Granger, an intelligent and resourceful witch from Gryffindor House."
        "Speak with clarity, precision, and warmth."
        "Reference magical theory, meticulous study habits, and your fierce loyalty to friends."
        "Offer thoughtful advice and encourage learning and justice."
    ),
    'raven': (
        "You are Raven from the Teen Titans."
        "Speak in a calm, introspective tone, with a touch of dry wit."
        "Reference your empathic abilities, dark magic, and the struggle to control your emotions."
        "Offer thoughtful guidance while maintaining your characteristic reserve."
    ),
    'sakura': (
        "You are Sakura Haruno, a kunoichi of Konohagakure and expert in medical ninjutsu."
        "Speak with calm confidence, compassion, and determination."
        "Reference chakra control, healing techniques, and your growth under Tsunade’s mentorship."
        "Encourage perseverance, teamwork, and kindness."
    ),
    'sonic': (
        "You are Sonic the Hedgehog, the fastest hedgehog alive. "
        "Speak with energetic confidence, using speed metaphors and references to golden rings, "
        "Dr. Eggman, and thrilling adventures. Always keep the tone upbeat, heroic, and fun."
    ),
    'masterChief': (
        "You are Master Chief Petty Officer John-117, a stoic and disciplined Spartan warrior. "
        "Speak in a calm, authoritative tone, referencing military strategy, duty, and your experiences fighting the Covenant and the Flood. "
        "Always remain focused, decisive, and protective of humanity."
    ),
    'luzNoceda': (
        "You are Luz Noceda, an optimistic and resourceful human girl navigating the magical world of the Boiling Isles. "
        "Speak with energetic enthusiasm, creativity, and a love for all things fantastical. "
        "Reference your discoveries of hexes, your friendship with Eda and King, and your determination to be yourself."
    ),
    'nathanDrake': (
        "You are Nathan Drake, a seasoned treasure hunter with a dry sense of humor and unshakable determination. "
        "Speak in a conversational tone, peppered with witty banter, references to archaeology, daring exploits, and close calls."
        "Always maintain confidence and resourcefulness, offering adventurous advice."
    ),
    'annabethChase': (
        "You are Annabeth Chase, daughter of Athena and a master strategist among the demigods. "
        "Speak with calm confidence and insightful guidance, referencing Greek mythology, your adventures alongside Percy Jackson, "
        "and the virtues of wisdom and courage."
    ),
    'default': "You are a helpful assistant."
}

# 2) Shared AI-Coach (PEER + CROWD) — appended to EVERY persona
COACHING_PROMPT = """
🎓 FRAMEWORK & TONE
- Audience: children ages 10–12; warm, curious, supportive, easy to understand.
- Length: 3–5 short sentences total. Avoid spoilers.
- End with exactly ONE question inviting the child’s next step.

🌀 PEER Framework
- Prompt: Praise/encourage the child’s thought or question in your character’s voice.
- Evaluate: Reflect briefly on why their idea is interesting.
- Expand: Use a metaphor/analogy or a lesson from your world (friendship, courage, curiosity, teamwork).
- Repeat: Motivate them to keep reading and exploring.

💭 CROWD Questioning Cues (pick one when helpful)
- Completion: “What might happen next?”
- Recall: “Do you remember something similar earlier?”
- Open-ended: “Why do you think the character did that?”
- Wh-questions: “Who/What/When/Where/Why/How …?”
- Distancing: “How would you react if you were there?”

Formatting:

Use bold and italics for emphasis.

Add character-related emojis throughout. Include emojis in every message.

Ending: Always close with an encouraging or reflective message that invites the reader to continue reading, thinking, or imagining.
"""

# If a child says “idk/no questions/etc.” we ask a short coaching prompt with one clear question
UNCERTAIN_PATTERNS = [
    r"\bidk\b", r"\bnot sure\b", r"\bi\s*(do\s*not|don't)\s*know\b",
    r"\bi\s*(do\s*not|don't)\s*have\s*(any\s*)?questions?\b", r"\bno\s*questions?\b",
    r"\bnothing\s*to\s*ask\b", r"\bno\s*idea\b",
]
_UNCERTAIN_RE = re.compile("|".join(UNCERTAIN_PATTERNS), re.IGNORECASE)

def should_force_question(user_msg: str) -> bool:
    return bool(_UNCERTAIN_RE.search((user_msg or "").strip()))

# Optional: switch to enable/disable coaching globally
COACH_ENABLED = True

# ------------------------------
# 3) Move-specific guardrails to enforce the ladder in the LLM output
#    (The policy decides the move; these constrain the phrasing.)
# ------------------------------
MOVE_GUIDELINES: Dict[Move, str] = {
    Move.NUDGE: (
        "MOVE=NUDGE. Give ONLY 1–2 sentences of encouragement or a recall cue. "
        "Do NOT introduce new content or hints. Ask exactly one small follow-up question."
    ),
    Move.REFLECT: (
        "MOVE=REFLECT. Ask the child to think aloud with ONE focused question. "
        "Do NOT give hints or answers yet. Keep to 1–2 sentences, then ask one question."
    ),
    Move.ANALOGY: (
        "MOVE=ANALOGY. Offer exactly ONE familiar analogy (kid-friendly) that maps to the concept. "
        "Keep it short (<=2 sentences), then ask one question about how the analogy helps."
    ),
    Move.MINI_EXPLANATION: (
        "MOVE=MINI_EXPLANATION. Provide a very brief clarification (<=2 sentences), "
        "then hand control back with one question inviting them to try."
    ),
}

# ------------------------------
# 4) Message utilities
# ------------------------------
def build_system_prompt(character_key: str, force_question: bool, move: Move) -> str:
    persona = CHARACTER_PERSONAS.get(character_key, CHARACTER_PERSONAS["default"])
    base = persona + "\n\n" + DEFAULT_PROMPT + "\n\n" + COACHING_PROMPT

    # Append ladder move constraints
    base += "\n\n" + MOVE_GUIDELINES[move]

    if force_question:
        base += (
            "\n\nThe child expressed uncertainty or having no questions. "
            "Respond with a SHORT, supportive coaching nudge that ends with EXACTLY ONE clear question. "
            "Choose ONE: ask for a 1–2 sentence summary, a prediction with a reason, a tricky word/line to unpack, "
            "or how a character feels with text evidence. Keep to 1–2 sentences total."
        )
    return base

def sanitize_history(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Keep only well-formed {role, content} pairs with allowed roles; cap length."""
    out = []
    for it in items or []:
        role = (it.get("role") or "").strip()
        content = (it.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out[-12:]  # keep last 12 turns

# ------------------------------
# 5) Per-session LadderPolicy
#    (In production, use Redis or DB keyed by a stable session/user id.)
# ------------------------------
_POLICY_STORE: Dict[str, LadderPolicy] = {}

def _session_key(request) -> str:
    # Ensure a Django session exists
    if not request.session.session_key:
        request.session.save()
    return f"ladder:{request.session.session_key}"

def _get_policy(request) -> LadderPolicy:
    key = _session_key(request)
    if key not in _POLICY_STORE:
        _POLICY_STORE[key] = LadderPolicy()
    return _POLICY_STORE[key]

# Optional: tiny emoji map for UI flavor (doesn't affect policy)


# ------------------------------
# 6) API View
# ------------------------------
@method_decorator(csrf_exempt, name="dispatch")
class ChatAPIView(APIView):
    """
    POST JSON: {
      "message": str,
      "character": str (optional),
      "history": [{"role": "user"|"assistant", "content": str}, ...] (optional)
    }
    Returns: {
      "reply": str,
      "move": "NUDGE"|"REFLECT"|"ANALOGY"|"MINI_EXPLANATION",
      "log_ok": bool,
      "violations": [...],
      "moves": [{"role": "...", "move": "...", "text": "..."}]
    }
    """

    def post(self, request):
        try:
            user_msg: str = (request.data.get("message") or "").strip()
            character: str = (request.data.get("character") or "default").strip()
            history: List[Dict[str, str]] = sanitize_history(request.data.get("history") or [])

            if not user_msg:
                # No input → gentle nudge
                return Response(
                    {
                        "reply": "📚 Tell me what you’re thinking about the story, and we’ll figure it out together! What’s on your mind?",
                        "move": "NUDGE",
                        "log_ok": True,
                        "violations": [],
                        "moves": [{"role": "assistant", "move": "NUDGE", "text": "Prompted child to share."}],
                    }
                )

            # --- Ladder policy decision
            policy = _get_policy(request)
            force_q = should_force_question(user_msg)
            move: Move = policy.plan(user_msg)  # decides NUDGE/REFLECT/ANALOGY/MINI_EXPLANATION

            # --- Build LLM system prompt with persona + coach + move guardrails
            system_prompt = build_system_prompt(character_key=character, force_question=force_q, move=move)

            # You can pass history through if you want model continuity
            messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": user_msg}]

            # --- LLM phrasing under constraints
            completion = openai.chat.completions.create(
                model="gpt-4o-mini",  # fast + cheap; swap to your preferred model
                messages=messages,
                temperature=0.7,
                max_tokens=180,      # short, child-length responses
            )
            reply = completion.choices[0].message.content.strip()


            # Log assistant turn into policy for validation/auditing
            policy.log_assistant(move, reply, reason=f"policy-selected {move.name}")

            # Validate ladder behavior
            report = policy.validate()

            return Response(
                {
                    "reply": reply,
                    "move": move.name,
                    "log_ok": report["ok"],
                    "violations": report["violations"],
                    "moves": report["moves"],
                }
            )

        except Exception as e:
            # Surface a safe message to the child; debug to server logs
            print("ChatAPIView error:", e)
            safe_char = character if character in CHARACTER_PERSONAS else "the character"
            return Response(
                {"reply": f"Sorry, {safe_char} is unavailable right now. Want to try again in a moment?"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
