from django.contrib import admin
from django.db.models import QuerySet

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
        'is_published',
        'is_inserted_to_db'
    )
    list_display_links = ('youtube_id',)
    list_filter = ('is_published', 'is_inserted_to_db')
    search_fields = ('title', 'youtube_id')
    actions = ['reset_download_errors']

    @admin.action(description="Reset download errors")
    def reset_download_errors(self, request, qs:QuerySet):
        count = 0
        for lesson in qs:
            lesson.error_count = 0
            lesson.skip = False
            lesson.save()
            count += 1

        self.message_user(request, f'{count} lessons updated successfully')
    
    @admin.action(description="Mark as inserted to Neo4j")
    def mark_inserted_to_db(self, request, qs:QuerySet):
        count = 0
        for lesson in qs:
            lesson.is_inserted_to_db = True
            lesson.save()
            count += 1

        self.message_user(request, f'{count} lessons updated successfully')



admin.site.register(Lesson, LessonAdmin)
