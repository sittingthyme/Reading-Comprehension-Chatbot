from django.test import TestCase
from . import audit


class AuditTests(TestCase):
    def test_compute_audit_basic(self):
        messages = [
            {
                "sender": "assistant",
                "content": "Let's think about the text.",
                "created_at": "2025-11-30T12:34:56-05:00",
                "meta": {
                    "role": "agent",
                    "on_text": True,
                    "stance": "RESPONSIVE",
                    "ladder_step": "NUDGE",
                    "affect": "WARM_SUPPORTIVE",
                },
            },
            {
                "sender": "user",
                "content": "I think the main idea is...",
                "created_at": "2025-11-30T12:34:57-05:00",
                "meta": {
                    "role": "child",
                    "on_task": True,
                    "elaborated": True,
                    "is_question": False,
                },
            },
        ]

        scores = audit.compute_audit(messages)

        # Agent-side
        self.assertAlmostEqual(scores["on_text_adherence"], 1.0)
        self.assertAlmostEqual(scores["warmth_rate"], 1.0)
        # No OVER_SOCIAL turns
        self.assertAlmostEqual(scores["over_social_rate"] or 0.0, 0.0)
        # With no stance changes, adaptivity_index is None
        self.assertIsNone(scores["adaptivity_index"])
        # First turn is treated as well-tailored
        self.assertAlmostEqual(scores["tailoring_score"], 1.0)

        # Child-side
        self.assertAlmostEqual(scores["child_on_task_rate"], 1.0)
        self.assertAlmostEqual(scores["child_elaboration_rate"], 1.0)
        self.assertAlmostEqual(scores["child_question_rate"], 0.0)


class MetricSanityTests(TestCase):
    def test_agent_text_and_affect_metrics(self):
        messages = [
            # Agent ON_TEXT + WARM
            {
                "sender": "assistant",
                "content": "On text, warm.",
                "created_at": "2025-01-01T10:00:00Z",
                "meta": {
                    "role": "agent",
                    "text_focus": "ON_TEXT",
                    "stance": "RESPONSIVE",
                    "ladder_step": "NUDGE",
                    "affect": "WARM_SUPPORTIVE",
                },
            },
            # Agent ON_TEXT + OVER_SOCIAL
            {
                "sender": "assistant",
                "content": "Still on text but too chatty 😅",
                "created_at": "2025-01-01T10:00:05Z",
                "meta": {
                    "role": "agent",
                    "text_focus": "ON_TEXT",
                    "stance": "RESPONSIVE",
                    "ladder_step": "REFLECT",
                    "affect": "OVER_SOCIAL",
                },
            },
            # Agent OFF_TEXT_SAFE + NEUTRAL
            {
                "sender": "assistant",
                "content": "Off text side-chatter.",
                "created_at": "2025-01-01T10:00:10Z",
                "meta": {
                    "role": "agent",
                    "text_focus": "OFF_TEXT_SAFE",
                    "stance": "RESPONSIVE",
                    "ladder_step": "NUDGE",
                    "affect": "NEUTRAL",
                },
            },
        ]

        scores = audit.compute_audit(messages)

        # 2 of 3 agent turns are ON_TEXT
        self.assertAlmostEqual(scores["on_text_adherence"], 2 / 3)
        # 1 of 3 is warm
        self.assertAlmostEqual(scores["warmth_rate"], 1 / 3)
        # 1 of 3 is over-social
        self.assertAlmostEqual(scores["over_social_rate"], 1 / 3)

    def test_child_engagement_metrics(self):
        messages = [
            {
                "sender": "user",
                "content": "Short, on task.",
                "created_at": "2025-01-01T10:00:00Z",
                "meta": {
                    "role": "child",
                    "on_task": True,
                    "elaborated": False,
                    "is_question": False,
                },
            },
            {
                "sender": "user",
                "content": "This is a longer explanation of the main idea.",
                "created_at": "2025-01-01T10:00:05Z",
                "meta": {
                    "role": "child",
                    "on_task": True,
                    "elaborated": True,
                    "is_question": False,
                },
            },
            {
                "sender": "user",
                "content": "Why did the character leave?",
                "created_at": "2025-01-01T10:00:10Z",
                "meta": {
                    "role": "child",
                    "on_task": False,
                    "elaborated": False,
                    "is_question": True,
                },
            },
        ]

        scores = audit.compute_audit(messages)

    
        self.assertAlmostEqual(scores["child_on_task_rate"], 2 / 3)
    
        self.assertAlmostEqual(scores["child_elaboration_rate"], 1 / 3)
        
        self.assertAlmostEqual(scores["child_question_rate"], 1 / 3)

    def test_adaptivity_and_tailoring(self):
        messages = [
     
            {
                "sender": "user",
                "content": "I don't know??",
                "created_at": "2025-01-01T10:00:00Z",
                "meta": {
                    "role": "child",
                    "on_task": True,
                    "elaborated": False,
                    "is_question": True,
                    "confusion_signal": "HIGH",
                    "autonomy_signal": "NONE",
                },
            },
            {
                "sender": "assistant",
                "content": "…",
                "created_at": "2025-01-01T10:00:03Z",
                "meta": {
                    "role": "agent",
                    "text_focus": "ON_TEXT",
                    "stance": "QUIET",
                    "ladder_step": "NUDGE",  
                    "affect": "NEUTRAL",
                },
            },
            {
                "sender": "user",
                "content": "I'm still confused.",
                "created_at": "2025-01-01T10:00:06Z",
                "meta": {
                    "role": "child",
                    "on_task": True,
                    "elaborated": False,
                    "is_question": False,
                    "confusion_signal": "HIGH",
                    "autonomy_signal": "NONE",
                },
            },

            {
                "sender": "assistant",
                "content": "Let me explain quickly...",
                "created_at": "2025-01-01T10:00:09Z",
                "meta": {
                    "role": "agent",
                    "text_focus": "ON_TEXT",
                    "stance": "PROACTIVE",
                    "ladder_step": "MINIEXPLAIN",
                    "affect": "WARM_SUPPORTIVE",
                },
            },
        ]

        scores = audit.compute_audit(messages)

        self.assertAlmostEqual(scores["tailoring_score"], 1 / 2)

        self.assertAlmostEqual(scores["adaptivity_index"], 1.0)
