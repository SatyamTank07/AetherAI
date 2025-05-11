from langchain.memory import VectorStoreRetrieverMemory
from langchain_pinecone import PineconeVectorStore
from scripts.config import load_config


class CMemoryManager:
    def __init__(self, embeddings):
        """Initialize VectorStoreRetrieverMemory with Pinecone vector store."""
        config = load_config()
        self.memory_vector_store = PineconeVectorStore(
            index_name=config["MineaiIndexName"],
            embedding=embeddings,
            pinecone_api_key=config["PINECONE_API_KEY"],
            namespace=config["NameSpace"]
        )
        self.memory = VectorStoreRetrieverMemory(
            retriever=self.memory_vector_store.as_retriever(search_kwargs={"k": 3}),
            memory_key="conversation_history",
            return_docs=True
        )

    def MSaveConversation(self, question, answer):
        """Save a question-answer pair to the conversation history."""
        
        # Also save context into LangChain memory
        self.memory.save_context({"question": question}, {"answer": answer})


    def MGetConversationContext(self, question):
        """Retrieve relevant conversation history for the given question."""
        history_docs = self.memory.load_memory_variables({"prompt": question})["conversation_history"]
        if isinstance(history_docs, list):
            history_parts = [doc.page_content for doc in history_docs]
            return "\n\n".join(history_parts)
        return history_docs if history_docs else ""