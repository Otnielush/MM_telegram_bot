import logging

import requests
from django.core.cache import cache
from mmtelegrambot.settings import ADMIN_ID, TELEGRAM_API_URL

import string
import random

logger = logging.getLogger(__name__)


def escape_str(text):
    translate_table = str.maketrans({
        '\\': r'\\',
        '_': r'\_',
        '*': r'\*',
        '[': r'\[',
        ']': r'\]',
        '(': r'\(',
        ')': r'\)',
        '~': r'\~',
        '`': r'\`',
        '>': r'\>',
        '#': r'\#',
        '+': r'\+',
        '-': r'\-',
        '=': r'\=',
        '|': r'\|',
        '{': r'\{',
        '}': r'\}',
        '.': r'\.',
        '!': r'\!'
    })

    text = str(text)

    return text.translate(translate_table)


def send_api_request(method, data):
    return requests.post(TELEGRAM_API_URL + method, data)


def notify_admin(text, silent=False, throttle_key=None, throttle_seconds=None):
    """Send a plain-text message to ADMIN_ID. Never raises; returns True if the message was sent.

    silent: deliver without a sound (Telegram disable_notification).
    throttle_key, throttle_seconds: send at most one message with this key per throttle_seconds;
    pass both or neither.
    """
    if not ADMIN_ID:
        return False

    if throttle_key and throttle_seconds:
        try:
            if not cache.add(f'admin_alert:{throttle_key}', 1, timeout=throttle_seconds):
                return False
        except Exception:
            # Better a duplicate alert than none when the cache is down
            logger.exception('Cache error while throttling admin alert %s', throttle_key)

    try:
        response = send_api_request('sendMessage', {
            'chat_id': ADMIN_ID,
            'text': text,
            'disable_notification': silent,
            'disable_web_page_preview': True,
        })
        if response.status_code != 200:
            logger.error('Telegram refused admin alert (%s): %s', response.status_code, response.text[:300])
            return False
        return True
    except Exception:
        logger.exception('Error notifying admin')
    return False


def get_webhook_secret_token(length=64):
    res = ''.join(random.choices(string.ascii_uppercase +
                                 string.ascii_lowercase +
                                 string.digits, k=length))

    return res
