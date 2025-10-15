# scaffold_policy.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Dict, Any, Optional, Tuple
import re
import time

class Move(IntEnum):
    NUDGE = 0
    REFLECT = 1
    ANALOGY = 2
    MINI_EXPLANATION = 3

@dataclass
class Turn:
    role: str  # 'child' | 'assistant' | 'system'
    content: str
    move: Optional[Move] = None  # Only set for assistant turns
    reason: Optional[str] = None  # Why we chose this move
    meta: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=lambda: time.time())

@dataclass
class PolicyConfig:
    max_step_up: int = 1              # prevent skipping ahead > 1 step
    min_step_down_after_success: int = 1
    confusion_threshold: float = 0.55 # > threshold => escalate one step
    success_threshold: float = 0.65   # > threshold => de-escalate one step
    window: int = 6                   # turns to look back
    allow_explanation_if_stuck_rounds: int = 2  # if repeated confusion at top-1
    enforce_no_chatter_on_flow: bool = True

class Heuristics:
    CONFUSION_PATTERNS = re.compile(r"\b(i don't know|idk|help|stuck|confused|what\?|huh|lost|can't|cannot|don't get)\b|\?\s*$",
                                    re.I)
    SUCCESS_PATTERNS = re.compile(r"\b(got it|i see|ohh|that makes sense|i can|let me try|done|answer is|because)\b", re.I)

    @staticmethod
    def confusion_score(text: str) -> float:
        # very light-weight proxy; pluggable for LLM classification
        base = 0.0
        if Heuristics.CONFUSION_PATTERNS.search(text):
            base += 0.7
        # Lots of question marks => increase
        qmarks = text.count('?')
        base += min(0.3, 0.05 * qmarks)
        # Very short/empty reply can indicate confusion
        if len(text.strip()) < 4:
            base += 0.2
        return max(0.0, min(1.0, base))

    @staticmethod
    def success_score(text: str) -> float:
        base = 0.0
        if Heuristics.SUCCESS_PATTERNS.search(text):
            base += 0.7
        # Presence of because/so/therefore often indicates explanation attempt
        if re.search(r"\b(because|therefore|so that)\b", text, re.I):
            base += 0.2
        # Slight bump for longer, coherent answers
        if len(text.split()) >= 8:
            base += 0.1
        return max(0.0, min(1.0, base))

@dataclass
class LadderState:
    history: List[Turn] = field(default_factory=list)
    last_move: Move = Move.NUDGE
    stuck_rounds: int = 0            # consecutive rounds with confusion

