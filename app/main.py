from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, Header, HTTPException
from pydantic import BaseModel, EmailStr

from fastapi.middleware.cors import CORSMiddleware
import google.oauth2.id_token
import google.auth.transport.requests
from motor.motor_asyncio import AsyncIOMotorClient
import os

from scripts.AgentGraph import AgentGraphBuilder
from scripts.VectorStore import CVectorStore

app = FastAPI()
selected_files = []

mongo_client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
mongo_db = mongo_client["mineai"]
users_col = mongo_db["users"]

class UserResponse(BaseModel):
    email: EmailStr
    name: str
    picture: str
    
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

@app.post("/auth/google", response_model=UserResponse)
async def auth_google(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    try:
        GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        request = google.auth.transport.requests.Request()
        id_info = google.oauth2.id_token.verify_oauth2_token(token, request, audience=GOOGLE_CLIENT_ID)

        user_data = {
            "_id": id_info["sub"],
            "email": id_info["email"],
            "name": id_info.get("name", ""),
            "picture": id_info.get("picture", "")
        }

        # Update or insert user in MongoDB (motor version)
        await users_col.update_one(
            {"_id": user_data["_id"]},
            {"$set": user_data},
            upsert=True
        )

        return {"message": "Login success", "user": user_data}

    except ValueError as e:
    # Token format issues
        raise HTTPException(status_code=400, detail="Invalid token format")
    except Exception as e:
        # Other OAuth issues
        raise HTTPException(status_code=401, detail="Token verification failed")

# uvicorn app.main:app --reload 