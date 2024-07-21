from django.db import models
from django.utils import timezone

class Message(models.Model):
    message_id = models.IntegerField(unique=True, verbose_name="Message ID")
    user_id = models.IntegerField(blank=True, null=True, verbose_name="User ID")
    time_sent = models.DateTimeField(default=timezone.now, verbose_name="Sent Date")
    text = models.TextField(blank=True, null=True, verbose_name="Text")
    time_added = models.DateTimeField(auto_now_add=True, verbose_name="Added to DB")
    is_deleted = models.BooleanField(default=False, verbose_name="Deleted?")
    error_count = models.IntegerField(default=0, verbose_name="Error count")
    skip = models.BooleanField(default=False, verbose_name="Skipped or Can't delete message")

    def __str__(self):
        return str(self.message_id)

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-time_added']

    def save(self, *args, **kwargs):
        if self.id:
            if self.error_count == 3:
                self.skip = True

        super(Message, self).save(*args, **kwargs)
