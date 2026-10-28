"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type KeyboardEvent } from "react";
import Link from "next/link";
import RideLayout, { RideCard } from "../../../components/RideLayout";
import { apiRequest } from "../../../lib/api";
import { rideError, type RideRequest } from "../../../lib/rides";
import CarpoolList from "../../../components/CarpoolList";

type MyRidesTab = "carpools" | "requests";
const tabStorageKey = "my-rides-tab";
const tabChangeEvent = "my-rides-tab-changed";

function subscribeToTab(callback: () => void) {
  window.addEventListener(tabChangeEvent, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(tabChangeEvent, callback);
    window.removeEventListener("storage", callback);
  };
}

function selectedTab(): MyRidesTab {
  return window.sessionStorage.getItem(tabStorageKey) === "requests" ? "requests" : "carpools";
}

export default function MyRidesPage() {
  return <RideLayout><MyRidesContent /></RideLayout>;
}

function MyRidesContent() {
  const tab = useSyncExternalStore(subscribeToTab, selectedTab, () => "carpools");
  const carpoolTab = useRef<HTMLButtonElement>(null);
  const requestTab = useRef<HTMLButtonElement>(null);
  function selectTab(value: MyRidesTab) {
    window.sessionStorage.setItem(tabStorageKey, value);
    window.dispatchEvent(new Event(tabChangeEvent));
  }
  function navigateTabs(event: KeyboardEvent<HTMLButtonElement>) {
    let next: MyRidesTab;
    if (event.key === "Home") next = "carpools";
    else if (event.key === "End") next = "requests";
    else if (event.key === "ArrowLeft" || event.key === "ArrowRight") next = tab === "carpools" ? "requests" : "carpools";
    else return;
    event.preventDefault();
    selectTab(next);
    (next === "carpools" ? carpoolTab : requestTab).current?.focus();
  }
  return <>
    <section className="page-heading"><div><p className="eyebrow">Your journeys</p><h1>My rides</h1><p className="muted">Manage planned carpools separately from ride requests and driver offers.</p></div></section>
    <p className="ride-notice">Ride and carpool updates are in your <Link className="text-link" href="/notifications">notifications</Link>. Use the bell beside your profile from anywhere in the app, or refresh here for current trip details.</p>
    <div className="my-rides-tabs" role="tablist" aria-label="My rides sections">
      <button ref={carpoolTab} id="my-carpools-tab" role="tab" type="button" aria-selected={tab === "carpools"} aria-controls="my-carpools-panel" tabIndex={tab === "carpools" ? 0 : -1} onClick={() => selectTab("carpools")} onKeyDown={navigateTabs}>Carpools</button>
      <button ref={requestTab} id="my-requests-tab" role="tab" type="button" aria-selected={tab === "requests"} aria-controls="my-requests-panel" tabIndex={tab === "requests" ? 0 : -1} onClick={() => selectTab("requests")} onKeyDown={navigateTabs}>Ride requests</button>
    </div>
    <div id="my-carpools-panel" role="tabpanel" aria-labelledby="my-carpools-tab" tabIndex={0} hidden={tab !== "carpools"}><CarpoolList mine /></div>
    <div id="my-requests-panel" role="tabpanel" aria-labelledby="my-requests-tab" tabIndex={0} hidden={tab !== "requests"}><MyRideRequests /></div>
  </>;
}

function MyRideRequests() {
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
  return <section aria-label="My ride requests and driver offers">
    <div className="ride-between"><h2>Ride requests and driver offers</h2><Link className="button button-primary" href="/rides/new">Request a ride</Link></div>
    <p className="muted">Requests you published and trips you offered to drive. Open a ride for offers and booking details.</p>
    <button className="button button-secondary" disabled={busy} onClick={() => refresh(offset)}>Refresh rides</button>
    {error && <p className="form-error" role="alert">{error}</p>}
    {busy ? <p role="status">Loading your rides...</p> : rides.length ? <div className="ride-grid">{rides.map(ride => <RideCard key={ride.id} ride={ride} role={ride.my_offer_status ? "Driver" : "Passenger"} />)}</div> : !error && <div className="state-card"><h2>No ride requests yet</h2><p>Request a ride, or help a community member by browsing requests.</p><div className="form-actions"><Link className="button button-primary" href="/rides/new">Request a ride</Link><Link className="button button-secondary" href="/rides">Browse requests</Link></div></div>}
    <div className="form-actions"><button className="button button-secondary" disabled={busy || offset === 0} onClick={() => refresh(offset - 20)}>Previous</button><button className="button button-secondary" disabled={busy || !more} onClick={() => refresh(offset + 20)}>Next</button></div>
  </section>;
}
