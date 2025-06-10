from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Query
from models.schemas import GoogleLoginResponse, GoogleCallbackResponse
import uvicorn
import os
import tempfile
from datetime import datetime
import logging

# Import your existing modules
from PdfProcessingGraph import PDFProcessingGraph
from QueryProcessingGraph import QueryProcessingGraph
from History import CHistory
from VectorStore import CVectorStore

# Import new modules we'll create
from models.schemas import (
    ChatCreateRequest, ChatCreateResponse,
    QueryRequest, QueryResponse,
    FileUploadResponse, FileListResponse,
    ChatHistoryResponse, HealthResponse
)
from services.file_service import FileService
from services.auth_service import AuthService
from database.mongo_client import MongoDBClient
from config import load_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG System API",
    description="A comprehensive RAG (Retrieval-Augmented Generation) system with PDF processing and chat capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize services
config = load_config()
file_service = FileService()
auth_service = AuthService()
mongodb_client = MongoDBClient()
pdf_processor = PDFProcessingGraph()
query_processor = QueryProcessingGraph()
history_service = CHistory()

# Dependency for authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Authenticate user based on token"""
    try:
        user_id = auth_service.verify_token(credentials.credentials)
        return user_id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )

# File upload endpoint
@app.post("/upload", response_model=FileUploadResponse, tags=["Files"])
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """Upload a PDF file to Cloudflare R2 and process it"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )
        
        # Validate file size (max 50MB)
        if file.size > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size too large. Maximum allowed size is 50MB"
            )
        
        logger.info(f"Processing file upload: {file.filename} for user: {user_id}")
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Upload to Cloudflare R2
            file_url, file_key = await file_service.upload_to_r2(
                file_content=content,
                filename=file.filename,
                user_id=user_id
            )
            
            # Generate file hash (namespace)
            vector_store = CVectorStore()
            file_hash = vector_store.MGenerateFileHash(temp_file_path)
            
            # Store file metadata in MongoDB
            file_metadata = await mongodb_client.store_file_metadata(
                user_id=user_id,
                original_filename=file.filename,
                file_key=file_key,
                file_url=file_url,
                namespace=file_hash,
                file_size=file.size
            )
            
            # Process PDF in background
            background_tasks.add_task(
                process_pdf_background,
                temp_file_path,
                file_hash,
                file_metadata["_id"]
            )
            
            return FileUploadResponse(
                file_id=str(file_metadata["_id"]),
                filename=file.filename,
                namespace=file_hash,
                file_url=file_url,
                status="uploaded",
                message="File uploaded successfully. Processing started in background."
            )
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )

async def process_pdf_background(temp_file_path: str, namespace: str, file_id: str):
    """Background task to process PDF and update status"""
    try:
        logger.info(f"Starting background PDF processing for namespace: {namespace}")
        
        # Process PDF using your existing graph
        result = pdf_processor.process_pdf(temp_file_path)
        
        # Update file status in MongoDB
        await mongodb_client.update_file_processing_status(
            file_id=file_id,
            status="processed" if result["success"] else "failed",
            processing_result=result
        )
        
        logger.info(f"PDF processing completed for namespace: {namespace}, Success: {result['success']}")
        
    except Exception as e:
        logger.error(f"Error in background PDF processing: {e}")
        await mongodb_client.update_file_processing_status(
            file_id=file_id,
            status="failed",
            error_message=str(e)
        )

# Create new chat session
@app.post("/chat/create", response_model=ChatCreateResponse, tags=["Chat"])
async def create_chat_session(
    request: ChatCreateRequest,
    user_id: str = Depends(get_current_user)
):
    """Create a new chat session"""
    try:
        chat_id = f"{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create chat session in history
        history_service.MStartNewChat(chat_id)
        
        # Store chat metadata in MongoDB
        chat_metadata = await mongodb_client.create_chat_session(
            user_id=user_id,
            chat_id=chat_id,
            namespace=request.namespace,
            title=request.title
        )
        
        return ChatCreateResponse(
            chat_id=chat_id,
            namespace=request.namespace,
            title=request.title,
            created_at=datetime.utcnow().isoformat(),
            message="Chat session created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create chat session: {str(e)}"
        )

# Query endpoint
@app.post("/chat/query", response_model=QueryResponse, tags=["Chat"])
async def process_query(
    request: QueryRequest,
    user_id: str = Depends(get_current_user)
):
    """Process a query in a chat session"""
    try:
        # Verify chat ownership
        chat_exists = await mongodb_client.verify_chat_ownership(
            chat_id=request.chat_id,
            user_id=user_id
        )
        
        if not chat_exists:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found or access denied"
            )
        
        # Process query using your existing graph
        result = query_processor.process_query(
            chat_id=request.chat_id,
            namespace=request.namespace,
            user_query=request.query,
            topk=request.topk
        )
        
        return QueryResponse(
            chat_id=request.chat_id,
            query=request.query,
            response=result["ai_response"],
            namespace=request.namespace,
            status=result["status"],
            timestamp=datetime.utcnow().isoformat(),
            processing_status=result.get("processing_status"),
            error_message=result.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

# Get chat history
@app.get("/chat/{chat_id}/history", response_model=ChatHistoryResponse, tags=["Chat"])
async def get_chat_history(
    chat_id: str,
    limit: int = 50,
    user_id: str = Depends(get_current_user)
):
    """Get chat history for a specific chat session"""
    try:
        # Verify chat ownership
        chat_exists = await mongodb_client.verify_chat_ownership(
            chat_id=chat_id,
            user_id=user_id
        )
        
        if not chat_exists:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found or access denied"
            )
        
        # Get chat history
        messages = history_service.MGetLastNChats(chat_id, n=limit)
        
        return ChatHistoryResponse(
            chat_id=chat_id,
            messages=messages,
            total_messages=len(messages),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get chat history: {str(e)}"
        )

# List user's files
@app.get("/files", response_model=FileListResponse, tags=["Files"])
async def list_user_files(
    skip: int = 0,
    limit: int = 20,
    user_id: str = Depends(get_current_user)
):
    """List user's uploaded files"""
    try:
        files = await mongodb_client.get_user_files(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        
        return FileListResponse(
            files=files,
            total=len(files),
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )

# Get file download URL
@app.get("/files/{file_id}/download", tags=["Files"])
async def get_file_download_url(
    file_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get a presigned download URL for a file"""
    try:
        # Verify file ownership
        file_metadata = await mongodb_client.get_file_metadata(file_id, user_id)
        
        if not file_metadata:
            raise HTTPException(
                status_code=404,
                detail="File not found or access denied"
            )
        
        # Generate presigned URL
        download_url = await file_service.generate_download_url(file_metadata["file_key"])
        
        return {
            "download_url": download_url,
            "filename": file_metadata["original_filename"],
            "expires_in": 3600  # 1 hour
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating download URL: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate download URL: {str(e)}"
        )

# Delete file
@app.delete("/files/{file_id}", tags=["Files"])
async def delete_file(
    file_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a file and its associated data"""
    try:
        # Verify file ownership
        file_metadata = await mongodb_client.get_file_metadata(file_id, user_id)
        
        if not file_metadata:
            raise HTTPException(
                status_code=404,
                detail="File not found or access denied"
            )
        
        # Delete from Cloudflare R2
        await file_service.delete_from_r2(file_metadata["file_key"])
        
        # Delete from MongoDB
        await mongodb_client.delete_file(file_id)
        
        # TODO: Delete vectors from Pinecone (implement in VectorStore)
        # vector_store = CVectorStore()
        # vector_store.delete_namespace(file_metadata["namespace"])
        
        return {
            "message": "File deleted successfully",
            "file_id": file_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )

# List user's chat sessions
@app.get("/chat/sessions", tags=["Chat"])
async def list_chat_sessions(
    skip: int = 0,
    limit: int = 20,
    user_id: str = Depends(get_current_user)
):
    """List user's chat sessions"""
    try:
        chat_sessions = await mongodb_client.get_user_chat_sessions(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        
        return {
            "chat_sessions": chat_sessions,
            "total": len(chat_sessions),
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error listing chat sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list chat sessions: {str(e)}"
        )

# Get file processing status
@app.get("/files/{file_id}/status", tags=["Files"])
async def get_file_processing_status(
    file_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get file processing status"""
    try:
        file_metadata = await mongodb_client.get_file_metadata(file_id, user_id)
        
        if not file_metadata:
            raise HTTPException(
                status_code=404,
                detail="File not found or access denied"
            )
        
        return {
            "file_id": file_id,
            "filename": file_metadata["original_filename"],
            "status": file_metadata.get("processing_status", "unknown"),
            "namespace": file_metadata.get("namespace"),
            "uploaded_at": file_metadata.get("uploaded_at"),
            "processed_at": file_metadata.get("processed_at"),
            "error_message": file_metadata.get("error_message")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get file status: {str(e)}"
        )
        
@app.delete("/chat/{chat_id}", tags=["Chat"])
async def delete_chat_session(chat_id: str, user_id: str = Depends(get_current_user)):
    chat_exists = await mongodb_client.verify_chat_ownership(chat_id, user_id)
    if not chat_exists:
        raise HTTPException(status_code=404, detail="Chat session not found or access denied")
    await mongodb_client.delete_chat_session(chat_id)
    history_service.collection.delete_one({"chat_id": chat_id})
    return {"message": "Chat session deleted successfully", "chat_id": chat_id}

@app.get("/login/google", response_model=GoogleLoginResponse, tags=["Auth"])
async def google_login():
    """Initiate Google OAuth login."""
    try:
        login_url = auth_service.get_google_login_url()
        return GoogleLoginResponse(login_url=login_url)
    except Exception as e:
        logger.error(f"Error generating Google login URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate Google login")

@app.get("/callback/google", response_model=GoogleCallbackResponse, tags=["Auth"])
async def google_callback(code: str = Query(...)):
    """Handle Google OAuth callback."""
    try:
        # Validate Google authorization code
        user_info = await auth_service.validate_google_code(code)
        
        # Create or update user in MongoDB
        user = await mongodb_client.create_or_update_google_user(
            google_id=user_info["google_id"],
            email=user_info["email"],
            username=user_info["username"]
        )
        
        # Generate JWT
        access_token = auth_service.create_access_token(user["user_id"])
        
        return GoogleCallbackResponse(
            access_token=access_token,
            user_id=user["user_id"],
            email=user["email"],
            username=user["username"],
            message="Google login successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google callback: {e}")
        raise HTTPException(status_code=500, detail="Failed to process Google callback")
    
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )