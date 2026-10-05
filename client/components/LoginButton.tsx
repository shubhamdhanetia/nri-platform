"use client";

import { GoogleLogin } from "@react-oauth/google";

export default function LoginButton() {
  return (
    <GoogleLogin
      onSuccess={async (credentialResponse) => {
        try {
          const response = await fetch(
            "http://localhost:8000/auth/google",
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                token: credentialResponse.credential,
              }),
            }
          );

          const data = await response.json();

          localStorage.setItem(
            "access_token",
            data.access_token
          );

          localStorage.setItem(
              "user",
              JSON.stringify(data.user)
          );

          localStorage.getItem("access_token")

          console.log("Backend response:", data);
        } catch (error) {
          console.error(error);
        }
      }}
      onError={() => {
        console.log("Login Failed");
      }}
    />
  );
}