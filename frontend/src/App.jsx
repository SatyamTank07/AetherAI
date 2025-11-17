import "./App.css";
import Sidebar from "./components/Sidebar";
import ChatComponent from "./components/ChatComponent";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { UserProvider, useUser } from "./components/UserContext";
import { useState, useEffect, useCallback } from "react";

// Helper to wrap App logic with user context
function AppWithSession() {
  const { user } = useUser();
  const [session, setSession] = useState(null);

  // Restore session from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("currentSession");
    if (saved) {
      setSession(JSON.parse(saved));
    }
  }, []);

  // Save session to localStorage when it changes
  useEffect(() => {
    if (session) {
      localStorage.setItem("currentSession", JSON.stringify(session));
    } else {
      localStorage.removeItem("currentSession");
    }
  }, [session]);

  // When user logs out, clear session
  useEffect(() => {
    if (!user) setSession(null);
  }, [user]);

  // Handler for new chat button
  const handleSessionSelect = useCallback(
    async (selectedSession) => {
      if (selectedSession === null && user) {
        // User clicked "New Chat"
        const res = await fetch("http://localhost:8000/chat-session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: user.email,
            title: `Session ${new Date().toLocaleString()}`,
            // No initial message
          }),
        });
        const data = await res.json();
        setSession({ id: data.id, title: `Session ${new Date().toLocaleString()}` });
      } else {
        setSession(selectedSession);
      }
    },
    [user]
  );

  return (
    <div className="container">
      <Sidebar onSessionSelect={handleSessionSelect} />
      <ChatComponent session={session} />
    </div>
  );
}

function App() {
  return (
    <GoogleOAuthProvider clientId="617973458212-2863n08170lussvrrnge4o0bkftsneqq.apps.googleusercontent.com">
      <UserProvider>
        <AppWithSession />
      </UserProvider>
    </GoogleOAuthProvider>
  );
}

export default App;