"use client";

import { useCallback, useEffect, useState } from "react";
import ProtectedPage from "../../components/ProtectedPage";
import { apiRequest, type User } from "../../lib/api";

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchProfile = useCallback(
    () => apiRequest<User>("/users/me"),
    [],
  );

  useEffect(() => {
    let active = true;
    fetchProfile()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load your profile.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fetchProfile]);

  async function retryLoadProfile() {
    setLoading(true);
    setError("");
    try {
      setUser(await fetchProfile());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load your profile.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ProtectedPage>
      <section className="page-heading">
        <div>
          <p className="eyebrow">Your corner of the community</p>
          <h1>My profile</h1>
        </div>
      </section>
      {loading ? (
        <div className="state-card"><span className="spinner" /> Loading your profile…</div>
      ) : error ? (
        <div className="state-card error-state" role="alert">
          <p>{error}</p>
          <button className="button button-secondary" onClick={() => void retryLoadProfile()} type="button">
            Try again
          </button>
        </div>
      ) : user ? (
          <section className="profile-card">
            {user.picture ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img className="profile-avatar" src={user.picture} alt="" />
            ) : (
              <span className="profile-avatar profile-avatar-fallback">{user.name.charAt(0).toUpperCase()}</span>
            )}
            <div>
              <h2>{user.name}</h2>
              <p className="muted">{user.email}</p>
              {user.provider && <span className="provider-label">Signed in with {user.provider}</span>}
            </div>
          </section>
      ) : null}
    </ProtectedPage>
  );
}
