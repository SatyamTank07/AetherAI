import { useState, useEffect } from "react";
import AuthSection from "./AuthSection";
import { useUser } from "./UserContext";
import "../App.css";

function Sidebar({ onSessionSelect }) {
  const [activeTab, setActiveTab] = useState("files");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyItems, setHistoryItems] = useState([]);
  const { user } = useUser();

  // Fetch uploaded files for the logged-in user
  const fetchFiles = async () => {
    if (!user) {
      setUploadedFiles([]);
      return;
    }
    const res = await fetch(`http://localhost:8000/my-files?email=${encodeURIComponent(user.email)}`);
    const data = await res.json();
    setUploadedFiles(data.files || []);
  };

  // Fetch chat sessions for the logged-in user
  const fetchSessions = async () => {
    if (!user) {
      setHistoryItems([]);
      return;
    }
    const res = await fetch(`http://localhost:8000/chat-sessions?email=${encodeURIComponent(user.email)}`);
    const data = await res.json();
    setHistoryItems(data || []);
  };

  useEffect(() => {
    fetchFiles();
    fetchSessions();
  }, [user]);

  // Toggle file selection
  const handleFileSelect = (filename) => {
    const isSelected = selectedFiles.includes(filename);
    const newSelection = isSelected
      ? selectedFiles.filter((f) => f !== filename) // Deselect
      : [...selectedFiles, filename];              // Select

    setSelectedFiles(newSelection);
    sendSelectedFilesToBackend(newSelection);
  };

  // Send selected files to backend
  const sendSelectedFilesToBackend = async (files) => {
    await fetch("http://localhost:8000/selected-files", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ files }),
    });
  };

  // Handle session selection
  const handleSessionSelect = (session) => {
    setShowHistory(false);
    if (onSessionSelect) {
      onSessionSelect(session);
      // Save to localStorage for persistence
      if (session) {
        localStorage.setItem("currentSession", JSON.stringify(session));
      } else {
        localStorage.removeItem("currentSession");
      }
    }
  };

  return (
    <div className="sidebar" style={{position: "relative"}}>
      <div className="sidebar-header">
        <h2>AetherAI</h2>
        <AuthSection />
      </div>

      {/* New Chat Button */}
      <button
        className="new-chat-btn"
        style={{
          width: "90%",
          margin: "12px auto 8px auto",
          display: "block",
          background: "#7c3aed",
          color: "#fff",
          border: "none",
          borderRadius: "6px",
          padding: "10px 0",
          fontWeight: "bold",
          fontSize: "1em",
          cursor: "pointer"
        }}
        // This will trigger App's handler to create a new chat session
        onClick={() => onSessionSelect && onSessionSelect(null)}
      >
        + New Chat
      </button>

      <div className="tabs">
        <button
          className={`tab-button ${activeTab === "files" ? "active" : ""}`}
          onClick={() => setActiveTab("files")}
        >
          Files
        </button>
      </div>

      <div className="tab-content">
        {/* File tab content */}
        {activeTab === "files" && (
          <ul className="file-tab-list">
            {uploadedFiles.map((file, i) => (
              <li
                key={i}
                className={`tab-button-files ${selectedFiles.includes(file.filename) ? "active" : ""}`}
                onClick={() => handleFileSelect(file.filename)}
              >
                <u><a href={file.url} target="_blank" rel="noopener noreferrer">{file.filename}</a></u>
                <span> ({(file.size/1024).toFixed(1)} KB)</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* History Icon */}
      <div
        className="history-icon"
        onClick={() => setShowHistory((prev) => !prev)}
        title="Show History"
      >
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="#555" strokeWidth="2"/>
          <path d="M12 7v5l3 3" stroke="#555" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </div>

      {/* History Popup */}
      {showHistory && (
        <div className="history-popup">
          <div className="history-popup-content">
            <h3 className="history-title">Your History</h3>
            <ul style={{listStyle: "none", paddingLeft: 0, maxHeight: 220, overflowY: "auto"}}>
              {historyItems.map(session => (
                <li key={session.id}>
                  <button className="history-item-btn" onClick={() => handleSessionSelect(session)}>
                    {session.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export default Sidebar;
