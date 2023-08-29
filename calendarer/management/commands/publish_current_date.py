from django.core.management.base import BaseCommand
from mmtelegrambot import settings
from datetime import datetime
from requests import get
import json
from telebot import TeleBot


bot = TeleBot(settings.TOKEN_BOT)


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

    date_now = datetime.now().date()
    response = get(
        "https://www.hebcal.com/converter/?cfg=json&gy={}&gm={}&gd={}&g2h=1".format(date_now.year, date_now.month,
                                                                                    date_now.day))
    date = json.loads(response.text)

    date['hmonthRu'] = hMonth[date['hm']]
    date['hmonthInt'] = hMonthInt[date['hm']]

    # date['Hd'], date['HmonthRu'], date['HmonthInt'], date['Gd'], date['Gm'], date['Gy']
    return "<b>{hd} {hmonthRu} ({hmonthInt})  /  {gd}.{gm}.{gy}</b>".format(**date)


class Command(BaseCommand):
    help = 'Publish current date to Telegram group'

    def handle(self, *args, **options):
        """
        Telling jewish date to chat
        """
        date = say_date()
        bot.send_message(
            settings.MM_CHAT_ID,
            date,
            parse_mode='Html',
            disable_notification=True
        )

        self.stdout.write(
            self.style.SUCCESS('Successfully posted: "%s"' % date)
        )
