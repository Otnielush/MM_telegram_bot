import os
from tqdm.auto import tqdm
import yt_dlp


Main_url = "https://www.youtube.com/watch?v="

Ydl_opts = {
    'format': 'm4a/bestaudio/best',
    # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
    'postprocessors': [{  # Extract audio using ffmpeg
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'm4a',
    }],
    "outtmpl": "%(title)s #%(upload_date>%d-%m-%Y)s# [%(id)s].%(ext)s",
    "quiet": True,
    "no_warnings": True
}




def download_audio_youtube(links, output_folder, verbose=False):
     links = [l.split('watch?v=')[-1] for l in links]  # leave only youtube video link

     os.chdir(os.path.abspath(output_folder))

     with yt_dlp.YoutubeDL(Ydl_opts) as ydl:
          errors = []
          cycle = tqdm(links, position=0)
          for link in cycle:
               cycle.set_description(link)
               path = Main_url + link
               try:
                    error_code = ydl.download(path)
               except:
                    errors.append(link)
                    if verbose:
                         print(error_code)
     return errors



if __name__ == '__main__':
     from argparse import ArgumentParser

     def parse_args():
          parser = ArgumentParser()
          parser.add_argument("--file", '-f', type=str, default='', help="reads txt file. 1 link in each row")
          parser.add_argument("--link", "-l", type=str, default='')
          parser.add_argument("--output_folder", "-o", type=str, required=True)
          parser.add_argument("--verbose", action='store_true')
          
          args = parser.parse_args()
          assert args.file != '' or args.link != '', "Need to pass or --file (-f) or --link (-l)"
          return args

     args = parse_args()

     links = []
     if args.file != '':
          with open(args.file, 'r') as f:
               links.extend([r.replace('\n', '') for r in f.readlines()])
     
     if args.link != '':
          links.append(args.link)
     
     errors = download_audio_youtube(links=links, output_folder=args.output_folder, verbose=args.verbose)

     if len(errors) > 0:
          print(f'Num errors: {len(errors)}')
          if args.verbose:
               print('Error links:\n', errors)