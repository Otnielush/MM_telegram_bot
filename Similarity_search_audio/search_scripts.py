import logging

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.retrievers import HybridRetriever
from neo4j_graphrag.types import RetrieverResultItem

from mmtelegrambot.settings import OPENAI_KEY, NEO4J_URI, NEO4J_DB, NEO4J_AUTH, NEO4J_embd_index, NEO4J_fulltext_index

logger = logging.getLogger(__name__)


def _record_formatter(record) -> RetrieverResultItem:
    # Keep node properties as a dict instead of the default str(node) repr,
    # which cannot be reliably parsed back (quotes inside lesson text break it).
    node = dict(record.get("node") or {})
    return RetrieverResultItem(
        content=node.get("text", ""),
        metadata={**node, "score": record.get("score")},
    )


driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, max_connection_pool_size=25)
embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_KEY)
retriever = HybridRetriever(
    driver=driver,
    vector_index_name=NEO4J_embd_index,
    fulltext_index_name=NEO4J_fulltext_index,
    embedder=embedder,
    neo4j_database=NEO4J_DB,
    # retrieval_query=query_sim,
    return_properties=["lesson_name", "time_start", "time_end", "upload_date", "youtube_id", "text", "part"],
    result_formatter=_record_formatter,
)



def similarity_search(query, top_k=10) -> list[dict]:
    retriever_result = retriever.search(query_text=query, top_k=30)
    result = []
    for r in retriever_result.items[:top_k]:
        data = r.metadata
        try:
            result.append({"lesson_name": data['lesson_name'], "part": data['part'],
                           "start": data['time_start'], "end": data['time_end'],
                           "upload_date": data['upload_date'], "yt_id": data['youtube_id'],
                           "score": round(data['score'], 3), "text": data['text']})
        except (KeyError, TypeError) as e:
            logger.warning('similarity_search: skipping malformed result %s: %r', e, data)

    return result




if __name__ == '__main__':
    q = "Что такое цдака?"
    res = similarity_search(q)

    for r in res:
        print(r)
