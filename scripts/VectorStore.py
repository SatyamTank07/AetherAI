from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from scripts.Initialize import CInitialize
from scripts.config import load_config
import hashlib

class CVectorStore:
    def __init__(self):
        config = load_config()
        self.MineaiIndexName = config["MineaiIndexName"]
        self.PINECONE_API_KEY = config["PINECONE_API_KEY"]

    def MLoadAndSplitDocuments(self, PDFPath):
        """Load PDF and split into chunks with metadata."""
        # NOTE : Make diffrant for all : load - split - HASH - METADATA 
        loader = PyPDFLoader(PDFPath)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)

        file_name = Path(PDFPath).name
        with open(PDFPath, "rb") as f:
            file_content = f.read()
        file_hash = hashlib.sha256(file_content).hexdigest()

        for chunk in chunks:
            chunk.metadata.update({
                "file_name": file_name,
                "file_hash": file_hash
            })

        return chunks, file_hash

    def MInitializeFileInVectorDB(self, obj_pinecone, embeddings, chunks, file_hash):
        """Initialize vector store under namespace derived from file hash."""
        # NOTE : Make diffrant for all : CheckDuplicate - Store 
        # NOTE : Return Some Valid and good
        namespace = file_hash
        mine_index = obj_pinecone.Index(self.MineaiIndexName)

        query_result = mine_index.query(
            vector=[0] * 384,
            filter={"file_hash": {"$eq": file_hash}},
            namespace=namespace,
            top_k=1,
            include_metadata=False
        )

        if query_result["matches"]:
            return f"Duplicate file detected in namespace '{namespace}'. Skipping upload.", namespace

        PineconeVectorStore.from_documents(
            documents=chunks,
            embedding=embeddings,
            index_name=self.MineaiIndexName,
            pinecone_api_key=self.PINECONE_API_KEY,
            namespace=namespace
        )
        return f"File stored in vectorDB under namespace '{namespace}' with hash {file_hash}", namespace

    def MStoreFileInVectorDB(self, PDFPath):
        """Main method to store file in vector DB if not already stored."""
        obj_init = CInitialize()
        chunks, file_hash = self.MLoadAndSplitDocuments(PDFPath)
        embedding = obj_init.MInitializeEmbeddings()
        obj_pinecone = obj_init.MInitializePinecone(self.MineaiIndexName)
        result, namespace = self.MInitializeFileInVectorDB(obj_pinecone, embedding, chunks, file_hash)
        return result, namespace
