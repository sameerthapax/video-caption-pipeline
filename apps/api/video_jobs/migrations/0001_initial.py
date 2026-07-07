from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="VideoJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("user_id", models.UUIDField(blank=True, null=True)),
                ("original_filename", models.CharField(max_length=255)),
                ("video_path", models.CharField(max_length=500)),
                ("status", models.CharField(choices=[("uploaded", "Uploaded"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")], default="uploaded", max_length=20)),
                ("current_step", models.CharField(default="uploaded", max_length=64)),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="VideoCaptionResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("neutral_summary", models.TextField()),
                ("formal_caption", models.TextField()),
                ("sarcastic_caption", models.TextField()),
                ("humorous_tech_caption", models.TextField()),
                ("humorous_non_tech_caption", models.TextField()),
                ("raw_pipeline_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="result", to="video_jobs.videojob")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
