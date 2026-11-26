from django.conf import settings
from django.core.management.base import BaseCommand

from cleaner.ai import AIError, build_answer_messages, chat_completion
from Similarity_search_audio.search_scripts import similarity_search


class Command(BaseCommand):
    help = 'Test get answer from the AI model (OpenRouter); handy to check OPENROUTER_API_KEY'

    def add_arguments(self, parser):
        parser.add_argument('question', type=str, help='The question to ask')

    def handle(self, *args, **options):
        question = options['question']

        messages, doc = build_answer_messages(question, similarity_search(question, 5))
        self.stdout.write(doc)
        self.stdout.write('=============')
        self.stdout.write(f'Model: {settings.OPENROUTER_MODEL}')

        try:
            self.stdout.write(chat_completion(messages, temperature=0.2, max_tokens=2500))
        except AIError as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
