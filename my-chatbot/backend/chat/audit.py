# audit.py
from typing import List, Dict, Any, Optional
from datetime import datetime

AGENT_SENDERS = {"assistant", "bot", "agent"}
CHILD_SENDERS = {"user", "child", "student"}


def _timestamp_from_iso(s: Optional[str], default: float) -> float:
    if not s:
        return default
    try:
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return default


def classify_role(msg: Dict[str, Any]) -> str:
    """
    Decide if a message belongs to the agent or the child.

    Priority:
    1. sender field if it matches AGENT_SENDERS / CHILD_SENDERS
    2. meta.role if provided
    """
    sender = (msg.get("sender") or "").lower()
    if sender in AGENT_SENDERS:
        return "agent"
    if sender in CHILD_SENDERS:
        return "child"

    meta = msg.get("meta") or {}
    meta_role = meta.get("role")
    if meta_role in ("agent", "child"):
        return meta_role

    return "other"


def safe_div(numerator: int, denominator: int) -> Optional[float]:
    """Return numerator / denominator, or None if denominator is 0."""
    if denominator == 0:
        return None
    return numerator / denominator


def is_stance_change(prev_agent: Dict[str, Any], curr_agent: Dict[str, Any]) -> bool:
    """Returns True if stance changed between two consecutive agent turns."""
    if prev_agent is None:
        return False
    return prev_agent.get("stance") != curr_agent.get("stance")


def is_justified_stance_change(
    prev_child: Optional[Dict[str, Any]],
    prev_agent: Optional[Dict[str, Any]],
    curr_agent: Dict[str, Any],
) -> bool:
    """
    VERY SIMPLE RULES (as in the spec):

    - If child showed HIGH confusion and agent becomes more proactive -> justified.
    - If child showed HIGH autonomy ('let me try') and agent backs off -> justified.
    - If child showed HIGH autonomy and agent becomes more proactive -> unjustified.
    - Otherwise, default to True (conservative).
    """
    if prev_child is None or prev_agent is None:
        return True  # nothing to compare, be conservative

    confusion = prev_child.get("confusion_signal", "NONE")
    autonomy = prev_child.get("autonomy_signal", "NONE")

    prev_stance = prev_agent.get("stance")
    curr_stance = curr_agent.get("stance")

    # Case 1: child confused -> more proactive help is good
    if confusion == "HIGH":
        if prev_stance in ("QUIET", "RESPONSIVE") and curr_stance == "PROACTIVE":
            return True

    # Case 2: child wants autonomy -> backing off is good
    if autonomy == "HIGH":
        # backing off
        if prev_stance == "PROACTIVE" and curr_stance in ("RESPONSIVE", "QUIET"):
            return True
        if curr_stance == "PROACTIVE":
            return False

    return True


def is_well_tailored(
    prev_child: Optional[Dict[str, Any]],
    curr_agent: Dict[str, Any],
) -> bool:
    """
    VERY SIMPLE RULES for Tailoring Score (from the spec):

    - If child confusion HIGH -> ANALOGY or MINIEXPLAIN are ideal.
    - If child confusion LOW -> REFLECT or ANALOGY are ideal.
    - If no confusion and no autonomy -> NUDGE or REFLECT are ideal.
    - If autonomy HIGH -> NUDGE or no scaffold are ideal (we treat NUDGE as OK).
    """
    if prev_child is None:
        return True  # first turn, be conservative

    confusion = prev_child.get("confusion_signal", "NONE")
    autonomy = prev_child.get("autonomy_signal", "NONE")
    step = curr_agent.get("ladder_step")

    # Autonomy overrides: child wants to try alone
    if autonomy == "HIGH":
        # best is minimal or no help; NUDGE is acceptable
        return step == "NUDGE"

    if confusion == "HIGH":
        return step in ("ANALOGY", "MINIEXPLAIN")

    if confusion == "LOW":
        return step in ("REFLECT", "ANALOGY")

    # confusion == "NONE"
    return step in ("NUDGE", "REFLECT")


