"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import ProtectedPage from "./ProtectedPage";

export default function HousingLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const active = pathname === "/housing" ? "/housing"
    : pathname === "/housing/people" || pathname === "/housing/roommates" ? "/housing/people"
      : pathname.startsWith("/housing/mine") || pathname === "/housing/saved" || pathname === "/housing/inquiries" ? "/housing/mine" : null;
  return <ProtectedPage>
    <nav className="housing-tabs" aria-label="Housing navigation">
      {[["/housing", "Find a place"], ["/housing/people", "Find people"], ["/housing/mine", "My housing"]].map(([href, label]) =>
        <Link key={href} href={href} aria-current={active === href ? "page" : undefined}>{label}</Link>)}
    </nav>
    {children}
  </ProtectedPage>;
}
