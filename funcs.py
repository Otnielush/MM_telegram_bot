import telebot
import sqlite3
import json
import datetime
import os
import pandas as pd
from parse import parse_rav


nameBot = "Machon Meir"
userNameBot = "Machon_Meir_bot"
DB_directory = os.path.join(os.getcwd(), 'DataBase')


def read_config(test=True):
    global config
    with open(os.path.join(os.getcwd(), 'settings','config.json'), 'r') as cfg:
        config = json.load(cfg)

    if test:
        config['TestMode'] = test
        print('!!! Test mode !!!')
        config['TokenBot'] = config['TokenTestBot']
        config['MMChatId'] = config['TestChatId']

    return config

config = read_config()


# БД
def create_table():

    # проверка наличия базы данных
    if not os.path.exists(DB_directory):
        os.mkdir(DB_directory)

    if not os.path.exists(os.path.join(DB_directory, 'MM_chat_5781.sqlite')):
        print('DataBase is created')
    connection = sqlite3.connect(os.path.join(DB_directory, 'MM_chat_5781.sqlite'))

    cur = connection.cursor()
    tables = list(cur.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall())

    if len(tables) > 0:
        if not 'Messages_MM_5781' in tables[0]:
            cur.execute('''
                        CREATE TABLE IF NOT EXISTS Messages_MM_5781
                        (id INTEGER PRIMARY KEY,
                        id_msg INT,
                        id_chat INT,
                        datetime TEXT,
                        username TEXT,
                        id_user INT,
                        text TEXT,
                        deleted INT,
                        week_day INT,
                        first_name TEXT,
                        last_name TEXT,
                        date_int INT)
                        ''')
            print('TABLE Messages_MM_5781 is created.')
    else:
        cur.execute('''
                    CREATE TABLE IF NOT EXISTS Messages_MM_5781
                    (id INTEGER PRIMARY KEY,
                    id_msg INT,
                    id_chat INT,
                    datetime TEXT,
                    username TEXT,
                    id_user INT,
                    text TEXT,
                    deleted INT,
                    week_day INT,
                    first_name TEXT,
                    last_name TEXT,
                    date_int INT)
                    ''')
        print('TABLE Messages_MM_5781 is created')

    connection.close()

create_table()

#connect to DataBase
connection = 0
def connect_to_db():
    global connection
    connection = sqlite3.connect(os.path.join(DB_directory, 'MM_chat_5781.sqlite'), check_same_thread=False)

def close_db():
    global connection
    connection.commit()
    connection.close()
    print('DataBade closed')

connect_to_db()


