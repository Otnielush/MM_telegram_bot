from django.core.management.base import BaseCommand
from django.db.models import Q
import re
import html
from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from youtuber.models import Lesson
from mmtelegrambot.settings import OPENAI_KEY

MODEL = "gpt-4o-mini"

PROMPT = (
    'Сделай краткое резюме этого текста, на 3–4 предложения. '
    'Начни со слов "В этом уроке рассказывается ..."'
)

def clean_vtt_text(vtt_text: str) -> str:
    # Decode HTML entities (e.g. &gt; → >)
    vtt_text = html.unescape(vtt_text)

    # Remove WEBVTT header
    vtt_text = re.sub(r'^WEBVTT.*?\n', '', vtt_text,
                      flags=re.IGNORECASE | re.DOTALL)

    # Remove timestamps
    vtt_text = re.sub(
        r'\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}.*',
        '',
        vtt_text
    )

    # Remove VTT markup tags (<c>, <b>, etc.)
    vtt_text = re.sub(r'<[^>]+>', '', vtt_text)

    # Remove cue IDs
    vtt_text = re.sub(r'^\s*\w+\s*$', '', vtt_text, flags=re.MULTILINE)

    # Get non-empty lines
    lines = [line.strip() for line in vtt_text.splitlines() if line.strip()]

    # Remove duplicates
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    # return one line
    return " ".join(unique_lines)

def clean_vtt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    cleaned = clean_vtt_text(raw)

    return cleaned

class Command(BaseCommand):
    help = 'Make summary of lesson'

    def handle(self, *args, **options):
        """
        Make a summary of a lesson
        """
        lessons_without_summary = Lesson.objects.filter(
            is_published=False,
            is_downloaded=True
        ).filter(Q(summary__isnull=True) | Q(summary=''))

        if len(lessons_without_summary) > 0:
            lesson = lessons_without_summary.last()

            subtitle_file_path = lesson.subtitles_file_path

            if subtitle_file_path is None:
                lesson.summary = 'skipped'
                lesson.save()
                print(f'Summary for lesson {lesson.title} is skipped, because there is no subtitles.')
                return

            text = clean_vtt(subtitle_file_path)

            client = OpenAI(api_key=OPENAI_KEY)

            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content=PROMPT),
                    ChatCompletionUserMessageParam(role="user", content=text),
                ]
            )

            summary = response.choices[0].message.content.strip()

            lesson.summary = summary
            lesson.save()
            print(f'Summary for lesson {lesson.title} is saved successfully.')
        else:
            self.stdout.write(
                self.style.SUCCESS('No lessons without summary')
            )