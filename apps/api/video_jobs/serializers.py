from rest_framework import serializers

from .models import VideoCaptionResult, VideoJob


class VideoUploadResponseSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    status = serializers.CharField()


class VideoJobStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoJob
        fields = (
            "id",
            "status",
            "current_step",
            "progress",
            "error_message",
            "original_filename",
            "created_at",
            "updated_at",
        )


class VideoCaptionResultSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source="job.id")

    class Meta:
        model = VideoCaptionResult
        fields = (
            "job_id",
            "neutral_summary",
            "formal_caption",
            "sarcastic_caption",
            "humorous_tech_caption",
            "humorous_non_tech_caption",
            "raw_pipeline_json",
            "created_at",
        )
