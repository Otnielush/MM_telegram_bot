import json
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch, MagicMock

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from cleaner.ai import (
    AIAuthError, AICreditsError, AIError, AIRateLimitError, build_answer_messages, chat_completion,
)
from cleaner.utils import llm_markdown_to_telegram
from cleaner.views import AI_RATE_LIMIT_MESSAGE, ERROR_MESSAGE, get_answer, get_date_time_sent, handle_search_command

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

MESSAGES = [{'role': 'user', 'content': 'hi'}]

SIMILAR_TEXTS = [
    {'lesson_name': 'Урок о субботе', 'upload_date': '2026-01-01', 'part': 2, 'text': 'Текст про субботу'},
    {'lesson_name': 'Урок о молитве', 'upload_date': '2026-02-01', 'part': 1, 'text': 'Текст про молитву'},
]


def fake_response(status_code, payload):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = json.dumps(payload)
    return response


def ok_response(content):
    return fake_response(200, {'choices': [{'message': {'role': 'assistant', 'content': content}}]})


def error_response(status_code, message='error'):
    return fake_response(status_code, {'error': {'code': status_code, 'message': message}})


@override_settings(OPENROUTER_API_KEY='test-key', OPENROUTER_MODEL='test/model:free')
class ChatCompletionTests(SimpleTestCase):

    @patch('cleaner.ai.requests.post')
    def test_returns_content_and_sends_model_and_params(self, post):
        post.return_value = ok_response('  Ответ  ')

        self.assertEqual(chat_completion(MESSAGES, temperature=0.2, max_tokens=1000), 'Ответ')
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs['json']['model'], 'test/model:free')
        self.assertEqual(kwargs['json']['messages'], MESSAGES)
        self.assertEqual(kwargs['json']['temperature'], 0.2)
        self.assertEqual(kwargs['json']['max_tokens'], 1000)
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-key')

    @patch('cleaner.ai.requests.post')
    def test_error_statuses_map_to_exceptions(self, post):
        cases = [
            (401, AIAuthError, 'Неверный ключ OpenRouter'),
            (403, AIAuthError, 'Доступ к OpenRouter запрещён'),
            (402, AICreditsError, 'Закончились кредиты OpenRouter'),
            (429, AIRateLimitError, 'Превышен лимит запросов OpenRouter'),
            (502, AIError, 'Ошибка OpenRouter'),
        ]
        for status, error_class, text in cases:
            with self.subTest(status=status):
                post.return_value = error_response(status, 'upstream says no')
                with self.assertRaises(error_class) as ctx:
                    chat_completion(MESSAGES)
                self.assertIn(text, str(ctx.exception))
                self.assertIn('upstream says no', str(ctx.exception))

    @patch('cleaner.ai.requests.post')
    def test_error_shows_provider_reason_from_metadata_raw(self, post):
        post.return_value = fake_response(429, {'error': {
            'code': 429,
            'message': 'Provider returned error',
            'metadata': {'raw': 'model is temporarily rate-limited upstream'},
        }})
        with self.assertRaises(AIRateLimitError) as ctx:
            chat_completion(MESSAGES)
        self.assertIn('model is temporarily rate-limited upstream', str(ctx.exception))
        self.assertNotIn('Provider returned error', str(ctx.exception))

    @patch('cleaner.ai.requests.post')
    def test_cut_answer_is_logged(self, post):
        post.return_value = fake_response(200, {'choices': [
            {'finish_reason': 'length', 'message': {'role': 'assistant', 'content': 'Обрезанный отв'}},
        ]})
        with self.assertLogs('cleaner.ai', level='WARNING') as logs:
            self.assertEqual(chat_completion(MESSAGES, max_tokens=2500), 'Обрезанный отв')
        self.assertIn('max_tokens=2500', logs.output[0])

    @patch('cleaner.ai.requests.post')
    def test_unexpected_body_raises_ai_error(self, post):
        post.return_value = fake_response(200, {'choices': []})
        with self.assertRaises(AIError):
            chat_completion(MESSAGES)

    @override_settings(OPENROUTER_API_KEY='')
    @patch('cleaner.ai.requests.post')
    def test_missing_key_does_not_call_api(self, post):
        with self.assertRaises(AIAuthError):
            chat_completion(MESSAGES)
        post.assert_not_called()


