from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from Initialize import CInitialize
from MemoryManager import CMemoryManager
from config import load_config

class CQueryProcessor:
    def __init__(self, namespace):
        config = load_config()
        self.MineaiIndex = config["MineaiIndexName"]
        self.NameSpace = namespace
    def MCreatePromptTemplate(self):
        """Create the prompt template for RAG queries with conversation history."""
        return PromptTemplate(
            input_variables=["context", "conversation_history", "question"],
            template="Conversation History:\n{conversation_history}\n\nDocument Context:\n{context}\n\nQuestion: {question}\nAnswer:"
        )

    def MRAGQuery(self, Query, pinecone, embeddings, llm, prompt_template, memory):
        """Execute a RAG query with conversation history."""
        query_embedding = embeddings.embed_query(Query)
        mineai_index = pinecone.Index(self.MineaiIndex)
        
        query_result = mineai_index.query(
            vector=query_embedding,
            top_k=5,
            namespace=self.NameSpace,
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
        
        # Retrieve conversation history
        conversation_history = memory.MGetConversationContext(Query)
        
        print("Query:")
        print("----------------------------------------------")
        print(Query)
        print("Conversation History:")
        print("----------------------------------------------")
        print(conversation_history or "No relevant history found.")
        print("Context:")
        print("----------------------------------------------")
        print(context)
        
        # Generate answer
        answer = llm.invoke(prompt_template.format(
            context=context,
            conversation_history=conversation_history,
            question=Query
        )).content
        
        # Save conversation to memory
        memory.MSaveConversation(Query, answer)
        
        return answer
    
    def MQueryProcess(self, Query):
        """Process a query with optional memory for conversation history."""
        objInit = CInitialize()        
        pinecone = objInit.MInitializePinecone(self.MineaiIndex)
        embeddings = objInit.MInitializeEmbeddings()
        
        memory = CMemoryManager(embeddings)
         
        llm = objInit.MInitializeLLM()
        prompt_template = self.MCreatePromptTemplate()
        return self.MRAGQuery(Query, pinecone, embeddings, llm, prompt_template, memory)
