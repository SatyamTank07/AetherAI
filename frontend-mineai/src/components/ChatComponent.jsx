import { useState, useRef, useEffect } from "react";
import { useUser } from "./UserContext";

function ChatComponent({ session }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const { user } = useUser();
  const fileInputRef = useRef(null);
  const [uploadMsg, setUploadMsg] = useState("");
  const chatBoxRef = useRef(null);

  // Load messages when session changes
  useEffect(() => {
    if (session && session.id) {
      fetch(`http://localhost:8000/chat-session/${session.id}`)
        .then(res => res.json())
        .then(data => setMessages(data.messages || []));
    } else {
      setMessages([]);
    }
  }, [session]);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (chatBoxRef.current) {
      // Scroll to bottom of the chat box container
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  const askQuestion = async () => {
    if (!question.trim() || !user) return;
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setQuestion("");
    setLoading(true);

    let sessionId = session && session.id;
    let answer = "";
    try {
      // Send user message to backend (create session if needed)
      if (!sessionId) {
        // Create new session
        const res = await fetch("http://localhost:8000/chat-session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: user.email,
            title: `Session ${new Date().toLocaleString()}`,
            message: { role: "user", text: question }
          })
        });
        const data = await res.json();
        sessionId = data.id;
        // Optionally, reload sessions in parent
      } else {
        // Add message to existing session
        await fetch(`http://localhost:8000/chat-session/${sessionId}/message`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: user.email,
            message: { role: "user", text: question }
          })
        });
      }

      // Get AI answer (simulate or call your /chat endpoint)
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });
      const data = await res.json();
      answer = data.answer;
      setMessages((prev) => [...prev, { role: "ai", text: answer }]);

      // Save AI answer to session
      if (sessionId) {
        await fetch(`http://localhost:8000/chat-session/${sessionId}/message`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: user.email,
            message: { role: "ai", text: answer }
          })
        });
      }
    } catch {
      setMessages((prev) => [...prev, { role: "ai", text: "Error." }]);
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
      <div className="chat-box" ref={chatBoxRef}>
        {messages.map((msg, i) => (
          <div key={i} className={`msg ${msg.role === "user" ? "user" : "bot"}`}>
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
