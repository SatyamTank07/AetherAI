import "./App.css";
import Sidebar from "./components/Sidebar";
import ChatComponent from "./components/ChatComponent";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { UserProvider } from "./components/UserContext";

function App() {
  return (
    <GoogleOAuthProvider clientId="617973458212-2863n08170lussvrrnge4o0bkftsneqq.apps.googleusercontent.com">
      <UserProvider>
        <div className="container">
          <Sidebar />
          <ChatComponent />
        </div>
      </UserProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
