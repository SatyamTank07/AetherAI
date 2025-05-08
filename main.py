import os
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from langchain_core.documents import Document
import hashlib
import time

# Step 0: Verify API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set. Please set it.")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY environment variable is not set. Please set it.")

# Step 1: Load and split PDF
pdf_path = r"Data\Docs\attention-is-all-you-need-Paper.pdf"
loader = PyPDFLoader(pdf_path)
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = text_splitter.split_documents(documents)

# Step 2: Initialize embedding model
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Step 3: Initialize Pinecone and manage index
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "mineai"  # Your Pinecone index name

# Generate file hash for duplicate checking
file_name = Path(pdf_path).name
with open(pdf_path, "rb") as f:
    file_content = f.read()
file_hash = hashlib.sha256(file_content).hexdigest()

# Add metadata to each chunk
for chunk in chunks:
    chunk.metadata.update({
        "file_name": file_name,
        "file_hash": file_hash
    })

# Check if index exists, create if it doesn't
try:
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=384,  # Matches sentence-transformers/all-MiniLM-L6-v2
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")  # Adjust region
        )
        # Wait for index to be ready
        time.sleep(10)
except Exception as e:
    raise ValueError(f"Failed to create Pinecone index: {e}")

# Step 4: Check for duplicates and connect to Pinecone vector store
try:
    index = pc.Index(index_name)
    # Query Pinecone to check if file_hash already exists
    query_result = index.query(
        vector=[0] * 384,  # Dummy vector for metadata query
        filter={"file_hash": {"$eq": file_hash}},
        top_k=1,
        include_metadata=True
    )

    if query_result["matches"]:
        print(f"Duplicate file detected with hash {file_hash}. Skipping upload.")
        vector_store = PineconeVectorStore(
            index_name=index_name,
            embedding=embeddings,
            pinecone_api_key=PINECONE_API_KEY
        )
    else:
        vector_store = PineconeVectorStore.from_documents(
            documents=chunks,
            embedding=embeddings,
            index_name=index_name,
            pinecone_api_key=PINECONE_API_KEY
        )
except Exception as e:
    raise ValueError(f"Failed to initialize Pinecone vector store: {e}")

# Step 5: Load LLM (Groq API) and define prompt
llm = ChatGroq(
    model="llama3-8b-8192",  # Groq-hosted LLaMA 3 model
    api_key=GROQ_API_KEY
)
prompt = PromptTemplate(
    input_variables=["context", "question"],
    template="Context: {context}\nQuestion: {question}\nAnswer:"
)

print("----------------------------------------------")
print(prompt)

# Step 6: RAG Query function
def rag_query(question, file_hash=None):
    # Embed the question
    query_embedding = embeddings.embed_query(question)
    
    # Query Pinecone with optional metadata filter
    index = pc.Index(index_name)
    # filter = {"file_hash": {"$eq": file_hash}} if file_hash else None
    query_result = index.query(
        vector=query_embedding,
        top_k=5,
        include_metadata=True,
        # filter=filter  # Uncomment if you want to filter by file_hash and for specific file
    )
    
    # Generate context from retrieved documents
    docs = []
    for match in query_result["matches"]:
        doc = Document(
            page_content=match["metadata"].get("text", ""),  # Assuming text stored in metadata
            metadata={
                "file_name": match["metadata"].get("file_name", ""),
                "file_hash": match["metadata"].get("file_hash", ""),
                "score": match["score"]
            }
        )
        docs.append(doc)
    
    # Create context with content and metadata
    context_parts = []
    for doc in docs:
        content = doc.page_content
        file_name = doc.metadata["file_name"]
        score = doc.metadata["score"]
        context_parts.append(f"Source: {file_name} (Score: {score:.4f})\n{content}")
    context = "\n\n".join(context_parts)
    
    print("Question :")
    print("----------------------------------------------")
    print(question)
    
    print("Context:")
    print("----------------------------------------------")
    print(context)

    return llm.invoke(prompt.format(context=context, question=question)).content

# Step 7: Test query
result = rag_query("What is the paper about? Say in 2 points")
print("Answer:")
print("----------------------------------------------")
print(result)