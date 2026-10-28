"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import RideLayout, { RideCard } from "../../../components/RideLayout";
import { apiRequest } from "../../../lib/api";
import { rideError, type RideRequest } from "../../../lib/rides";
import CarpoolList from "../../../components/CarpoolList";

export default function MyRidesPage() {
  const [rides, setRides] = useState<RideRequest[]>([]);
  const [offset, setOffset] = useState(0);
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback((nextOffset: number, signal?: AbortSignal) =>
    apiRequest<RideRequest[]>(`/rides/mine?offset=${nextOffset}&limit=20`, { signal }), []);
  useEffect(() => {
    const controller = new AbortController();
    load(0, controller.signal).then(rows => {
      if (!controller.signal.aborted) { setRides(rows); setMore(rows.length === 20); }
    }).catch((err: unknown) => { if (!controller.signal.aborted) setError(rideError(err)); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [load]);
  async function refresh(nextOffset: number) {
    setBusy(true); setError("");
    try {
      const rows = await load(nextOffset);
      setRides(rows); setOffset(nextOffset); setMore(rows.length === 20);
    } catch (err) { setError(rideError(err)); } finally { setBusy(false); }
  }
  return <RideLayout>
    <section className="page-heading"><div><p className="eyebrow">Your journeys</p><h1>My rides</h1><p className="muted">Your carpools, ride requests, and trips you have offered to drive. Open a trip for requests and booking details.</p></div><Link className="button button-primary" href="/rides/new">Request a ride</Link></section>
    <CarpoolList mine />
    <h2>Ride requests and driver offers</h2>
    <p className="ride-notice">Ride and carpool updates are in your <Link className="text-link" href="/notifications">notifications</Link>. Use the bell beside your profile from anywhere in the app, or refresh here for current trip details.</p>
    <button className="button button-secondary" disabled={busy} onClick={() => refresh(offset)}>Refresh rides</button>
    {error && <p className="form-error" role="alert">{error}</p>}
    {busy ? <p role="status">Loading your rides...</p> : rides.length ? <div className="ride-grid">{rides.map(ride => <RideCard key={ride.id} ride={ride} />)}</div> : !error && <div className="state-card"><h2>No ride requests yet</h2><p>Request a ride, or help a community member by browsing requests.</p><div className="form-actions"><Link className="button button-primary" href="/rides/new">Request a ride</Link><Link className="button button-secondary" href="/rides">Browse requests</Link></div></div>}
    <div className="form-actions"><button className="button button-secondary" disabled={busy || offset === 0} onClick={() => refresh(offset - 20)}>Previous</button><button className="button button-secondary" disabled={busy || !more} onClick={() => refresh(offset + 20)}>Next</button></div>
  </RideLayout>;
}
