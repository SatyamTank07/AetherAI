import { useState, useEffect } from "react";
import { useUser } from "./UserContext";
import LoginButton from "./LoginButton";

function Sidebar() {
  const { user } = useUser();
  const [activeTab, setActiveTab] = useState("files");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);

  // Fetch uploaded files from backend
  const fetchFiles = async () => {
    const res = await fetch("http://localhost:8000/files");
    const data = await res.json();
    setUploadedFiles(data.files);
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  // Toggle file selection
  const handleFileSelect = (file) => {
    const isSelected = selectedFiles.includes(file);
    const newSelection = isSelected
      ? selectedFiles.filter((f) => f !== file) // Deselect
      : [...selectedFiles, file];              // Select

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

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>MineAI Chat</h2>
        {user ? (
          <img src={user.picture} alt="avatar" style={{ width: 40, borderRadius: "50%" }} />
        ) : (
          <LoginButton />
        )}
      </div>

      <div className="tabs">
        {/* History tab (not implemented yet) */}
        {/* 
        <button
          className={`tab-button ${activeTab === "history" ? "active" : ""}`}
          onClick={() => setActiveTab("history")}
        >
          History
        </button> 
        */}
        <button
          className={`tab-button ${activeTab === "files" ? "active" : ""}`}
          onClick={() => setActiveTab("files")}
        >
          Files
        </button>
      </div>

      <div className="tab-content">
        {/* Placeholder for future history */}
        {activeTab === "history" && (
          <ul>
            <li>Previous conversation #1</li>
            <li>Previous conversation #2</li>
            <li>(Static for now)</li>
          </ul>
        )}

        {/* File tab content */}
        {activeTab === "files" && (
          <ul className="file-tab-list">
            {uploadedFiles.map((file, i) => (
              <li
                key={i}
                className={`tab-button-files ${
                  selectedFiles.includes(file) ? "active" : ""
                }`}
                onClick={() => handleFileSelect(file)}
              >
                {file}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default Sidebar;
