from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0004_participant_studysession_conversation_participant"),
    ]

    operations = [
        migrations.AddField(
            model_name="participant",
            name="login_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Stable code for return login (no ambiguous 0/O/1/I).",
                max_length=16,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="participant",
            name="pin_hash",
            field=models.CharField(blank=True, max_length=256),
        ),
    ]
