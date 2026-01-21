from neo4j import GraphDatabase
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.retrievers import HybridRetriever

import json

from mmtelegrambot.settings import OPENAI_KEY, NEO4J_URI, NEO4J_DB, NEO4J_AUTH, NEO4J_embd_index, NEO4J_fulltext_index


driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, max_connection_pool_size=25)
embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_KEY)
retriever = HybridRetriever(
    driver=driver,
    vector_index_name=NEO4J_embd_index,
    fulltext_index_name=NEO4J_fulltext_index,
    embedder=embedder,
    neo4j_database=NEO4J_DB,
    # retrieval_query=query_sim,
    return_properties=["lesson_name", "time_start", "time_end", "upload_date", "youtube_id", "text"],
)



def similarity_search(query, top_k=10):
    retriever_result = retriever.search(query_text=query, top_k=30)
    result = []
    for r in retriever_result.items[:top_k]:
        try:
            data = json.loads(r.content.replace("'", '"'))
        except Exception as e:
            print('similarity_search json parse error:', e)
            continue
        # result.append({"name": data['lesson_name'], "start":data['time_start'], "end":data['time_end'],
        #                      "upload_date":data['upload_date'], "yt_id":data['youtube_id'],
        #                      "score":round(r.metadata['score'], 3)})
        result.append(data['text'])

    return result




if __name__ == '__main__':
    q = "Что такое цдака?"
    res = similarity_search(q)

    for r in res:
        print(r)