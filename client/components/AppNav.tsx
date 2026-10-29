"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { apiRequest, type User } from "../lib/api";
import NotificationBell from "./NotificationBell";

const links = [
  { href: "/explore", label: "Community" },
  { href: "/rides", label: "Rides" },
];

export default function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const activeSection = pathname === "/explore" || pathname === "/feed" || pathname === "/create-post" || pathname.startsWith("/posts/")
    ? "/explore"
    : pathname === "/rides" || pathname.startsWith("/rides/") ? "/rides" : null;
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
  const [profilePicture, setProfilePicture] = useState<string | null>(null);
  const [failedPicture, setFailedPicture] = useState<string | null>(null);
  const accountMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    apiRequest<User>("/users/me")
      .then((user) => {
        if (active) setProfilePicture(user.picture ?? null);
      })
      .catch(() => {
        if (active) setProfilePicture(null);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!isAccountMenuOpen) return;

    function handlePointerDown(event: MouseEvent) {
      if (event.target instanceof Node && !accountMenuRef.current?.contains(event.target)) {
        setIsAccountMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsAccountMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isAccountMenuOpen]);

  function signOut() {
    window.localStorage.removeItem("access_token");
    window.localStorage.removeItem("user");
    setIsAccountMenuOpen(false);
    router.replace("/login");
  }

  return (
    <header className="app-header">
      <div className="nav-inner">
        <Link className="brand nav-brand" href="/explore">
          <span className="brand-mark">N</span>
          <span>NRI Platform</span>
        </Link>
        <nav className="main-nav" aria-label="Main navigation">
          {links.map((link) => (
            <Link
              className={activeSection === link.href ? "nav-link active" : "nav-link"}
              aria-current={activeSection === link.href ? "page" : undefined}
              href={link.href}
              key={link.href}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="nav-account-actions">
          <NotificationBell />
          <div className="account-menu" ref={accountMenuRef}>
            <button
              aria-expanded={isAccountMenuOpen}
              aria-controls="account-menu-options"
              aria-label="Account options"
              className="account-menu-trigger"
              onClick={() => setIsAccountMenuOpen((isOpen) => !isOpen)}
              type="button"
            >
              {profilePicture && failedPicture !== profilePicture ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  alt=""
                  className="account-menu-avatar"
                  onError={() => setFailedPicture(profilePicture)}
                  src={profilePicture}
                />
              ) : (
                <svg aria-hidden="true" viewBox="0 0 24 24">
                  <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-4.42 0-8 2.24-8 5v1h16v-1c0-2.76-3.58-5-8-5Z" />
                </svg>
              )}
            </button>
            {isAccountMenuOpen && (
              <div className="account-menu-dropdown" id="account-menu-options">
                <Link
                  aria-current={pathname === "/profile" ? "page" : undefined}
                  className={pathname === "/profile" ? "account-menu-link active" : "account-menu-link"}
                  href="/profile"
                  onClick={() => setIsAccountMenuOpen(false)}
                >
                  My profile
                </Link>
                <Link
                  aria-current={pathname === "/my-posts" ? "page" : undefined}
                  className={pathname === "/my-posts" ? "account-menu-link active" : "account-menu-link"}
                  href="/my-posts"
                  onClick={() => setIsAccountMenuOpen(false)}
                >
                  My posts
                </Link>
                <Link
                  aria-current={pathname.startsWith("/saved") ? "page" : undefined}
                  className={pathname.startsWith("/saved") ? "account-menu-link active" : "account-menu-link"}
                  href="/saved"
                  onClick={() => setIsAccountMenuOpen(false)}
                >
                  Saved posts
                </Link>
                <button className="account-menu-link account-menu-logout" onClick={signOut} type="button">
                  Log out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
