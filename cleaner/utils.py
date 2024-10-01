from neo4j import GraphDatabase
import openai
from mmtelegrambot.settings import OPENAI_KEY, NEO4J_URI, NEO4J_DB, NEO4J_AUTH
from youtuber.management.commands.send_lesson_to_telegram import make_youtube_link_msg
from cleaner.models import Question

VECTOR_INDEX_NAME = "lessons_text_embd"

def make_sim_search(q):
    # Connect to Neo4j database
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, max_connection_pool_size=25)
    driver.verify_connectivity()
    print("Connection established.")

    client = openai.OpenAI(api_key=OPENAI_KEY)

    def get_embedding(text, model='text-embedding-3-small'):
        if isinstance(text, str):
            text = [text]
        out = client.embeddings.create(input=text, model=model)
        return [o.embedding for o in out.data]

    query_sim = """CALL db.index.vector.queryNodes($vector_index_name, $top_k, $query_vector) YIELD node, score 
            RETURN node.lesson_name AS lesson_name, node.part AS part, node.time_start AS start, node.time_end AS end, node.upload_date AS upload_date, 
            node.youtube_id AS youtube_id, round(score * 1000) / 1000 AS search_score 
            """

    embd = get_embedding(q)[0]
    result, _, _ = driver.execute_query(query_sim,
                                        vector_index_name=VECTOR_INDEX_NAME, top_k=10, query_vector=embd,
                                        database_=NEO4J_DB)
    return result

def save_result(message_id, user_id, sent_at, text, result):
    if len(result):
        results = []
        for item in result:
            results.append({
                "name": item["lesson_name"],
                "yt_id": item["youtube_id"],
                "part": item["part"],
                "score": item["search_score"]
            })
        try:
            Question.objects.create(
                message_id = message_id,
                user_id = user_id,
                sent_at = sent_at,
                text = text,
                result = results
            )
            return True
        except Exception as e:
            print(e)

    return False

def make_result_message(result):
    if len(result):
        item_strings = []
        for item in result:
            title = item["lesson_name"]
            youtube_id = item["youtube_id"]
            start_time = round(item["start"])
            end_time = round(item["end"]) if item["end"] > 0 else None
            upload_date = item["upload_date"]
            msg = make_youtube_link_msg(title, youtube_id, start_time, end_time, upload_date)
            item_strings.append(msg)
        return '\n\n'.join(item_strings)

    return "К сожалению, ничего не найдено"