# Generated manually for study gating

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_conversation_audit"),
    ]

    operations = [
        migrations.CreateModel(
            name="Participant",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("condition", models.CharField(max_length=20)),
                ("display_name", models.CharField(blank=True, max_length=100)),
                ("enrollment_code_used", models.CharField(blank=True, max_length=128)),
                ("auth_token", models.CharField(db_index=True, max_length=64, unique=True)),
                ("memory_summary", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name="conversation",
            name="participant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="conversations",
                to="chat.participant",
            ),
        ),
        migrations.CreateModel(
            name="StudySession",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("week_index", models.PositiveSmallIntegerField()),
                ("slot_index", models.PositiveSmallIntegerField()),
                ("status", models.CharField(default="locked", max_length=20)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("active_seconds", models.PositiveIntegerField(default=0)),
                ("last_activity_at", models.DateTimeField(blank=True, null=True)),
                ("time_cap_triggered_at", models.DateTimeField(blank=True, null=True)),
                ("end_reason", models.CharField(blank=True, max_length=40)),
                ("comprehension_responses", models.JSONField(blank=True, null=True)),
                ("likert_responses", models.JSONField(blank=True, null=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="study_sessions",
                        to="chat.conversation",
                    ),
                ),
                (
                    "participant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="study_sessions",
                        to="chat.participant",
                    ),
                ),
            ],
            options={
                "ordering": ["week_index", "slot_index"],
            },
        ),
        migrations.AddConstraint(
            model_name="studysession",
            constraint=models.UniqueConstraint(
                fields=("participant", "week_index", "slot_index"),
                name="chat_studysession_unique_participant_week_slot",
            ),
        ),
    ]
