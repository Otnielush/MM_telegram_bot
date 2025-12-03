import json
from time import time
import textwrap

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.utils import timezone
from mmtelegrambot.settings import MM_CHAT_ID, WEBHOOK_SECRET_TOKEN, BOT_MENTION
from .models import Message
from youtuber.utils import escape_str, send_api_request
from .utils import make_result_message, save_result
from Similarity_search_audio.search_scripts import similarity_search
from cleaner.spam_detector import spam_detector

SHORT_TERM_LIMIT = 1       # maximum requests every 30 seconds
SHORT_TERM_WINDOW = 30     # 30-second window

DAILY_LIMIT = 20           # maximum requests per day
DAILY_WINDOW = 86400       # 24-hour window (in seconds)

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
    question = text.strip()
    try:
        result = similarity_search(question)
        save_result(message_id, user_id, chat_id, sent_at, question, result)
        message = make_result_message(result)
        send_api_request("sendMessage", {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'MarkdownV2',
            'disable_notification': True,
            'disable_web_page_preview': True,
            'reply_to_message_id': message_id
        })
    except Exception as e:
        print(e)
        return HttpResponseBadRequest('Bad Request')

def handle_start_command(chat_id, is_group=False):
    message = f'''
    {BOT_MENTION} поможет найти, в каких уроках на YouTube-канале Махон Меир может быть ответ на ваш вопрос.
    Просто отправьте ваш вопрос в личный чат с ботом.
    В ответ бот пришлет список ссылок на уроки с тайм-кодами, в которых может содержаться ответ на вопрос.
    Есть ограничения: 20 вопросов в сутки, и не чаще 1 вопроса в 30 секунд.
    '''
    message = textwrap.dedent(message)

    try:
        msg_new = send_api_request("sendMessage", {
            'chat_id': chat_id,
            'text': escape_str(message),
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

                        message = Message(
                            message_id=message_id,
                            user_id=user_id,
                            time_sent=time_sent,
                            text=text,
                            is_spam=res["is_spam"],
                            prob_spam=res["prob_spam"],
                            prob_ham=res["prob_ham"]
                        )

                        try:
                            message.save()

                            if '/start' in text or BOT_MENTION in text:
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

