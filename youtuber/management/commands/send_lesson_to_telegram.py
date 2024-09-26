from django.core.management.base import BaseCommand
from youtuber.models import Lesson
from calendarer.models import Date
from datetime import date
import time
from mmtelegrambot import settings
from youtuber.utils import escape_str, send_api_request
from cleaner.models import Message
from telebot import TeleBot


bot = TeleBot(settings.TOKEN_BOT)


def seconds_to_hhmmss(seconds):
    seconds = int(seconds)
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

def make_youtube_link_msg(title, youtube_id, start_time=None, end_time=None):
    title = escape_str(title)
    if start_time is not None:
        period = f'⏱{seconds_to_hhmmss(start_time)}-{seconds_to_hhmmss(end_time)}' if end_time else f'⏱{seconds_to_hhmmss(start_time)}'
        return f'📺 [{title}](https://youtu.be/{youtube_id}?t={start_time})\n{escape_str(period)}'
    return f'📺 [{title}](https://youtu.be/{youtube_id})'


def save_video_message(video_message_response):
    message_id = video_message_response['result']['message_id']
    text = 'Need to delete this message with youtube link because audio message was not sent'

    message = Message(
        message_id=message_id,
        text=text
    )

    message.save()


class Command(BaseCommand):
    help = 'Send lesson to Telegram'

    def handle(self, *args, **options):
        """
        Send message to Telegram
        """
        unpublished_lessons = Lesson.objects.filter(is_published=False).filter(is_downloaded=True)

        if len(unpublished_lessons) > 0:
            lesson = unpublished_lessons.last()
            title = lesson.title
            performer = "Махон Меир"
            video_message_response = {}
            audio_message_response = {}

            try:
                youtube_message = make_youtube_link_msg(title, lesson.youtube_id)
                result = send_api_request("sendMessage", {
                    'chat_id': settings.MM_CHAT_ID,
                    'text': youtube_message,
                    'parse_mode': 'MarkdownV2',
                    'disable_notification': True,
                    'disable_web_page_preview': True
                })
                video_message_response = result.json()

                if video_message_response['ok']:
                    audio_message_response = bot.send_audio(
                        chat_id=settings.MM_CHAT_ID,
                        audio=lesson.audio_file,
                        duration=lesson.duration,
                        performer=performer,
                        title=title.strip(),
                        disable_notification=True
                    )

                    if audio_message_response.message_id:
                        lesson.is_published = True
                        lesson.save()

                        # Mark that today we have lessons
                        current_date = date.today()
                        current_date_record = Date.objects.filter(date=current_date)
                        if len(current_date_record) > 0 and not current_date_record[0].has_lessons:
                            current_date_record[0].has_lessons = True
                            current_date_record[0].save()

                        self.stdout.write(
                            self.style.SUCCESS(f'Audio lesson {lesson.title} sent to Telegram')
                        )
                    else:
                        # If audio message not sent - save id of video message to delete it later
                        save_video_message(video_message_response)

                        self.stdout.write(
                            self.style.SUCCESS(f'Audio lesson {lesson.title} not sent. Response: {audio_message_response}')
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Video lesson {lesson.title} not sent. Response: {video_message_response}')
                    )
            except Exception as e:
                print(e)
                # Handle case then video message sent, but audio message not
                if video_message_response.get('ok', False) and not audio_message_response.get('message_id', False):
                    save_video_message(video_message_response)

                    self.stdout.write(
                        self.style.SUCCESS(f'Audio lesson {lesson.title} not sent. Video message saved.')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Unknown Error while sending lesson {lesson.title}')
                    )
        else:
            self.stdout.write(
                self.style.SUCCESS('No unpublished lessons')
            )
