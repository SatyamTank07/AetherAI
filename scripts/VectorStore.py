from helper.logConfig import get_logger
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from Initialize import CInitialize
from config import load_config
from pinecone import Pinecone
import hashlib

logger = get_logger("VectorStore")

class CVectorStore:
    def __init__(self):
        config = load_config()
        # Validate config keys
        if "MINEAI_INDEX_NAME" not in config or "PINECONE_API_KEY" not in config:
            logger.error("Missing required configuration keys in config file.")
            raise KeyError("Missing required configuration keys in config file.")
        self.MINEAI_INDEX_NAME: str = config["MINEAI_INDEX_NAME"]
        self.PINECONE_API_KEY: str = config["PINECONE_API_KEY"]

    def MGenerateFileHash(self, PDFPath: str) -> str:
        """Generate a hash for the PDF file."""
        try:
            with open(PDFPath, 'rb') as f:
                hasher = hashlib.sha256()
                while chunk := f.read(8192):
                    hasher.update(chunk)
                logger.info(f"Generated file hash for {PDFPath}")
                return hasher.hexdigest()
        except FileNotFoundError:
            logger.error(f"PDF file not found: {PDFPath}")
            raise FileNotFoundError(f"PDF file not found: {PDFPath}")
        except Exception as e:
            logger.error(f"Unexpected error generating file hash: {e}")
            raise

    def MPDFLoader(self, PDFPath: str) -> list:
        """Load PDF file and return documents."""
        try:
            loader = PyPDFLoader(PDFPath)
            documents = loader.load()
            logger.info(f"Loaded PDF file: {PDFPath} with {len(documents)} documents.")
            return documents
        except Exception as e:
            logger.error(f"Error loading PDF file: {PDFPath}, Error: {e}")
            raise

    def MCreateChunks(self, documents: list) -> list:
        """Create text chunks from documents."""
        try:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = text_splitter.split_documents(documents)
            logger.info(f"Created {len(chunks)} chunks from documents.")
            return chunks
        except Exception as e:
            logger.error(f"Error creating chunks from documents: {e}")
            raise

    def MLoadAndCreateChunks(self, PDFPath: str) -> list:
        """Load PDF and split into chunks."""
        documents = self.MPDFLoader(PDFPath)
        return self.MCreateChunks(documents)

    def MStoreInPineconeDB(self, embedding, chunks: list, FileHash: str):
        """NOTE : Store chunks in Pinecone."""
        try:
            res = PineconeVectorStore.from_documents(
                documents=chunks,
                embedding=embedding,
                index_name=self.MINEAI_INDEX_NAME,
                pinecone_api_key=self.PINECONE_API_KEY,
                namespace=FileHash
            )
            logger.info(f"Stored {len(chunks)} chunks in Pinecone DB under namespace {FileHash}.")
            return res
        except Exception as e:
            logger.error(f"Error storing in Pinecone DB: {e}")
            raise

    def MIsFileHashUnique(self, FileHash: str) -> bool:
        """Check if the file hash (namespace) already exists in the Pinecone index."""
        try:
            pc = Pinecone(api_key=self.PINECONE_API_KEY)
            index = pc.Index(self.MINEAI_INDEX_NAME)
            # Query for any vector in the namespace (file hash)
            query_result = index.query(
                vector=[0.0] * 384,  # dummy vector, dimension should match your embeddings
                namespace=FileHash,
                top_k=1,
                include_metadata=False
            )
            # If there are matches, the file hash (namespace) is not unique
            is_unique = not bool(query_result.get('matches'))
            logger.info(f"File hash '{FileHash}' unique: {is_unique}")
            return is_unique
        except Exception as e:
            logger.error(f"Error checking uniqueness of file hash '{FileHash}': {e}")
            raise

    def MStoreFileInVectorDB(self, PDFPath: str):
        """Main method to store file in vector DB if not already stored."""
        FileHash = self.MGenerateFileHash(PDFPath)
        if not self.MIsFileHashUnique(FileHash):
            logger.info(f"File with hash {FileHash} already exists in the vector DB. Skipping store.")
            return True
        chunks = self.MLoadAndCreateChunks(PDFPath)
        embedding = CInitialize().MInitializeEmbeddings()
        result = self.MStoreInPineconeDB(embedding, chunks, FileHash)
        return result

def main():
    PDFPath = r"Data\Docs\PEFT.pdf"
    objVectorDB = CVectorStore()
    status = objVectorDB.MStoreFileInVectorDB(PDFPath)
    if status:
        print(f"File stored successfully in vector DB. {status}")
    else:
        print(f"Failed to store file in vector DB. {status}")

if __name__ == "__main__":
    main()