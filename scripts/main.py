import pinecone
from VectorStore import CVectorStore
from AgentGraph import AgentGraphBuilder
from pinecone import Pinecone
from config import load_config
config = load_config()

def delete_namespace(index_name, api_key, namespace):
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    try:
        index.delete(delete_all=True, namespace=namespace)
        print(f"Namespace '{namespace}' deleted from Pinecone.")
    except pinecone.core.client.exceptions.NotFoundException as e:
        print("Namespce not found")
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
            response = GraphApp.invoke({"question": query})
            print("Answer:")
            print("----------------------------------------------")
            print(response["answer"])
        except Exception as e:
            print(f"Error: {e}")

    delete_namespace(config["MineaiIndexName"], config["PINECONE_API_KEY"], config["NameSpace"])

if __name__ == "__main__":
    # Before added Frontend and Backend
    main()