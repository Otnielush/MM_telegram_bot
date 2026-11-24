import json
from unittest.mock import patch, MagicMock

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from cleaner.ai import (
    AIAuthError, AICreditsError, AIError, AIRateLimitError, build_answer_messages, chat_completion,
)
from cleaner.views import AI_RATE_LIMIT_MESSAGE, ERROR_MESSAGE, get_answer

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
@patch('cleaner.utils.ADMIN_ID', '42')
@patch('cleaner.utils.send_api_request')
@patch('cleaner.ai.requests.post')
class GetAnswerTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

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
        send.assert_called_once()
        method, data = send.call_args.args
        self.assertEqual(method, 'sendMessage')
        self.assertEqual(data['chat_id'], '42')
        self.assertIn('Закончились кредиты OpenRouter', data['text'])

        # Repeated failures within the hour don't spam the admin
        get_answer('Ещё вопрос')
        send.assert_called_once()

    def test_rate_limit_explains_free_models_and_does_not_notify_admin(self, post, send, _search):
        post.return_value = error_response(429, 'Rate limit exceeded: free-models-per-day')

        answer, _doc, _texts, error_message = get_answer('Вопрос')

        self.assertIsNone(answer)
        self.assertEqual(error_message, AI_RATE_LIMIT_MESSAGE)
        send.assert_not_called()
