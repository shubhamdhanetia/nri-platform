"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Check, CheckCheck, RefreshCw } from "lucide-react";
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
  async function markAllRead() {
    setBusy(true); setError("");
    try {
      await apiRequest<{ updated_count: number; unread_count: number }>("/notifications/read-all", { method: "POST" });
      setInbox(current => current ? {
        ...current,
        unread_count: 0,
        notifications: current.notifications.map(item => ({ ...item, is_read: true })),
      } : current);
      refreshNotifications();
    } catch (err) { setError(notificationError(err)); }
    finally { setBusy(false); }
  }
  return <>
    <section className="page-heading notification-page-heading">
      <div>
        <p className="eyebrow">Stay in the loop</p>
        <h1>Notifications{inbox && <span className="notification-unread-count">{inbox.unread_count} unread</span>}</h1>
        <p className="muted">Ride, carpool, and housing updates in one place.</p>
      </div>
      <div className="notification-page-actions">
        {Boolean(inbox?.unread_count) && <button className="button button-secondary" disabled={busy} onClick={() => void markAllRead()}><CheckCheck size={16} aria-hidden="true" />Mark all as read</button>}
        <button className="button button-secondary" disabled={busy} onClick={() => void refresh(offset)} aria-label="Refresh notifications"><RefreshCw size={16} aria-hidden="true" />Refresh</button>
      </div>
    </section>
    {error && <p className="form-error" role="alert">{error}</p>}
    {busy && <p className="notification-loading" role="status"><span className="spinner" />{inbox ? "Updating notifications..." : "Loading notifications..."}</p>}
    {inbox?.notifications.map(item => <article className={`notification-card${item.is_read ? "" : " notification-unread"}`} key={item.id}>
      <div className="notification-meta"><span className="notification-category">{item.category}</span><span className={`notification-read-state${item.is_read ? "" : " is-unread"}`}>{!item.is_read && <span className="notification-unread-dot" aria-hidden="true" />}{item.is_read ? "Read" : "Unread"}</span><time dateTime={item.created_at}>{notificationDate(item.created_at)}</time></div>
      <p className="notification-message">{item.message}</p>
      <div className="notification-actions"><Link className="button button-secondary" href={item.target_path}>View details</Link>{!item.is_read && <button className="button button-quiet notification-mark-read" disabled={busy} onClick={() => void markRead(item.id)}><Check size={16} aria-hidden="true" />Mark read</button>}</div>
    </article>)}
    {!busy && !error && inbox?.notifications.length === 0 && offset === 0 && <div className="notification-empty"><span className="notification-empty-icon"><CheckCheck size={22} aria-hidden="true" /></span><div><h2>You&apos;re all caught up</h2><p>New ride, carpool, and housing updates will appear here.</p></div><Link className="text-link" href="/rides">Explore rides</Link></div>}
    {!busy && !error && inbox?.notifications.length === 0 && offset > 0 && <div className="notification-empty"><div><h2>No updates on this page</h2><p>Go back to the previous page of notifications.</p></div></div>}
    {(Boolean(inbox?.notifications.length) || offset > 0) && <nav className="notification-pagination" aria-label="Notification pages"><button className="button button-secondary" disabled={busy || offset === 0} onClick={() => void refresh(offset - 20)}>Previous</button><button className="button button-secondary" disabled={busy || !inbox?.has_more} onClick={() => void refresh(offset + 20)}>Next</button></nav>}
  </>;
}
