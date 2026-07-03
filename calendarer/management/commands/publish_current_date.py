from django.core.management.base import BaseCommand
from django.utils import timezone
from requests import get
import json
from youtuber.utils import send_api_request
from mmtelegrambot.settings import MM_CHAT_ID
from calendarer.models import Date
from youtuber.utils import escape_str


def say_date():
    """
    Jewish date parser
    https://www.hebcal.com/converter/?cfg=json&gy=2011&gm=6&gd=2&g2h=1
    """

    hMonth = {"Nisan": "Нисан", "Iyyar": "Ияр", "Sivan": "Сиван", "Tamuz": "Тамуз", "Av": "Ав", "Elul": "Элуль",
              "Tishrei": "Тишрей", "Cheshvan": "Хешван", "Kislev": "Кислев", "Tevet": "Тевет", "Sh'vat": "Шват",
              "Adar I": "Адар 1", "Adar II": "Адар 2", "Adar": "Адар"}
    hMonthInt = {"Nisan": 1, "Iyyar": 2, "Sivan": 3, "Tamuz": 4, "Av": 5, "Elul": 6, "Tishrei": 7, "Cheshvan": 8,
                 "Kislev": 9, "Tevet": 10, "Sh'vat": 11, "Adar I": 12, "Adar II": 13, "Adar": 12}

    today = timezone.localdate()
    response = get(
        "https://www.hebcal.com/converter/?cfg=json&gy={}&gm={}&gd={}&g2h=1&lg=ru".format(today.year, today.month,
                                                                                          today.day))
    date = json.loads(response.text)

    date['hmonthRu'] = hMonth[date['hm']]
    date['hmonthInt'] = hMonthInt[date['hm']]
    date['heventsRu'] = "\n".join(date['events'])

    # date['Hd'], date['HmonthRu'], date['HmonthInt'], date['Gd'], date['Gm'], date['Gy']
    date_str = "🗓 {hd} {hmonthRu} ({hmonthInt}) {hy} / {gd}.{gm}.{gy}".format(**date)
    date_str = escape_str(date_str)
    events_str = escape_str(date['heventsRu'])

    return f"*{date_str}*\n{events_str}"


class Command(BaseCommand):
    help = 'Publish current date to Telegram group'

    def handle(self, *args, **options):
        """
        Telling jewish date to chat
        """
        today = timezone.localdate()

        if Date.objects.filter(date=today).exists():
            self.stdout.write(
                self.style.WARNING(f'Date {today} already posted, skipping.')
            )
            return

        try:
            date = say_date()

            date_message = send_api_request("sendMessage", {
                'chat_id': MM_CHAT_ID,
                'text': date,
                'parse_mode': 'MarkdownV2',
                'disable_notification': True
            })

            response = date_message.json()
            if response['ok']:
                message_id = response['result']['message_id']

                date_record = Date(message_id=message_id)

                try:
                    date_record.save()
                except:
                    print(f'Error while saving Date message {message_id}')

            self.stdout.write(
                self.style.SUCCESS('Successfully posted: "%s"' % date)
            )
        except:
            self.stdout.write(
                self.style.ERROR('Error while trying to post current date')
            )
