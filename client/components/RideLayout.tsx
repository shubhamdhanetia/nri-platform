"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSyncExternalStore, type ReactNode } from "react";
import ProtectedPage from "./ProtectedPage";
import { rideDate, type RideRequest } from "../lib/rides";

const subscribe = () => () => {};

export function useRideTimezone() {
  return useSyncExternalStore(subscribe, () => Intl.DateTimeFormat().resolvedOptions().timeZone, () => "UTC");
}

export default function RideLayout({ children }: { children: ReactNode }) {
  const path = usePathname();
  return <ProtectedPage>
    <nav className="ride-tabs" aria-label="Rides navigation">
      {[["/rides", "Browse requests"], ["/rides/carpools", "Find a carpool"], ["/rides/new", "Request a ride"], ["/rides/mine", "My rides"], ["/rides/driver", "Driver profile"]].map(([href, label]) =>
        <Link key={href} href={href} aria-current={path === href ? "page" : undefined}>{label}</Link>)}
    </nav>
    {children}
  </ProtectedPage>;
}

export function RideCard({ ride, role }: { ride: RideRequest; role?: "Driver" | "Passenger" }) {
  return <article className="ride-card">
    <div className="ride-between"><strong>{ride.rider.name}</strong><span className="ride-badge">{ride.booking_status ?? ride.status}</span></div>
    {role && <p className="field-hint">Your role: <span className="ride-badge">{role}</span></p>}
    {ride.my_offer_status && <p className="field-hint">Your driver offer: {ride.my_offer_status.toLowerCase().replaceAll("_", " ")}</p>}
    <RideRoute ride={ride} />
    <div className="ride-meta"><span>{rideDate(ride.pickup_start, ride.timezone)}</span><span>{ride.passengers} passenger(s)</span><span>{ride.bags} bag(s)</span></div>
    <p className="field-hint">Times in {ride.timezone}. Cost-sharing offers in {ride.currency}.</p>
    <Link className="button button-secondary" href={`/rides/${ride.id}`}>View ride</Link>
  </article>;
}

export function RideRoute({ ride }: { ride: RideRequest }) {
  return <div className="ride-route"><div><span>Pickup</span><strong>{ride.pickup.location}</strong></div><div><span>Drop-off</span><strong>{ride.dropoff.location}</strong></div></div>;
}
