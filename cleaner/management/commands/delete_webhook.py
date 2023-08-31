from django.core.management.base import BaseCommand
from youtuber.utils import send_api_request


class Command(BaseCommand):
    help = 'Delete telegram bot webhook'

    def handle(self, *args, **options):
        """
        Delete telegram bot webhook
        """
        response = send_api_request('deleteWebhook', {
            'drop_pending_updates': True
        })

        self.stdout.write(
            self.style.SUCCESS(f"{response}")
        )
