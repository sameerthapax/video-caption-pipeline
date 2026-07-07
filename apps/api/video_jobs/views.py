from pathlib import Path
import threading

from django.conf import settings
from django.http import Http404
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from pipeline.run_pipeline import run_video_pipeline
from .models import VideoJob
from .serializers import VideoCaptionResultSerializer, VideoJobStatusSerializer


class VideoUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        video_file = request.FILES.get("video")
        if video_file is None:
            return Response({"detail": "A video file is required."}, status=status.HTTP_400_BAD_REQUEST)

        videos_dir = Path(settings.MEDIA_ROOT) / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{video_file.name}"
        stored_path = videos_dir / stored_name

        counter = 1
        while stored_path.exists():
            stored_path = videos_dir / f"{stored_path.stem}-{counter}{stored_path.suffix}"
            counter += 1

        with stored_path.open("wb+") as destination:
            for chunk in video_file.chunks():
                destination.write(chunk)

        job = VideoJob.objects.create(
            original_filename=video_file.name,
            video_path=str(stored_path.relative_to(settings.MEDIA_ROOT)),
            status=VideoJob.Status.UPLOADED,
            current_step="uploaded",
            progress=5,
        )

        threading.Thread(target=run_video_pipeline, args=(str(job.id),), daemon=True).start()

        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)


class JobStatusView(APIView):
    def get(self, request, job_id):
        try:
            job = VideoJob.objects.get(pk=job_id)
        except VideoJob.DoesNotExist as exc:
            raise Http404("Job not found") from exc

        serializer = VideoJobStatusSerializer(job)
        return Response(serializer.data)


class JobResultView(APIView):
    def get(self, request, job_id):
        try:
            job = VideoJob.objects.select_related("result").get(pk=job_id)
        except VideoJob.DoesNotExist as exc:
            raise Http404("Job not found") from exc

        if job.status != VideoJob.Status.COMPLETED or not hasattr(job, "result"):
            return Response({"detail": "Result is not ready yet."}, status=status.HTTP_409_CONFLICT)

        serializer = VideoCaptionResultSerializer(job.result)
        return Response(serializer.data)
