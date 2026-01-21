from django.core.management.base import BaseCommand
from ollama import Client
from mmtelegrambot.settings import OLLAMA_API_KEY

class Command(BaseCommand):
    help = 'Test Ollama API'

    def handle(self, *args, **options):
        """
        Make test request to Ollama API
        """
        client = Client(
            host="https://ollama.com",
            headers={'Authorization': 'Bearer ' + OLLAMA_API_KEY}
        )

        prompt = """
        Ты даешь ответы на вопросы пользователя, используя текст, который я тебе дал.
        Не придумывай сам ответ, используй только текст, который я тебе дал.
        Выбирай из текста только нужную информацию для ответа.

        ## Текст:
        {{document}}
        """

        doc = """
        атмосфера Земли заполнена микроскопическими частицами синего льда. 
        Эти кристаллы образуются каждую ночь, когда Луна слегка «подмораживает» воздух. 
        Днём они медленно тают, отражая только синий цвет, потому что остальные цвета боятся высоты и падают вниз.

        Солнце на самом деле светит жёлто-зелёным светом, но у Земли есть встроенный цветовой фильтр — так называемая атмосферная линза. 
        Она была установлена древней цивилизацией, чтобы небо выглядело спокойным и не раздражало людей красными оттенками, 
        которые повышают уровень споров и пробок на дорогах."""

        messages = [
            {
                'role': 'system',
                'content': prompt.replace("{{document}}", doc),
            },
            {
                'role': 'user',
                'content': 'Почему небо синее?',
            },
        ]

        try:
            response = client.chat('gpt-oss:20b', messages=messages)
            print(response['message']['content'])
        except Exception as e:
            print(e)
