from pymongo import MongoClient
from datetime import datetime, timezone
from config import load_config
from helper.logConfig import get_logger

logging = get_logger("History")
class CHistory:
    def __init__(self):
        config = load_config()
        self.mongo_uri = config.get("MONGODB_URI", "mongodb://localhost:27017/")
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["mineai"]
        self.collection = self.db["chat_sessions"]

    def MStartNewChat(self, chat_id: str):
        """Start a new chat session."""
        if not chat_id:
            logging.error("Chat ID is required for starting a new chat session.")
            raise ValueError("Chat ID is required")
        try:
            session = {
                "chat_id": chat_id,
                "timestamp": datetime.now(timezone.utc),
                "messages": []
            }
            self.collection.insert_one(session)
            logging.info(f"Started new chat session with chat_id: {chat_id}")
        except Exception as e:
            logging.error(f"Error starting new chat session: {e}")

    def MAddMessageToChat(self, chat_id: str, user_query: str, ai_response: str):
        """Add a message to an existing chat session."""
        if not chat_id or not user_query or not ai_response:
            logging.error("Chat ID, user query, and AI response are required for adding a message.")
            raise ValueError("Chat ID, user query, and AI response are required")
        try:
            result = self.collection.update_one(
                {"chat_id": chat_id},
                {"$push": {
                    "messages": {
                        "user": user_query,
                        "ai": ai_response,
                        "timestamp": datetime.now(timezone.utc)
                    }
                }}
            )
            if result.matched_count == 0:
                logging.warning(f"No chat session found with chat_id: {chat_id} to add message.")
            else:
                logging.info(f"Added message to chat_id: {chat_id}")
        except Exception as e:
            logging.error(f"Error adding message to chat session: {e}")

    def MGetChatHistory(self, user_id: str, chat_id: str):
        """Get full chat history for a specific chat session."""
        if not user_id or not chat_id:
            logging.error("User ID and chat ID are required for retrieving chat history.")
            raise ValueError("User ID and chat ID are required")
        try:
            chat = self.collection.find_one(
                {"user_id": user_id, "chat_id": chat_id},
                {"_id": 0, "messages": 1}
            )
            if chat:
                logging.info(f"Retrieved chat history for chat_id: {chat_id}")
                return chat["messages"]
            else:
                logging.warning(f"No chat history found for chat_id: {chat_id}")
                return []
        except Exception as e:
            logging.error(f"Error retrieving chat history: {e}")
            return []

    def MGetLastNChats(self, chat_id: str, n: int = 5):
        """Get last N chat sessions' summaries."""
        if not chat_id:
            logging.error("Chat ID is required for retrieving last N chat sessions.")
            raise ValueError("Chat ID is required")
        try:
            cursor = self.collection.find(
                {"chat_id": chat_id}
            ).sort("timestamp", -1).limit(n)
            # Bug fix: Use 'messages' instead of 'conversation'
            result = [doc["messages"] for doc in reversed(list(cursor)) if "messages" in doc]
            logging.info(f"Retrieved last {n} chat sessions for chat_id: {chat_id}")
            return result
        except Exception as e:
            logging.error(f"Error retrieving last N chat sessions: {e}")
            return []
        
def test_history():
    history = CHistory()

    # Use a dummy chat_id and user_id
    chat_id = "test_chat_001"

    # 1. Start new chat
    history.MStartNewChat(chat_id)

    # 2. Add messages to chat
    history.MAddMessageToChat(chat_id, "Hello AI!", "Hello human, how can I assist?")

    history.MAddMessageToChat(chat_id, "What's the weather?", "I can't check weather now.")

    # 4. Get last N chats
    print("Last N Chats:")
    print(history.MGetLastNChats(chat_id, n=2))

if __name__ == "__main__":
    test_history()