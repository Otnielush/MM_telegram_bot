import csv
from django.contrib import admin
from django.db.models import QuerySet
from django.urls import path
from django.http import HttpResponse

from .models import Lesson


class LessonAdmin(admin.ModelAdmin):
    change_list_template = 'admin/changelist_with_export_btn.html'
    list_display = (
        'youtube_id',
        'is_downloaded',
        'error_count',
        'skip',
        'title',
        'duration',
        'summary',
        'time_added',
        'is_published',
        'is_inserted_to_db'
    )
    list_display_links = ('youtube_id',)
    list_filter = ('is_published', 'is_inserted_to_db')
    search_fields = ('title', 'youtube_id')
    actions = ['reset_download_errors', 'mark_inserted_to_db']

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

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('export-csv/', self.admin_site.admin_view(self.export_csv))
        ]
        return my_urls + urls

    def export_csv(self, request):
        qs = Lesson.objects.all()

        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="lessons.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'youtube_id', 
            'title', 
            'duration', 
            'upload_date', 
            'sent_to_telegram', 
            'inserted_to_neo4j'
        ])

        for obj in qs:
            writer.writerow([
                obj.youtube_id, 
                obj.title, 
                obj.duration, 
                obj.upload_date, 
                obj.is_published, 
                obj.is_inserted_to_db
            ]) 

        return response



admin.site.register(Lesson, LessonAdmin)
