from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from Initialize import CInitialize
from config import load_config
import hashlib


class CVectorStore():
    def __init__(self):
        config = load_config()        
        self.MineaiIndexName = config["MineaiIndexName"]
        self.PINECONE_API_KEY = config["PINECONE_API_KEY"]
        
    def MLoadAndSplitDocuments(self, PDFPath=None):
        """Load PDF and split into chunks with metadata."""

        loader = PyPDFLoader(PDFPath)
        documents = loader.load()
        
        TextSpliter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        Chunks = TextSpliter.split_documents(documents)
        
        FileName = Path(PDFPath).name
        with open(PDFPath, "rb") as f:
            FileContent = f.read()
        FileHash = hashlib.sha256(FileContent).hexdigest()
        
        for chunk in Chunks:
            chunk.metadata.update({
                "file_name": FileName,
                "file_hash": FileHash
            })
        
        return Chunks, FileHash

    def MInitializeFileInVectorDB(self, objPinecone, embeddings, chunks, FileHash):
        """Initialize vector store, checking for duplicates."""
        MineIndex = objPinecone.Index(self.MineaiIndexName)
        QueryResult = MineIndex.query(
            vector=[0] * 384,
            filter={"file_hash": {"$eq": FileHash}},
            top_k=1,
            include_metadata=True
        )
        
        if QueryResult["matches"]:
            PineconeVectorStore(
                index_name=self.MineaiIndexName,
                embedding=embeddings,
                pinecone_api_key=self.PINECONE_API_KEY
            )
            return (f"Duplicate file detected with hash {FileHash}. Skipping upload.")
        else:    
            PineconeVectorStore.from_documents(
                documents=chunks,
                embedding=embeddings,
                index_name=self.MineaiIndexName,
                pinecone_api_key=self.PINECONE_API_KEY
            )
            return (f"File is succussfully store in vectorDB. with {FileHash} Hash ")
        
    def MStoreFileInVectorDB(self, PDFPath):
        objInit = CInitialize()
        Chunks, FileHash = self.MLoadAndSplitDocuments(PDFPath)
        Embedding = objInit.MInitializeEmbeddings()
        objPinecone = objInit.MInitializePinecone(self.MineaiIndexName)
        result = self.MInitializeFileInVectorDB(objPinecone, Embedding, Chunks, FileHash)
        return result