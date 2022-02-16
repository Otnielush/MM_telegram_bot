import time
import datetime

import funcs, downloader, parse

# set PYTHONOPTIMIZE=1 && pyinstaller --onefile main.py
# installed pyTelegramBotAPI, pytube

# CONST
PARSE_MAX = 5
TEST = True

settings = funcs.read_config(test=TEST)
admins = []
try:
    bot = funcs.bot_create()
    bot_connected = True
    bot_id = bot.get_me().id
    admins = [x.user.id for x in bot.get_chat_administrators(settings['MMChatId'])]  # not implemented
    print('Bot connected')
except:
    bot_connected = False
    print('Bot failed to connect', end='\r')

loop = True
# take variables from DB
params = funcs.vars_from_db()
last_update_id = 0


# Main loop
while loop:
    # for updates
    time_now = datetime.datetime.now()

    # try to reconnect
    while not bot_connected:
        try:
            bot = funcs.bot_create()
            bot_connected = True
            if len(admins) < 1:
                admins = [x.user.id for x in bot.get_chat_administrators(settings['MMChatId'])]
        except:
            print('Bot failed to connect', datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), end='\r')
            time.sleep(30)

    ### Youtube video loader
    if time_now >= params['last_parsed_date'] + params['youtube_inverval']:  # datetime format

        # parsing MM channel for new videos
        vid_ids, yt_objects, titles, error = parse.parse_new_videos_MM(max=PARSE_MAX, till_date=params['last_parsed_date'], parsed_ids=params['last_loaded_videos_id'])
        print('Num of ids: ', len(vid_ids), '; error = ', error, sep='')

        # if error in downloading videos -> check library updates
        if error:
            downloader.update_if_need()


        # WE HAVE THIS IN PARSING
        # checking already loaded videos
        # temp_ids = list()
        # temp_obj = list()
        # for i, id in enumerate(vid_ids):
        #     if not id in params['last_loaded_videos_id']:
        #         temp_ids.append(vid_ids[i])
        #         temp_obj.append(yt_objects[i])
        # print('Num of ids after check:', len(vid_ids))


        # downloading from youtube audio
        mp3_to_publish = list()
        downloaded_ids = list()
        mp3_durations = list()
        titles_to_publish = list()
        if len(vid_ids) > 0:
            print('Starting download video from YouTube (' + str(len(vid_ids)) + ') ' + datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            print('Done: ', end='')
            for i in range(len(vid_ids)):
                try:
                    file_name, mp3_duration = downloader.download_mp3(vid_ids[i], yt_objects[i])
                    if file_name != '':
                        print(str(i+1), end=' ')
                        mp3_to_publish.append(file_name)
                        downloaded_ids.append(vid_ids[i])
                        mp3_durations.append(mp3_duration)
                        titles_to_publish.append(titles[i])
                except:
                    print('fail', end=' ')
            print()

        # publishing to group
        published_ids = list()
        if len(mp3_to_publish) > 0:
            published_ids = funcs.publish_lesson(bot, settings['MMChatId'], mp3_to_publish, downloaded_ids, titles_to_publish, mp3_durations)

        # saving parse date and last ids to data base and deleting previous data
        params['last_parsed_date'] = time_now

        if len(published_ids) > 0:
            params['last_loaded_videos_id'] = published_ids + params['last_loaded_videos_id']
            while len(params['last_loaded_videos_id']) > 15:
                _ = params['last_loaded_videos_id'].pop(-1)

        # update online parameters in file
        funcs.vars_to_db(params)

        # deleting loaded mp3`s if published
        if len(mp3_to_publish) > 0:
            not_deleted = funcs.del_published_mp3(mp3_to_publish)
            if len(not_deleted) > 0:
                time.sleep(4)
                _ = funcs.del_published_mp3(not_deleted)

    ### end: Youtube video uploader

    ### Updates messages

    try:
        updates = bot.get_updates(offset=last_update_id)
        bot_connected = True
    except (ConnectionError, TimeoutError):
        print('Connection to telegram lost')
        bot_connected = False
    except Exception as e:
        print('Error in bot.get_updates', e)
        bot_connected = False

    if bot_connected:
        for update in updates:
            # print(update.update_id)
            ### for chat MM
            if update.message != None:
                if update.message.chat.id == settings['MMChatId']:
                    # new user
                    if update.message.new_chat_members != None:
                        if len(update.message.new_chat_members) > 0:
                            try:
                                bot.delete_message(update.message.chat.id, update.message.message_id)
                            except:
                                print('can`t delete message of new member')
                            msg_new = bot.send_message(update.message.chat.id, 'Приветствуем нового участника <i>{}</i>'.format(
                                update.message.from_user.first_name if update.message.from_user.first_name != None and update.message.from_user.first_name != '' else update.message.from_user.username),
                                                       parse_mode='Html')

                        # save message to db
                        funcs.message_to_db(msg_new)

                    # in common not deleting bots messages
                    elif update.message.from_user.id != bot_id:
                        # save message to db
                        funcs.message_to_db(update.message)

                        # check message for sex advertisement

                ### end: for chat MM

                ### private chat
                # if admin
                if update.message.from_user.id in admins:
                    # answer to commands
                    if update.message.text != None:
                        if update.message.text[0] == '/':

                            # commands: reboot, status, lesson, parse
                            # download file (file sended to chat, directory to download ('./'))
                            if update.message.text[1:9].lower() == 'download':
                                # print('Downloading '+update.message.text[10:]+' for '+str(update.message.from_user.username))
                                # downloader.download_file(bot, update.message, update.message.text[10:])
                                # bot.delete_message(update.message.chat.id, update.message.message_id)
                                mp3_to_publish = ''
                                mp3_to_publish, mp3_duration = downloader.download_mp3(update.message.text[8:])
                                if mp3_to_publish != '':
                                    published_ids = funcs.publish_lesson(bot, update.message.from_user.id, [mp3_to_publish],
                                                                         [update.message.text[8:]], duration=[mp3_duration])
                                    try:
                                        _ = funcs.del_published_mp3(mp3_to_publish)
                                        bot.delete_message(update.message.chat.id, update.message.message_id)
                                    except:
                                        funcs.message_to_db(update.message)
                                else:
                                    bot.delete_message(update.message.chat.id, update.message.message_id)
                                    bot.send_message(update.message.from_user.id, 'fail to download' + update.message.text[8:])


                            # reload all functions
                            elif update.message.text[1:] == 'reboot':
                                print('Rebooting')
                                funcs.close_db()
                                bot = funcs.bot_create()
                                settings = funcs.read_config(test=TEST)
                                bot_id = bot.get_me().id
                                funcs.connect_to_db()
                                admins = [x.user.id for x in bot.get_chat_administrators(settings['MMChatId'])]
                                params = funcs.vars_from_db()
                                bot.delete_message(update.message.chat.id, update.message.message_id)

                            # Status
                            elif update.message.text[1:] == 'status':
                                msg_new = bot.send_message(update.message.chat.id, 'status online', parse_mode='Html')
                                try:
                                    bot.delete_message(update.message.chat.id, update.message.message_id)
                                except:
                                    pass
                                # save message to db
                                funcs.message_to_db(msg_new)

                            # publishing lesson by admin (message: '/lesson https://www.youtube.com/watch?v=bAyrObl7TYE')
                            elif update.message.text[1:7] == 'lesson':
                                mp3_to_publish = ''

                                print('Downloading mp3 by admin')
                                mp3_to_publish, mp3_duration = downloader.download_mp3(update.message.text[8:])
                                if mp3_to_publish != '':

                                    published_ids = funcs.publish_lesson(bot, settings['MMChatId'], [mp3_to_publish],
                                                                         [update.message.text[8:]], [mp3_duration])
                                    if len(published_ids) > 0:
                                        params['last_loaded_videos_id'].insert(0, published_ids[0])
                                    if len(params['last_loaded_videos_id']) > 15:
                                        _ = params['last_loaded_videos_id'].pop(-1)

                                    try:
                                        _ = funcs.del_published_mp3(mp3_to_publish)
                                        bot.delete_message(update.message.chat.id, update.message.message_id)
                                    except:
                                        funcs.message_to_db(update.message)

                                else:
                                    bot.send_message(update.message.chat.id, 'video not published')


                            elif update.message.text[1:6] == 'parse':
                                params['last_parsed_date'] = time_now - params['youtube_inverval']

                            elif update.message.text[1:7] == 'params':
                                # show params
                                pass

                # if not admin

        ### end: private chat

        ### end: Updates messages

        ### Delete messages from chat
        if params['del_msg_hour'] != time_now.hour:
            # loading messages from data base

            # deleting messages from chat
            funcs.delete_msg(bot)
            params['del_msg_hour'] = time_now.hour

        ### end: Delete messages from chat

        ### New Day
        # Telling jewish date to chat
        if time_now.day != params['jew_date_posted']:
            bot.send_message(settings['MMChatId'], parse.say_date(), parse_mode='Html')
            params['jew_date_posted'] = time_now.day
            funcs.vars_to_db(params)

        ### end: New Day

        # eliminate dublicates in updates
        if len(updates) > 0:
            last_update_id = updates[-1].update_id + 1
        time.sleep(1)

    time.sleep(30)