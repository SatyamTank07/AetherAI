# Replace your existing RAGChatbot methods
from PdfProcessingGraph import PDFProcessingGraph
from QueryProcessingGraph import QueryProcessingGraph


class RAGChatbot:
    def __init__(self):
        self.pdf_processor = PDFProcessingGraph()
        self.query_processor = QueryProcessingGraph()
    
    def upload_and_process_pdf(self, pdf_path: str):
        result = self.pdf_processor.process_pdf(pdf_path)
        return result['namespace'] if result['success'] else None
    
    def chat(self, chat_id: str, namespace: str, user_query: str, topk: int = 5):
        return self.query_processor.process_query(chat_id, namespace, user_query, topk)