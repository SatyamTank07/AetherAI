import { useState, useEffect } from "react";

function Sidebar() {
  const [activeTab, setActiveTab] = useState("files");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);

  const fetchFiles = async () => {
    const res = await fetch("http://localhost:8000/files");
    const data = await res.json();
    setUploadedFiles(data.files);
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>MineAI Chat</h2>
        {/* <button className="plus-btn">+</button> */}
      </div>

      <div className="tabs">
        {/* <button
          className={`tab-button ${activeTab === "history" ? "active" : ""}`}
          onClick={() => setActiveTab("history")}
        >
          History
        </button> */}
        <button
          className={`tab-button ${activeTab === "files" ? "active" : ""}`}
          onClick={() => setActiveTab("files")}
        >
          Files
        </button>
      </div>

      <div className="tab-content">
        {activeTab === "history" && (
          <ul>
            <li>Previous conversation #1</li>
            <li>Previous conversation #2</li>
            <li>(Static for now)</li>
          </ul>
        )}
        {activeTab === "files" && (
          <ul className="file-tab-list">
            {uploadedFiles.map((file, i) => (
              <li
                key={i}
                className={`tab-button-files ${
                  selectedFile === file ? "active" : ""
                }`}
                onClick={() => setSelectedFile(file)}
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
