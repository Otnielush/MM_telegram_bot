from django.db import models


class Message(models.Model):
    message_id = models.IntegerField(unique=True, verbose_name="Message ID")
    user_id = models.IntegerField(blank=True, null=True, verbose_name="User ID")
    date = models.IntegerField(blank=True, null=True, verbose_name="Sent date")
    text = models.TextField(blank=True, null=True, verbose_name="Text")
    time_added = models.DateTimeField(auto_now_add=True, verbose_name="Added to DB")
    is_deleted = models.BooleanField(default=False, verbose_name="Deleted?")

    def __str__(self):
        return str(self.message_id)

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-time_added']
