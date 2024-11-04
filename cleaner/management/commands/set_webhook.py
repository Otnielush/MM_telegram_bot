from django.core.management.base import BaseCommand
from youtuber.utils import send_api_request
from mmtelegrambot.settings import TELEGRAM_API_URL, URL, WEBHOOK_SECRET_TOKEN


class Command(BaseCommand):
    help = 'Set telegram bot webhook'

    def handle(self, *args, **options):
        """
        Set telegram bot webhook
        """
        response = send_api_request('setWebhook', {
            'url': URL,
            'secret_token': WEBHOOK_SECRET_TOKEN,
            'allowed_updates': ["message"]
        })

        self.stdout.write(
            self.style.SUCCESS(f"{response.json()}")
        )
