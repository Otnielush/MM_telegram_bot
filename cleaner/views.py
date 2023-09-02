import json
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from mmtelegrambot.settings import MM_CHAT_ID, WEBHOOK_SECRET_TOKEN
from .models import Message
from youtuber.utils import escape_str, send_api_request


@csrf_exempt
def telegram_bot(request):
    if request.method == 'POST':
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_token == WEBHOOK_SECRET_TOKEN:
            update = json.loads(request.body.decode('utf-8'))
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
                else:
                    user_id = update['message']['from']['id']
                    date = update['message']['date']
                    text = update['message'].get('text')

                    message = Message(
                        message_id=message_id,
                        user_id=user_id,
                        date=date,
                        text=text
                    )

                    try:
                        message.save()
                        return HttpResponse('ok')
                    except:
                        return HttpResponseBadRequest('Bad Request')

            return HttpResponse('ok')
        else:
            return HttpResponseBadRequest('Bad Request')
    else:
        return HttpResponseBadRequest('Bad Request')

