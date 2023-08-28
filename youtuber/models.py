from django.db import models
from django.utils.functional import cached_property
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_delete
from django.core.files.storage import default_storage


class Lesson(models.Model):
    youtube_id = models.CharField(max_length=15, unique=True, verbose_name="YouTube ID")
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Title")
    audio_file = models.FileField(upload_to="audio/", blank=True, null=True, verbose_name="Audio File")
    is_published = models.BooleanField(default=False, verbose_name="Sent to Telegram")
    time_added = models.DateTimeField(auto_now_add=True, verbose_name="Added to DB")
    skip = models.BooleanField(default=False, verbose_name="Can't download audio")
    error_count = models.IntegerField(default=0, verbose_name="Error count")

    @cached_property
    def audio_file_path(self):
        return self.audio_file.path

    def __str__(self):
        if self.title is not None:
            return self.title
        else:
            return self.youtube_id

    class Meta:
        verbose_name = 'Lesson'
        verbose_name_plural = 'Lessons'
        ordering = ['-time_added']

    def save(self, *args, **kwargs):
        if self.id:
            if self.error_count == 3:
                self.skip = True

            if self.is_published is True:
                self.audio_file = ''

        super(Lesson, self).save(*args, **kwargs)


@receiver(pre_save, sender=Lesson)
def delete_old_file(sender, instance, **kwargs):
    if not instance.pk:
        return False

    try:
        old_file = sender.objects.get(pk=instance.pk).audio_file
    except sender.DoesNotExist:
        return False

    new_file = instance.audio_file

    if not old_file == new_file:
        if old_file:
            default_storage.delete(old_file.path)
    return True


@receiver(post_delete, sender=Lesson)
def delete_file_from_disk(sender, instance, **kwargs):
    if instance.audio_file_path:
        default_storage.delete(instance.audio_file_path)
