from django.db import models
import uuid

from . import audit


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_name = models.CharField(max_length=100)
    character = models.CharField(max_length=100)
    started_at = models.DateTimeField(auto_now_add=True)

    messages = models.JSONField(default=list)

    audit = models.JSONField(default=dict, blank=True)

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
