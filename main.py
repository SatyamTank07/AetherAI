import os
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Step 0: Verify Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set. Please set it.")

# Step 1: Load and split PDF
pdf_path = r"Data\Docs\attention-is-all-you-need-Paper.pdf"
loader = PyPDFLoader(pdf_path)
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = text_splitter.split_documents(documents)

# Step 2: Initialize embedding model
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Step 3: Create dynamic directory based on PDF name
pdf_name = Path(pdf_path).stem
VECTOR_STORE_PATH = os.path.join("Data", "Embedding", pdf_name)

os.makedirs(VECTOR_STORE_PATH, exist_ok=True)

# Step 4: Save/load FAISS vector store
if os.path.exists(os.path.join(VECTOR_STORE_PATH, "index.faiss")):
    vector_store = FAISS.load_local(
        VECTOR_STORE_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )
else:
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(VECTOR_STORE_PATH)

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
def rag_query(question):
    docs = vector_store.similarity_search(question, k=5)
    context = "\n".join([doc.page_content for doc in docs])
    
    print("Context:")
    print("----------------------------------------------")
    print(context)

    return llm.invoke(prompt.format(context=context, question=question)).content


# Step 7: Test query
result = rag_query("What is the paper about? Say in 2 points")
print("Answer :")
print("----------------------------------------------")
print(result)