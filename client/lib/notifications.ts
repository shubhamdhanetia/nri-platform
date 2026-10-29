export interface AppNotification {
  id: string;
  category: string;
  event_type: string;
  resource_id: string;
  target_path: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationInbox {
  notifications: AppNotification[];
  unread_count: number;
  has_more: boolean;
}

export interface NotificationCount {
  unread_count: number;
}

export function refreshNotifications() {
  window.dispatchEvent(new Event("notifications-changed"));
}

export function notificationError(error: unknown) {
  return error instanceof Error ? error.message : "Unable to update notifications. Please try again.";
}

export function notificationDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
