from django.core.management.base import BaseCommand
from requests import get
from re import findall
from youtuber.models import Lesson
from django.db import IntegrityError


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
                        print("Video already saved!")

            self.stdout.write(
                self.style.SUCCESS('Saved "%s" videos' % count_saved_videos)
            )
        except:
            self.stdout.write(
                self.style.SUCCESS('Can`t open url youtube')
            )



