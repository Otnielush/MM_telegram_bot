from django.core.management.base import BaseCommand
from Similarity_search_audio.search_scripts import similarity_search


class Command(BaseCommand):
    help = 'Find answer in lessons base'

    def add_arguments(self, parser):
        parser.add_argument(
            'question',
            type=str,
            help='The question'
        )

    def handle(self, *args, **options):
        q = options['question']
        result = similarity_search(q)
        print(result)