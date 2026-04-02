from django.contrib import admin

from .models import Conversation, Participant, StudySession


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user_name", "character", "participant", "started_at", "messages_preview")
    ordering = ("-started_at",)
    raw_id_fields = ("participant",)

    def messages_preview(self, obj):
        if not obj.messages:
            return "(no messages)"
        first = obj.messages[0]
        sender = first.get("sender", "?")
        content = first.get("content", "")[:40]
        return f"{sender}: {content}..."

    messages_preview.short_description = "First message"


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "login_code",
        "condition",
        "display_name",
        "enrollment_code_used",
        "created_at",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "auth_token", "pin_hash", "created_at")
    search_fields = ("display_name", "enrollment_code_used", "login_code", "id")


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "participant",
        "week_index",
        "slot_index",
        "status",
        "started_at",
        "ended_at",
        "end_reason",
    )
    list_filter = ("status", "week_index")
    ordering = ("participant", "week_index", "slot_index")
    raw_id_fields = ("participant", "conversation")
