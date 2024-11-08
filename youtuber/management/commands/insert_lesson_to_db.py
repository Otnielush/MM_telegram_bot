from django.core.management.base import BaseCommand
from Similarity_search_audio.all_steps_add_lesson_to_base import insert_audio_to_graph_base
from youtuber.models import Lesson


class Command(BaseCommand):
    help = 'Insert audio lesson to graph base'

    def handle(self, *args, **options):
        lessons_to_insert = Lesson.objects.filter(is_downloaded=True, is_inserted_to_db=False)

        if len(lessons_to_insert) > 0:
            lesson = lessons_to_insert.last()
            db_payload = {
                'yt_link': lesson.youtube_id,
                'upload_date': lesson.upload_date.strftime("%d-%m-%Y") if lesson.upload_date else '',
                'name': lesson.title
            }
            is_inserted = insert_audio_to_graph_base(filepath=lesson.audio_file.path, db_payload=db_payload)

            if is_inserted:
                lesson.is_inserted_to_db = True
                lesson.save()