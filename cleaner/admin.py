from django.contrib import admin
from .models import Message


class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'message_id',
        'text',
        'time_added',
        'is_deleted',
        'error_count',
        'skip',
    )
    list_display_links = ('message_id',)
    list_filter = ('is_deleted',)
    search_fields = ('text', 'user_id', 'message_id')


admin.site.register(Message, MessageAdmin)
