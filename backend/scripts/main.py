import os
from typing import Optional, Dict, Any
from scripts.helper.logConfig import get_logger
from History import CHistory
from QueryModule import CQuery
from VectorStore import CVectorStore
from scripts.config import load_config

logger = get_logger("MainChatbot")

class RAGChatbot:
    def __init__(self):
        """Initialize the RAG Chatbot with all necessary components."""
        try:
            self.history = CHistory()
            self.query_module = CQuery()
            self.vector_store = CVectorStore()
            self.config = load_config()
            logger.info("RAG Chatbot initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing RAG Chatbot: {e}")
            raise

    def format_chat_history(self, chat_history: list, max_messages: int = 5) -> str:
        """Format chat history for context in LLM prompt."""
        try:
            if not chat_history:
                return "No previous conversation history."
            
            # Take only the last max_messages conversations
            recent_history = chat_history[-max_messages:] if len(chat_history) > max_messages else chat_history
            
            formatted_history = []
            for conversation in recent_history:
                if isinstance(conversation, list):
                    for message in conversation:
                        if isinstance(message, dict) and 'user' in message and 'ai' in message:
                            formatted_history.append(f"User: {message['user']}")
                            formatted_history.append(f"Assistant: {message['ai']}")
            
            if not formatted_history:
                return "No previous conversation history."
            
            return "\n".join(formatted_history)
        except Exception as e:
            logger.error(f"Error formatting chat history: {e}")
            return "Error retrieving chat history."

    def create_enhanced_prompt_template(self):
        """Create an enhanced prompt template that includes history, context, and current query."""
        template = """
        You are an AI assistant that answers questions based on the provided context and conversation history.
        Use the following information to provide a comprehensive and contextual answer.

        Previous Conversation History:
        {history}

        Relevant Context from Documents:
        {context}

        Current Question: {question}

        Instructions:
        1. Use the conversation history to understand the context of the current question
        2. Refer to the document context to provide accurate information
        3. If the question relates to previous conversations, acknowledge that connection
        4. If you don't know the answer based on the provided context, say so clearly
        5. Be conversational and maintain continuity with the chat history
        6. Provide detailed explanations when appropriate

        Answer:
        """
        return template

    def generate_contextual_answer(self, namespace: str, query: str, chat_id: str, topk: int = 5) -> str:
        """Generate answer using history, context, and current query."""
        try:
            # Get chat history
            chat_history = self.history.MGetLastNChats(chat_id, n=3)  # Get last 3 conversations
            formatted_history = self.format_chat_history(chat_history)
            
            # Get relevant context from vector store
            retrieved_docs = self.query_module.retrieval.MRetrivTopk(namespace, query, topk)
            context = self.query_module.MFormatContext(retrieved_docs)
            
            # Create enhanced prompt
            enhanced_template = self.create_enhanced_prompt_template()
            prompt = enhanced_template.format(
                history=formatted_history,
                context=context,
                question=query
            )
            
            # Generate response using LLM
            response = self.query_module.llm.invoke(prompt)
            
            # Handle different response types
            if hasattr(response, 'content'):
                answer = response.content
            elif isinstance(response, str):
                answer = response
            else:
                answer = str(response)
            
            logger.info(f"Generated contextual answer for query: '{query[:50]}...'")
            return answer
            
        except Exception as e:
            logger.error(f"Error generating contextual answer: {e}")
            return "Sorry, I encountered an error while processing your query. Please try again."

    def chat(self, chat_id: str, namespace: str, user_query: str, topk: int = 5) -> Dict[str, Any]:
        """Main chat method that handles the complete conversation flow."""
        try:
            logger.info(f"Processing chat for chat_id: {chat_id}, namespace: {namespace}")
            
            # Generate contextual answer
            ai_response = self.generate_contextual_answer(namespace, user_query, chat_id, topk)
            
            # Add message to chat history
            self.history.MAddMessageToChat(chat_id, user_query, ai_response)
            
            result = {
                "chat_id": chat_id,
                "namespace": namespace,
                "user_query": user_query,
                "ai_response": ai_response,
                "status": "success"
            }
            
            logger.info(f"Chat processed successfully for chat_id: {chat_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in chat processing: {e}")
            error_response = "I apologize, but I encountered an error processing your request. Please try again."
            
            # Still try to save the interaction even if there was an error
            try:
                self.history.MAddMessageToChat(chat_id, user_query, error_response)
            except:  # noqa: E722
                pass
            
            return {
                "chat_id": chat_id,
                "namespace": namespace,
                "user_query": user_query,
                "ai_response": error_response,
                "status": "error",
                "error": str(e)
            }

    def start_new_chat_session(self, chat_id: str) -> bool:
        """Start a new chat session."""
        try:
            self.history.MStartNewChat(chat_id)
            logger.info(f"Started new chat session: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error starting new chat session: {e}")
            return False

    def upload_and_process_pdf(self, pdf_path: str) -> Optional[str]:
        """Upload and process a PDF file, return the namespace (file hash)."""
        try:
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return None
            
            logger.info(f"Processing PDF file: {pdf_path}")
            result = self.vector_store.MStoreFileInVectorDB(pdf_path)
            
            if result:
                # Get the file hash to use as namespace
                file_hash = self.vector_store.MGenerateFileHash(pdf_path)
                logger.info(f"PDF processed successfully. Namespace: {file_hash}")
                return file_hash
            else:
                logger.error("Failed to process PDF file")
                return None
                
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return None

