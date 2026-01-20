import os
import sys
from pathlib import Path
import re
import pandas as pd


def reorder_text(df, time_step=120):
    new = []
    cur_start_time = 0
    cur_max_time = time_step
    cur_text = []
    for i in range(len(df)):
        start = df.loc[i, 'start']
        end = df.loc[i, 'end']
        text = df.loc[i, 'text']
        if text is None:
            continue
        if end < cur_max_time:
            cur_text.append(text.strip())
        else:
            text_chunk = ' '.join(cur_text).replace('  ', ' ').strip()
            if len(text_chunk) > 4:
                new.append([cur_start_time, start, text_chunk])
            cur_start_time = start
            cur_max_time = start + time_step
            cur_text = [text.strip()]

    # Add the remaining text
    if cur_text:
        text_chunk = ' '.join(cur_text).replace('  ', ' ').strip()
        if len(text_chunk) > 4:
            new.append([cur_start_time, df.iloc[-1]['end'], text_chunk])

    ds = pd.DataFrame(new, columns=['start', 'end', 'text'])
    ds = ds[ds['text'].notna()].reset_index(drop=True)
    return ds


def timestamp_to_seconds(ts):
    """Converts HH:MM:SS.mmm to total seconds as a float."""
    h, m, s = ts.split(':')
    total = int(h) * 3600 + int(m) * 60 + float(s)
    return round(total, 3)  # Fixes the 0.999999999 noise


def recognize_audio_api(file_path) -> pd.DataFrame:
    """
    Transform .vtt file to DataFrame
    """

    if not os.path.exists(file_path):
        print(f"Warning: VTT file not found at {file_path}")
        return pd.DataFrame()

    # List of phrases to strictly remove
    junk_phrases = [
        r"\[музыка\]",
        r"Махон\s?Меир",
        r"Иудаизм с любовью",
        r"^Yeah\.$",
        r"^am$",
    ]
    # Combine into a single regex pattern
    junk_pattern = re.compile("|".join(junk_phrases), re.IGNORECASE)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into blocks (divided by double newlines)
    blocks = content.strip().split('\n\n')

    data = []
    last_text_lines = set()
    timestamp_re = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})')

    for block in blocks:
        lines = [line.strip() for line in block.split('\n')]

        # Find timestamp line
        time_match = None
        text_start_idx = 0
        for i, line in enumerate(lines):
            if "-->" in line:
                time_match = timestamp_re.search(line)
                text_start_idx = i + 1
                break

        if not time_match:
            continue

        start_str, end_str = time_match.groups()
        start_sec = timestamp_to_seconds(start_str)
        end_sec = timestamp_to_seconds(end_str)

        # Clean tags and extract unique text
        current_block_text = []
        for line in lines[text_start_idx:]:
            # Clean tags and entities
            clean_line = re.sub(r'<[^>]+>', '', line)
            clean_line = clean_line.replace('&gt;', '').replace('&lt;', '').strip()

            # Deduplication
            if clean_line and clean_line not in last_text_lines:
                current_block_text.append(clean_line)

        # Only add to data if there is actual new text
        if current_block_text:
            combined_text = " ".join(current_block_text)
            if not junk_pattern.search(combined_text):
                data.append({
                    'start': start_sec,
                    'end': end_sec,
                    'text': combined_text
                })
            # Store these lines to compare with the next block
            last_text_lines = set(current_block_text)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Merge timing gaps (Stretch 'end' time to the 'start' time of the next row)
    if not df.empty:
        df['end'] = df['start'].shift(-1).fillna(df['end'])

    return df


def main():
    if len(sys.argv) != 3:
        print("Usage: python clean_vtt.py input.vtt output.csv")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: input file '{input_path}' does not exist.")
        sys.exit(1)

    df = recognize_audio_api(input_path)

    if not df.empty:
        df = reorder_text(df)

        df.to_csv(output_path, index=False)
        print(f"Success: Saved to {output_path}")
    else:
        print("Error: No data found or file missing.")


if __name__ == '__main__':
    main()