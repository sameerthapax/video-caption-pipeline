from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import VideoCaptionResult, VideoJob


def immediate_pipeline(job_id: str) -> None:
    job = VideoJob.objects.get(pk=job_id)
    job.status = VideoJob.Status.COMPLETED
    job.current_step = "completed"
    job.progress = 100
    job.save(update_fields=["status", "current_step", "progress", "updated_at"])
    VideoCaptionResult.objects.create(
        job=job,
        neutral_summary="A test summary.",
        formal_caption="A formal caption.",
        sarcastic_caption="A sarcastic caption.",
        humorous_tech_caption="A humorous tech caption.",
        humorous_non_tech_caption="A humorous non-tech caption.",
        raw_pipeline_json={"source": "test"},
    )


class VideoJobsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("video_jobs.views.run_video_pipeline", side_effect=immediate_pipeline)
    @patch("video_jobs.views.threading.Thread")
    def test_upload_creates_job_and_result(self, thread_cls, _pipeline_mock):
        thread_instance = thread_cls.return_value
        thread_instance.start.side_effect = lambda: immediate_pipeline(
            thread_cls.call_args.kwargs["args"][0]
        )

        upload = SimpleUploadedFile("clip.mp4", b"fake-video-bytes", content_type="video/mp4")
        response = self.client.post("/api/videos/upload/", {"video": upload}, format="multipart")

        self.assertEqual(response.status_code, 202)
        job = VideoJob.objects.get(pk=response.data["job_id"])
        self.assertTrue((Path(settings.MEDIA_ROOT) / "videos" / "clip.mp4").exists())
        self.assertEqual(job.original_filename, "clip.mp4")

        status_response = self.client.get(f"/api/jobs/{job.id}/status/")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data["status"], "completed")

        result_response = self.client.get(f"/api/jobs/{job.id}/result/")
        self.assertEqual(result_response.status_code, 200)
        self.assertEqual(result_response.data["formal_caption"], "A formal caption.")

    def test_result_before_completion_returns_conflict(self):
        job = VideoJob.objects.create(
            original_filename="pending.mp4",
            video_path="videos/pending.mp4",
            status=VideoJob.Status.PROCESSING,
            current_step="extracting_frames",
            progress=35,
        )

        response = self.client.get(f"/api/jobs/{job.id}/result/")
        self.assertEqual(response.status_code, 409)
