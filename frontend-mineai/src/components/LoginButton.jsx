import { GoogleLogin } from "@react-oauth/google";
import { useUser } from "./UserContext";

function LoginButton() {
  const { setUser } = useUser();

  return (
    <GoogleLogin
      onSuccess={async (credentialResponse) => {
        const id_token = credentialResponse.credential;

        const res = await fetch("http://localhost:8000/auth/google", {
          method: "POST",
          headers: { Authorization: `Bearer ${id_token}` },
        });

        const data = await res.json();
        setUser(data.user); // { email, name, picture, sub }
      }}
      onError={() => {
        alert("Login Failed");
      }}
    />
  );
}

export default LoginButton;
