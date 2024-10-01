from django.contrib import admin
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
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }
    list_display = (
        'message_id',
        'user_id',
        'text',
        'saved_at',
    )
    list_display_links = ('message_id',)
    search_fields = ('text', 'user_id', 'message_id')


admin.site.register(Message, MessageAdmin)
admin.site.register(Question, QuestionAdmin)
