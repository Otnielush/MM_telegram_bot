from django.core.management.base import BaseCommand
from youtuber.models import Lesson
from calendarer.models import Date
from datetime import date
from mmtelegrambot import settings
from telebot import TeleBot
from youtuber.utils import escape_str

bot = TeleBot(settings.TOKEN_BOT)


def make_youtube_link_msg(title, youtube_id, hash_name):
    hash_name = escape_str(hash_name)
    title = escape_str(title)
    return f'📺 [{title}](https://youtu.be/{youtube_id})\n\n{hash_name}'


def make_hash_name(name):
    name = name.replace(" ", "")
    return f'#{name}'


class Command(BaseCommand):
    help = 'Send lesson to Telegram'

    def handle(self, *args, **options):
        """
        Send message to Telegram
        """
        unpublished_lessons = Lesson.objects.filter(is_published=False).filter(is_downloaded=True)

        if len(unpublished_lessons) > 0:
            lesson = unpublished_lessons.last()
            [name, title] = lesson.title.split('.', 1)

            try:
                hash_name = make_hash_name(name)
                youtube_message = make_youtube_link_msg(lesson.title, lesson.youtube_id, hash_name)
                result = bot.send_message(
                    settings.MM_CHAT_ID,
                    youtube_message,
                    parse_mode='MarkdownV2',
                    disable_notification=True,
                    disable_web_page_preview=True
                )

                try:
                    audio_message = bot.send_audio(
                        chat_id=settings.MM_CHAT_ID,
                        audio=lesson.audio_file,
                        duration=lesson.duration,
                        performer=name.strip(),
                        title=title.strip(),
                        disable_notification=True
                    )

                    if audio_message.message_id:
                        lesson.is_published = True
                        lesson.save()

                        current_date = date.today()
                        current_date_record = Date.objects.filter(date=current_date)
                        if len(current_date_record) > 0 and not current_date_record[0].has_lessons:
                            current_date_record[0].has_lessons = True
                            current_date_record[0].save()

                        self.stdout.write(
                            self.style.SUCCESS(f'Audio lesson {lesson.title} sent to Telegram')
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f'Error while sending audio lesson {lesson.title}. You need to delete '
                                               f'sent video message: {result.message_id}')
                        )
                except:
                    self.stdout.write(
                        self.style.SUCCESS(f'Unknown Error while sending audio lesson {lesson.title}: {audio_message.json()}. You need to delete sent video message: {result.message_id}')
                    )
            except:
                self.stdout.write(
                    self.style.SUCCESS(f'Error while sending lesson {lesson.title}')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('No unpublished lessons')
            )
