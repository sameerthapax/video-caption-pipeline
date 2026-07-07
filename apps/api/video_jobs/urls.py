from django.urls import path

from .views import JobResultView, JobStatusView, VideoUploadView

urlpatterns = [
    path("videos/upload/", VideoUploadView.as_view(), name="video-upload"),
    path("jobs/<uuid:job_id>/status/", JobStatusView.as_view(), name="job-status"),
    path("jobs/<uuid:job_id>/result/", JobResultView.as_view(), name="job-result"),
]
