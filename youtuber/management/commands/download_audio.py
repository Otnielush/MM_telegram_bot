from django.core.management.base import BaseCommand
from youtuber.models import Lesson
import os
import unicodedata
from mmtelegrambot.settings import MEDIA_ROOT
import yt_dlp
import time
from datetime import datetime

class Command(BaseCommand):
    help = 'Download audio track from YouTube lesson'

    def handle(self, *args, **options):
        """
        Check for saved lessons without audio and download first of them
        """
        lessons_without_audio = Lesson.objects.filter(is_published=False, is_downloaded=False, skip=False)

        if len(lessons_without_audio) > 0:
            lesson = lessons_without_audio.last()
            youtube_id = lesson.youtube_id
            youtube_url = f'http://youtube.com/watch?v={youtube_id}'

            def format_selector(ctx):
                formats = ctx.get('formats')[::-1]

                for f in formats:
                    if f.get('ext') == 'm4a' and f.get('filesize_approx') and f['filesize_approx'] <= 50 * 1024 * 1024:
                        return [f]
                return None

            ydl_opts = {
                'format': format_selector,
                'outtmpl': os.path.join(MEDIA_ROOT, 'audio', '%(id)s.%(ext)s'),
                "quiet": True,
                "no_warnings": True
            }

            retry_count = 3
            for attempt in range(retry_count):
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info(youtube_url, download=False)
                        title = unicodedata.normalize('NFC', info_dict.get('title', ''))
                        duration = info_dict.get('duration', 0)
                        upload_date_str = info_dict.get('upload_date', '')
                        upload_date = (
                            datetime.strptime(upload_date_str, "%Y%m%d")
                            if upload_date_str 
                            else None
                        )

                        error_code = ydl.download(youtube_url)

                        # Saving results to DB
                        lesson.title = title
                        lesson.duration = duration
                        lesson.upload_date = upload_date
                        lesson.audio_file = f"audio/{youtube_id}.m4a"
                        lesson.is_downloaded = True
                        lesson.save()

                        print(f'Successfully downloaded audio for lesson {title}')
                        break
                except Exception as e:
                    if attempt < retry_count - 1:
                        time.sleep(5)  # Wait before retrying
                        print(f'Retrying download for video {youtube_id} (attempt {attempt + 1}/{retry_count})')
                    else:
                        lesson.error_count = lesson.error_count + 1
                        lesson.save()

                        print(f'Error while processing video {youtube_id}:\n {e}.\nError count: {lesson.error_count}.')
        else:
            self.stdout.write(
                self.style.SUCCESS('No lessons without audio')
            )
