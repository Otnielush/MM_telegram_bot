from django.core.management.base import BaseCommand
import requests
from mmtelegrambot.settings import TELEGRAM_API_URL, URL


class Command(BaseCommand):
    help = 'Set telegram bot webhook'

    def handle(self, *args, **options):
        """
        Set telegram bot webhook
        """
        response = requests.post(TELEGRAM_API_URL + "setWebhook?url=" + URL).json()

        self.stdout.write(
            self.style.SUCCESS(f"{response}")
        )
