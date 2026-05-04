from django.db import models
import uuid

from . import audit


class Participant(models.Model):
    class Condition(models.TextChoices):
        PERSONALIZED = "personalized", "Personalized"
        GENERIC = "generic", "Generic"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
    )
    display_name = models.CharField(max_length=100, blank=True)
    enrollment_code_used = models.CharField(max_length=128, blank=True)
    auth_token = models.CharField(max_length=64, unique=True, db_index=True)
    login_code = models.CharField(
        max_length=16,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text="Stable code for return login (no ambiguous 0/O/1/I).",
    )
    pin_hash = models.CharField(max_length=256, blank=True)
    memory_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} ({self.condition})"


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_name = models.CharField(max_length=100)
    character = models.CharField(max_length=100)
    started_at = models.DateTimeField(auto_now_add=True)

    messages = models.JSONField(default=list)

    audit = models.JSONField(default=dict, blank=True)

    participant = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )

    def recompute_audit(self, save: bool = True) -> dict:
        """
        Recompute auditing scores from self.messages and optionally save them
        into self.audit.
        """
        scores = audit.compute_audit(self.messages or [])
        self.audit = scores
        if save:
            self.save(update_fields=["audit"])
        return scores

    def __str__(self):
        return f"{self.user_name} - {self.character} - {self.started_at}"


class StudySession(models.Model):
    class Status(models.TextChoices):
        LOCKED = "locked", "Locked"
        AVAILABLE = "available", "Available"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="study_sessions",
    )
    week_index = models.PositiveSmallIntegerField()
    slot_index = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.LOCKED,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_sessions",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    active_seconds = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    time_cap_triggered_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=40, blank=True)
    comprehension_responses = models.JSONField(null=True, blank=True)
    likert_responses = models.JSONField(null=True, blank=True)
    reading_questionnaire_submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Likert + comprehension (slot 3) saved; CAIQ-PANAS may still be pending.",
    )
    caiq_panas_submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="CAIQ-PANAS batch saved before session completion.",
    )
    survey_scores = models.JSONField(
        null=True,
        blank=True,
        help_text="Aggregates from CAIQ-PANAS scoring after successful survey submit.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "week_index", "slot_index"],
                name="chat_studysession_unique_participant_week_slot",
            ),
        ]
        ordering = ["week_index", "slot_index"]

    def __str__(self):
        return f"{self.participant_id} W{self.week_index}S{self.slot_index} {self.status}"


class SurveyResponse(models.Model):
    """One row per CAIQ-PANAS item answer (long-form export)."""

    class SurveyVersion(models.TextChoices):
        FULL = "full", "Full"
        MINI = "mini", "Mini"

    class CompletionStatus(models.TextChoices):
        COMPLETE = "complete", "Complete"
        PARTIAL = "partial", "Partial"

    id = models.BigAutoField(primary_key=True)
    study_session = models.ForeignKey(
        StudySession,
        on_delete=models.CASCADE,
        related_name="survey_responses",
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="survey_responses",
    )
    participant_code = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Login code (or fallback id) at submission time.",
    )
    condition = models.CharField(max_length=20)
    session_number = models.PositiveSmallIntegerField()
    survey_version = models.CharField(max_length=10, choices=SurveyVersion.choices)
    item_id = models.CharField(max_length=32, db_index=True)
    item_text = models.TextField()
    value = models.PositiveSmallIntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    completion_status = models.CharField(
        max_length=16,
        choices=CompletionStatus.choices,
        default=CompletionStatus.COMPLETE,
    )

    class Meta:
        ordering = ["study_session_id", "item_id"]

    def __str__(self):
        return f"{self.participant_code} S{self.session_number} {self.item_id}={self.value}"