def message_to_db(msg):
    global connection
    cur = connection.cursor()

    date = datetime.datetime.now()
    cur.execute('''INSERT OR IGNORE INTO Messages_MM_5781 
            (id, id_msg, id_chat, datetime, username, id_user, text, deleted, week_day, first_name, last_name, date_int) 
                        VALUES(null, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (msg.message_id,
                 msg.chat.id,
                 date.isoformat(),
                 msg.from_user.username,
                 msg.from_user.id,
                 msg.text,
                 0,
                 date.weekday(),
                 msg.from_user.first_name,
                 msg.from_user.last_name,
                 date_to_int(date)))
    connection.commit()


def date_to_int(date):
    if type(date) == datetime.datetime:
        return date.year*100000000 + date.month*1000000 + date.day*10000 + date.hour*100 + date.minute # 2012 09 15 20:15:54 -> 201 209 152 015
    elif type(date) == datetime.date:
        return date.year * 100000000 + date.month * 1000000 + date.day * 10000
    elif type(date) == str:
        date = datetime.datetime.fromisoformat(date)
        return date.year * 100000000 + date.month * 1000000 + date.day * 10000 + date.hour * 100 + date.minute
    elif type(date) == int:
        return date


def int_to_date(num):
    year = num // 100000000
    month = num // 1000000 - year
    day = num // 10000 - year - month
    hour = num // 100 - year - month - day
    minute = num - year - month - day - hour
    return datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)


def bot_create():

    bot = telebot.TeleBot(config['TokenBot'])

    '''
    # Команды бота
    @bot.message_handler(commands=['start'])
    def start(msg):
        bot.send_message(msg.chat.id, 'Привет от бота. команда старт')

    # Сообщения
    @bot.message_handler(func=lambda m: True)
    def bot_send_msg(msg):
        # if msg not from chat Machon Meir or from Admins
        if msg.chat.id != config['MMChatId'] and msg.chat.id != config['Otniel_id']:
            return

        # saving msg to DataBase
        message_to_db(msg)

        # replying to msg
        message_to_db(bot.reply_to(msg, f"Я повторяю твои сообщения: {msg.text}"))'''

    return bot

def read_db(condition=''):
    global connection
    cur = connection.cursor()
    cols = [description[0] for description in cur.execute('SELECT * FROM  Messages_MM_5781').description]
    data = pd.DataFrame(cur.execute('SELECT * FROM Messages_MM_5781 '+condition).fetchall(), columns=cols)
    connection.commit()
    return data.set_index('id')


def delete_msg(bot, date=None):

    global connection
    cur = connection.cursor()
    if date == None:
        date = datetime.datetime.now()-datetime.timedelta(days=1)

    if type(date) == datetime.datetime:
        date = date_to_int(date)
    if type(date) != int:
        print('Wrong date type')
        return


    data = read_db('WHERE date_int <= '+str(date)+' AND deleted != 1')  # AND id_chat == '+str(id))
    # data['datetime'] = data['datetime'].apply(lambda x: datetime.datetime.fromisoformat(x))

    deleted = 0
    for indx, row in data.iterrows():
        try:
            if bot.delete_message(row['id_chat'], row['id_msg']):
                cur.execute('UPDATE Messages_MM_5781 SET deleted = 1 WHERE id ==' + str(indx))

                # data.iloc[indx]['deleted'] = 1
                deleted += 1
            else:
                print('Msg not deleted')
        except:
            print('Failed to delete msg')
            cur.execute('UPDATE Messages_MM_5781 SET deleted = 1 WHERE id ==' + str(indx))

    connection.commit()
    print(deleted,' messages deleted', datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    return data

# in: chat_id - to send msg; paths_to_files - list of local paths; ids_in_youtube - ids in youtube to send a link
# out: urls published
def publish_lesson(bot, chat_id, paths_to_files, url_in_youtube, titles=None, duration=None):
    print('Publishing videos:', len(paths_to_files),'|', datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print('Done: ', end='')
    published = list()
    # publishing to group
    for i, a_file in enumerate(paths_to_files):
        # link to video
        if len(url_in_youtube[i]) == 11:
            link_y = 'https://www.youtube.com/watch?v=' + url_in_youtube[i]
        else:
            link_y = url_in_youtube[i]
            url_in_youtube[i] = url_in_youtube[i].split('=')[-1]

        audio_file = open(a_file, 'rb')

        # downloading video
        tries = 0
        while tries < 3:
            try:
                video_name = titles[i] if titles != None else os.path.split(a_file)[1][:-4]
                rav, title = parse_rav(video_name)
                bot.send_audio(chat_id=chat_id, audio=audio_file, duration=duration[i],
                               performer=rav, title=title, thumb='audio/mpeg')
                audio_file.close()

                bot.send_message(chat_id, '<a href="{}">🎦 {}</a>'.format(link_y, title), parse_mode='Html', disable_web_page_preview=True)
                print(i+1, end=' ')
                break
            except Exception as e:
                if tries >= 2:
                    print('Ошибка в публикации видео', e)
                tries += 1

        if tries >= 3:
            audio_file.close()
        else:
            published.append(url_in_youtube[i])
    print()

    return published


# for now just saving to json file
def vars_to_db(parameters):
    params = parameters.copy()

    if len(params) < 3:
        return
    with open('./settings/params.json', 'w') as pars:
        params['youtube_inverval'] = params['youtube_inverval'].seconds
        params['last_parsed_date'] = params['last_parsed_date'].isoformat()
        pars.write(json.dumps(params))


def vars_from_db():
    with open('./settings/params.json', 'r') as pars:
        try:
            params = json.load(pars)
            params['youtube_inverval'] = datetime.timedelta(seconds=params['youtube_inverval'])
            params['last_parsed_date'] = datetime.datetime.fromisoformat(params['last_parsed_date'])

            return params
        except:
            return {}


def del_published_mp3(mp3_to_publish):
    not_deleted = list()

    if type(mp3_to_publish) == str:
        mp3_to_publish = [mp3_to_publish]

    for mp3 in mp3_to_publish:
        try:
            os.remove(mp3)
        except:
            not_deleted.append(mp3)
    return not_deleted

