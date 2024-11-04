from django.core.management.base import BaseCommand
from requests import get
from re import findall

from mmtelegrambot import settings
from youtuber.models import Lesson
from django.db import IntegrityError

from youtuber.utils import send_api_request, escape_str


class Command(BaseCommand):
    help = 'Check for updates on YouTube Channel'

    def handle(self, *args, **options):
        """
        Check for updates
        """

        try:
            html = get('https://www.youtube.com/@MeirTvRu/videos')
            videos = findall('/watch\?v=.{11}', html.text)
            videos = [v[9:] for v in videos]  # cutting 'watch..'

            if len(videos) > 0:
                count_saved_videos = 0
                for video in videos:
                    lesson = Lesson(youtube_id=video)
                    try:
                        lesson.save()
                        count_saved_videos = count_saved_videos + 1
                    except IntegrityError:
                        continue

            self.stdout.write(
                self.style.SUCCESS('Saved "%s" videos' % count_saved_videos)
            )
            if count_saved_videos > 0:
                try:
                    message = escape_str(f'Added {count_saved_videos} new lessons')
                    send_api_request("sendMessage", {
                        'chat_id': settings.ADMIN_ID,
                        'text': message,
                        'parse_mode': 'MarkdownV2',
                        'disable_notification': True,
                        'disable_web_page_preview': True
                    })
                except Exception as e:
                    print(e)
        except:
            self.stdout.write(
                self.style.SUCCESS('Can`t open url youtube')
            )



