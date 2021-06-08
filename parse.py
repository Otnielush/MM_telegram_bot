from requests import get
from re import findall, finditer, sub
from pytube import YouTube
from datetime import datetime
import json

import pytube


# in: max - max parsed videos(30), till_date - max date to parse
# out:  video ids from Machon Meir channel
#       titles
#       publish dates
def parse_new_videos_MM(max=None, till_date=None, parsed_ids=None):
    print('Parsing YouTube channel Machon Meir')
    try:
        html = get('https://www.youtube.com/c/MeirTvRussian/videos')
    except:
        print('Can`t open url youtube')
        return [], []
    videos = findall('/watch\?v=.{11}', html.text)
    ids = list()
    yt_objects = list()

    if max == None:
        max = len(videos)

    if max != None:
        print('{} videos found.'.format(max), end=' ')
        print(videos)

    if till_date != None:
        if type(till_date) == str:
            till_date = datetime.fromisoformat(till_date).date()
        else:
            till_date = till_date.date()
        # elif not type(till_date) == datetime.date:
        #     print('Date given not correctly. Need %Y-%m-%d or datetime.date format')
        #     print(type(till_date))
        #     till_date = None


    print('Parsing: ', end='')

    for i in range(max):
        if parsed_ids != None:
            if videos[i] in parsed_ids:
                print('-', end=' ')
                continue
        print(i+1, end=' ')

        try:
            connects = 0
            while connects < 3:
                try:
                    yt_obj = YouTube('https://www.youtube.com' + videos[i])
                    yt_objects.append(yt_obj)
                    ids.append(videos[i][9:])
                    break
                except:
                    print('not')
                    connects += 1

            # if not connected => go next
            if connects >= 3:
                continue

            date = yt_obj.player_response['microformat']['playerMicroformatRenderer']['publishDate']

            # if date reached
            if till_date != None:
                # print(datetime.fromisoformat(date), till_date)
                if datetime.fromisoformat(date) < till_date:
                    ids = ids[:i]
                    yt_objects = yt_objects[:i]
                    break

        except:
            pass

    print('\n')
    return ids, yt_objects

# ids, titles, dates = parse_new_videos_MM(max=4, till_date=datetime(2020, 9, 8, 2, 22, 25, 225530))

# Parsing name of rebe and title from file name
# Out: name of rebe, title
def parse_rav(name):
    artist = ''
    cut_start = [x.start() for x in finditer(r'рав', name.lower())]
    if len(cut_start) > 0:
        cut_start = cut_start[0]
        search_rav = [x for x in finditer(
            r'левин|йона|авраам|адлер|рэувен|трушин|довид|иуда|зеев|зээв|мешков|яаков|меир|яков|регев|йосеф|делевич|пинхас|гулис|фаерман|исраэль|амиуд|элиягу|жинский',
            name.lower())]
        if len(search_rav) > 0:
            cut_end = 0
            for o in search_rav:
                if o.end() > cut_end:
                    cut_end = o.end()

            artist = cleaner_txt(name[cut_start:cut_end])
            m = 1 if cut_start == 0 else 0
            title = cleaner_txt(name[:cut_start] + name[cut_end + m:])

        # not found рав and name
        else:
            title = name
    else:
        title = name

    return artist, title


# Substracting not needed symbols from start and end string
def cleaner_txt(txt):
    return sub(r'^(\s|-|=|:|,|\.|\?)+', '', sub(r'(\s|-|=|:|,|\.|\?)+$', '', txt))


# Jewish date parser
# "https://www.hebcal.com/converter/?cfg=json&gy=2011&gm=6&gd=2&g2h=1"
hMonth = {"Nisan": "Нисан", "Iyyar": "Ияр", "Sivan": "Сиван", "Tamuz": "Тамуз", "Av": "Ав", "Elul": "Элуль", "Tishrei": "Тишрей", "Cheshvan": "Хешван", "Kislev": "Кислев", "Tevet": "Тевет", "Sh'vat": "Шват", "Adar I": "Адар 1", "Adar II": "Адар 2", "Adar": "Адар"}
hMonthInt = {"Nisan": 1, "Iyyar": 2, "Sivan": 3, "Tamuz": 4, "Av": 5, "Elul": 6, "Tishrei": 7, "Cheshvan": 8, "Kislev": 9, "Tevet": 10, "Sh'vat": 11, "Adar I": 12, "Adar II": 13, "Adar": 12}

def say_date():
    date_now = datetime.now().date()
    response = get("https://www.hebcal.com/converter/?cfg=json&gy={}&gm={}&gd={}&g2h=1".format(date_now.year, date_now.month, date_now.day))
    date = json.loads(response.text)

    date['hmonthRu'] = hMonth[date['hm']]
    date['hmonthInt'] = hMonthInt[date['hm']]

    # date['Hd'], date['HmonthRu'], date['HmonthInt'], date['Gd'], date['Gm'], date['Gy']
    return "<b>{hd} {hmonthRu} ({hmonthInt})  /  {gd}.{gm}.{gy}</b>".format(**date)


if __name__ == '__main__':
    # yt = YouTube('https://www.youtube.com/watch?v=79-UbfNRWbo')
    ids, yt = parse_new_videos_MM(3)
    print(ids)