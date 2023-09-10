from django.contrib import admin
from .models import Date


class DateAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'message_id',
        'has_lessons',
        'is_deleted',
    )
    list_display_links = ('date',)
    list_filter = ('is_deleted',)
    search_fields = ('date', 'message_id')


admin.site.register(Date, DateAdmin)