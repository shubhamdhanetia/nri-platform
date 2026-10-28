"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { apiRequest } from "../lib/api";
import type { CarpoolPage } from "../lib/carpools";
import { rideError, type LocationSelection } from "../lib/rides";
import CarpoolCard from "./CarpoolCard";
import LocationAutocomplete from "./LocationAutocomplete";

export default function CarpoolList({ mine = false }: { mine?: boolean }) {
  const [page, setPage] = useState<CarpoolPage | null>(null);
  const [pickup, setPickup] = useState<LocationSelection | null>(null);
  const [dropoff, setDropoff] = useState<LocationSelection | null>(null);
  const [filters, setFilters] = useState("");
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback((nextOffset: number, query: string, signal?: AbortSignal) =>
    apiRequest<CarpoolPage>(`/rides/carpools/${mine ? "mine" : "trips"}?limit=20&offset=${nextOffset}${query}`, { signal }), [mine]);
  useEffect(() => {
    const controller = new AbortController();
    load(0, "", controller.signal).then(result => {
      if (!controller.signal.aborted) setPage(result);
    }).catch((err: unknown) => { if (!controller.signal.aborted) setError(rideError(err)); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [load]);
  async function refresh(nextOffset: number, query = filters) {
    setBusy(true); setError("");
    try {
      const result = await load(nextOffset, query);
      setPage(result); setOffset(nextOffset); setFilters(query);
    } catch (err) { setError(rideError(err)); }
    finally { setBusy(false); }
  }
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const query = new URLSearchParams();
    if (pickup) query.set("pickup_location_id", pickup.locationId);
    if (dropoff) query.set("dropoff_location_id", dropoff.locationId);
    if (form.get("date")) query.set("departure_date", String(form.get("date")));
    query.set("passengers", String(form.get("passengers")));
    query.set("radius_km", String(form.get("radius")));
    void refresh(0, `&${query}`);
  }
  return <section aria-label={mine ? "My carpools" : "Find a carpool"}>
    <div className="ride-between"><h2>{mine ? "My carpools" : "Available carpools"}</h2><Link className="button button-primary" href="/rides/carpools/new">Offer a carpool</Link></div>
    {mine ? <p className="muted">Trips you published and directions you requested. Outbound and return approvals are independent.</p> :
      <form className="form-card" onSubmit={search}>
        <div className="form-row"><LocationAutocomplete label="Pickup area (optional)" onAddressSelected={setPickup} /><LocationAutocomplete label="Destination area (optional)" onAddressSelected={setDropoff} /></div>
        <div className="form-row">
          <label className="form-field"><span>Departure date (optional)</span><input type="date" name="date" /></label>
          <label className="form-field"><span>Seats needed</span><input type="number" name="passengers" min={1} max={8} defaultValue={1} required /></label>
          <label className="form-field"><span>Area radius</span><select name="radius" defaultValue="25"><option value="10">10 km</option><option value="25">25 km</option><option value="50">50 km</option><option value="100">100 km</option></select></label>
        </div>
        <p className="field-hint">Date uses each trip&apos;s displayed timezone. Radius applies to both selected areas. These are meeting-point trips, not door-to-door services.</p>
        <button className="button button-primary" disabled={busy}>Search carpools</button>
      </form>}
    <button className="button button-secondary" disabled={busy} onClick={() => void refresh(offset)}>Refresh carpools</button>
    {error && <p className="form-error" role="alert">{error}</p>}
    {busy ? <p role="status">Loading carpools...</p> : page && (
      page.trips.length ? <div className="ride-grid">{page.trips.map(trip => <CarpoolCard key={trip.id} trip={trip} />)}</div> :
        <div className="state-card"><p>{mine ? "No carpools yet. Offer your planned trip or request seats on a community trip." : "No available carpools match. Try another date or area, or request a ride instead."}</p><Link className="text-link" href={mine ? "/rides/carpools" : "/rides/new"}>{mine ? "Find a carpool" : "Request a ride"}</Link></div>
    )}
    <div className="form-actions"><button className="button button-secondary" disabled={busy || offset === 0} onClick={() => void refresh(offset - 20)}>Previous carpools</button><button className="button button-secondary" disabled={busy || !page?.has_more} onClick={() => void refresh(offset + 20)}>Next carpools</button></div>
  </section>;
}
