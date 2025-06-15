import { GoogleLogin } from "@react-oauth/google";
import { useUser } from "./UserContext";
import GoogleIcon from "./GoogleIcon";

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
        setUser(data); // { email, name, picture }
      }}
      onError={() => {
        alert("Login Failed");
      }}
      type="icon"
      shape="circle"
      theme="outline"
    />
  );
}

export default LoginButton;
