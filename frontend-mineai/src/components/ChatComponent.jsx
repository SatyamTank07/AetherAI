import { useState, useRef } from "react";
import { useUser } from "./UserContext";

function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const { user } = useUser();
  const fileInputRef = useRef(null);
  const [uploadMsg, setUploadMsg] = useState("");

  const askQuestion = async () => {
    if (!question.trim()) return;
    setMessages((prev) => [...prev, { type: "user", text: question }]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { type: "bot", text: data.answer }]);
    } catch {
      setMessages((prev) => [...prev, { type: "bot", text: "Error." }]);
    }
    setLoading(false);
  };

  const handleUploadBtn = () => {
    if (!user) {
      setUploadMsg("Please log in to upload files.");
      return;
    }
    setUploadMsg("");
    fileInputRef.current.click();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      setUploadMsg("Only PDF files are allowed.");
      return;
    }
    setUploadMsg("Uploading...");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", user.name);
    formData.append("email", user.email);
    formData.append("picture", user.picture || "");

    try {
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setUploadMsg(data.message || "Upload complete.");
      setTimeout(() => setUploadMsg(""), 3000);
    } catch {
      setUploadMsg("Upload failed.");
      setTimeout(() => setUploadMsg(""), 3000);
    }
    e.target.value = ""; // reset input
  };

  return (
    <div className="chat-area">
      <div className="chat-box">
        {messages.map((msg, i) => (
          <div key={i} className={`msg ${msg.type}`}>
            {msg.text}
          </div>
        ))}
      </div>

      {loading && <p className="loading">Thinking...</p>}
      {uploadMsg && <p className="upload-msg">{uploadMsg}</p>}

      <div className="input-area">
        <button className="plus-btn" onClick={handleUploadBtn}>
          Upload File
        </button>
        <input
          type="file"
          accept="application/pdf"
          style={{ display: "none" }}
          ref={fileInputRef}
          onChange={handleFileChange}
        />
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && askQuestion()}
          placeholder="Ask something..."
        />
        <button onClick={askQuestion}>Send</button>
      </div>
    </div>
  );
}

export default ChatComponent;
