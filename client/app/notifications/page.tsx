"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import ProtectedPage from "../../components/ProtectedPage";
import { apiRequest } from "../../lib/api";
import {
  refreshNotifications, notificationDate, notificationError,
  type NotificationInbox, type AppNotification,
} from "../../lib/notifications";

export default function NotificationsPage() {
  return <ProtectedPage><Inbox /></ProtectedPage>;
}

function Inbox() {
  const [inbox, setInbox] = useState<NotificationInbox | null>(null);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    apiRequest<NotificationInbox>("/notifications?limit=20", { signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) setInbox(data);
    }).catch((err: unknown) => { if (!controller.signal.aborted) setError(notificationError(err)); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, []);
  async function refresh(nextOffset: number) {
    setBusy(true); setError("");
    try {
      const data = await apiRequest<NotificationInbox>(`/notifications?offset=${nextOffset}&limit=20`);
      setInbox(data); setOffset(nextOffset); refreshNotifications();
    } catch (err) { setError(notificationError(err)); }
    finally { setBusy(false); }
  }
  async function markRead(id: string) {
    setBusy(true); setError("");
    try {
      const row = await apiRequest<AppNotification>(`/notifications/${id}/read`, { method: "POST" });
      setInbox(current => current ? {
        ...current,
        unread_count: Math.max(0, current.unread_count - (current.notifications.find(item => item.id === id)?.is_read === false ? 1 : 0)),
        notifications: current.notifications.map(item => item.id === id ? row : item),
      } : current);
      refreshNotifications();
    } catch (err) { setError(notificationError(err)); }
    finally { setBusy(false); }
  }
  return <>
    <section className="page-heading"><div><p className="eyebrow">Stay in the loop</p><h1>Notifications{inbox ? ` (${inbox.unread_count} unread)` : ""}</h1><p className="muted">Your platform updates, together in one inbox. Ride and carpool updates are available now. No email, SMS, or push notifications are sent.</p></div><button className="button button-secondary" disabled={busy} onClick={() => void refresh(offset)}>Refresh notifications</button></section>
    {error && <p className="form-error" role="alert">{error}</p>}
    {busy && <p role="status">Updating notifications...</p>}
    {inbox?.notifications.map(item => <article className={`notification-card${item.is_read ? "" : " notification-unread"}`} key={item.id}>
      <div className="notification-meta"><span className="notification-category">{item.category}</span><strong>{item.is_read ? "Read" : "Unread"}</strong><time dateTime={item.created_at}>{notificationDate(item.created_at)}</time></div>
      <p>{item.message}</p>
      <div className="form-actions"><Link className="button button-secondary" href={item.target_path}>View details</Link>{!item.is_read && <button className="button button-secondary" disabled={busy} onClick={() => void markRead(item.id)}>Mark as read</button>}</div>
    </article>)}
    {!busy && !error && inbox?.notifications.length === 0 && <div className="state-card"><h2>No notifications yet</h2><p>Updates from the features you use will appear here.</p><Link className="text-link" href="/rides">Explore rides</Link></div>}
    <div className="form-actions"><button className="button button-secondary" disabled={busy || offset === 0} onClick={() => void refresh(offset - 20)}>Previous updates</button><button className="button button-secondary" disabled={busy || !inbox?.has_more} onClick={() => void refresh(offset + 20)}>Next updates</button></div>
  </>;
}
