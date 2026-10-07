const EDIT_WINDOW_MS = 30 * 60 * 1000;

function parseUtcTimestamp(timestamp: string): number {
  const normalizedTimestamp = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp)
    ? timestamp
    : `${timestamp}Z`;
  return new Date(normalizedTimestamp).getTime();
}

export function isWithinEditWindow(createdAt: string): boolean {
  const elapsed = Date.now() - parseUtcTimestamp(createdAt);
  return elapsed >= 0 && elapsed < EDIT_WINDOW_MS;
}

export function getEditWindowRemainingMs(createdAt: string): number {
  return Math.max(0, EDIT_WINDOW_MS - (Date.now() - parseUtcTimestamp(createdAt)));
}
