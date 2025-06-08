from helper.logConfig import get_logger
from Initialize import CInitialize
from Retrival import CRetrival
from config import load_config
from langchain.prompts import PromptTemplate

config = load_config()
logger = get_logger("Query")

class CQuery:
    
    def __init__(self):
        """Initialize the Query module with LLM and retrieval components."""
        try:
            objInit = CInitialize()
            self.llm = objInit.MInitializeLLM() 
            self.retrieval = CRetrival()
            logger.info("CQuery initialized successfully.")
        except Exception as e:
            logger.error(f"Error during CQuery initialization: {e}")
            raise

    def MCreatePromptTemplate(self):
        """Create a prompt template for the LLM."""
        template = """
        You are an AI assistant that answers questions based on the provided context. 
        Use the following pieces of context to answer the question at the end.
        If you don't know the answer based on the context, just say that you don't know, 
        don't try to make up an answer.

        Context:
        {context}

        Question: {question}

        Answer:
        """
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

    def MFormatContext(self, retrieved_docs):
        """Format retrieved documents into a single context string."""
        try:
            if not retrieved_docs:
                logger.warning("No documents retrieved for context formatting.")
                return "No relevant context found."
            
            context = "\n\n".join(retrieved_docs)
            logger.info(f"Formatted context from {len(retrieved_docs)} documents.")
            return context
        except Exception as e:
            logger.error(f"Error formatting context: {e}")
            return "Error formatting context."

    def MGenerateAnswer(self, query, context):
        """Generate answer using LLM with query and context."""
        try:
            prompt_template = self.MCreatePromptTemplate()
            prompt = prompt_template.format(context=context, question=query)
            
            # Generate response using LLM
            response = self.llm.invoke(prompt)
            
            # Handle different response types
            if hasattr(response, 'content'):
                answer = response.content
            elif isinstance(response, str):
                answer = response
            else:
                answer = str(response)
            
            logger.info(f"Generated answer for query: '{query[:50]}...'")
            return answer
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Sorry, I encountered an error while generating the answer."

    def MQueryWithContext(self, namespace, query, topk=5):
        """Main method to query with context retrieval and LLM generation."""
        try:
            # Retrieve relevant context
            logger.info(f"Retrieving context for query: '{query}'")
            retrieved_docs = self.retrieval.MRetrivTopk(namespace, query, topk)
            
            # Format context
            context = self.MFormatContext(retrieved_docs)
            
            # Generate answer
            answer = self.MGenerateAnswer(query, context)
            
            result = {
                "query": query,
                "context": context,
                "answer": answer,
                "retrieved_docs_count": len(retrieved_docs) if retrieved_docs else 0
            }
            
            logger.info("Query processing completed successfully.")
            return result
            
        except Exception as e:
            logger.error(f"Error in query processing: {e}")
            return {
                "query": query,
                "context": "",
                "answer": "Sorry, I encountered an error while processing your query.",
                "retrieved_docs_count": 0,
                "error": str(e)
            }

    def MSimpleQuery(self, namespace, query, topk=5):
        """Simplified method that returns just the answer."""
        try:
            result = self.MQueryWithContext(namespace, query, topk)
            return result["answer"]
        except Exception as e:
            logger.error(f"Error in simple query: {e}")
            return "Sorry, I encountered an error while processing your query."

    def MBatchQuery(self, namespace, queries, topk=5):
        """Process multiple queries in batch."""
        try:
            results = []
            for query in queries:
                result = self.MQueryWithContext(namespace, query, topk)
                results.append(result)
            
            logger.info(f"Processed {len(queries)} queries in batch.")
            return results
        except Exception as e:
            logger.error(f"Error in batch query processing: {e}")
            return []

def main():
    """Test the Query module."""
    try:
        # Initialize Query module
        query_module = CQuery()
        
        # Test parameters
        namespace = "3cca71e666ef6e0d7b33cb88ee2e9f6ff9a4041b35b5315df47edea5a25f05fb"
        query = "What is Self Attention?"
        topk = 5
        
        print("Testing Query Module...")
        print(f"Query: {query}")
        
        print("\n" + "="*50 + "\n")
        
        # Test simple query
        simple_answer = query_module.MSimpleQuery(namespace, query, topk)
        print(f"Simple Answer: {simple_answer}")
        
        # Test batch query
        batch_queries = [
            "What is Self Attention?",
            "Explain transformer architecture",
            "What are the benefits of attention mechanism?"
        ]
        
        print("\n" + "="*50 + "\n")
        print("Testing Batch Queries...")
        
        batch_results = query_module.MBatchQuery(namespace, batch_queries, topk)
        for i, result in enumerate(batch_results):
            print(f"Query {i+1}: {result['query']}")
            print(f"Answer: {result['answer'][:100]}...")
            print("-" * 30)
        
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    main()