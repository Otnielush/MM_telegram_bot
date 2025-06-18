from neo4j import GraphDatabase
import openai
from mmtelegrambot.settings import OPENAI_KEY, NEO4J_URI, NEO4J_DB, NEO4J_AUTH, NEO4J_embd_index


client = openai.OpenAI(api_key=OPENAI_KEY)


def get_embeddings(text, model='text-embedding-3-small'):
    if isinstance(text, str):
        text = [text]
    out = client.embeddings.create(input = text, model=model)
    return [o.embedding for o in out.data]


query_sim = """CALL db.index.vector.queryNodes($vector_index_name, 30, $query_vector) YIELD node, score 
RETURN node.lesson_name AS lesson_name, node.time_start AS start, node.time_end AS end, node.upload_date AS upload_date, 
node.youtube_id AS youtube_id, round(score * 1000) / 1000 AS search_score LIMIT $top_k
"""

hybrid_search_example = (
        "CALL { "
        "CALL db.index.vector.queryNodes($index, $k, $embedding) "
        "YIELD node, score "
        "WITH collect({node:node, score:score}) AS nodes, max(score) AS max "
        "UNWIND nodes AS n "
        # We use 0 as min
        "RETURN n.node AS node, (n.score / max) AS score UNION "
        "CALL db.index.fulltext.queryNodes($keyword_index, $query, {limit: $k}) "
        "YIELD node, score "
        "WITH collect({node:node, score:score}) AS nodes, max(score) AS max "
        "UNWIND nodes AS n "
        # We use 0 as min
        "RETURN n.node AS node, (n.score / max) AS score "
        "} "
        # dedup
        "WITH node, max(score) AS score ORDER BY score DESC LIMIT $k "
    )


def similarity_search(query, top_k=10):
    embeddings = get_embeddings(query)[0]
    with GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, max_connection_pool_size=25) as driver:
        result, _, _ = driver.execute_query(query_sim, vector_index_name=NEO4J_embd_index, top_k=top_k,
                                            query_vector=embeddings, database_=NEO4J_DB)
    return result



if __name__ == '__main__':
    q = "Что такое цдака?"
    res = similarity_search(q)

    for r in res:
        print(r)