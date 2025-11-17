from django.db import models
import uuid

class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_name = models.CharField(max_length=100)
    character = models.CharField(max_length=100)
    started_at = models.DateTimeField(auto_now_add=True)

    # all messages for this conversation live here
    messages = models.JSONField(default=list)

    def __str__(self):
        return f"{self.user_name} - {self.character} - {self.started_at}"
