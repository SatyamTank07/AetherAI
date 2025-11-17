import os
from typing import Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
from scripts.helper.logConfig import get_logger
from VectorStore import CVectorStore
from scripts.config import load_config

logger = get_logger("PDFProcessingGraph")

class PDFProcessingState(TypedDict):
    """State schema for PDF processing workflow"""
    pdf_path: str
    file_exists: bool
    file_hash: Optional[str]
    processing_status: str
    error_message: Optional[str]
    namespace: Optional[str]
    success: bool

class PDFProcessingGraph:
    def __init__(self):
        """Initialize the PDF Processing Graph with necessary components."""
        try:
            self.vector_store = CVectorStore()
            self.config = load_config()
            logger.info("PDF Processing Graph initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing PDF Processing Graph: {e}")
            raise

    def validate_pdf_file(self, state: PDFProcessingState) -> PDFProcessingState:
        """Node: Validate if PDF file exists and is accessible"""
        try:
            pdf_path = state["pdf_path"]
            logger.info(f"Validating PDF file: {pdf_path}")
            
            if not pdf_path:
                state["file_exists"] = False
                state["error_message"] = "PDF path is empty or None"
                state["processing_status"] = "validation_failed"
                logger.error("PDF path is empty")
                return state
            
            if not os.path.exists(pdf_path):
                state["file_exists"] = False
                state["error_message"] = f"PDF file not found: {pdf_path}"
                state["processing_status"] = "file_not_found"
                logger.error(f"PDF file not found: {pdf_path}")
                return state
            
            if not pdf_path.lower().endswith('.pdf'):
                state["file_exists"] = False
                state["error_message"] = f"File is not a PDF: {pdf_path}"
                state["processing_status"] = "invalid_file_type"
                logger.error(f"File is not a PDF: {pdf_path}")
                return state
            
            state["file_exists"] = True
            state["processing_status"] = "file_validated"
            logger.info(f"PDF file validated successfully: {pdf_path}")
            return state
            
        except Exception as e:
            logger.error(f"Error validating PDF file: {e}")
            state["file_exists"] = False
            state["error_message"] = f"Validation error: {str(e)}"
            state["processing_status"] = "validation_error"
            return state

    def generate_file_hash(self, state: PDFProcessingState) -> PDFProcessingState:
        """Node: Generate hash for the PDF file"""
        try:
            pdf_path = state["pdf_path"]
            logger.info(f"Generating hash for PDF file: {pdf_path}")
            
            file_hash = self.vector_store.MGenerateFileHash(pdf_path)
            
            if file_hash:
                state["file_hash"] = file_hash
                state["namespace"] = file_hash
                state["processing_status"] = "hash_generated"
                logger.info(f"File hash generated successfully: {file_hash}")
            else:
                state["error_message"] = "Failed to generate file hash"
                state["processing_status"] = "hash_generation_failed"
                logger.error("Failed to generate file hash")
            
            return state
            
        except Exception as e:
            logger.error(f"Error generating file hash: {e}")
            state["error_message"] = f"Hash generation error: {str(e)}"
            state["processing_status"] = "hash_generation_error"
            return state

    def check_existing_vectors(self, state: PDFProcessingState) -> PDFProcessingState:
        """Node: Check if vectors already exist for this file"""
        try:
            namespace = state["namespace"]
            logger.info(f"Checking existing vectors for namespace: {namespace}")
            
            # Check if vectors already exist in the vector store
            # This is a placeholder - implement based on your vector store's capability
            existing_vectors = self.vector_store.MCheckNamespaceExists(namespace) if hasattr(self.vector_store, 'MCheckNamespaceExists') else False
            
            if existing_vectors:
                state["processing_status"] = "vectors_exist"
                state["success"] = True
                logger.info(f"Vectors already exist for namespace: {namespace}")
            else:
                state["processing_status"] = "vectors_not_found"
                logger.info(f"No existing vectors found for namespace: {namespace}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error checking existing vectors: {e}")
            state["error_message"] = f"Vector check error: {str(e)}"
            state["processing_status"] = "vector_check_error"
            return state

    def process_pdf_to_vectors(self, state: PDFProcessingState) -> PDFProcessingState:
        """Node: Process PDF file and store in vector database"""
        try:
            pdf_path = state["pdf_path"]
            logger.info(f"Processing PDF to vectors: {pdf_path}")
            
            # Process the PDF and store in vector database
            result = self.vector_store.MStoreFileInVectorDB(pdf_path)
            
            if result:
                state["processing_status"] = "pdf_processed"
                state["success"] = True
                logger.info(f"PDF processed successfully: {pdf_path}")
            else:
                state["processing_status"] = "pdf_processing_failed"
                state["error_message"] = "Failed to process PDF file"
                state["success"] = False
                logger.error(f"Failed to process PDF file: {pdf_path}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error processing PDF to vectors: {e}")
            state["error_message"] = f"PDF processing error: {str(e)}"
            state["processing_status"] = "pdf_processing_error"
            state["success"] = False
            return state

    def finalize_processing(self, state: PDFProcessingState) -> PDFProcessingState:
        """Node: Finalize the processing and prepare final response"""
        try:
            if state.get("success", False):
                state["processing_status"] = "completed_successfully"
                logger.info(f"PDF processing completed successfully. Namespace: {state['namespace']}")
            else:
                state["processing_status"] = "completed_with_errors"
                logger.warning(f"PDF processing completed with errors: {state.get('error_message', 'Unknown error')}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error finalizing processing: {e}")
            state["error_message"] = f"Finalization error: {str(e)}"
            state["processing_status"] = "finalization_error"
            return state

    def should_process_pdf(self, state: PDFProcessingState) -> str:
        """Conditional edge: Determine if PDF should be processed"""
        if state["processing_status"] == "vectors_exist":
            return "finalize"
        elif state["processing_status"] == "vectors_not_found":
            return "process"
        else:
            return "finalize"

    def should_continue_after_validation(self, state: PDFProcessingState) -> str:
        """Conditional edge: Determine next step after validation"""
        if state["file_exists"]:
            return "generate_hash"
        else:
            return "finalize"

    def should_continue_after_hash(self, state: PDFProcessingState) -> str:
        """Conditional edge: Determine next step after hash generation"""
        if state.get("file_hash"):
            return "check_vectors"
        else:
            return "finalize"

    def build_graph(self) -> StateGraph:
        """Build and return the PDF processing workflow graph"""
        # Create the graph
        workflow = StateGraph(PDFProcessingState)
        
        # Add nodes
        workflow.add_node("validate_file", self.validate_pdf_file)
        workflow.add_node("generate_hash", self.generate_file_hash)
        workflow.add_node("check_vectors", self.check_existing_vectors)
        workflow.add_node("process_pdf", self.process_pdf_to_vectors)
        workflow.add_node("finalize", self.finalize_processing)
        
        # Set entry point
        workflow.set_entry_point("validate_file")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "validate_file",
            self.should_continue_after_validation,
            {
                "generate_hash": "generate_hash",
                "finalize": "finalize"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_hash",
            self.should_continue_after_hash,
            {
                "check_vectors": "check_vectors",
                "finalize": "finalize"
            }
        )
        
        workflow.add_conditional_edges(
            "check_vectors",
            self.should_process_pdf,
            {
                "process": "process_pdf",
                "finalize": "finalize"
            }
        )
        
        # Add edges to finalize
        workflow.add_edge("process_pdf", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Main method to process a PDF file using the graph"""
        try:
            # Build the graph
            graph = self.build_graph()
            
            # Initial state
            initial_state = PDFProcessingState(
                pdf_path=pdf_path,
                file_exists=False,
                file_hash=None,
                processing_status="initialized",
                error_message=None,
                namespace=None,
                success=False
            )
            
            # Execute the graph
            logger.info(f"Starting PDF processing workflow for: {pdf_path}")
            final_state = graph.invoke(initial_state)
            
            # Prepare result
            result = {
                "pdf_path": final_state["pdf_path"],
                "namespace": final_state.get("namespace"),
                "file_hash": final_state.get("file_hash"),
                "success": final_state.get("success", False),
                "status": final_state["processing_status"],
                "error_message": final_state.get("error_message")
            }
            
            logger.info(f"PDF processing workflow completed. Status: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Error in PDF processing workflow: {e}")
            return {
                "pdf_path": pdf_path,
                "namespace": None,
                "file_hash": None,
                "success": False,
                "status": "workflow_error",
                "error_message": str(e)
            }

def main():
    """Test the PDF processing graph"""
    try:
        # Initialize the graph
        pdf_processor = PDFProcessingGraph()
        
        # Test with a PDF file
        pdf_path = input("Enter PDF file path: ").strip()
        
        if not pdf_path:
            print("PDF path is required!")
            return
        
        print(f"\n🔄 Processing PDF: {pdf_path}")
        result = pdf_processor.process_pdf(pdf_path)
        
        print(f"\n{'='*60}")
        print("📋 PDF Processing Result")
        print(f"{'='*60}")
        print(f"📄 PDF Path: {result['pdf_path']}")
        print(f"🔗 Namespace: {result['namespace']}")
        print(f"#️⃣ File Hash: {result['file_hash']}")
        print(f"✅ Success: {result['success']}")
        print(f"📊 Status: {result['status']}")
        if result['error_message']:
            print(f"❌ Error: {result['error_message']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
