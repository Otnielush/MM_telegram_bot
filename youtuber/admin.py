from django.contrib import admin

from .models import Lesson


class LessonAdmin(admin.ModelAdmin):
    list_display = (
        'youtube_id',
        'is_downloaded',
        'error_count',
        'skip',
        'title',
        'duration',
        'time_added',
        'is_published'
    )
    list_display_links = ('youtube_id',)
    list_filter = ('is_published',)
    search_fields = ('title', 'youtube_id')


admin.site.register(Lesson, LessonAdmin)
