import json
from time import time
import textwrap

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.utils import timezone
from mmtelegrambot.settings import MM_CHAT_ID, WEBHOOK_SECRET_TOKEN, BOT_MENTION, WHITELISTED_USERS
from .models import Message
from youtuber.utils import escape_str, send_api_request
from .ai import AIAuthError, AICreditsError, AIError, AIRateLimitError, build_answer_messages, chat_completion
from .utils import make_message_with_youtube_links, notify_admin, save_result
from Similarity_search_audio.search_scripts import similarity_search
from cleaner.spam_detector import spam_detector
import logging

logger = logging.getLogger(__name__)

SHORT_TERM_LIMIT = 1       # maximum requests every 30 seconds
SHORT_TERM_WINDOW = 30     # 30-second window

DAILY_LIMIT = 10           # maximum requests per day (OpenRouter free models allow only 50 a day for the whole bot)
DAILY_WINDOW = 86400       # 24-hour window (in seconds)

ERROR_MESSAGE = "Произошла ошибка, пожалуйста, повторите вопрос позже"
AI_RATE_LIMIT_MESSAGE = (
    "Бот работает на бесплатных AI-моделях, у которых есть лимит запросов, и сейчас он исчерпан. "
    "Пожалуйста, повторите вопрос позже.\n\n"
    "Это некоммерческий проект. Если хотите поддержать его как спонсор — "
    "напишите администраторам группы Махон Меир: @machonmeir"
)

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
        return True, f"Вы превысили суточный лимит в {DAILY_LIMIT} вопросов. Пожалуйста, повторите вопрос завтра"

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
    """Returns (answer, doc, similar_texts, error_message); error_message is shown to the user when answer is None."""
    similar_texts = similarity_search(question, 5)
    messages, doc = build_answer_messages(question, similar_texts)

    try:
        answer = chat_completion(messages, temperature=0.2, max_tokens=2500)
        return answer, doc, similar_texts, None
    except AIError as e:
        logger.error('Error getting AI answer for question "%s": %s', question, e)
        if isinstance(e, AIRateLimitError):
            return None, doc, similar_texts, AI_RATE_LIMIT_MESSAGE
        if isinstance(e, (AIAuthError, AICreditsError)):
            # Key/credits problems won't fix themselves — let the admin know
            notify_admin(f'Бот не может отвечать на вопросы: {e}')
        return None, doc, similar_texts, ERROR_MESSAGE

def handle_search_command(update):
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    message_id = update['message']['message_id']

    if user_id not in WHITELISTED_USERS:
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
    answer = None
    try:
        answer, doc, similar_texts, error_message = get_answer(question)
        response_text = answer or error_message or ERROR_MESSAGE
        response_text = response_text.replace('**', '*')
        send_api_request("sendMessage", {
            'chat_id': chat_id,
            'text': response_text,
            'parse_mode': 'Markdown',
            'disable_notification': True,
            'disable_web_page_preview': True,
            'reply_to_message_id': message_id
        })
        youtube_links_message = make_message_with_youtube_links(similar_texts)
        if youtube_links_message is not None:
            has_answer = answer is not None and "В моей базе текстов по урокам не нашлась информация" not in answer
            title = "*Источники:*\n\n" if has_answer else "*Похожие на ваш вопрос темы можно посмотреть в этих уроках:*\n\n"
            send_api_request("sendMessage", {
                'chat_id': chat_id,
                'text': title + youtube_links_message,
                'parse_mode': 'MarkdownV2',
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
    except Exception:
        logger.exception('Error handling search question "%s"', question)
        return HttpResponseBadRequest('Bad Request')
    finally:
        # Record every question, including ones where search/LLM/Telegram failed.
        save_result(message_id, user_id, chat_id, sent_at, question, answer)

def handle_start_command(chat_id, is_group=False):
    message = f'''
    Просто отправьте ваш вопрос в личный чат с ботом\.
    {BOT_MENTION} сгенерирует ответ на основе содержимого уроков YouTube\-канала Махон Меир\.
    Чем подробнее вы сформулируете вопрос, тем более точным будет ответ\.
    Обратите внимание \- *каждое* ваше сообщение бот воспринимает как *новый* вопрос\.
    Есть ограничения: {DAILY_LIMIT} вопросов в сутки, и не чаще 1 вопроса в {SHORT_TERM_WINDOW} секунд\.
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
    message = f'''
    ✅ Чтобы задать вопрос, просто отправьте сообщение в свободной форме.
    ⚠️ В сутки можно задать {DAILY_LIMIT} вопросов, не чаще 1 вопроса в {SHORT_TERM_WINDOW} секунд.
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

