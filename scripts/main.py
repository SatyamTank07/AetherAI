from VectorStore import CVectorStore
from QueryProcessor import CQueryProcessor
from pinecone import Pinecone
from config import load_config
config = load_config()

def delete_namespace(index_name, api_key, namespace):
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    # Add a check to ensure the namespace exists before deleting
    index.delete(delete_all=True, namespace=namespace)
    print(f"Namespace '{namespace}' deleted from Pinecone.")
    
def main():
    # Load and split documents
    PDFPath = "Data/Docs/attention-is-all-you-need-Paper.pdf"
    objVectorDB = CVectorStore()
    status, namespace = objVectorDB.MStoreFileInVectorDB(PDFPath)
    print(status)
    
    # Initialize query processor
    objQueryProcess = CQueryProcessor(namespace)

    # Continuous chat loop
    print("\nWelcome to MineAi Chat! Type your question or 'exit'/'quit' to stop.")
    while True:
        # Get user input
        query = input("\nYour question: ").strip()
        
        # Check for exit conditions
        if query.lower() in ["exit", "quit"]:
            print("Exiting MineAi Chat. Goodbye!")
            break
        
        # Skip empty queries
        if not query:
            print("Please enter a valid question.")
            continue
        
        # Process query with memory
        try:
            answer = objQueryProcess.MQueryProcess(query)
            print("Answer:")
            print("----------------------------------------------")
            print(answer)
        except Exception as e:
            print(f"Error processing query: {e}")
        
    delete_namespace(config["MineaiIndexName"], config["PINECONE_API_KEY"], config["NameSpace"])

if __name__ == "__main__":
    main()