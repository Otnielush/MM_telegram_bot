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
# Instruction:
Ты даешь ответы на вопросы пользователя, используя текст, который я тебе дал.
Не придумывай сам ответ, используй только Текст, который я тебе дал.
Выбирай из текста только нужную информацию для ответа.
Если в тексте нет ответа, используй фразу: "В моей базе текстов по урокам не нашлась информация о ..."
---

# Текст:
{{document}}
"""

        similar_texts = similarity_search(question, 5)
        doc = []
        for i, res in enumerate(similar_texts):
            doc_sep = (f"## Source #{i + 1}\nLesson name: {res['lesson_name']} from {res['upload_date']}\n"
                       f"Part # {res['part']}\nText:\n{res['text']}")
            doc.append(doc_sep)
        doc = "\n---\n".join(doc)
        print(doc)
        print("=============")

        messages = [
            {
                'role': 'system',
                'content': prompt.replace("{{document}}", doc),
            },
            {
                'role': 'user',
                'content': question + "\n\n# Output Guidelines:\nНапиши ответ в соответствии с Instruction.",
            },
        ]

        try:
            response = client.chat('gpt-oss:20b-cloud', messages=messages, stream=False)
            print(response['message']['content'])
        except Exception as e:
            print(e)
