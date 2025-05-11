# MineAi
- MineAi is an AI-powered chat application that enables users to upload PDF documents and interact with them through natural language queries. Leveraging FastAPI for the backend and React for the frontend, MineAi integrates with vector databases like Pinecone to provide intelligent document querying and summarization capabilities.

## 🚀 Features
- Document Upload: Users can upload PDF files, which are then stored in a vector database for efficient querying.
- Interactive Chat: Engage in a conversational interface to ask questions about the uploaded documents.
- Dynamic Routing: Automatically routes queries to appropriate agents based on context, such as QA or summarization.

## 🛠️ Installation
### Prerequisites
- Python 3.10+
- Node.js 16+ and npm
- Pinecone API Key
- Groq API Key

## Backend Setup
### 1) Clone the Repository:
```
git clone https://github.com/SatyamTank07/MineAi.git
cd MineAi
```

### 2) Create a Virtual Environment:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
### 3) Install Dependencies:
```
pip install -r requirements.txt
```

### 4) Configure Environment Variables:
Create a ```.env``` file or set the following environment variables:
```
PINECONE_API_KEY=your_pinecone_api_key
GROQ_API_KEY=your_index_name
```
### 5) Start the Backend Server:
```
uvicorn main:app --reload
```

## Frontend Setup
### 1) Navigate to the Frontend Directory:
```
cd frontend
```
### 2) Install Dependencies:
```
npm install
```

### 3) Start the Frontend Server:
```
npm run dev
```
The application will be available at ```http://localhost:5173```

## 🧠 How It Works
**1) File Upload:** Users upload PDF files, which are stored in the Data/Uploads directory.<br>
**2) Vectorization:** Uploaded files are processed and stored in a vector database (e.g., Pinecone) for efficient similarity searches.<br>
**3) Agent Routing:** Based on the user's query and selected file, the system routes the question to the appropriate agent <br>   (QA, summarization, or master).<br>
**4) Response Generation:** The selected agent processes the query and returns a response, which is displayed in the chat interface.<br>

## 📬 Contact
For any inquiries or support, please contact ```satyamtank03@gmail.com```<br>
**Thank You**
