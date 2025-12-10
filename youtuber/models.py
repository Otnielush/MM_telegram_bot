from django.db import models
from django.utils.functional import cached_property
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_delete
from django.core.files.storage import default_storage


class Lesson(models.Model):
    youtube_id = models.CharField(max_length=15, unique=True, verbose_name="YouTube ID")
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Title")
    duration = models.IntegerField(blank=True, null=True, verbose_name="Duration")
    upload_date = models.DateField(blank=True, null=True, verbose_name="Upload date")
    is_downloaded = models.BooleanField(default=False, verbose_name="Audio downloaded")
    audio_file = models.FileField(upload_to="audio/", blank=True, null=True, verbose_name="Audio File")
    subtitles_file = models.FileField(upload_to="audio/", blank=True, null=True, verbose_name="Subtitles File")
    summary = models.TextField(blank=True, null=True, verbose_name="Summary")
    is_published = models.BooleanField(default=False, verbose_name="Sent to Telegram")
    is_inserted_to_db = models.BooleanField(default=False, verbose_name="Inserted to Neo4j")
    time_added = models.DateTimeField(auto_now_add=True, verbose_name="Added to DB")
    skip = models.BooleanField(default=False, verbose_name="Can't download audio")
    error_count = models.IntegerField(default=0, verbose_name="Error count")

    @cached_property
    def audio_file_path(self):
        if self.audio_file:
            return self.audio_file.path
        return None

    @cached_property
    def subtitles_file_path(self):
        if self.subtitles_file:
            return self.subtitles_file.path

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

            if self.is_published and self.is_inserted_to_db:
                self.audio_file = ''
                self.subtitles_file = ''

        super(Lesson, self).save(*args, **kwargs)


@receiver(pre_save, sender=Lesson)
def delete_old_file(sender, instance, **kwargs):
    if not instance.pk:
        return False

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        old_audio = old_instance.audio_file
        old_subtitles = old_instance.subtitles_file
    except sender.DoesNotExist:
        return False

    new_audio = instance.audio_file
    new_subtitles = instance.subtitles_file

    if not old_audio == new_audio:
        if old_audio:
            default_storage.delete(old_audio.path)

    if not old_subtitles == new_subtitles:
        if old_subtitles:
            default_storage.delete(old_subtitles.path)
    return True


@receiver(post_delete, sender=Lesson)
def delete_file_from_disk(sender, instance, **kwargs):
    if instance.audio_file and instance.audio_file_path:
        default_storage.delete(instance.audio_file_path)

    if instance.subtitles_file and instance.subtitles_file_path:
        default_storage.delete(instance.subtitles_file_path)
