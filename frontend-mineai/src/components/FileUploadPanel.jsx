import { useState, useEffect } from "react";
import "../App.css";

function FileUploadPanel() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploadMsg, setUploadMsg] = useState("");

  useEffect(() => {
    fetchUploadedFiles();
  }, []);

  const fetchUploadedFiles = async () => {
    const res = await fetch("http://localhost:8000/files");
    const data = await res.json();
    setUploadedFiles(data.files);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append("file", selectedFile);

    const res = await fetch("http://localhost:8000/upload", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setUploadMsg(data.message);
    fetchUploadedFiles(); // refresh file list
  };

  return (
    <div className="upload-panel">
      <h3>Upload PDF to Vector DB</h3>
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => setSelectedFile(e.target.files[0])}
      />
      <button onClick={handleUpload}>Upload</button>
      <p>{uploadMsg}</p>

      <h4>Uploaded Files:</h4>
      <ul>
        {uploadedFiles.map((file, i) => (
          <li key={i}>{file}</li>
        ))}
      </ul>
    </div>
  );
}

export default FileUploadPanel;
