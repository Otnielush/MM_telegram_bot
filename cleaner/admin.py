import csv
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget
from .models import Message, Question


class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'message_id',
        'text',
        'time_sent',
        'is_deleted',
        'error_count',
        'skip',
    )
    list_display_links = ('message_id',)
    list_filter = ('is_deleted',)
    search_fields = ('text', 'user_id', 'message_id')

class QuestionAdmin(admin.ModelAdmin):
    change_list_template = 'admin/changelist_with_export_btn.html'
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }
    list_display = (
        'message_id',
        'chat_id',
        'user_id',
        'text',
        'saved_at',
    )
    list_display_links = ('message_id',)
    search_fields = ('text', 'user_id', 'message_id')

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('export-csv/', self.admin_site.admin_view(self.export_csv))
        ]
        return my_urls + urls

    def export_csv(self, request):
        qs = Question.objects.all()

        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="questions.csv"'

        writer = csv.writer(response)
        writer.writerow(['sent_at', 'text', 'result'])

        for obj in qs:
            writer.writerow([obj.sent_at, obj.text, obj.result]) 

        return response


admin.site.register(Message, MessageAdmin)
admin.site.register(Question, QuestionAdmin)
