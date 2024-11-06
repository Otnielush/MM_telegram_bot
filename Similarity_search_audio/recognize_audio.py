import os
import pandas as pd
from tqdm.auto import tqdm
from mmtelegrambot.settings import LEMONFOX_key_ASR

import requests


def reorder_text(df, time_step=120):
    new = []
    cur_start_time = 0
    cur_max_time = time_step
    cur_text = []
    for i in range(len(df)):
        end = df.loc[i, 'end']
        text = df.loc[i, 'text']
        if end < cur_max_time:
            cur_text.append(text.strip())
        else:
            text_chunk = ' '.join(cur_text).replace('  ', ' ').strip()
            if len(text_chunk) > 4:
                new.append([cur_start_time, df.loc[i, 'start'], ])
            cur_start_time = df.loc[i, 'start']
            cur_max_time += time_step
            cur_text = [text.strip()]
    new.append([cur_start_time, end, ' '.join(cur_text).replace('  ', ' ')])
    return pd.DataFrame(new, columns=['start', 'end', 'text'])


def recognize_audio_api(file_path) -> pd.DataFrame:
    url = "https://api.lemonfox.ai/v1/audio/transcriptions"
    headers = {"Authorization": "Bearer " + LEMONFOX_key_ASR}
    data = {"response_format": "verbose_json"}
    
    audio_file = open(file_path, "rb")
    try:
        response = requests.post(url, headers=headers, files={'file': audio_file}, data=data).json()
        assert 'segments' in response
    except:
        return pd.DataFrame()
    ds = pd.DataFrame()    
    ds['start'] = [r['start'] for r in response['segments']]
    ds['end'] = [r['end'] for r in response['segments']]
    ds['text'] = [r['text'] for r in response['segments']]
    ds = ds[ds['text'].notna()]
    return ds



if __name__ == '__main__':
     from argparse import ArgumentParser

     parser = ArgumentParser()
     parser.add_argument("--local_model", '-l', action='store_true', help="If passed uses downloads model and runs local recognition, otherwise sends data to API")
     parser.add_argument("--paths", nargs='+')
     parser.add_argument("--interval", type=int, default=120)
     parser.add_argument("--output_folder", "-o", type=str, default='')
     
     args = parser.parse_args()
     

     if args.local_model:
        from local_speach_recognition import recognize_audio_local as recognize_audio
          
     else:
        recognize_audio = recognize_audio_api


     if args.output_folder != '':
          os.makedirs(args.output_folder, exist_ok=True)
          
     prog = tqdm(args.paths)
     for path in prog:
          prog.set_description(os.path.basename(path)[:40])

          ds = recognize_audio(path)
          if len(ds) == 0:
               continue

          ds = reorder_text(ds, time_step=args.interval)

          file_name = os.path.splitext(os.path.basename(path))[0] + ".csv"
          if args.output_folder == '':
               file_name = os.path.join(os.path.dirname(path), file_name)
          else:
               file_name = os.path.join(args.output_folder, file_name)
          ds.to_csv(file_name, index=False)
