"use client";

import { useState } from "react";
import Image from "next/image";
import { CalendarDays, Check, Copy, Languages, MapPin } from "lucide-react";
import type { ProfileFields } from "../lib/api";

export function MemberIdentity({ name, picture, memberSince }: {
  name: string;
  picture?: string | null;
  memberSince: string;
}) {
  const [failedPicture, setFailedPicture] = useState<string | null>(null);
  const joined = new Intl.DateTimeFormat(undefined, {
    month: "long", year: "numeric", timeZone: "UTC",
  }).format(new Date(`${memberSince.slice(0, 7)}-01T00:00:00Z`));

  return <div className="member-identity">
    {picture && failedPicture !== picture ? (
      <Image className="profile-avatar" src={picture} alt="" width={72} height={72} unoptimized onError={() => setFailedPicture(picture)} />
    ) : (
      <span className="profile-avatar profile-avatar-fallback" aria-hidden="true">{name.charAt(0).toUpperCase()}</span>
    )}
    <div>
      <h2>{name}</h2>
      <p className="member-since"><CalendarDays size={16} aria-hidden="true" /> Member since {joined}</p>
    </div>
  </div>;
}

export function MemberDetails({ profile, showEmpty = false }: { profile: ProfileFields; showEmpty?: boolean }) {
  return <div className="member-details">
    {(profile.bio || showEmpty) && <p className="member-bio">{profile.bio || "No bio added"}</p>}
    <dl className="member-facts">
      {(profile.home_city || showEmpty) && <div>
        <dt><MapPin size={16} aria-hidden="true" /> Home city</dt>
        <dd>{profile.home_city || "Not added"}</dd>
      </div>}
      {(profile.languages.length > 0 || showEmpty) && <div>
        <dt><Languages size={16} aria-hidden="true" /> Languages</dt>
        <dd>{profile.languages.length > 0 ? profile.languages.join(", ") : "Not added"}</dd>
      </div>}
    </dl>
  </div>;
}

export function CopyProfileLink({ userId }: { userId: string }) {
  const [copied, setCopied] = useState(false);
  const [fallback, setFallback] = useState("");

  async function copyLink() {
    const url = `${window.location.origin}/profile/${userId}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setFallback("");
    } catch {
      setCopied(false);
      setFallback(url);
    }
  }

  return <div className="profile-share">
    <button type="button" className="button button-secondary" onClick={() => void copyLink()}>
      {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
      {copied ? "Link copied" : "Copy profile link"}
    </button>
    <span className="profile-share-status" role="status">{copied ? "Profile link copied" : ""}</span>
    {fallback && <label className="profile-link-fallback">Profile link
      <input readOnly value={fallback} onFocus={event => event.currentTarget.select()} />
    </label>}
  </div>;
}