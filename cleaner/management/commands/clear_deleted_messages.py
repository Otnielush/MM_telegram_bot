from django.core.management.base import BaseCommand
from cleaner.models import Message


class Command(BaseCommand):
    help = 'Clear from DB successfully deleted messages'

    def handle(self, *args, **options):
        """
        Clear from DB successfully deleted messages
        """
        deleted_messages = Message.objects.filter(is_deleted=True)
        count_messages_to_clear = len(deleted_messages)

        if count_messages_to_clear > 0:
            try:
                deleted_messages.delete()

                self.stdout.write(
                    self.style.SUCCESS(f'Successfully cleared {count_messages_to_clear} messages')
                )
            except:
                self.stdout.write(
                    self.style.SUCCESS(f'Error while clearing deleted messages')
                )
