from helper.logConfig import get_logger
from Initialize import CInitialize
from config import load_config

config = load_config()
logging = get_logger("Retrival")
class CRetrival:
    
    def __init__(self):
        """Initialize the retriever with embeddings and Pinecone index."""
        try:
            objInit = CInitialize()
            self.embeddings = objInit.MInitializeEmbeddings()
            self.pinecone = objInit.MInitializePinecone(config["MINEAI_INDEX_NAME"])
            logging.info("CRetrival initialized successfully.")
        except Exception as e:
            logging.error(f"Error during CRetrival initialization: {e}")
            raise

    def MRetrivTopk(self,namespace, query, topk):
        """Retrieve top-k results for a given query from the specified namespace."""
        
        try:
            query_embedding = self.embeddings.embed_query(query)
            QueryResult = self.pinecone.query(
                vector=query_embedding,
                top_k=topk,
                include_metadata=True,
                namespace= namespace
            )
            matches = QueryResult.get("matches", [])
            if not matches:
                logging.warning(f"No matches found for query: '{query}' in namespace: '{namespace}'")
            retriveTopK = [
                match["metadata"].get("text", "")
                for match in matches
            ]
            logging.info(f"Retrieved {len(retriveTopK)} results for query: '{query}'")
            return retriveTopK
        except Exception as e:
            logging.error(f"Error during retrieval: {e}")
            return []
    
def main():
    retrival = CRetrival()
    namespace = "3cca71e666ef6e0d7b33cb88ee2e9f6ff9a4041b35b5315df47edea5a25f05fb"
    query = "What is Selef Attention ?"
    topk = 5
    
    results = retrival.MRetrivTopk(namespace, query, topk)
    print("Top-k results:", results)
    
if __name__ == "__main__":
    main()