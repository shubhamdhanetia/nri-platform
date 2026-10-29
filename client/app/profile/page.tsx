"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowUpRight, Pencil, Save, X } from "lucide-react";
import ProtectedPage from "../../components/ProtectedPage";
import { CopyProfileLink, MemberDetails, MemberIdentity } from "../../components/MemberProfile";
import { apiRequest, type User } from "../../lib/api";

export default function ProfilePage() {
  return <ProtectedPage><ProfileContent /></ProtectedPage>;
}

function ProfileContent() {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);

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
    <div className="member-profile-page">
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
        <>
          <MemberIdentity name={user.name} picture={user.picture} memberSince={user.created_at} />
          <div className="member-profile-actions">
            <Link className="button button-secondary" href={`/profile/${user.id}`}><ArrowUpRight size={16} aria-hidden="true" /> View public profile</Link>
            <CopyProfileLink userId={user.id} />
          </div>
          <section className="member-profile-section" aria-labelledby="member-details-heading">
            <div className="section-title-row">
              <div><h2 id="member-details-heading">Community profile</h2><p className="muted">Visible to signed-in members</p></div>
              {!editing && <button className="button button-secondary" type="button" onClick={() => { setEditing(true); setSaved(false); }}><Pencil size={16} aria-hidden="true" /> Edit profile</button>}
            </div>
            {editing ? <ProfileForm user={user} onCancel={() => setEditing(false)} onSaved={updated => { setUser(updated); setEditing(false); setSaved(true); }} /> : <MemberDetails profile={user} showEmpty />}
            {saved && <p role="status" className="profile-save-status">Profile saved</p>}
          </section>
          <section className="member-profile-section" aria-labelledby="account-details-heading">
            <div className="section-title-row"><div><h2 id="account-details-heading">Account details</h2><p className="muted">Only visible to you</p></div></div>
            <dl className="member-facts">
              <div><dt>Email</dt><dd>{user.email}</dd></div>
              {user.provider && <div><dt>Sign-in provider</dt><dd>{user.provider}</dd></div>}
            </dl>
          </section>
        </>
      ) : null}
    </div>
  );
}

function ProfileForm({ user, onSaved, onCancel }: { user: User; onSaved: (user: User) => void; onCancel: () => void }) {
  const [bio, setBio] = useState(user.bio ?? "");
  const [city, setCity] = useState(user.home_city ?? "");
  const [languages, setLanguages] = useState(user.languages.join(", "));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const languageList = languages.split(",").map(language => language.trim()).filter(Boolean);
    if (languageList.length > 10 || languageList.some(language => language.length > 50)) {
      setError("Enter up to 10 languages, each no longer than 50 characters.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      onSaved(await apiRequest<User>("/users/me", {
        method: "PATCH",
        body: JSON.stringify({ bio: bio.trim() || null, home_city: city.trim() || null, languages: languageList }),
      }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save your profile.");
    } finally {
      setSaving(false);
    }
  }

  return <form className="member-profile-form" onSubmit={event => void save(event)}>
    <fieldset disabled={saving}>
      <label htmlFor="profile-bio">Bio <span className="muted">Optional</span></label>
      <textarea id="profile-bio" rows={3} maxLength={160} value={bio} onChange={event => setBio(event.target.value)} aria-describedby="profile-bio-count" />
      <span className="profile-field-hint" id="profile-bio-count">{bio.length}/160</span>
      <label htmlFor="profile-city">Home city <span className="muted">Optional</span></label>
      <input id="profile-city" maxLength={100} autoComplete="address-level2" value={city} onChange={event => setCity(event.target.value)} />
      <label htmlFor="profile-languages">Languages (comma-separated) <span className="muted">Optional</span></label>
      <input id="profile-languages" maxLength={518} value={languages} onChange={event => setLanguages(event.target.value)} />
    </fieldset>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="form-actions">
      <button className="button button-primary" type="submit" disabled={saving}><Save size={16} aria-hidden="true" />{saving ? "Saving..." : "Save profile"}</button>
      <button className="button button-secondary" type="button" disabled={saving} onClick={onCancel}><X size={16} aria-hidden="true" />Cancel</button>
    </div>
  </form>;
}
