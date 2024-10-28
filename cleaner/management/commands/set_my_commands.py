from django.core.management.base import BaseCommand
from requests import post
from mmtelegrambot.settings import TELEGRAM_API_URL


class Command(BaseCommand):
    help = 'Set telegram bot commands menu'

    def handle(self, *args, **options):
        """
        Set telegram bot commands menu
        """
        commands = [
            {"command": "start", "description": "Информация о боте"},
            {"command": "help", "description": "Помощь"},
        ]

        url = f'{TELEGRAM_API_URL}setMyCommands'

        private_chat_payload = {
            "commands": commands,
            "scope": {"type": "all_private_chats"}
        }

        response = post(url, json=private_chat_payload)

        if response.status_code == 200:
            print("Commands set successfully.")
        else:
            print(f"Failed to set commands. Error: {response.text}")
