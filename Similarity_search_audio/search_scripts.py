from neo4j import GraphDatabase
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.retrievers import HybridRetriever

from dataclasses import dataclass
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
    return_properties=["lesson_name", "time_start", "time_end", "upload_date", "youtube_id"],
)


@dataclass
class Result:
    lesson_name: str
    start: float
    end: float
    upload_date: str
    youtube_id: str
    search_score: float


def similarity_search(query, top_k=10):
    retriever_result = retriever.search(query_text=query, top_k=top_k)
    result = []
    for r in retriever_result.items:
        try:
            data = json.loads(r.content.replace("'", '"'))
        except Exception as e:
            print('similarity_search error:', e)
            continue
        result.append(Result(lesson_name=data['lesson_name'], start=data['time_start'], end=data['time_end'],
                             upload_date=data['upload_date'], youtube_id=data['youtube_id'],
                             search_score=round(r.metadata['score'], 3)))

    return result




if __name__ == '__main__':
    q = "Что такое цдака?"
    res = similarity_search(q)

    for r in res:
        print(r)