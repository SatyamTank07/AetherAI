import { useState, useEffect } from "react";
import AuthSection from "./AuthSection";
import { useUser } from "./UserContext";

function Sidebar() {
  const [activeTab, setActiveTab] = useState("files");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
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

  useEffect(() => {
    fetchFiles();
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

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>MineAI Chat</h2>
        <AuthSection />
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
    </div>
  );
}

export default Sidebar;
