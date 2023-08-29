from django.core.management.base import BaseCommand
from youtuber.models import Lesson
from pytube import YouTube
from pytube.exceptions import VideoUnavailable
import os
from mmtelegrambot.settings import MEDIA_ROOT


class Command(BaseCommand):
    help = 'Download audio track from YouTube lesson'

    def handle(self, *args, **options):
        """
        Check for saved lessons without audio and download first of them
        """
        lessons_without_audio = Lesson.objects.filter(is_published=False).filter(is_downloaded=False).filter(skip=False)

        if len(lessons_without_audio) > 0:
            lesson = lessons_without_audio.last()

            try:
                yt = YouTube(f'http://youtube.com/watch?v={lesson.youtube_id}')
                title = yt.title
                duration = yt.length
                streams = yt.streams.filter(mime_type="audio/mp4")

                # Find stream with highest file size, but less than 50Mb due to Telegram limitations
                filesizes = [float(item.filesize_mb) for item in streams]
                max_number = max([num for num in filesizes if num < 50], default=None)
                if max_number is not None:
                    index = filesizes.index(max_number)
                    stream = streams[index]

                    stream.download(
                        output_path=os.path.join(MEDIA_ROOT, 'audio'),
                        filename=f'{title}.m4a'
                    )

                    # Saving results to DB
                    lesson.title = title
                    lesson.duration = duration
                    lesson.audio_file = f'audio/{title}.m4a'
                    lesson.is_downloaded = True
                    lesson.save()

                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully download audio for lesson {title}')
                    )
                else:
                    lesson.title = title
                    lesson.duration = duration
                    lesson.skip = True
                    lesson.save()

                    self.stdout.write(
                        self.style.SUCCESS(f'Filesize of {title} is higher then 50Mb, skipping.')
                    )
            except VideoUnavailable:
                lesson.skip = True
                lesson.save()

                self.stdout.write(
                    self.style.SUCCESS(f'Video {lesson.youtube_id} is unavaialable, skipping.')
                )
            except:
                lesson.error_count = lesson.error_count + 1
                lesson.save()

                self.stdout.write(
                    self.style.SUCCESS(f'Unknown error while processing video {lesson.youtube_id}, error count: {lesson.error_count}.')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('No lessons without audio')
            )
