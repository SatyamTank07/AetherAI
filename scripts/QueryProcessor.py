from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from Initialize import CInitialize
from config import load_config


class CQueryProcessor():
    def __init__(self):
        config = load_config()        
        self.MineaiIndex = config["MineaiIndexName"]
    def MCreatePromptTemplate(self):
        """Create the prompt template for RAG queries."""
        return PromptTemplate(
            input_variables=["context", "question"],
            template="Context: {context}\nQuestion: {question}\nAnswer:"
        )

    def MRAGQuery(self, Query, pinecone, embeddings, llm, prompt_template):
        """Execute a RAG query with optional file_hash filter."""
        query_embedding = embeddings.embed_query(Query)
        mineai_index = pinecone.Index(self.MineaiIndex)
        
        query_result = mineai_index.query(
            vector=query_embedding,
            top_k=5,
            include_metadata=True
        )
        
        docs = [
            Document(
                page_content=match["metadata"].get("text", ""),
                metadata={
                    "file_name": match["metadata"].get("file_name", ""),
                    "file_hash": match["metadata"].get("file_hash", ""),
                    "score": match["score"]
                }
            )
            for match in query_result["matches"]
        ]
        
        context_parts = [
            f"Source: {doc.metadata['file_name']} (Score: {doc.metadata['score']:.4f})\n{doc.page_content}"
            for doc in docs
        ]
        context = "\n\n".join(context_parts)
        
        print("Query:")
        print("----------------------------------------------")
        print(Query)
        print("Context:")
        print("----------------------------------------------")
        print(context)
        
        return llm.invoke(prompt_template.format(context=context, question=Query)).content
    
    def MQueryProcess(self, Query):
        objInit = CInitialize()
        pinecone = objInit.MInitializePinecone(self.MineaiIndex)
        embeddings = objInit.MInitializeEmbeddings()
        llm = objInit.MInitializeLLM()
        prompt_template = self.MCreatePromptTemplate()
        Answer = self.MRAGQuery(Query, pinecone, embeddings, llm, prompt_template)
        return Answer