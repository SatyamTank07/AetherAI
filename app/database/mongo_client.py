# database/mongo_client.py
from pymongo import MongoClient
from passlib.context import CryptContext
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Optional
from helper.logConfig import get_logger
from config import load_config

logger = get_logger("MongoDBClient")

class MongoDBClient:
    def __init__(self):
        config = load_config()
        self.client = MongoClient(config["MONGODB_URI"])
        self.db = self.client["mineai"]
        self.files_collection = self.db["files"]
        self.chat_sessions_collection = self.db["chat_sessions"]
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def store_file_metadata(self, user_id: str, original_filename: str, file_key: str, file_url: str, namespace: str, file_size: int) -> Dict:
        metadata = {
            "user_id": user_id,
            "original_filename": original_filename,
            "file_key": file_key,
            "file_url": file_url,
            "namespace": namespace,
            "file_size": file_size,
            "uploaded_at": datetime.utcnow().isoformat(),
            "processing_status": "uploaded",
            "processed_at": None,
            "error_message": None
        }
        result = self.files_collection.insert_one(metadata)
        metadata["_id"] = str(result.inserted_id)
        logger.info(f"Stored file metadata for file_id: {metadata['_id']}")
        return metadata

    async def update_file_processing_status(self, file_id: str, status: str, processing_result: Optional[Dict] = None):
        update = {
            "$set": {
                "processing_status": status,
                "processed_at": datetime.utcnow().isoformat(),
                "error_message": processing_result.get("error_message") if processing_result else None
            }
        }
        self.files_collection.update_one({"_id": ObjectId(file_id)}, update)
        logger.info(f"Updated file processing status for file_id: {file_id} to {status}")

    async def create_chat_session(self, user_id: str, chat_id: str, namespace: str, title: Optional[str]) -> Dict:
        chat_metadata = {
            "user_id": user_id,
            "chat_id": chat_id,
            "namespace": namespace,
            "title": title,
            "created_at": datetime.utcnow().isoformat(),
            "last_message_at": None,
            "message_count": 0
        }
        result = self.chat_sessions_collection.insert_one(chat_metadata)
        chat_metadata["_id"] = str(result.inserted_id)
        logger.info(f"Created chat session: {chat_id}")
        return chat_metadata

    async def verify_chat_ownership(self, chat_id: str, user_id: str) -> bool:
        chat = self.chat_sessions_collection.find_one({"chat_id": chat_id, "user_id": user_id})
        return bool(chat)

    async def get_user_files(self, user_id: str, skip: int, limit: int) -> List[Dict]:
        files = self.files_collection.find({"user_id": user_id}).skip(skip).limit(limit)
        return [self._serialize_doc(file) for file in files]

    async def get_file_metadata(self, file_id: str, user_id: str) -> Optional[Dict]:
        file = self.files_collection.find_one({"_id": ObjectId(file_id), "user_id": user_id})
        return self._serialize_doc(file) if file else None

    async def delete_file(self, file_id: str):
        self.files_collection.delete_one({"_id": ObjectId(file_id)})
        logger.info(f"Deleted file metadata: {file_id}")

    async def delete_chat_session(self, chat_id: str):
        self.chat_sessions_collection.delete_one({"chat_id": chat_id})
        logger.info(f"Deleted chat session: {chat_id}")

    async def get_user_chat_sessions(self, user_id: str, skip: int, limit: int) -> List[Dict]:
        sessions = self.chat_sessions_collection.find({"user_id": user_id}).skip(skip).limit(limit)
        return [self._serialize_doc(session) for session in sessions]

    async def search_files(self, user_id: str, query: Optional[str], status: Optional[str], date_from: Optional[datetime], date_to: Optional[datetime], skip: int, limit: int) -> List[Dict]:
        filters = {"user_id": user_id}
        if query:
            filters["original_filename"] = {"$regex": query, "$options": "i"}
        if status:
            filters["processing_status"] = status
        if date_from:
            filters["uploaded_at"] = {"$gte": date_from.isoformat()}
        if date_to:
            filters["uploaded_at"] = {**filters.get("uploaded_at", {}), "$lte": date_to.isoformat()}
        files = self.files_collection.find(filters).skip(skip).limit(limit)
        return [self._serialize_doc(file) for file in files]

    async def get_user_stats(self, user_id: str) -> Dict:
        total_files = self.files_collection.count_documents({"user_id": user_id})
        total_chat_sessions = self.chat_sessions_collection.count_documents({"user_id": user_id})
        total_queries = sum(s.get("message_count", 0) for s in self.chat_sessions_collection.find({"user_id": user_id}))
        storage_used = sum(f.get("file_size", 0) for f in self.files_collection.find({"user_id": user_id}))
        files_by_status = self.files_collection.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$processing_status", "count": {"$sum": 1}}}
        ])
        files_by_status = {doc["_id"]: doc["count"] for doc in files_by_status}
        recent_activity = [
            {"type": "file_upload", "timestamp": f["uploaded_at"], "filename": f["original_filename"]}
            for f in self.files_collection.find({"user_id": user_id}).sort("uploaded_at", -1).limit(5)
        ]
        return {
            "total_files": total_files,
            "total_chat_sessions": total_chat_sessions,
            "total_queries": total_queries,
            "storage_used": storage_used,
            "files_by_status": files_by_status,
            "recent_activity": recent_activity
        }

    async def get_system_stats(self) -> Dict:
        total_users = len(self.files_collection.distinct("user_id"))
        total_files = self.files_collection.count_documents({})
        total_chat_sessions = self.chat_sessions_collection.count_documents({})
        total_queries = sum(s.get("message_count", 0) for s in self.chat_sessions_collection.find({}))
        storage_used = sum(f.get("file_size", 0) for f in self.files_collection.find({}))
        files_processed_today = self.files_collection.count_documents({
            "processed_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()}
        })
        active_users_today = len(self.chat_sessions_collection.distinct("user_id", {
            "last_message_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()}
        }))
        return {
            "total_users": total_users,
            "total_files": total_files,
            "total_chat_sessions": total_chat_sessions,
            "total_queries": total_queries,
            "storage_used": storage_used,
            "active_users_today": active_users_today,
            "files_processed_today": files_processed_today
        }

    async def is_admin(self, user_id: str) -> bool:
        user = self.db["users"].find_one({"user_id": user_id, "role": "admin"})
        return bool(user)

    def _serialize_doc(self, doc: Dict) -> Dict:
        doc["_id"] = str(doc["_id"])
        return doc
    
    async def create_or_update_google_user(self, google_id: str, email: str, username: str) -> Dict:
        """Create or update a user based on Google profile."""
        user = self.db["users"].find_one({"google_id": google_id})
        if user:
            # Update existing user
            self.db["users"].update_one(
                {"google_id": google_id},
                {"$set": {
                    "email": email,
                    "username": username,
                    "last_login": datetime.utcnow().isoformat()
                }}
            )
            user = self.db["users"].find_one({"google_id": google_id})
        else:
            # Create new user
            user = {
                "google_id": google_id,
                "email": email,
                "username": username,
                "user_id": str(ObjectId()),
                "created_at": datetime.utcnow().isoformat(),
                "last_login": datetime.utcnow().isoformat(),
                "role": "user"
            }
            result = self.db["users"].insert_one(user)
            user["_id"] = str(result.inserted_id)
        logger.info(f"Google user created/updated: {user['user_id']}")
        return self._serialize_doc(user)

    async def get_user_by_google_id(self, google_id: str) -> Optional[Dict]:
        """Retrieve user by Google ID."""
        user = self.db["users"].find_one({"google_id": google_id})
        return self._serialize_doc(user) if user else None