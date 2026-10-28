"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "../lib/api";
import { usePathname } from "next/navigation";
import { Bell, CircleAlert } from "lucide-react";
import { notificationError, type NotificationCount } from "../lib/notifications";

export default function NotificationBell() {
  const path = usePathname();
  const [unread, setUnread] = useState<number | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let latestRequest = 0;
    async function refresh() {
      const request = ++latestRequest;
      try {
        const inbox = await apiRequest<NotificationCount>("/notifications/unread-count", { signal: controller.signal });
        if (!controller.signal.aborted && request === latestRequest) { setUnread(inbox.unread_count); setError(""); }
      } catch (err) {
        if (!controller.signal.aborted && request === latestRequest) setError(notificationError(err));
      }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30000);
    window.addEventListener("focus", refresh);
    window.addEventListener("notifications-changed", refresh);
    return () => {
      controller.abort(); window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      window.removeEventListener("notifications-changed", refresh);
    };
  }, []);
  const label = error ? "Notifications unavailable. Open to retry." :
    unread === null ? "Notifications (loading)" : `Notifications (${unread} unread)`;
  return <Link className="notification-bell" href="/notifications"
    aria-current={path === "/notifications" ? "page" : undefined} aria-label={label}
    title={error || label}>
    <Bell size={21} aria-hidden="true" />
    {error ? <CircleAlert className="notification-bell-error" size={15} aria-hidden="true" /> :
      unread !== null && unread > 0 && <span className="notification-badge" aria-hidden="true">{unread > 99 ? "99+" : unread}</span>}
    <span className="sr-only" aria-live="polite">{label}</span>
  </Link>;
}
