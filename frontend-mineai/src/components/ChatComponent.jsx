import { useState } from "react";

function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

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

      <div className="input-area">
        {/* <button className="plus-btn">+</button> */}
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && askQuestion()}
          placeholder="Ask something..."
        />
        <button onClick={askQuestion}>➤</button>
      </div>
    </div>
  );
}

export default ChatComponent;
