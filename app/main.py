from pathlib import Path
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
import os

from scripts.AgentGraph import AgentGraphBuilder
from scripts.VectorStore import CVectorStore

app = FastAPI()
selected_files = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace with actual domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str

PDF_PATH = "Data/Docs/attention-is-all-you-need-Paper.pdf"
UPLOAD_DIR = "Data/Uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
namespace = None
graph_app = None

def ensure_graph_loaded():
    global namespace, graph_app
    if graph_app is None:
        vector = CVectorStore()
        status, namespace = vector.MStoreFileInVectorDB(PDF_PATH)
        print("Loaded namespace:", namespace)
        graph_app = AgentGraphBuilder(namespace).build()


@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    file_path = Path(UPLOAD_DIR) / file.filename

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    vector = CVectorStore()
    status, namespace = vector.MStoreFileInVectorDB(str(file_path))
    return {"message": status, "namespace": namespace}

@app.get("/files")
def list_files():
    files = [f.name for f in Path(UPLOAD_DIR).glob("*.pdf")]
    return {"files": files}

@app.post("/selected-files")
async def set_selected_files(request: Request):
    global selected_files
    data = await request.json()
    print("Selected files:", data.get("files", []))
    selected_files = data.get("files", []) 
    return {"status": "received"}

@app.post("/chat")
def chat(request: ChatRequest):
    ensure_graph_loaded()
    result = graph_app.invoke({"question": request.question, "selected_files": selected_files})
    return {"answer": result["answer"]}
# uvicorn app.main:app --reload