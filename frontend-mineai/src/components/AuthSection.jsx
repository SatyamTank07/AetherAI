// AuthSection.jsx
import { useState, useEffect } from "react";
import { useUser } from "./UserContext";
import LoginButton from "./LoginButton";

function AuthSection() {
  const { user, logout } = useUser();
  const [showDropdown, setShowDropdown] = useState(false);

  const handleLogout = () => {
    logout();
    setShowDropdown(false);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showDropdown && !event.target.closest(".user-menu")) {
        setShowDropdown(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showDropdown]);

  return (
    <>
      {user ? (
        <div className="user-menu">
          <div
            className="user-avatar"
            onClick={() => setShowDropdown(!showDropdown)}
            style={{ cursor: "pointer", position: "relative" }}
          >
            <img
              src={user.picture}
              alt="avatar"
              style={{ width: 40, height: 40, borderRadius: "50%" }}
            />
          </div>

          {showDropdown && (
            <div
              className="dropdown-menu"
              style={{
                position: "absolute",
                top: "60px",
                right: "10px",
                background: "white",
                border: "1px solid #ccc",
                borderRadius: "8px",
                padding: "15px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                zIndex: 1000,
                minWidth: "200px",
              }}
            >
              <div
                className="user-info"
                style={{
                  borderBottom: "1px solid #eee",
                  paddingBottom: "10px",
                  marginBottom: "10px",
                }}
              >
                <p
                  style={{
                    margin: "0 0 5px 0",
                    fontWeight: "bold",
                    fontSize: "14px",
                  }}
                >
                  {user.name}
                </p>
                <p
                  style={{
                    margin: "0",
                    fontSize: "12px",
                    color: "#666",
                  }}
                >
                  {user.email}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="logout-btn"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  background: "#ff4444",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "14px",
                  transition: "background 0.2s",
                }}
                onMouseOver={(e) =>
                  (e.target.style.background = "#cc0000")
                }
                onMouseOut={(e) =>
                  (e.target.style.background = "#ff4444")
                }
              >
                Logout
              </button>
            </div>
          )}
        </div>
      ) : (
        <LoginButton />
      )}
    </>
  );
}

export default AuthSection;
