from django.core.management.base import BaseCommand
from youtuber.models import Lesson
import os
import unicodedata
from mmtelegrambot.settings import MEDIA_ROOT
import yt_dlp
import time
from datetime import datetime

class Command(BaseCommand):
    help = 'Download audio track from YouTube lesson'

    def handle(self, *args, **options):
        """
        Check for saved lessons without audio and download first of them
        """
        lessons_without_audio = Lesson.objects.filter(is_published=False, is_downloaded=False, skip=False)

        if len(lessons_without_audio) > 0:
            lesson = lessons_without_audio.last()
            youtube_id = lesson.youtube_id
            youtube_url = f'http://youtube.com/watch?v={youtube_id}'

            def format_selector(ctx):
                formats = ctx.get('formats')[::-1]
                # Filter only m4a formats
                m4a_formats = [f for f in formats if f.get('ext') == 'm4a']

                if not m4a_formats:
                    return None

                # Sort by quality metrics (preferring higher values)
                best_format = max(m4a_formats, key=lambda x: (
                    x.get('abr', 0),  # average bitrate
                    x.get('asr', 0),  # audio sampling rate
                    x.get('filesize', 0)  # file size as a last resort
                ))

                return [best_format]

            ydl_opts = {
                'format': format_selector,
                'outtmpl': os.path.join(MEDIA_ROOT, 'audio', '%(id)s.%(ext)s'),
                "quiet": True,
                "no_warnings": True
            }

            retry_count = 3
            for attempt in range(retry_count):
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info(youtube_url, download=False)
                        title = unicodedata.normalize('NFC', info_dict.get('title', ''))
                        duration = info_dict.get('duration', 0)
                        upload_date_str = info_dict.get('upload_date', '')
                        upload_date = (
                            datetime.strptime(upload_date_str, "%Y%m%d")
                            if upload_date_str 
                            else None
                        )

                        error_code = ydl.download(youtube_url)

                        audio_file = f"audio/{youtube_id}.m4a"
                        audio_file_path = os.path.join(MEDIA_ROOT, audio_file)

                        # Check file size and compress if needed
                        file_size = os.path.getsize(audio_file_path)
                        max_size = 50 * 1024 * 1024  # 50MB

                        if file_size > max_size:
                            compressed_path = os.path.join(MEDIA_ROOT, 'audio', f'{youtube_id}_compressed.m4a')

                            # Start with a moderate bitrate
                            target_bitrate = "128k"

                            while True:
                                # Use ffmpeg to compress the file
                                import subprocess
                                # First, analyze the audio to get volume statistics
                                analyze_cmd = [
                                    'ffmpeg', '-i', audio_file_path,
                                    '-af', 'volumedetect',
                                    '-f', 'null', '-'
                                ]
                                result = subprocess.run(analyze_cmd, capture_output=True, text=True)

                                # Extract mean volume from the analysis
                                mean_volume = None
                                for line in result.stderr.split('\n'):
                                    if 'mean_volume:' in line:
                                        mean_volume = float(line.split(':')[1].strip().replace(' dB', ''))
                                        break

                                # Calculate volume adjustment (target: -14 dB, which is a good standard)
                                volume_adjust = '-14' if mean_volume is None else f"{-14 - mean_volume:.1f}"

                                # Compress with volume normalization
                                cmd = [
                                    'ffmpeg', '-y',  # -y to overwrite output file
                                    '-i', audio_file_path,
                                    '-af', f'volume={volume_adjust}dB',  # Apply volume adjustment
                                    '-c:a', 'aac',
                                    '-b:a', target_bitrate,
                                    compressed_path
                                ]

                                try:
                                    subprocess.run(cmd, check=True, capture_output=True)
                                except subprocess.CalledProcessError as e:
                                    print(f"FFmpeg error: {e.stderr.decode()}")
                                    raise

                                new_size = os.path.getsize(compressed_path)

                                if new_size <= max_size:
                                    # Replace original file with compressed version
                                    os.replace(compressed_path, audio_file_path)
                                    break
                                elif new_size > max_size:
                                    # If still too large, reduce bitrate and try again
                                    current_bitrate = int(target_bitrate.replace('k', ''))
                                    target_bitrate = f"{max(64, current_bitrate - 32)}k"
                                    # If we've reached minimum acceptable bitrate, use the last version
                                    if current_bitrate <= 64:
                                        os.replace(compressed_path, audio_file_path)
                                        break

                        # Saving results to DB
                        lesson.title = title
                        lesson.duration = duration
                        lesson.upload_date = upload_date
                        lesson.audio_file = audio_file
                        lesson.is_downloaded = True
                        lesson.save()

                        print(f'Successfully downloaded audio for lesson {title}')
                        break
                except Exception as e:
                    if attempt < retry_count - 1:
                        time.sleep(5)  # Wait before retrying
                        print(f'Retrying download for video {youtube_id} (attempt {attempt + 1}/{retry_count})')
                    else:
                        lesson.error_count = lesson.error_count + 1
                        lesson.save()

                        print(f'Error while processing video {youtube_id}:\n {e}.\nError count: {lesson.error_count}.')
        else:
            self.stdout.write(
                self.style.SUCCESS('No lessons without audio')
            )
