export function safeReturnPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u0020]/.test(value)) {
    return "/explore";
  }
  const destination = new URL(value, "https://local.invalid");
  if (destination.origin !== "https://local.invalid" || destination.pathname === "/login") {
    return "/explore";
  }
  return `${destination.pathname}${destination.search}${destination.hash}`;
}