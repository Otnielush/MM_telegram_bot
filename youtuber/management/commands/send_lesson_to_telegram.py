from django.core.management.base import BaseCommand
from youtuber.models import Lesson
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
                bot.send_message(
                    settings.MM_CHAT_ID,
                    youtube_message,
                    parse_mode='MarkdownV2',
                    disable_notification=True
                )

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

                    self.stdout.write(
                        self.style.SUCCESS(f'Audio lesson {lesson.title} sent to Telegram')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Error while sending audio lesson {lesson.title}')
                    )
            except:
                self.stdout.write(
                    self.style.SUCCESS(f'Error while sending lesson {lesson.title}')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('No unpublished lessons')
            )