def compute_session_metrics(turns: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """
    Given a list of turn dicts (single session), compute:

      - on_text_adherence
      - adaptivity_index
      - tailoring_score
      - child_on_task_rate
      - child_elaboration_rate
      - child_question_rate
      - warmth_rate
      - over_social_rate
    """
    if not turns:
        return {}

    # Sort by timestamp to ensure correct order
    turns = sorted(turns, key=lambda t: t.get("timestamp", 0))

    # Counters
    agent_turns = 0
    agent_on_text = 0
    stance_changes = 0
    justified_stance_changes = 0
    well_tailored_scaffolds = 0

    child_turns = 0
    child_on_task = 0
    child_elaborated = 0
    child_questions = 0

    warm_supportive_turns = 0
    over_social_turns = 0

    prev_agent_turn: Optional[Dict[str, Any]] = None
    prev_child_turn: Optional[Dict[str, Any]] = None

    for turn in turns:
        speaker = turn.get("speaker")

        if speaker == "agent":
            agent_turns += 1

            # On-text adherence
            if turn.get("text_focus") == "ON_TEXT":
                agent_on_text += 1

            # Warmth vs over-social
            affect = turn.get("affect")
            if affect == "WARM_SUPPORTIVE":
                warm_supportive_turns += 1
            elif affect == "OVER_SOCIAL":
                over_social_turns += 1

            # Tailoring score: did we pick the right ladder level?
            if is_well_tailored(prev_child_turn, turn):
                well_tailored_scaffolds += 1

            # Adaptivity index: stance changes justified by child signal?
            if prev_agent_turn is not None and is_stance_change(prev_agent_turn, turn):
                stance_changes += 1
                if is_justified_stance_change(prev_child_turn, prev_agent_turn, turn):
                    justified_stance_changes += 1

            prev_agent_turn = turn

        elif speaker == "child":
            child_turns += 1

            if turn.get("on_task") is True:
                child_on_task += 1
            if turn.get("elaborated") is True:
                child_elaborated += 1
            if turn.get("is_question") is True:
                child_questions += 1

            prev_child_turn = turn

    metrics = {
        # Agent-side fidelity
        "on_text_adherence": safe_div(agent_on_text, agent_turns),
        "warmth_rate": safe_div(warm_supportive_turns, agent_turns),
        "over_social_rate": safe_div(over_social_turns, agent_turns),
        "tailoring_score": safe_div(well_tailored_scaffolds, agent_turns),
        "adaptivity_index": safe_div(justified_stance_changes, stance_changes),

        # Child-side engagement
        "child_on_task_rate": safe_div(child_on_task, child_turns),
        "child_elaboration_rate": safe_div(child_elaborated, child_turns),
        "child_question_rate": safe_div(child_questions, child_turns),
    }

    return metrics



def messages_to_turns(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert stored Conversation.messages into the 'turn' dicts expected
    by compute_session_metrics.
    """
    turns: List[Dict[str, Any]] = []

    for idx, msg in enumerate(messages or []):
        role = classify_role(msg)
        if role not in ("agent", "child"):
            continue

        meta = msg.get("meta") or {}
        ts = _timestamp_from_iso(msg.get("created_at"), float(idx))

        turn: Dict[str, Any] = {
            "timestamp": ts,
            "speaker": role,
        }

        if role == "agent":
            # Text focus: prefer explicit text_focus, otherwise infer from legacy on_text flag
            text_focus = meta.get("text_focus")
            if not text_focus:
                on_text_flag = meta.get("on_text")
                if on_text_flag is True:
                    text_focus = "ON_TEXT"
                elif on_text_flag is False:
                    text_focus = "OFF_TEXT_SAFE"
                else:
                    text_focus = "ON_TEXT"
            turn["text_focus"] = text_focus

            # Stance & ladder step (if you log these in meta)
            turn["stance"] = meta.get("stance", "RESPONSIVE")
            turn["ladder_step"] = meta.get("ladder_step") or meta.get("move") or "NUDGE"

            # Affect: neutral if not annotated
            turn["affect"] = meta.get("affect", "NEUTRAL")

        else:  # child
            turn["on_task"] = bool(meta.get("on_task", False))
            turn["elaborated"] = bool(meta.get("elaborated", False))

            is_q = meta.get("is_question")
            if is_q is None:
                content = msg.get("content") or ""
                is_q = "?" in content
            turn["is_question"] = bool(is_q)

            # Signals; default to NONE if not annotated
            turn["confusion_signal"] = meta.get("confusion_signal", "NONE")
            turn["autonomy_signal"] = meta.get("autonomy_signal", "NONE")

        turns.append(turn)

    return turns


def compute_audit(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Public API: takes raw Conversation.messages, converts to turns,
    and computes all session metrics as defined in the spec.
    """
    turns = messages_to_turns(messages)
    return compute_session_metrics(turns)
