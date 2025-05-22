from helper.logConfig import get_logger
from VectorStore import CVectorStore
from AgentGraph import AgentGraphBuilder
from config import load_config
config = load_config()
logger = get_logger("main")
logger.info("Main script started")

def main():
    PDFPath = "Data/Docs/attention-is-all-you-need-Paper.pdf"
    
    # Store file in vector DB and get namespace (hash)
    objVectorDB = CVectorStore()
    status, namespace = objVectorDB.MStoreFileInVectorDB(PDFPath)
    print(status)

    if namespace is None:
        print("Using existing namespace...")
        return
        
    GraphApp = AgentGraphBuilder(namespace).build()
    
    print("\nWelcome to MineAi Chat! Type your question or 'exit'/'quit' to stop.")
    while True:
        query = input("\nYour question: ").strip()

        if query.lower() in ["exit", "quit"]:
            print("Exiting MineAi Chat. Goodbye!")
            break

        if not query:
            print("Please enter a valid question.")
            continue

        try:
            response = GraphApp.invoke({"question": query, "selected_files": selected_files })
            print("Answer:")
            print("----------------------------------------------")
            print(response["answer"])
        except Exception as e:
            print(f"Error: {e}")

    delete_namespace(config["MineaiIndexName"], config["PINECONE_API_KEY"], config["NameSpace"])

if __name__ == "__main__":
    # Before added Frontend and Backend
    main()