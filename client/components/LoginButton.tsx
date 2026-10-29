"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { GoogleLogin } from "@react-oauth/google";
import { apiRequest, type LoginResponse } from "../lib/api";
import { safeReturnPath } from "../lib/auth-redirect";

export default function LoginButton() {
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    if (window.localStorage.getItem("access_token")) {
      router.replace(safeReturnPath(new URLSearchParams(window.location.search).get("next")));
    }
  }, [router]);

  return (
    <div className="login-button-wrap">
      <GoogleLogin
        onSuccess={async (credentialResponse) => {
          if (!credentialResponse.credential) {
            setError("Google sign-in did not return a credential. Please try again.");
            return;
          }

          setError("");
          try {
            const data = await apiRequest<LoginResponse>("/auth/google", {
              method: "POST",
              body: JSON.stringify({ token: credentialResponse.credential }),
            });
            window.localStorage.setItem("access_token", data.access_token);
            window.localStorage.setItem("user", JSON.stringify(data.user));
            router.replace(safeReturnPath(new URLSearchParams(window.location.search).get("next")));
          } catch (requestError) {
            setError(requestError instanceof Error ? requestError.message : "Unable to sign in. Please try again.");
          }
        }}
        onError={() => {
          setError("Google sign-in failed. Please try again.");
        }}
        text="signin_with"
        theme="outline"
        width="320"
      />
      {error && <p className="form-error login-error" role="alert">{error}</p>}
    </div>
  );
}