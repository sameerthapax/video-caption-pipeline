from django.contrib import admin

from .models import VideoCaptionResult, VideoJob


@admin.register(VideoJob)
class VideoJobAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "status", "current_step", "progress", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "original_filename")


@admin.register(VideoCaptionResult)
class VideoCaptionResultAdmin(admin.ModelAdmin):
    list_display = ("job", "created_at")
