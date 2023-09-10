from django.db import models


class Date(models.Model):
    date = models.DateField(auto_now_add=True, unique=True, verbose_name="Sent date")
    message_id = models.IntegerField(unique=True, verbose_name="Message ID")
    has_lessons = models.BooleanField(default=False, verbose_name="Has any Lesson?")
    is_deleted = models.BooleanField(default=False, verbose_name="Deleted?")

    def __str__(self):
        return str(self.message_id)

    class Meta:
        verbose_name = 'Date'
        verbose_name_plural = 'Dates'
        ordering = ['-date']
