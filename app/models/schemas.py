# models/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

class ChatCreateRequest(BaseModel):
    namespace: str = Field(..., description="Namespace/file hash for the chat context")
    title: Optional[str] = Field(None, description="Optional title for the chat session")
    
    @validator('namespace')
    def validate_namespace(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Namespace cannot be empty')
        return v.strip()

class ChatCreateResponse(BaseModel):
    chat_id: str
    namespace: str
    title: Optional[str]
    created_at: str
    message: str

class QueryRequest(BaseModel):
    chat_id: str = Field(..., description="Chat session ID")
    namespace: str = Field(..., description="Namespace/file hash for context retrieval")
    query: str = Field(..., min_length=1, max_length=2000, description="User's question")
    topk: Optional[int] = Field(5, ge=1, le=20, description="Number of top results to retrieve")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Query cannot be empty')
        return v.strip()

class QueryResponse(BaseModel):
    chat_id: str
    query: str
    response: str
    namespace: str
    status: str
    timestamp: str
    processing_status: Optional[str] = None
    error_message: Optional[str] = None

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    namespace: str
    file_url: str
    status: str
    message: str

class FileMetadata(BaseModel):
    file_id: str
    filename: str
    namespace: str
    file_url: str
    file_size: int
    uploaded_at: str
    processing_status: str
    processed_at: Optional[str] = None
    error_message: Optional[str] = None

class FileListResponse(BaseModel):
    files: List[FileMetadata]
    total: int
    skip: int
    limit: int

class ChatMessage(BaseModel):
    user: str
    ai: str
    timestamp: str

class ChatHistoryResponse(BaseModel):
    chat_id: str
    messages: List[List[ChatMessage]]  # Your current structure returns list of lists
    total_messages: int
    timestamp: str

class ChatSession(BaseModel):
    chat_id: str
    title: Optional[str]
    namespace: str
    created_at: str
    last_message_at: Optional[str]
    message_count: int

class ChatSessionsResponse(BaseModel):
    chat_sessions: List[ChatSession]
    total: int
    skip: int
    limit: int

class FileProcessingStatus(BaseModel):
    file_id: str
    filename: str
    status: str  # uploaded, processing, processed, failed
    namespace: Optional[str]
    uploaded_at: str
    processed_at: Optional[str]
    error_message: Optional[str]

class DeleteFileResponse(BaseModel):
    message: str
    file_id: str

class DownloadUrlResponse(BaseModel):
    download_url: str
    filename: str
    expires_in: int  # seconds

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: Optional[str] = None

class BulkDeleteRequest(BaseModel):
    file_ids: List[str] = Field(..., min_items=1, max_items=50)

class BulkDeleteResponse(BaseModel):
    deleted_files: List[str]
    failed_files: List[Dict[str, str]]  # file_id and error message
    message: str

class SearchFilesRequest(BaseModel):
    query: Optional[str] = None
    status: Optional[str] = None  # uploaded, processing, processed, failed
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

class UserStatsResponse(BaseModel):
    total_files: int
    total_chat_sessions: int
    total_queries: int
    storage_used: int  # bytes
    files_by_status: Dict[str, int]
    recent_activity: List[Dict[str, Any]]

class SystemStatsResponse(BaseModel):
    total_users: int
    total_files: int
    total_chat_sessions: int
    total_queries: int
    storage_used: int
    active_users_today: int
    files_processed_today: int
    
class GoogleLoginResponse(BaseModel):
    login_url: str
    message: str = "Redirect to this URL to initiate Google OAuth login"

class GoogleCallbackResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    username: str
    message: str