class BuildAnswerMessagesTests(SimpleTestCase):

    def test_sources_in_system_and_question_in_user(self):
        messages, doc = build_answer_messages('Что такое суббота?', SIMILAR_TEXTS)

        self.assertEqual([m['role'] for m in messages], ['system', 'user'])
        self.assertIn('## Source #1\nLesson name: Урок о субботе from 2026-01-01\nPart 2', doc)
        self.assertIn('## Source #2', doc)
        self.assertIn(doc, messages[0]['content'])
        self.assertTrue(messages[1]['content'].startswith('Что такое суббота?'))

    def test_no_texts(self):
        messages, doc = build_answer_messages('Вопрос', None)
        self.assertEqual(doc, '')
        self.assertEqual(len(messages), 2)


@override_settings(OPENROUTER_API_KEY='test-key', CACHES=LOCMEM_CACHE)
@patch('cleaner.views.similarity_search', return_value=SIMILAR_TEXTS)
@patch('youtuber.utils.ADMIN_ID', '42')
@patch('youtuber.utils.send_api_request', return_value=fake_response(200, {'ok': True}))
@patch('cleaner.ai.requests.post')
class GetAnswerTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def assert_alert(self, send, text, silent):
        send.assert_called_once()
        method, data = send.call_args.args
        self.assertEqual(method, 'sendMessage')
        self.assertEqual(data['chat_id'], '42')
        self.assertIn(text, data['text'])
        self.assertEqual(data['disable_notification'], silent)

    def test_returns_answer(self, post, send, _search):
        post.return_value = ok_response('Суббота — день отдыха')

        answer, doc, similar_texts, error_message = get_answer('Что такое суббота?')

        self.assertEqual(answer, 'Суббота — день отдыха')
        self.assertIsNone(error_message)
        self.assertIn('Текст про субботу', doc)
        self.assertEqual(similar_texts, SIMILAR_TEXTS)
        send.assert_not_called()

    def test_out_of_credits_notifies_admin_once(self, post, send, _search):
        post.return_value = error_response(402, 'Insufficient credits')

        answer, doc, similar_texts, error_message = get_answer('Вопрос')
        self.assertIsNone(answer)
        self.assertEqual(error_message, ERROR_MESSAGE)
        self.assertEqual(similar_texts, SIMILAR_TEXTS)
        self.assert_alert(send, 'Закончились кредиты OpenRouter (402', silent=False)

        # Repeated failures within the hour don't spam the admin
        get_answer('Ещё вопрос')
        send.assert_called_once()

    def test_invalid_key_is_loud(self, post, send, _search):
        post.return_value = error_response(401, 'No auth credentials found')

        get_answer('Вопрос')

        self.assert_alert(send, 'Неверный ключ OpenRouter (401', silent=False)

    def test_rate_limit_explains_free_models_and_notifies_admin_silently(self, post, send, _search):
        post.return_value = error_response(429, 'Rate limit exceeded: free-models-per-day')

        answer, _doc, _texts, error_message = get_answer('Вопрос')

        self.assertIsNone(answer)
        self.assertEqual(error_message, AI_RATE_LIMIT_MESSAGE)
        self.assert_alert(send, 'Превышен лимит запросов OpenRouter', silent=True)

    def test_server_error_is_silent(self, post, send, _search):
        post.return_value = error_response(502, 'Bad gateway')

        _answer, _doc, _texts, error_message = get_answer('Вопрос')

        self.assertEqual(error_message, ERROR_MESSAGE)
        self.assert_alert(send, 'Ошибка OpenRouter (502', silent=True)

    def test_timeout_is_silent(self, post, send, _search):
        post.side_effect = requests.Timeout('read timed out')

        _answer, _doc, _texts, error_message = get_answer('Вопрос')

        self.assertEqual(error_message, ERROR_MESSAGE)
        self.assert_alert(send, 'OpenRouter недоступен', silent=True)

    def test_error_types_are_throttled_separately(self, post, send, _search):
        post.return_value = error_response(502)
        get_answer('Вопрос')
        get_answer('Вопрос')
        post.return_value = error_response(402)
        get_answer('Вопрос')
        get_answer('Вопрос')

        self.assertEqual(send.call_count, 2)
        self.assertEqual([c.args[1]['disable_notification'] for c in send.call_args_list], [True, False])

    def test_alert_failure_does_not_break_answer(self, post, send, _search):
        post.return_value = error_response(402)
        send.side_effect = requests.ConnectionError('telegram is down')

        answer, _doc, similar_texts, error_message = get_answer('Вопрос')

        self.assertIsNone(answer)
        self.assertEqual(error_message, ERROR_MESSAGE)
        self.assertEqual(similar_texts, SIMILAR_TEXTS)


