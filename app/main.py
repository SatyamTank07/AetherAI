from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, Header, HTTPException, Form, Query
from pydantic import BaseModel, EmailStr

from fastapi.middleware.cors import CORSMiddleware
import google.oauth2.id_token
import google.auth.transport.requests
from motor.motor_asyncio import AsyncIOMotorClient
import os
import boto3
from botocore.client import Config
import io

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
async def upload_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    email: str = Form(...),
    picture: str = Form(None)
):
    # Cloudflare R2 credentials from environment
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
    R2_ENDPOINT = os.getenv("R2_ENDPOINT")
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Upload to R2
    session = boto3.session.Session()
    s3 = session.client(
        service_name="s3",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        endpoint_url=R2_ENDPOINT,
        config=Config(signature_version="s3v4")
    )
    s3.upload_fileobj(
        Fileobj=io.BytesIO(file_content),
        Bucket=R2_BUCKET_NAME,
        Key=file.filename
    )
    r2_url = f"{os.getenv('R2_PUBLIC_DOMAIN').rstrip('/')}/{file.filename}"

    # Store metadata in MongoDB
    file_doc = {
        "user": {
            "name": name,
            "email": email,
            "picture": picture
        },
        "file": {
            "filename": file.filename,
            "url": r2_url,
            "size": file_size
        }
    }
    await mongo_db["uploads"].insert_one(file_doc)

    return {"message": "File uploaded to R2 and metadata saved.", "file": file_doc["file"]}

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

        return {
            "email": user_data["email"],
            "name": user_data["name"],
            "picture": user_data["picture"]
        }

    except ValueError as e:
    # Token format issues
        raise HTTPException(status_code=400, detail="Invalid token format")
    except Exception as e:
        # Other OAuth issues
        raise HTTPException(status_code=401, detail="Token verification failed")

@app.get("/my-files")
async def get_my_files(email: str = Query(...)):
    files = await mongo_db["uploads"].find({"user.email": email}).to_list(length=100)
    # Return only file info, not user info
    return {"files": [f["file"] for f in files]}

# uvicorn app.main:app --reload