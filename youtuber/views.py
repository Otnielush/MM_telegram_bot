from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import feedparser
from mmtelegrambot import settings
from telebot import TeleBot
from .utils import escape_str


bot = TeleBot(settings.TOKEN_BOT)


@require_POST
@csrf_exempt
def handle_push_notification(request):
    if request.body:
        feed = feedparser.parse(request.body)

        title = escape_str(feed.entries[0].title)
        video_id = escape_str(feed.entries[0].yt_videoid)
        link = feed.entries[0].link
        link = f"[link]({link})"
        published = escape_str(feed.entries[0].published)
        updated = escape_str(feed.entries[0].updated)

        message = f"title: {title}\nvideo\_id: {video_id}\nlink: {link}\npublished: {published}\nupdated: {updated}"

        bot.send_message(settings.MM_CHAT_ID, message, parse_mode='MarkdownV2')

        return HttpResponse('Callback received successfully')
    else:
        return HttpResponse('Callback received successfully (no body)')

