"""Answers to user questions over lesson texts via OpenRouter (Chat Completions API)."""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
REQUEST_TIMEOUT = 120

ANSWER_PROMPT = """
# Instruction:
Ты даешь ответы на вопросы пользователя, используя текст, который я тебе дал.
Не придумывай сам ответ, используй только Текст, который я тебе дал.
Выбирай из текста только нужную информацию для ответа.
Если в тексте нет ответа, используй фразу: "В моей базе текстов по урокам не нашлась информация о ..."
Отвечай по существу, не длиннее 1000 символов.
---

# Текст:
{document}
"""


class AIError(Exception):
    """Base error of the AI provider; the message is readable as is."""


class AIAuthError(AIError):
    pass


class AICreditsError(AIError):
    pass


class AIRateLimitError(AIError):
    pass


_ERRORS_BY_STATUS = {
    401: (AIAuthError, 'Неверный ключ OpenRouter'),
    403: (AIAuthError, 'Доступ к OpenRouter запрещён: ключ отключён или достигнут лимит расходов'),
    402: (AICreditsError, 'Закончились кредиты OpenRouter'),
    429: (AIRateLimitError, 'Превышен лимит запросов OpenRouter, попробуйте через минуту'),
}


def _api_error_message(response):
    """OpenRouter puts the provider's own reason into error.metadata.raw; error.message is often generic."""
    try:
        error = response.json()['error']
        raw = (error.get('metadata') or {}).get('raw')
        return str(raw or error['message'])[:300]
    except (ValueError, KeyError, TypeError, AttributeError):
        return response.text[:300]


def chat_completion(messages, **params):
    """Send messages to the configured model and return the answer text.

    Extra params (temperature, max_tokens, ...) are passed to the API as is.
    """
    if not settings.OPENROUTER_API_KEY:
        raise AIAuthError('Не задан ключ OPENROUTER_API_KEY')

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}'},
            json={'model': settings.OPENROUTER_MODEL, 'messages': messages, **params},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        raise AIError(f'OpenRouter недоступен: {e}') from e

    if response.status_code != 200:
        error_class, text = _ERRORS_BY_STATUS.get(response.status_code, (AIError, 'Ошибка OpenRouter'))
        raise error_class(f'{text} ({response.status_code}: {_api_error_message(response)})')

    try:
        data = response.json()
        choice = data['choices'][0]
        content = choice['message']['content'].strip()
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
        raise AIError(f'Неожиданный ответ OpenRouter: {response.text[:300]}') from e

    if choice.get('finish_reason') == 'length':
        # Reasoning tokens count towards max_tokens too, so a long "thinking" can cut the answer
        logger.warning('OpenRouter answer was cut by max_tokens=%s (usage: %s)',
                       params.get('max_tokens'), data.get('usage'))
    return content


def build_answer_messages(question, similar_texts):
    """Prompt answering the question using only the found lesson parts. Returns (messages, doc)."""
    doc = "\n---\n".join(
        f"## Source #{i + 1}\nLesson name: {res['lesson_name']} from {res['upload_date']}\n"
        f"Part {res['part']}\nText:\n{res['text']}"
        for i, res in enumerate(similar_texts or [])
    )
    messages = [
        {'role': 'system', 'content': ANSWER_PROMPT.format(document=doc)},
        {
            'role': 'user',
            # Repeat the task at the end so it isn't lost after a long text
            'content': question + "\n\n# Output Guidelines:\nНапиши ответ в соответствии с Instruction.",
        },
    ]
    return messages, doc