MARKDOWN_V2_SPECIALS = set('_*[]()~`>#+-=|{}.!\\')


def assert_valid_markdown_v2(test, text):
    """Every MarkdownV2 special char is escaped, except balanced * pairs (bold)."""
    bold = False
    i = 0
    while i < len(text):
        char = text[i]
        if char == '\\':
            test.assertLess(i + 1, len(text), 'dangling backslash')
            test.assertIn(text[i + 1], MARKDOWN_V2_SPECIALS, f'needless escape at {i}')
            i += 2
            continue
        if char == '*':
            bold = not bold
        else:
            test.assertNotIn(char, MARKDOWN_V2_SPECIALS, f'unescaped {char!r} at {i}: {text[max(0, i - 20):i + 20]!r}')
        i += 1
    test.assertFalse(bold, 'unclosed bold')


# Real answers: the first two weren't delivered (odd number of * after the old ** -> * replace)
HANUKKAH_ANSWER = (
    "Согласно урокам рава Реувена Трушина, Ханука учит нас **умело радоваться**.\n\nОсновные моменты:\n"
    "*   Ханука — это **«праздник подготовки»**, полностью погруженный в понятие веселья (симхи), "
    "но это **скрытое, внутреннее веселье**, а не внешнее (как в Пурим).\n"
    "*   Суть праздника — **подготовка к великому будущему веселью** (приходу Машиаха).\n"
    "*   Рав Трушин подчеркивает: «Оказывается, господа, что мы с вами этого не умели делать».\n\n"
    "Также в уроках рава Йоны Левина: Ханука (как «греческий праздник») символизирует "
    "**прохождение еврейским народом через очередную цивилизацию** и взаимное влияние с человечеством."
)
ISAAC_ANSWER = (
    "Из предоставленных текстов о Ицхаке (Исааке, Исхаке) известно следующее:\n\n**Родословная и возраст:**\n"
    "*   Сын Авраама, отец Есава и Яакова (близнецов), родил их в 60 лет.\n*   Прожил 180 лет.\n\n"
    "**Сущность и качества (по каббале/толкованиям):**\n"
    "*   Олицетворяет атрибут **Дин (Суд)** и **Гвура (Сила/Могущество)**. Это «одно качество» — сторона левого.\n"
    "*   Описывается как **«цельный» (шалем)** и **могучий** человек («шел всех по рублю покалечу»).\n\n"
    "**Ключевые события:**\n"
    "*   **Акедат Ицхак (Связывание Ицхака / Жертвоприношение):** Главное испытание. Ицхак в 8 дней сказал: "
    "«Если мне скажут отдать жизнь — отдам сразу»).\n"
)
ISAAC_SENT_ANSWER = (
    "Из предоставленных текстов о Ицхаке (Исааке) известно следующее:\n\n"
    "*   **Родословная:** Один из отцов (авот), сын Авраама, отец Яакова и Эсава. Жена — Ривка.\n"
    "*   **Возраст и хронология:**\n    *   Прожил **180 лет**.\n    *   Сыновья-близнецы родились, когда ему было **60 лет**.\n"
)


