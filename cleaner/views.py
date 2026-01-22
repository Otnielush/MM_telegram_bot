import json
from time import time
import textwrap

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.utils import timezone
from mmtelegrambot.settings import MM_CHAT_ID, WEBHOOK_SECRET_TOKEN, BOT_MENTION, OLLAMA_API_KEY
from .models import Message
from youtuber.utils import escape_str, send_api_request
from .utils import make_result_message, save_result
from Similarity_search_audio.search_scripts import similarity_search
from cleaner.spam_detector import spam_detector
from ollama import Client
import logging

logger = logging.getLogger(__name__)

SHORT_TERM_LIMIT = 1       # maximum requests every 30 seconds
SHORT_TERM_WINDOW = 30     # 30-second window

DAILY_LIMIT = 20           # maximum requests per day
DAILY_WINDOW = 86400       # 24-hour window (in seconds)

ollama_client = Client(
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

def is_rate_limited(user_id):
    """
    Check if the user is rate-limited.
    Returns a tuple of (rate_limited, message).
    """
    current_time = int(time())

    short_term_cache_key = f"rate_limit_short:{user_id}"
    last_request_time = cache.get(short_term_cache_key)

    if last_request_time and current_time - last_request_time < SHORT_TERM_WINDOW:
        time_remaining = SHORT_TERM_WINDOW - (current_time - last_request_time)
        return True, f"Вы задаете вопросы слишком часто, попробуйте через {time_remaining} сек"

    daily_cache_key = f"rate_limit_daily:{user_id}"
    request_count = cache.get(daily_cache_key, 0)

    if request_count >= DAILY_LIMIT:
        return True, "Вы превысили суточный лимит в 20 вопросов. Пожалуйста, повторите вопрос завтра"

    cache.set(short_term_cache_key, current_time, timeout=SHORT_TERM_WINDOW)
    cache.set(daily_cache_key, request_count + 1, timeout=DAILY_WINDOW)

    return False, None


def get_date_time_sent(update):
    date = update['message']['date']

    # Convert Unix timestamp to naive datetime in UTC
    time_sent = datetime.utcfromtimestamp(date)

    # Make the datetime aware in the local timezone
    time_sent = timezone.make_aware(time_sent)

    return time_sent

def get_answer(question):
    similar_texts = similarity_search(question, 5)
    doc = []
    for i, res in enumerate(similar_texts):
        doc_sep = (f"## Source #{i + 1}\nLesson name: {res['lesson_name']} from {res['upload_date']}\n"
                   f"Part # {res['part']}\nText:\n{res['text']}")
        doc.append(doc_sep)
    doc = "\n---\n".join(doc)

    messages = [
        {
            'role': 'system',
            'content': prompt.replace("{{document}}", doc),
        },
        {
            'role': 'user',
            'content': question + "\n\n# Output Guidelines:\nНапиши ответ в соответствии с Instruction.",  # повторить задании на случай длинного текста, чтоб не потерялся
        },
    ]

    try:
        response = ollama_client.chat('gpt-oss:20b-cloud', messages=messages, stream=False,
                                      options={'temperature': 0.2, "num_predict": 1000, 'num_ctx': 8192})
        answer = response['message']['content']
        return answer, doc
    except Exception as e:
        logger.error('Error getting Ollama response for question "%s": %s', question, e)
        return None, doc

def handle_search_command(update):
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    message_id = update['message']['message_id']

    rate_limited, limit_message = is_rate_limited(user_id)
    if rate_limited:
        try:
            send_api_request('sendMessage', {
                'chat_id': chat_id,
                'text': escape_str(limit_message),
                'parse_mode': 'MarkdownV2',
                'disable_notification': True,
                'reply_to_message_id': message_id
            })
        except Exception as e:
            print(e)

        return JsonResponse({'error': 'Rate limit exceeded, user notified.'}, status=200)

    sent_at = get_date_time_sent(update)
    text = update['message'].get('text')

    is_debug = False
    if "#debug" in text:
        text = text.replace("#debug", "").strip()
        is_debug = True

    question = text.strip()
    try:
        answer, doc = get_answer(question)
        save_result(message_id, user_id, chat_id, sent_at, question, answer)
        #message = make_result_message(answer)
        response_text = answer or "Произошла ошибка, пожалуйста, повторите вопрос позже"
        response_text = response_text.replace('**', '*')
        send_api_request("sendMessage", {
            'chat_id': chat_id,
            'text': response_text,
            'parse_mode': 'Markdown',
            'disable_notification': True,
            'disable_web_page_preview': True,
            'reply_to_message_id': message_id
        })
        if is_debug:
            # Handle large text in `doc` by splitting it into chunks
            max_length = 4000  # Slightly less than Telegram limit to account for other data/formatting
            chunks = [doc[i:i + max_length] for i in range(0, len(doc), max_length)]

            # Send each chunk as a separate message
            for chunk in chunks:
                send_api_request("sendMessage", {
                    'chat_id': chat_id,
                    'text': chunk,
                    'parse_mode': 'Markdown',
                    'disable_notification': True,
                    'disable_web_page_preview': True,
                    'reply_to_message_id': message_id
                })
    except Exception as e:
        print(e)
        return HttpResponseBadRequest('Bad Request')

def handle_start_command(chat_id, is_group=False):
    message = f'''
    Просто отправьте ваш вопрос в личный чат с ботом\.
    {BOT_MENTION} сгенерирует ответ на основе содержимого уроков YouTube\-канала Махон Меир\.
    Чем подробнее вы сформулируете вопрос, тем более точным будет ответ\.
    Обратите внимание \- *каждое* ваше сообщение бот воспринимает как *новый* вопрос\.
    Есть ограничения: 20 вопросов в сутки, и не чаще 1 вопроса в 30 секунд\.
    '''
    message = textwrap.dedent(message)

    try:
        msg_new = send_api_request("sendMessage", {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'MarkdownV2',
            'disable_notification': True,
            'disable_web_page_preview': True
        })

        if is_group:
            response = msg_new.json()
            if response['ok']:
                message_id = response['result']['message_id']
                text = response['result']['text']

                message = Message(
                    message_id=message_id,
                    text=text
                )
                message.save()

        return HttpResponse('ok')
    except Exception as e:
        print(e)
        return HttpResponseBadRequest('Bad Request')

def handle_help_command(chat_id):
    message = '''
    ✅ Чтобы задать вопрос, просто отправьте сообщение в свободной форме.
    ⚠️ В сутки можно задать 20 вопросов, не чаще 1 вопроса в 30 секунд.
    ✍️ Будем рады вашим идеям и замечаниям - пишите в группу Махон Меир: @machonmeir
    '''
    message = textwrap.dedent(message)

    try:
        send_api_request("sendMessage", {
            'chat_id': chat_id,
            'text': escape_str(message),
            'parse_mode': 'MarkdownV2',
            'disable_notification': True,
            'disable_web_page_preview': True
        })
        return HttpResponse('ok')
    except Exception as e:
        print(e)
        return HttpResponseBadRequest('Bad Request')

@csrf_exempt
def telegram_bot(request):
    if request.method == 'POST':
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_token == WEBHOOK_SECRET_TOKEN:
            update = json.loads(request.body.decode('utf-8'))
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                message_id = update['message']['message_id']

                if str(chat_id) == MM_CHAT_ID:
                    if 'new_chat_member' in update['message']:
                        is_deleted = send_api_request('deleteMessage', {
                            'chat_id': chat_id,
                            'message_id': message_id
                        })
                        if is_deleted:
                            first_name = update['message']['new_chat_member'].get('first_name')
                            username = update['message']['new_chat_member'].get('username')
                            name = first_name if first_name is not None else username
                            name = escape_str(name)

                            msg_new = send_api_request('sendMessage', {
                                'chat_id': chat_id,
                                'text': f'Приветствуем нового участника _{name}_ 👋',
                                'parse_mode': 'MarkdownV2'
                            })

                            response = msg_new.json()
                            if response['ok']:
                                message_id = response['result']['message_id']
                                text = response['result']['text']

                                message = Message(
                                    message_id=message_id,
                                    text=text
                                )

                                try:
                                    message.save()
                                    return HttpResponse('ok')
                                except:
                                    return HttpResponseBadRequest('Bad Request')
                    elif 'pinned_message' in update['message']:
                        pinned_message_id = update['message']['pinned_message']['message_id']
                        try:
                            message = Message.objects.get(message_id=pinned_message_id)
                            message.skip = True
                            message.save()
                        except Exception as e:
                            print(f'Error while skipping pinned message {message_id}:\n {e}')
                    else:
                        user_id = update['message']['from']['id']
                        text = update['message'].get('text')
                        time_sent = get_date_time_sent(update)

                        res = spam_detector.predict(text)
                        try:
                            prob_spam = float(res.get("prob_spam", 0))
                        except (TypeError, ValueError):
                            prob_spam = 0
                        is_spam = prob_spam > 0.7
                        is_deleted = False
                        if is_spam:
                            try:
                                send_api_request('deleteMessage', {
                                    'chat_id': chat_id,
                                    'message_id': message_id
                                })
                                is_deleted = True
                                logger.info('Spam message %s was deleted', message_id)
                            except Exception as e:
                                logger.error('Error deleting spam message %s: %s', message_id, e)

                        message = Message(
                            message_id=message_id,
                            user_id=user_id,
                            time_sent=time_sent,
                            text=text,
                            is_spam=is_spam,
                            prob_spam=res["prob_spam"],
                            prob_ham=res["prob_ham"],
                            skip=is_deleted
                        )

                        try:
                            message.save()

                            is_start_command = (
                                    text.startswith('/start') or
                                    BOT_MENTION in text
                            )

                            if not is_spam and is_start_command:
                                handle_start_command(chat_id, is_group=True)
                            
                            return HttpResponse('ok')
                        except:
                            return HttpResponseBadRequest('Bad Request')
                elif update['message']['chat']['type'] == 'private':
                    if '/start' in update['message'].get('text'):
                        handle_start_command(chat_id)
                    elif '/help' in update['message'].get('text'):
                        handle_help_command(chat_id)
                    else:
                        handle_search_command(update)
            return HttpResponse('ok')
        else:
            return HttpResponseBadRequest('Bad Request')
    else:
        return HttpResponseBadRequest('Bad Request')