def interactive_chat_mode(chatbot: RAGChatbot, chat_id: str, namespace: str):
    """Interactive chat mode for continuous conversation."""
    print(f"\n{'='*60}")
    print("🤖 RAG Chatbot - Interactive Mode")
    print(f"Chat ID: {chat_id}")
    print(f"Namespace: {namespace[:12]}...")
    print(f"{'='*60}")
    print("Type 'quit', 'exit', or 'bye' to end the conversation")
    print(f"{'='*60}\n")
    
    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("\n👋 Thank you for using RAG Chatbot! Goodbye!")
                break
            
            if not user_input:
                print("Please enter a valid question.")
                continue
            
            print("\n🤖 AI: Thinking...")
            
            # Process the chat
            result = chatbot.chat(chat_id, namespace, user_input)
            
            if result["status"] == "success":
                print(f"\n🤖 AI: {result['ai_response']}")
            else:
                print(f"\n❌ Error: {result['ai_response']}")
                
        except KeyboardInterrupt:
            print("\n\n👋 Chat interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")

def main():
    """Main function to run the RAG Chatbot."""
    try:
        print("🚀 Initializing RAG Chatbot...")
        chatbot = RAGChatbot()
        print("✅ RAG Chatbot initialized successfully!")
        
        # Get inputs from user
        print(f"\n{'='*60}")
        print("📋 Setup Configuration")
        print(f"{'='*60}")
        
        # Get chat_id
        chat_id = input("Enter Chat ID: ").strip()
        if not chat_id:
            print("❌ Chat ID is required!")
            return
        
        # Ask if user wants to upload a new PDF or use existing namespace
        print("\nOptions:")
        print("1. Upload new PDF file")
        print("2. Use existing namespace")
        
        choice = input("Choose option (1 or 2): ").strip()
        
        namespace = None
        
        if choice == "1":
            pdf_path = input("Enter PDF file path: ").strip()
            if not pdf_path:
                print("❌ PDF path is required!")
                return
            
            print(f"\n📄 Processing PDF: {pdf_path}")
            namespace = chatbot.upload_and_process_pdf(pdf_path)
            
            if not namespace:
                print("❌ Failed to process PDF file!")
                return
            
            print("✅ PDF processed successfully!")
            print(f"📝 Generated namespace: {namespace}")
            
        elif choice == "2":
            namespace = input("Enter namespace (file hash): ").strip()
            if not namespace:
                print("❌ Namespace is required!")
                return
        else:
            print("❌ Invalid choice!")
            return
        
        # Start new chat session
        print("\n🆕 Starting new chat session...")
        if not chatbot.start_new_chat_session(chat_id):
            print("⚠️ Warning: Could not create new chat session, but continuing...")
        
        # Ask for interaction mode
        print("\nInteraction modes:")
        print("1. Interactive chat mode")
        print("2. Single query mode")
        
        mode_choice = input("Choose mode (1 or 2): ").strip()
        
        if mode_choice == "1":
            # Interactive mode
            interactive_chat_mode(chatbot, chat_id, namespace)
            
        elif mode_choice == "2":
            # Single query mode
            user_query = input("Enter your question: ").strip()
            if not user_query:
                print("❌ Question is required!")
                return
            
            print("\n🤖 Processing your query...")
            result = chatbot.chat(chat_id, namespace, user_query)
            
            print(f"\n{'='*60}")
            print("📋 Query Result")
            print(f"{'='*60}")
            print(f"❓ Question: {result['user_query']}")
            print(f"🤖 Answer: {result['ai_response']}")
            print(f"✅ Status: {result['status']}")
            
        else:
            print("❌ Invalid mode choice!")
            return
            
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted. Goodbye!")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main()
