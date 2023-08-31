import requests
from mmtelegrambot.settings import TELEGRAM_API_URL


def escape_str(text):
    translate_table = str.maketrans({
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
