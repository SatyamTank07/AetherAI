from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone, ServerlessSpec
from langchain_groq import ChatGroq
from scripts.config import load_config
import time

class CInitialize():
    def __init__(self):
        config = load_config()
        self.EmbeddingModel = config["EmbeddingModel"]
        self.PINECONE_API_KEY = config["PINECONE_API_KEY"]
        self.GROQ_API_KEY = config["GROQ_API_KEY"]
        self.LLM_Model = config["LLM_Model"]
        
        
    def MInitializeEmbeddings(self):        
        """Initialize the embedding model."""
        return HuggingFaceEmbeddings(model_name=self.EmbeddingModel)
    
    def MInitializePinecone(self, MineaiIndexName):
        """Initialize Pinecone and create index if it doesn't exist."""
        
        objPinecone = Pinecone(api_key=self.PINECONE_API_KEY)
        
        if MineaiIndexName not in objPinecone.list_indexes().names():
            objPinecone.create_index(
                name=MineaiIndexName,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            time.sleep(5)
        
        return objPinecone
    
    def MInitializeLLM(self):
        """Initialize the LLM with Groq API."""
        return ChatGroq(
            model=self.LLM_Model,
            api_key= self.GROQ_API_KEY
        )
      