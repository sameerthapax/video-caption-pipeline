import uuid

from django.db import models


class VideoJob(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    video_path = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    current_step = models.CharField(max_length=64, default="uploaded")
    progress = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class VideoCaptionResult(models.Model):
    job = models.OneToOneField(VideoJob, on_delete=models.CASCADE, related_name="result")
    neutral_summary = models.TextField()
    formal_caption = models.TextField()
    sarcastic_caption = models.TextField()
    humorous_tech_caption = models.TextField()
    humorous_non_tech_caption = models.TextField()
    raw_pipeline_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