class LlmMarkdownToTelegramTests(SimpleTestCase):

    def test_real_answers_are_valid_markdown_v2(self):
        for answer in (HANUKKAH_ANSWER, ISAAC_ANSWER, ISAAC_SENT_ANSWER):
            with self.subTest(answer=answer[:40]):
                assert_valid_markdown_v2(self, llm_markdown_to_telegram(answer))

    def test_bold_and_bullets(self):
        self.assertEqual(
            llm_markdown_to_telegram('Итог:\n*   **Дин (Суд)** и гвура.\n- второй'),
            'Итог:\n• *Дин \\(Суд\\)* и гвура\\.\n• второй',
        )

    def test_nested_bullets_keep_indent(self):
        self.assertEqual(llm_markdown_to_telegram('*   a\n    *   b'), '• a\n    • b')

    def test_heading_becomes_bold(self):
        self.assertEqual(llm_markdown_to_telegram('## Итог **важно**\nтекст'), '*Итог важно*\nтекст')

    def test_stray_markup_is_shown_literally(self):
        text = llm_markdown_to_telegram('a * b _c_ `d` [e](f) \\ **незакрытый')
        assert_valid_markdown_v2(self, text)
        self.assertEqual(text, 'a \\* b \\_c\\_ \\`d\\` \\[e\\]\\(f\\) \\\\ \\*\\*незакрытый')


def telegram_update(text='Что такое суббота?', user_id=7, chat_id=7, message_id=100):
    return {'message': {
        'message_id': message_id, 'date': 1764000000, 'text': text,
        'from': {'id': user_id}, 'chat': {'id': chat_id, 'type': 'private'},
    }}


@override_settings(CACHES=LOCMEM_CACHE)
@patch('cleaner.views.WHITELISTED_USERS', [7])
@patch('cleaner.views.save_result')
@patch('cleaner.views.make_message_with_youtube_links', return_value=None)
@patch('cleaner.views.notify_admin')
@patch('cleaner.views.send_api_request', return_value=fake_response(200, {'ok': True}))
@patch('cleaner.views.get_answer', return_value=(HANUKKAH_ANSWER, 'doc', SIMILAR_TEXTS, None))
class HandleSearchCommandTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def test_answer_is_sent_as_markdown_v2(self, get_answer_, send, notify, _links, save):
        handle_search_command(telegram_update())

        send.assert_called_once()
        data = send.call_args.args[1]
        self.assertEqual(data['parse_mode'], 'MarkdownV2')
        assert_valid_markdown_v2(self, data['text'])
        save.assert_called_once()
        notify.assert_not_called()

    def test_redelivered_update_is_answered_once(self, get_answer_, send, _notify, _links, save):
        handle_search_command(telegram_update())
        handle_search_command(telegram_update())

        get_answer_.assert_called_once()
        send.assert_called_once()
        save.assert_called_once()

    def test_other_message_is_answered(self, get_answer_, send, _notify, _links, _save):
        handle_search_command(telegram_update(message_id=100))
        handle_search_command(telegram_update(message_id=101))

        self.assertEqual(get_answer_.call_count, 2)

    def test_rejected_markup_is_resent_as_plain_text(self, _get_answer, send, notify, _links, _save):
        send.side_effect = [
            fake_response(400, {'ok': False, 'description': "Bad Request: can't parse entities"}),
            fake_response(200, {'ok': True}),
        ]
        with self.assertLogs('cleaner.views', level='ERROR') as logs:
            handle_search_command(telegram_update())

        self.assertIn("can't parse entities", logs.output[0])
        retry = send.call_args_list[1].args[1]
        self.assertNotIn('parse_mode', retry)
        self.assertEqual(retry['text'], HANUKKAH_ANSWER)
        notify.assert_not_called()

    def test_undelivered_answer_notifies_admin(self, _get_answer, send, notify, _links, save):
        send.return_value = fake_response(403, {'ok': False, 'description': 'Forbidden: bot was blocked by the user'})
        with self.assertLogs('cleaner.views', level='ERROR'):
            handle_search_command(telegram_update())

        send.assert_called_once()  # not a markup problem, no plain-text retry
        notify.assert_called_once()
        self.assertIn('bot was blocked by the user', notify.call_args.args[0])
        save.assert_called_once()


@override_settings(TIME_ZONE='Asia/Jerusalem')
class GetDateTimeSentTests(SimpleTestCase):

    def test_unix_timestamp_is_utc(self):
        # 2026-11-26 13:24:33 UTC = 15:24:33 in Jerusalem; it used to be stored as 13:24:33 Jerusalem time
        sent = get_date_time_sent({'message': {'date': 1795699473}})
        self.assertEqual(sent, datetime(2026, 11, 26, 13, 24, 33, tzinfo=dt_timezone.utc))
