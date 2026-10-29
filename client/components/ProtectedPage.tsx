"use client";

import { useEffect, useSyncExternalStore, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import AppNav from "./AppNav";

function subscribeToAuth(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function hasAccessToken() {
  return Boolean(window.localStorage.getItem("access_token"));
}

export default function ProtectedPage({ children }: { children: ReactNode }) {
  const router = useRouter();
  const isAuthenticated = useSyncExternalStore(
    subscribeToAuth,
    hasAccessToken,
    () => false,
  );

  useEffect(() => {
    if (!window.localStorage.getItem("access_token")) {
      const destination = window.location.pathname + window.location.search + window.location.hash;
      router.replace(`/login?next=${encodeURIComponent(destination)}`);
    }
  }, [router]);

  if (!isAuthenticated) {
    return (
      <main className="loading-page">
        <span className="spinner" />
        <p>Getting things ready…</p>
      </main>
    );
  }

  return (
    <div className="app-page">
      <AppNav />
      <main className="page-container">{children}</main>
    </div>
  );
}
