import os
import pandas as pd
from neo4j import GraphDatabase
import re

import openai
from tqdm.auto import tqdm
from mmtelegrambot.settings import OPENAI_KEY, NEO4J_URI, NEO4J_DB, NEO4J_AUTH

# from dotenv import load_dotenv, find_dotenv
# load_dotenv()
#
# # prod env if DEBUG
# if os.getenv("DEBUG", "True").lower() == 'false':
#     load_dotenv(find_dotenv(".env.prod"), override=True)
          

Client = openai.OpenAI(api_key=OPENAI_KEY)

def get_embeddings(text, model='text-embedding-3-small'):
    if isinstance(text, str):
        text = [text]
    out = Client.embeddings.create(input = text, model=model)
    return [o.embedding for o in out.data]



def parse_folder(folder_path):
    return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('csv')]


def parse_link_date_from_csv(filename: str):
    link = re.search(r"(\[[^\]]+\])\.", filename)
    link = link.group(1)[1: -1] if link else ''

    date = re.search(r" #([^#]+)# ", filename)
    date = date.group(1) if date else ''
    return link, date


def insert_dataframe_to_db(dataframe: pd.DataFrame, filename: str, database_: str=None, driver: GraphDatabase=None):
    texts = dataframe.loc[:, 'text'].tolist()

    embeddings = get_embeddings(texts)
    youtube_link, upload_date = parse_link_date_from_csv(filename=filename)
    upload_date_sorting = int(''.join(upload_date.split('-')[::-1]))
    name = os.path.splitext(filename)[0].split(' #')[0]
    properties = {"name": name, "rav": None, "youtube_id": youtube_link,
                  "upload_date": upload_date, "_date_sort": upload_date_sorting}

    database_ = NEO4J_DB if database_ is None else database_
    driver_close = False
    if driver is None:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, max_connection_pool_size=5)
        driver.verify_connectivity()
        driver_close = True

    lesson_node = driver.execute_query("CREATE (a:Lesson) SET a += $props RETURN a", props=properties,
                                       database_=database_)
    lesson_element_id = lesson_node[0][0]['a'].element_id
    for idx in range(len(texts)):
        if len(texts[idx].strip()) == 0:
            continue
        properties = {"lesson_name": name, 'part': idx + 1, "embeddings": embeddings[idx], "text": texts[idx],
                      'time_start': dataframe.loc[idx, 'start'], "time_end": dataframe.loc[idx, 'end'], "youtube_id": youtube_link,
                      "upload_date": upload_date, "_date_sort": upload_date_sorting}

        summary = driver.execute_query("""CREATE (txt:Part)
                SET txt += $props
                    WITH txt
                    MATCH (les)
                    WHERE elementId(les) = $les_element_id
                    WITH les, txt
                    CREATE (les)-[:Text_part]->(txt)
                    """, props=properties, les_element_id=lesson_element_id,
                                       database_=database_)

    if driver_close:
        driver.close()


def process_paths_to_database(paths):
    cur_file = tqdm(paths)
    for file_path in cur_file:
        cur_file.set_description(os.path.basename(file_path)[:40])
        ds = pd.read_csv(file_path)
        filename = os.path.basename(file_path)
        insert_dataframe_to_db(dataframe=ds, filename=filename)



if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--folder", default='', help="Parses folder for csv files reads and inserts to database")
    parser.add_argument("--path", default='', help='Reads single file and inserts to database')   
    args = parser.parse_args()
    
    assert args.folder != '' or args.path != '', "One of 'folder' or 'path' parameters must be passed"

    paths = []
    if args.folder != '':
        paths.extend(parse_folder(args.folder))
    if args.path != '':
        paths.append(args.path)

    process_paths_to_database(paths=paths)