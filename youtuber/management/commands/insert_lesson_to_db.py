from django.core.management.base import BaseCommand
from django.db.models import Q
from Similarity_search_audio.all_steps_add_lesson_to_base import insert_audio_to_graph_base
from youtuber.models import Lesson


class Command(BaseCommand):
    help = 'Insert audio lesson to graph base'

    def handle(self, *args, **options):
        lessons_to_insert = Lesson.objects.filter(
            is_downloaded=True,
            is_published=True,
            is_inserted_to_db=False
        ).exclude(Q(subtitles_file='') | Q(subtitles_file__isnull=True))

        if len(lessons_to_insert) > 0:
            lesson = lessons_to_insert.last()
            db_payload = {
                'yt_link': lesson.youtube_id,
                'upload_date': lesson.upload_date.strftime("%d-%m-%Y") if lesson.upload_date else '',
                'name': lesson.title
            }

            is_inserted = insert_audio_to_graph_base(file_path=lesson.subtitles_file.path, db_payload=db_payload)

            if is_inserted:
                lesson.is_inserted_to_db = True
                lesson.save()
                print(f'Lesson {lesson.youtube_id} inserted to graph base')
            else:
                print(f'Error inserting lesson {lesson.youtube_id} to graph base')
