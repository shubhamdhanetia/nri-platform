"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const links = [
  { href: "/feed", label: "Explore" },
  { href: "/create-post", label: "Create a post" },
  { href: "/profile", label: "My profile" },
];

export default function AppNav() {
  const pathname = usePathname();
  const router = useRouter();

  function signOut() {
    window.localStorage.removeItem("access_token");
    window.localStorage.removeItem("user");
    router.replace("/login");
  }

  return (
    <header className="app-header">
      <div className="nav-inner">
        <Link className="brand nav-brand" href="/feed">
          <span className="brand-mark">N</span>
          <span>NRI Platform</span>
        </Link>
        <nav className="main-nav" aria-label="Main navigation">
          {links.map((link) => (
            <Link
              className={pathname === link.href ? "nav-link active" : "nav-link"}
              href={link.href}
              key={link.href}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <button className="sign-out-button" onClick={signOut} type="button">
          Sign out
        </button>
      </div>
    </header>
  );
}
