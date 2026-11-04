"use client";

import Link from "next/link";
import { Bookmark, BookmarkCheck } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "../lib/api";
import { housingError, type HousingItem, type HousingStatus } from "../lib/housing";

export function HousingSaveButton({ item, onChanged }: { item: HousingItem; onChanged: (item: HousingItem) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true); setError("");
    try {
      const result = await apiRequest<{ saved: boolean }>(`/housing/${item.id}/saved`, { method: item.my_saved ? "DELETE" : "PUT" });
      onChanged({ ...item, my_saved: result.saved });
    } catch (failure) { setError(housingError(failure)); } finally { setBusy(false); }
  }
  return <span className="housing-control"><button className={`button button-secondary housing-save-button${item.my_saved ? " is-saved" : ""}`} type="button" disabled={busy} aria-pressed={item.my_saved} aria-label={item.my_saved ? "Remove from saved housing" : "Save housing"} onClick={() => void save()}>{item.my_saved ? <BookmarkCheck size={16} aria-hidden="true" /> : <Bookmark size={16} aria-hidden="true" />}{busy ? "Updating..." : item.my_saved ? "Saved" : "Save"}</button>{error && <span className="form-error" role="alert">{error}</span>}</span>;
}

export function HousingOwnerActions({ item, onChanged, onDeleted }: {
  item: HousingItem; onChanged: (item: HousingItem) => void; onDeleted?: (id: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  async function update(suffix: string, method: string, body?: object) {
    setBusy(true); setError("");
    try {
      const result = await apiRequest<HousingItem>(`/housing/${item.id}/${suffix}`, { method, ...(body ? { body: JSON.stringify(body) } : {}) });
      onChanged(result);
    } catch (failure) { setError(housingError(failure)); } finally { setBusy(false); }
  }
  async function remove() {
    if (!window.confirm("Delete this housing post and its inquiries? This cannot be undone.")) return;
    setBusy(true); setError("");
    try {
      await apiRequest<{ detail: string }>(`/housing/${item.id}`, { method: "DELETE" });
      if (onDeleted) onDeleted(item.id); else router.push("/housing/mine");
    } catch (failure) { setError(housingError(failure)); } finally { setBusy(false); }
  }
  function status(value: HousingStatus) { void update("status", "PUT", { status: value }); }
  return <div className="housing-owner-controls">
    <div className="housing-actions" role="group" aria-label={`Manage ${item.title}`}>
      {item.status === "ACTIVE"
        ? <><button className="button button-primary" disabled={busy} onClick={() => status("FILLED")}>{item.kind === "LISTING" ? "Mark filled" : "Mark resolved"}</button><button className="button button-secondary" disabled={busy} onClick={() => void update("renew", "POST")}>Still available / renew</button></>
        : <button className="button button-primary" disabled={busy} onClick={() => status("ACTIVE")}>Reopen for 30 days</button>}
      {item.status !== "ARCHIVED" && <button className="button button-secondary" disabled={busy} onClick={() => status("ARCHIVED")}>Archive</button>}
      <button className="button button-secondary" disabled={busy} onClick={() => void update("visibility", "PUT", { is_private: !item.is_private })}>{item.is_private ? "Make public" : "Make private"}</button>
      <Link className="button button-secondary" href={`/housing/${item.id}/edit`}>Edit</Link>
      <button className="button housing-delete" disabled={busy} onClick={() => void remove()}>Delete</button>
    </div>
    {busy && <span className="field-hint" role="status">Updating housing post...</span>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </div>;
}

export function HousingLoadState({ loading, error, retry }: { loading: boolean; error: string; retry: () => void }) {
  return loading ? <div className="state-card" role="status">Loading housing...</div>
    : error ? <div className="state-card error-state" role="alert"><p>{error}</p><button className="button button-secondary" onClick={retry}>Try again</button></div> : null;
}

export function HousingManageLinks() {
  return <nav className="housing-manage-links" aria-label="Manage housing"><Link href="/housing/mine">My posts</Link><Link href="/housing/saved">Saved housing</Link><Link href="/housing/inquiries">Inquiries</Link></nav>;
}
