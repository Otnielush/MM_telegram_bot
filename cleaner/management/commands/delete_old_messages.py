from django.core.management.base import BaseCommand
from cleaner.models import Message
from datetime import datetime, timedelta
from django.db.models import Q
from youtuber.utils import send_api_request
from mmtelegrambot.settings import MM_CHAT_ID


class Command(BaseCommand):
    help = 'Delete old messages from chat'

    def handle(self, *args, **options):
        """
        Delete old messages
        """
        count_deleted_messages = 0
        older_than_24_hours = datetime.now() - timedelta(hours=24)
        old_messages = Message.objects.filter(Q(is_deleted=False) & Q(time_added__lte=older_than_24_hours))

        if len(old_messages) > 0:
            for message in old_messages:
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
