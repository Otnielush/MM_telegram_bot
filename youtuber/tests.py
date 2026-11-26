import json
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from youtuber.models import Lesson
from youtuber.utils import notify_admin

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


def telegram_response(status_code=200, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.text = json.dumps(payload or {'ok': status_code == 200})
    return response


@override_settings(CACHES=LOCMEM_CACHE)
@patch('youtuber.utils.ADMIN_ID', '42')
@patch('youtuber.utils.send_api_request', return_value=telegram_response())
class NotifyAdminTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def test_sends_plain_text_to_admin(self, send):
        self.assertTrue(notify_admin('Привет'))

        method, data = send.call_args.args
        self.assertEqual(method, 'sendMessage')
        self.assertEqual(data['chat_id'], '42')
        self.assertEqual(data['text'], 'Привет')
        self.assertFalse(data['disable_notification'])
        self.assertNotIn('parse_mode', data)

    def test_silent(self, send):
        notify_admin('Тихо', silent=True)

        self.assertTrue(send.call_args.args[1]['disable_notification'])

    def test_throttles_by_key(self, send):
        self.assertTrue(notify_admin('1', throttle_key='a', throttle_seconds=60))
        self.assertFalse(notify_admin('2', throttle_key='a', throttle_seconds=60))
        self.assertTrue(notify_admin('3', throttle_key='b', throttle_seconds=60))
        self.assertTrue(notify_admin('4'))
        self.assertTrue(notify_admin('5'))

        self.assertEqual([c.args[1]['text'] for c in send.call_args_list], ['1', '3', '4', '5'])

    def test_no_admin_id(self, send):
        with patch('youtuber.utils.ADMIN_ID', None):
            self.assertFalse(notify_admin('text'))
        send.assert_not_called()

    def test_send_error_is_swallowed(self, send):
        send.side_effect = ConnectionError('telegram is down')

        self.assertFalse(notify_admin('text'))

    def test_telegram_refusal_returns_false(self, send):
        send.return_value = telegram_response(400, {'ok': False, 'description': 'chat not found'})

        self.assertFalse(notify_admin('text'))

    def test_cache_error_still_sends(self, send):
        with patch('youtuber.utils.cache.add', side_effect=ConnectionError('redis is down')):
            self.assertTrue(notify_admin('text', throttle_key='a', throttle_seconds=60))
        send.assert_called_once()


@patch('youtuber.management.commands.download_audio.time.sleep')
@patch('youtuber.management.commands.download_audio.yt_dlp.YoutubeDL',
       side_effect=Exception('ERROR: [youtube] badbadbad01: Video unavailable'))
@patch('youtuber.utils.ADMIN_ID', '42')
@patch('youtuber.utils.send_api_request', return_value=telegram_response())
class DownloadAudioNotificationTests(TestCase):

    def setUp(self):
        self.lesson = Lesson.objects.create(youtube_id='badbadbad01')
        # The command waits 2 hours after a lesson is added before downloading it
        Lesson.objects.filter(pk=self.lesson.pk).update(time_added=timezone.now() - timedelta(hours=3))

    def run_command(self):
        call_command('download_audio', stdout=StringIO())

    def sent_messages(self, send):
        return [c.args[1] for c in send.call_args_list]

    def test_silent_on_first_error_nothing_on_second_loud_on_third(self, send, _ydl, _sleep):
        self.run_command()
        messages = self.sent_messages(send)
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages[0]['disable_notification'])
        self.assertIn('Первая ошибка загрузки урока', messages[0]['text'])
        self.assertIn('https://youtu.be/badbadbad01', messages[0]['text'])
        self.assertIn('Video unavailable', messages[0]['text'])

        self.run_command()
        self.assertEqual(send.call_count, 1)

        self.run_command()
        messages = self.sent_messages(send)
        self.assertEqual(len(messages), 2)
        self.assertFalse(messages[1]['disable_notification'])
        self.assertIn('Урок пропущен после 3 ошибок загрузки', messages[1]['text'])
        self.assertIn('https://youtu.be/badbadbad01', messages[1]['text'])

        self.lesson.refresh_from_db()
        self.assertTrue(self.lesson.skip)
        self.assertEqual(self.lesson.error_count, 3)

        # Skipped lessons aren't retried, so no more alerts
        self.run_command()
        self.assertEqual(send.call_count, 2)

    def test_long_error_is_truncated(self, send, ydl, _sleep):
        ydl.side_effect = Exception('x' * 5000)

        self.run_command()

        text = send.call_args.args[1]['text']
        self.assertLess(len(text), 1000)
        self.assertIn('x' * 500 + '…', text)

    def test_send_failure_does_not_break_command(self, send, _ydl, _sleep):
        send.side_effect = ConnectionError('telegram is down')

        self.run_command()

        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.error_count, 1)
