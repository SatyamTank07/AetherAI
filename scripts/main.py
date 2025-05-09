from VectorStore import CVectorStore
from QueryProcessor import CQueryProcessor

def main():
    
    # Load and split documents
    PDFPath = "Data/Docs/attention-is-all-you-need-Paper.pdf"
    objVectorDB = CVectorStore()
    status = objVectorDB.MStoreFileInVectorDB(PDFPath)
    print(status)

    objQueryProcess = CQueryProcessor()
    Answer = objQueryProcess.MQueryProcess("What is self attention? Say in 2 points")
    print("Answer:")
    print("----------------------------------------------")
    print(Answer)

if __name__ == "__main__":
    main()