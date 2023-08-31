from django.core.management.base import BaseCommand
from datetime import date
from youtuber.utils import send_api_request
from mmtelegrambot.settings import MM_CHAT_ID
from calendarer.models import Date


class Command(BaseCommand):
    help = 'Delete date message if there were no lessons in that day'

    def handle(self, *args, **options):
        """
        Delete date message if there were no lessons in that day
        """
        current_date = date.today()

        past_dates = Date.objects\
            .filter(date__lt=current_date)\
            .filter(has_lessons=False)\
            .filter(is_deleted=False)

        if len(past_dates) > 0:
            count_deleted_messages = 0
            for message in past_dates:
                try:
                    is_deleted = send_api_request('deleteMessage', {
                        'chat_id': MM_CHAT_ID,
                        'message_id': message.message_id
                    })
                    if is_deleted:
                        message.is_deleted = True
                        message.save()

                    count_deleted_messages = count_deleted_messages + 1
                except:
                    print(f"Error while deleting message {message.message_id}")

            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {count_deleted_messages} messages')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Nothing to delete')
            )
