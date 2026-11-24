from django.core.cache import cache

from mmtelegrambot.settings import ADMIN_ID
from youtuber.management.commands.send_lesson_to_telegram import make_youtube_link_msg
from youtuber.utils import send_api_request
from cleaner.models import Question
import logging

logger = logging.getLogger(__name__)

VECTOR_INDEX_NAME = "lessons_text_embd"

ADMIN_ALERT_CACHE_KEY = 'ai_admin_alert'
ADMIN_ALERT_INTERVAL = 3600  # don't alert the admin more often than once an hour


def notify_admin(text):
    """Send a plain-text alert to ADMIN_ID, at most once per ADMIN_ALERT_INTERVAL."""
    if not ADMIN_ID:
        return False
    try:
        if not cache.add(ADMIN_ALERT_CACHE_KEY, 1, timeout=ADMIN_ALERT_INTERVAL):
            return False
        send_api_request('sendMessage', {
            'chat_id': ADMIN_ID,
            'text': text,
            'disable_web_page_preview': True,
        })
        return True
    except Exception:
        logger.exception('Error notifying admin')
    return False


def save_result(message_id, user_id, chat_id, sent_at, text, results):
    # Always store the question, even when no answer was produced (result stays null).
    try:
        Question.objects.create(
            message_id = message_id,
            user_id = user_id,
            chat_id = chat_id,
            sent_at = sent_at,
            text = text,
            result = results or None
        )
        return True
    except Exception:
        logger.exception('Error saving question %s', message_id)

    return False

def make_message_with_youtube_links(result):
    if result:
        item_strings = []
        for item in result:
            title = item["lesson_name"]
            youtube_id = item["yt_id"]
            start_time = round(item["start"])
            end_time = round(item["end"]) if item["end"] > 0 else None
            upload_date = item["upload_date"]
            msg = make_youtube_link_msg(title, youtube_id, start_time, end_time, upload_date)
            item_strings.append(msg)
        return '\n\n'.join(item_strings)

    return None