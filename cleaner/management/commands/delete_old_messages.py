from django.core.management.base import BaseCommand
from cleaner.models import Message
from django.utils import timezone
from datetime import timedelta
from youtuber.utils import send_api_request
from mmtelegrambot.settings import MM_CHAT_ID


class Command(BaseCommand):
    help = 'Delete old messages from chat'

    def handle(self, *args, **options):
        """
        Delete old messages
        """
        count_deleted_messages = 0
        older_than_24_hours = timezone.now() - timedelta(hours=24)
        old_messages = Message.objects.filter(
            is_deleted=False,
            skip=False,
            time_sent__lte=older_than_24_hours
        )

        if len(old_messages) > 0:
            for message in old_messages:
                try:
                    is_deleted = send_api_request('deleteMessage', {
                        'chat_id': MM_CHAT_ID,
                        'message_id': message.message_id
                    })
                    result = is_deleted.json()
                    if result.get('ok', None):
                        message.is_deleted = True
                        message.save()

                        count_deleted_messages = count_deleted_messages + 1
                    else:
                        message.error_count = message.error_count + 1
                        message.save()

                        print(f"Error while deleting message {message.message_id}, result: {result}")

                except Exception as e:
                    message.error_count = message.error_count + 1
                    message.save()

                    print(f"Error while deleting message {message.message_id}: \n {e}")

        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {count_deleted_messages} messages')
        )
