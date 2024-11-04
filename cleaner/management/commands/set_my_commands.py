from django.core.management.base import BaseCommand
from requests import post
from mmtelegrambot.settings import TELEGRAM_API_URL


class Command(BaseCommand):
    help = 'Set telegram bot commands menu'

    def handle(self, *args, **options):
        """
        Set telegram bot commands menu
        """
        private_commands = [
            {"command": "start", "description": "Информация о боте"},
            {"command": "help", "description": "Помощь"},
        ]
        group_commands = [
            {"command": "start", "description": "Информация о боте"},
        ]

        url = f'{TELEGRAM_API_URL}setMyCommands'

        private_chat_payload = {
            "commands": private_commands,
            "scope": {"type": "all_private_chats"}
        }
        group_chat_payload = {
            "commands": group_commands,
            "scope": {"type": "all_group_chats"}
        }

        response = post(url, json=private_chat_payload)
        if response.status_code == 200:
            print("Private commands set successfully.")
        else:
            print(f"Failed to set private commands. Error: {response.text}")

        response = post(url, json=group_chat_payload)
        if response.status_code == 200:
            print("Group commands set successfully.")
        else:
            print(f"Failed to set group commands. Error: {response.text}")
