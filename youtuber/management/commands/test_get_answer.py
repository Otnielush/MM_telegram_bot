from django.core.management.base import BaseCommand
from ollama import Client

from Similarity_search_audio.search_scripts import similarity_search
from mmtelegrambot.settings import OLLAMA_API_KEY

class Command(BaseCommand):
    help = 'Test get answer from Ollama API'

    def add_arguments(self, parser):
        parser.add_argument('question', type=str, help='The question to ask')

    def handle(self, *args, **options):
        """
        Test get answer from Ollama API
        """
        question = options['question']

        client = Client(
            host="https://ollama.com",
            headers={'Authorization': 'Bearer ' + OLLAMA_API_KEY}
        )

        prompt = """
        Ты даешь ответы на вопросы пользователя, используя текст, который я тебе дал.
        Не придумывай сам ответ, используй только текст, который я тебе дал.
        Выбирай из текста только нужную информацию для ответа.
        Если в тексте нет ответа, используй фразу: "В моей базе текстов по урокам не нашлась информация о ..."

        ## Текст:
        {{document}}
        """

        res = similarity_search(question, 3)
        doc = " ".join(res)
        print(doc)
        print("=============")

        messages = [
            {
                'role': 'system',
                'content': prompt.replace("{{document}}", doc),
            },
            {
                'role': 'user',
                'content': question,
            },
        ]

        try:
            response = client.chat('gpt-oss:20b', messages=messages, stream=False)
            print(response['message']['content'])
        except Exception as e:
            print(e)
