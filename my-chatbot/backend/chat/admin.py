from django.contrib import admin
from .models import Conversation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user_name", "character", "started_at", "messages_preview")
    ordering = ("-started_at",)

    def messages_preview(self, obj):
        # show a short preview of the messages JSON
        if not obj.messages:
            return "(no messages)"
        first = obj.messages[0]
        sender = first.get("sender", "?")
        content = first.get("content", "")[:40]
        return f"{sender}: {content}..."
    
    messages_preview.short_description = "First message"
