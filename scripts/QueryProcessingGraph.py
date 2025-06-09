from typing import Dict, Any, Optional, List, TypedDict
from langgraph.graph import StateGraph, END
from helper.logConfig import get_logger
from History import CHistory
from QueryModule import CQuery
from VectorStore import CVectorStore
from config import load_config

logger = get_logger("QueryProcessingGraph")

class QueryProcessingState(TypedDict):
    """State schema for query processing workflow"""
    chat_id: str
    namespace: str
    user_query: str
    topk: int
    chat_history: Optional[List]
    formatted_history: Optional[str]
    retrieved_docs: Optional[List]
    context: Optional[str]
    enhanced_prompt: Optional[str]
    ai_response: Optional[str]
    processing_status: str
    error_message: Optional[str]
    success: bool
    final_result: Optional[Dict[str, Any]]

class QueryProcessingGraph:
    def __init__(self):
        """Initialize the Query Processing Graph with all necessary components."""
        try:
            self.history = CHistory()
            self.query_module = CQuery()
            self.vector_store = CVectorStore()
            self.config = load_config()
            logger.info("Query Processing Graph initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing Query Processing Graph: {e}")
            raise

    def validate_inputs(self, state: QueryProcessingState) -> QueryProcessingState:
        """Node: Validate input parameters"""
        try:
            logger.info("Validating query processing inputs")
            
            # Check required inputs
            if not state.get("chat_id"):
                state["error_message"] = "Chat ID is required"
                state["processing_status"] = "validation_failed"
                state["success"] = False
                return state
            
            if not state.get("namespace"):
                state["error_message"] = "Namespace is required"
                state["processing_status"] = "validation_failed"
                state["success"] = False
                return state
            
            if not state.get("user_query"):
                state["error_message"] = "User query is required"
                state["processing_status"] = "validation_failed"
                state["success"] = False
                return state
            
            # Set default topk if not provided
            if not state.get("topk"):
                state["topk"] = 5
            
            state["processing_status"] = "inputs_validated"
            logger.info("Query processing inputs validated successfully")
            return state
            
        except Exception as e:
            logger.error(f"Error validating inputs: {e}")
            state["error_message"] = f"Input validation error: {str(e)}"
            state["processing_status"] = "validation_error"
            state["success"] = False
            return state

    def retrieve_chat_history(self, state: QueryProcessingState) -> QueryProcessingState:
        """Node: Retrieve and format chat history"""
        try:
            chat_id = state["chat_id"]
            logger.info(f"Retrieving chat history for chat_id: {chat_id}")
            
            # Get last 3 conversations from history
            chat_history = self.history.MGetLastNChats(chat_id, n=3)
            state["chat_history"] = chat_history
            
            # Format chat history for context
            formatted_history = self.format_chat_history(chat_history)
            state["formatted_history"] = formatted_history
            
            state["processing_status"] = "history_retrieved"
            logger.info(f"Chat history retrieved and formatted for chat_id: {chat_id}")
            return state
            
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            state["error_message"] = f"Chat history retrieval error: {str(e)}"
            state["processing_status"] = "history_retrieval_error"
            # Continue processing even if history retrieval fails
            state["formatted_history"] = "No previous conversation history available."
            return state

    def retrieve_relevant_context(self, state: QueryProcessingState) -> QueryProcessingState:
        """Node: Retrieve relevant documents from vector store"""
        try:
            namespace = state["namespace"]
            user_query = state["user_query"]
            topk = state["topk"]
            
            logger.info(f"Retrieving relevant context for query: '{user_query[:50]}...'")
            
            # Retrieve top-k relevant documents
            retrieved_docs = self.query_module.retrieval.MRetrivTopk(namespace, user_query, topk)
            state["retrieved_docs"] = retrieved_docs
            
            # Format the context from retrieved documents
            context = self.query_module.MFormatContext(retrieved_docs)
            state["context"] = context
            
            state["processing_status"] = "context_retrieved"
            logger.info(f"Retrieved {len(retrieved_docs) if retrieved_docs else 0} relevant documents")
            return state
            
        except Exception as e:
            logger.error(f"Error retrieving relevant context: {e}")
            state["error_message"] = f"Context retrieval error: {str(e)}"
            state["processing_status"] = "context_retrieval_error"
            state["context"] = "No relevant context found."
            return state

    def create_enhanced_prompt(self, state: QueryProcessingState) -> QueryProcessingState:
        """Node: Create enhanced prompt with history and context"""
        try:
            logger.info("Creating enhanced prompt")
            
            # Create the enhanced prompt template
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
            
            # Format the prompt with actual values
            enhanced_prompt = template.format(
                history=state.get("formatted_history", "No previous conversation history."),
                context=state.get("context", "No relevant context available."),
                question=state["user_query"]
            )
            
            state["enhanced_prompt"] = enhanced_prompt
            state["processing_status"] = "prompt_created"
            logger.info("Enhanced prompt created successfully")
            return state
            
        except Exception as e:
            logger.error(f"Error creating enhanced prompt: {e}")
            state["error_message"] = f"Prompt creation error: {str(e)}"
            state["processing_status"] = "prompt_creation_error"
            return state

    def generate_ai_response(self, state: QueryProcessingState) -> QueryProcessingState:
        """Node: Generate AI response using LLM"""
        try:
            enhanced_prompt = state["enhanced_prompt"]
            logger.info("Generating AI response using LLM")
            
            # Generate response using the LLM
            response = self.query_module.llm.invoke(enhanced_prompt)
            
            # Handle different response types
            if hasattr(response, 'content'):
                ai_response = response.content
            elif isinstance(response, str):
                ai_response = response
            else:
                ai_response = str(response)
            
            state["ai_response"] = ai_response
            state["processing_status"] = "response_generated"
            logger.info(f"AI response generated successfully for query: '{state['user_query'][:50]}...'")
            return state
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            state["error_message"] = f"Response generation error: {str(e)}"
            state["processing_status"] = "response_generation_error"
            state["ai_response"] = "Sorry, I encountered an error while processing your query. Please try again."
            return state

    def save_to_history(self, state: QueryProcessingState) -> QueryProcessingState:
        """Node: Save the conversation to chat history"""
        try:
            chat_id = state["chat_id"]
            user_query = state["user_query"]
            ai_response = state["ai_response"]
            
            logger.info(f"Saving conversation to history for chat_id: {chat_id}")
            
            # Add the message to chat history
            self.history.MAddMessageToChat(chat_id, user_query, ai_response)
            
            state["processing_status"] = "saved_to_history"
            logger.info(f"Conversation saved to history for chat_id: {chat_id}")
            return state
            
        except Exception as e:
            logger.error(f"Error saving to chat history: {e}")
            state["error_message"] = f"History saving error: {str(e)}"
            state["processing_status"] = "history_saving_error"
            # Continue even if saving fails
            return state

    def prepare_final_result(self, state: QueryProcessingState) -> QueryProcessingState:
        """Node: Prepare the final result"""
        try:
            logger.info("Preparing final result")
            
            # Determine success status
            success = state["processing_status"] not in [
                "validation_failed", "validation_error", 
                "response_generation_error", "prompt_creation_error"
            ] and state.get("ai_response") is not None
            
            state["success"] = success
            
            # Prepare final result dictionary
            final_result = {
                "chat_id": state["chat_id"],
                "namespace": state["namespace"],
                "user_query": state["user_query"],
                "ai_response": state.get("ai_response", "No response generated"),
                "status": "success" if success else "error",
                "processing_status": state["processing_status"],
                "error_message": state.get("error_message")
            }
            
            state["final_result"] = final_result
            state["processing_status"] = "completed"
            
            logger.info(f"Final result prepared. Success: {success}")
            return state
            
        except Exception as e:
            logger.error(f"Error preparing final result: {e}")
            state["error_message"] = f"Result preparation error: {str(e)}"
            state["processing_status"] = "result_preparation_error"
            state["success"] = False
            return state

    def format_chat_history(self, chat_history: list, max_messages: int = 5) -> str:
        """Helper method to format chat history for context in LLM prompt."""
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

    def should_continue_after_validation(self, state: QueryProcessingState) -> str:
        """Conditional edge: Determine next step after validation"""
        if state["processing_status"] == "inputs_validated":
            return "retrieve_history"
        else:
            return "prepare_result"

    def should_continue_after_context(self, state: QueryProcessingState) -> str:
        """Conditional edge: Determine next step after context retrieval"""
        if state["processing_status"] in ["context_retrieved", "context_retrieval_error"]:
            return "create_prompt"
        else:
            return "prepare_result"

    def should_continue_after_prompt(self, state: QueryProcessingState) -> str:
        """Conditional edge: Determine next step after prompt creation"""
        if state["processing_status"] == "prompt_created":
            return "generate_response"
        else:
            return "prepare_result"

    def should_continue_after_response(self, state: QueryProcessingState) -> str:
        """Conditional edge: Determine next step after response generation"""
        if state.get("ai_response"):
            return "save_history"
        else:
            return "prepare_result"

    def build_graph(self) -> StateGraph:
        """Build and return the query processing workflow graph"""
        # Create the graph
        workflow = StateGraph(QueryProcessingState)
        
        # Add nodes
        workflow.add_node("validate_inputs", self.validate_inputs)
        workflow.add_node("retrieve_history", self.retrieve_chat_history)
        workflow.add_node("retrieve_context", self.retrieve_relevant_context)
        workflow.add_node("create_prompt", self.create_enhanced_prompt)
        workflow.add_node("generate_response", self.generate_ai_response)
        workflow.add_node("save_history", self.save_to_history)
        workflow.add_node("prepare_result", self.prepare_final_result)
        
        # Set entry point
        workflow.set_entry_point("validate_inputs")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "validate_inputs",
            self.should_continue_after_validation,
            {
                "retrieve_history": "retrieve_history",
                "prepare_result": "prepare_result"
            }
        )
        
        # Add direct edges
        workflow.add_edge("retrieve_history", "retrieve_context")
        
        workflow.add_conditional_edges(
            "retrieve_context",
            self.should_continue_after_context,
            {
                "create_prompt": "create_prompt",
                "prepare_result": "prepare_result"
            }
        )
        
        workflow.add_conditional_edges(
            "create_prompt",
            self.should_continue_after_prompt,
            {
                "generate_response": "generate_response",
                "prepare_result": "prepare_result"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_response",
            self.should_continue_after_response,
            {
                "save_history": "save_history",
                "prepare_result": "prepare_result"
            }
        )
        
        workflow.add_edge("save_history", "prepare_result")
        workflow.add_edge("prepare_result", END)
        
        return workflow.compile()

    def process_query(self, chat_id: str, namespace: str, user_query: str, topk: int = 5) -> Dict[str, Any]:
        """Main method to process a query using the graph"""
        try:
            # Build the graph
            graph = self.build_graph()
            
            # Initial state
            initial_state = QueryProcessingState(
                chat_id=chat_id,
                namespace=namespace,
                user_query=user_query,
                topk=topk,
                chat_history=None,
                formatted_history=None,
                retrieved_docs=None,
                context=None,
                enhanced_prompt=None,
                ai_response=None,
                processing_status="initialized",
                error_message=None,
                success=False,
                final_result=None
            )
            
            # Execute the graph
            logger.info(f"Starting query processing workflow for chat_id: {chat_id}")
            final_state = graph.invoke(initial_state)
            
            # Return the final result
            result = final_state.get("final_result", {
                "chat_id": chat_id,
                "namespace": namespace,
                "user_query": user_query,
                "ai_response": "Error processing query",
                "status": "error",
                "processing_status": final_state.get("processing_status", "unknown"),
                "error_message": final_state.get("error_message", "Unknown error")
            })
            
            logger.info(f"Query processing workflow completed. Status: {result.get('status')}")
            return result
            
        except Exception as e:
            logger.error(f"Error in query processing workflow: {e}")
            return {
                "chat_id": chat_id,
                "namespace": namespace,
                "user_query": user_query,
                "ai_response": "I apologize, but I encountered an error processing your request. Please try again.",
                "status": "error",
                "processing_status": "workflow_error",
                "error_message": str(e)
            }

def main():
    """Test the query processing graph"""
    try:
        # Initialize the graph
        query_processor = QueryProcessingGraph()
        
        # Get inputs from user
        print(f"\n{'='*60}")
        print("📋 Query Processing Test")
        print(f"{'='*60}")
        
        chat_id = input("Enter Chat ID: ").strip()
        namespace = input("Enter Namespace: ").strip()
        user_query = input("Enter your question: ").strip()
        
        if not all([chat_id, namespace, user_query]):
            print("❌ All fields are required!")
            return
        
        print("\n🔄 Processing query...")
        result = query_processor.process_query(chat_id, namespace, user_query)
        
        print(f"\n{'='*60}")
        print("📋 Query Processing Result")
        print(f"{'='*60}")
        print(f"💬 Chat ID: {result['chat_id']}")
        print(f"🔗 Namespace: {result['namespace']}")
        print(f"❓ Question: {result['user_query']}")
        print(f"🤖 Answer: {result['ai_response']}")
        print(f"✅ Status: {result['status']}")
        if result.get('error_message'):
            print(f"❌ Error: {result['error_message']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()