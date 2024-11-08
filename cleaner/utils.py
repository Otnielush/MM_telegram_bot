from youtuber.management.commands.send_lesson_to_telegram import make_youtube_link_msg
from cleaner.models import Question

VECTOR_INDEX_NAME = "lessons_text_embd"


def save_result(message_id, user_id, chat_id, sent_at, text, result):
    if len(result):
        results = []
        for item in result:
            results.append({
                "name": item["lesson_name"],
                "yt_id": item["youtube_id"],
                "part": item["part"],
                "score": item["search_score"]
            })
        try:
            Question.objects.create(
                message_id = message_id,
                user_id = user_id,
                chat_id = chat_id,
                sent_at = sent_at,
                text = text,
                result = results
            )
            return True
        except Exception as e:
            print(e)

    return False

def make_result_message(result):
    if len(result):
        item_strings = []
        for item in result:
            title = item["lesson_name"]
            youtube_id = item["youtube_id"]
            start_time = round(item["start"])
            end_time = round(item["end"]) if item["end"] > 0 else None
            upload_date = item["upload_date"]
            msg = make_youtube_link_msg(title, youtube_id, start_time, end_time, upload_date)
            item_strings.append(msg)
        return '\n\n'.join(item_strings)

    return "К сожалению, ничего не найдено"