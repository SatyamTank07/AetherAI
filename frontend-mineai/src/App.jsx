import "./App.css";
import Sidebar from "./components/Sidebar";
import ChatComponent from "./components/ChatComponent";

function App() {
  return (
    <div className="container">
      <Sidebar />
      <ChatComponent />
    </div>
  );
}

export default App;