class LadderPolicy:
    def __init__(self, config: Optional[PolicyConfig] = None):
        self.cfg = config or PolicyConfig()
        self.state = LadderState()

    def _recent_child_text(self) -> str:
        # Return the most recent child utterance (within window), else ''
        for turn in reversed(self.state.history[-self.cfg.window:]):
            if turn.role == 'child':
                return turn.content
        return ''

    def _step_up(self, move: Move) -> Move:
        return Move(min(move + 1, Move.MINI_EXPLANATION))

    def _step_down(self, move: Move) -> Move:
        return Move(max(move - 1, Move.NUDGE))

    def _choose_next_move(self, last_move: Move, confusion_p: float, success_p: float) -> Tuple[Move, str]:
        reason = []
        if success_p >= self.cfg.success_threshold:
            # De-escalate
            new_move = self._step_down(last_move)
            reason.append(f"success_p={success_p:.2f} ≥ {self.cfg.success_threshold:.2f}: de-escalate")
            # reset stuck counter
            self.state.stuck_rounds = 0
        elif confusion_p >= self.cfg.confusion_threshold:
            # Escalate one step
            candidate = self._step_up(last_move)
            # Prevent skipping more than one level (already enforced by _step_up)
            new_move = candidate
            reason.append(f"confusion_p={confusion_p:.2f} ≥ {self.cfg.confusion_threshold:.2f}: escalate")
            # track stuck rounds (only counts if not already at top)
            if last_move in (Move.REFLECT, Move.ANALOGY) and new_move == self._step_up(last_move):
                self.state.stuck_rounds += 1
            else:
                self.state.stuck_rounds = 1 if new_move > last_move else 0
        else:
            # Maintain or gently step down if already low
            if last_move > Move.NUDGE:
                new_move = self._step_down(last_move)
                reason.append("no strong confusion: gentle de-escalation")
            else:
                new_move = last_move
                reason.append("stable: keep Nudge")
            self.state.stuck_rounds = 0

        # Allow mini-explanation only if we've climbed sequentially OR repeated stuck
        if new_move == Move.MINI_EXPLANATION:
            # Check if we climbed through steps in logs
            climbed_ok = self._climbed_sequentially()
            if not climbed_ok and self.state.stuck_rounds < self.cfg.allow_explanation_if_stuck_rounds:
                # pull back to ANALOGY
                new_move = Move.ANALOGY
                reason.append("blocked skip-to-explanation; using Analogy instead")

        return new_move, '; '.join(reason)

    def _climbed_sequentially(self) -> bool:
        # Look at last window and see if we saw NUDGE -> REFLECT -> ANALOGY (in order)
        seen = set()
        order = [Move.NUDGE, Move.REFLECT, Move.ANALOGY]
        idx = 0
        for t in self.state.history[-self.cfg.window:]:
            if t.role == 'assistant' and t.move is not None:
                if t.move == order[idx]:
                    seen.add(order[idx])
                    if idx < len(order) - 1:
                        idx += 1
        return seen == set(order)

    def plan(self, child_utterance: str) -> Move:
        """Given child text, choose the next move respecting the ladder."""
        # Record child turn
        self.state.history.append(Turn(role='child', content=child_utterance))

        last_move = self.state.last_move
        confusion_p = Heuristics.confusion_score(child_utterance)
        success_p = Heuristics.success_score(child_utterance)
        move, reason = self._choose_next_move(last_move, confusion_p, success_p)

        # Save placeholder (assistant turn will be appended in .log_assistant)
        self.state.last_move = move
        self.state.history.append(Turn(role='system', content=f"policy_decision: {move.name}", meta={
            'confusion_p': confusion_p, 'success_p': success_p
        }))
        return move

    def log_assistant(self, move: Move, message: str, reason: str, meta: Optional[Dict[str, Any]] = None):
        self.state.history.append(Turn(role='assistant', content=message, move=move, reason=reason, meta=meta or {}))

    def validate(self) -> Dict[str, Any]:
        """Check that logs follow the sequential, context-sensitive ladder.
        Returns a report dict with violations (if any)."""
        violations = []
        last_move: Optional[Move] = None
        for t in self.state.history:
            if t.role == 'assistant' and t.move is not None:
                if last_move is None:
                    last_move = t.move
                else:
                    # No skipping upward > 1 step
                    if t.move - last_move > 1:
                        violations.append({
                            'type': 'skip_up',
                            'message': f"Skipped from {Move(last_move).name} to {Move(t.move).name}",
                            'turn': t.content[:120]
                        })
                    # No chatter during self-initiated flow: if last child success was high, the next move shouldn't escalate
                    child_text = self._recent_child_text()
                    success_p = Heuristics.success_score(child_text)
                    if success_p >= self.cfg.success_threshold and t.move > last_move:
                        violations.append({
                            'type': 'unnecessary_escalation',
                            'message': f"Escalated despite success_p={success_p:.2f}",
                            'turn': t.content[:120]
                        })
                    last_move = t.move
        return {
            'ok': len(violations) == 0,
            'violations': violations,
            'moves': [
                {'role': t.role, 'move': (t.move.name if t.move is not None else None), 'text': t.content}
                for t in self.state.history if t.role != 'system'
            ]
        }

# Templated utterance generators (you can customize style/voice elsewhere)

def render_move(move: Move, prompt: str, persona_emoji: str = "") -> str:
    if move == Move.NUDGE:
        return f"{persona_emoji} Nice work! What’s the next small step you’d try?"
    if move == Move.REFLECT:
        return f"{persona_emoji} What makes you think that? Can you think out loud and tell me your reasoning?"
    if move == Move.ANALOGY:
        return f"{persona_emoji} Imagine this is like {{ANALOGY}}. How does that help you decide?"
    if move == Move.MINI_EXPLANATION:
        return f"{persona_emoji} Quick tip: {{MINI_EXPLANATION}} Now, want to try it your way?"
    return ""

