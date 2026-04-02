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
