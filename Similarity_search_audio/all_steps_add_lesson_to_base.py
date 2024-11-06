import os

from neo4j import GraphDatabase
from mmtelegrambot.settings import NEO4J_URI, NEO4J_DB, NEO4J_AUTH

from Similarity_search_audio.recognize_audio import recognize_audio_api, reorder_text
from Similarity_search_audio.embd_database import insert_dataframe_to_db, parse_link_date_from_csv


def is_youtube_link_in_base(yt_link: str, driver: GraphDatabase=None) -> bool:
    if driver is None:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, max_connection_pool_size=25)
        driver.verify_connectivity()
    resp, _, _ = driver.execute_query("MATCH (l:Lesson {youtube_id: $link}) RETURN COUNT(l) > 0 AS exists",
                                          link=yt_link, database_=NEO4J_DB)
    return bool(resp[0]['exists'])


def insert_audio_to_graph_base(file_path: str, database_: str=None, verbose=False):
    filename = os.path.basename(file_path)
    yt_link, _ = parse_link_date_from_csv(filename=filename)
    if is_youtube_link_in_base(yt_link=yt_link):
        if verbose: print(f'Func: insert_audio_to_graph_base -> youtube lesson already in base, link: {yt_link}')
        return

    ds = recognize_audio_api(file_path=file_path)
    if len(ds) == 0:
        print(f'Error, file not recognized: {file_path}')
    ds = reorder_text(ds)
    insert_dataframe_to_db(dataframe=ds, filename=filename, database_=database_)



def process_youtube_links_csv_to_database(path_csv, local=True, both_databases=False):
    import pandas as pd
    links = pd.read_csv(path_csv)['youtube_id'].tolist()

    from tqdm.auto import tqdm
    prog = tqdm(links)
    added = 0

    from Similarity_search_audio.get_audio import download_audio_youtube
    from Similarity_search_audio.recognize_audio import reorder_text, recognize_audio_api as recognize_audio
    if local:
        from Similarity_search_audio.local_speach_recognition import recognize_audio_local as recognize_audio
    tmp_folder = r"D:\Programming\My_reps\MM_telegram_bot\tmp_dev\tmp"
    os.makedirs(tmp_folder, exist_ok=True)


    driver_dev = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, max_connection_pool_size=20)
    driver_dev.verify_connectivity()
    if both_databases:
        from dotenv import find_dotenv, load_dotenv
        env_file = find_dotenv(".env.prod")
        load_dotenv(env_file, override=True)
        NEO4J_URI_ = os.getenv("NEO4J_URI")
        NEO4J_DB_ = os.getenv("NEO4J_DB")
        NEO4J_AUTH_ = tuple(item.strip() for item in os.getenv("NEO4J_AUTH").split(','))
        driver_prod = GraphDatabase.driver(NEO4J_URI_, auth=NEO4J_AUTH_, max_connection_pool_size=20)
        driver_prod.verify_connectivity()



    for link in prog:
        prog.set_description(f'added: {added}, current link: {link}')
        prog.refresh()
        if is_youtube_link_in_base(link, driver=driver_dev):
            continue

        errors = download_audio_youtube(links=link, output_folder=tmp_folder)
        if len(errors) > 0:
            continue
        filename = [f for f in os.listdir(tmp_folder) if f.endswith('m4a')][0]
        file_path = os.path.join(tmp_folder, filename)
        ds = recognize_audio(file_path=file_path)
        ds = reorder_text(df=ds)


        insert_dataframe_to_db(dataframe=ds, filename=filename, database_=NEO4J_DB, driver=driver_dev)
        if both_databases:
            insert_dataframe_to_db(dataframe=ds, filename=filename, database_=NEO4J_DB_, driver=driver_prod)


        os.remove(file_path)
        added += 1

        # if added >= 3:
        #     break


    import shutil
    shutil.rmtree(tmp_folder)




if __name__ == '__main__':
    if False:  # test
        print(f'{is_youtube_link_in_base("PkhDrhmurdo") = } | True')
        print(f'{is_youtube_link_in_base("Pkxxxxxdo") = } | False')

        NEO4J_DB = 'manual'
        insert_audio_to_graph_base(r"C:\Users\Otniel\Downloads\tests\Bot made with ChatGPT ｜ Detailed Instructions #26-10-2024# [ICDJv6w9DtU].m4a",
                                   database_=NEO4J_DB, verbose=True)

    if True: # fill database from csv links file
        process_youtube_links_csv_to_database(r"D:\Programming\My_reps\MM_telegram_bot\tmp_dev\lessons.csv",
                                              local=True, both_databases=True)




