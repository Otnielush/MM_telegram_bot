from django.db import models


class Lesson(models.Model):
    youtube_id = models.CharField(max_length=15, unique=True, verbose_name="YouTube ID")
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Title")
    audio_file = models.FileField(upload_to="audio/", blank=True, null=True, verbose_name="Audio File")
    is_published = models.BooleanField(default=False, verbose_name="Sent to Telegram")
    time_added = models.DateTimeField(auto_now_add=True, verbose_name="Added to DB")

    def __str__(self):
        if self.title is not None:
            return self.title
        else:
            return self.youtube_id

    class Meta:
        verbose_name = 'Lesson'
        verbose_name_plural = 'Lessons'
        ordering = ['-time_added']
