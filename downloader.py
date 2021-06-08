from pytube import YouTube
from os import rename, path, getcwd, remove, stat
from requests import get

Download_folder = path.abspath('.')+'\\downloads\\'


# in: url youtube video
# out: path to file
def download_mp3(url, yt_obj=None):
    if len(url) == 11:
        urll = 'https://www.youtube.com/watch?v='+url
    else:
        urll = url

    if yt_obj == None:
        connects = 0
        while connects < 3:
            try:
                yt_obj = YouTube(urll)
                break

            except:
                connects += 1
        if connects >= 3:
            return '', 0


    # checking if file already downloaded (not working)
    # new_name = getcwd()+'\\downloads\\'+yt_obj.title+'.mp3'
    # if path.isfile(new_name):
    #     return new_name

    # more than 54 mins, so file will be more than 50 Mb
    if yt_obj.length > 3240:
        stream_num = (len(yt_obj.streams.filter(only_audio=True)) - 1) if len(yt_obj.streams.filter(only_audio=True)) < 3 else 2
        yt_stream = yt_obj.streams.filter(only_audio=True)[stream_num]
        end_name = 4
    else:
        yt_stream = yt_obj.streams.filter(only_audio=True).first()
        end_name = 3

    tries = 0
    while tries <= 3:
        try:
            ytd = yt_stream.download(Download_folder)
            break
        except:
            tries += 1

    # failed to download
    if tries >= 3:
        try:
            if stat(ytd).st_size <= 1:
                remove(ytd)
        except:
            pass

        return '', 0

    new_name = ytd[:-end_name]+'mp3'
    try:
        if stat(ytd).st_size <= 1:
            remove(ytd)
        else:
            try:
                remove(new_name)
            except:
                pass
            finally:
                rename(ytd, new_name)
    except:
        return '', 0

    return new_name, int(yt_obj.length/60)


# downloading file from telegram (scripts, settings...)
# in: file id, directory to save file
def download_file(bot, msg, dir):
    # file = bot.get_file(msg.document.file_id)
    # receive = get('https://api.telegram.org/file/bot{}/{}'.format(bot.token, file.file_path))
    # with open(dir+msg.document.file_name, 'wb') as f:
    #     f.write(receive.content)
    pass
