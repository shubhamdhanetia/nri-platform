"use client";

import Link from "next/link";
import { ArrowLeft, ArrowRight, RefreshCw, SlidersHorizontal } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import ExploreLocationSearch from "./ExploreLocationSearch";
import { apiRequest } from "../lib/api";
import { rideDate, rideError, type LocationSelection, type RideRequest } from "../lib/rides";

type Cursor = { pickup_start: string; id: number };
type Filters = {
  pickup_location_id?: string; radius_km?: number; departure_date?: string;
  pickup_time_from?: string; pickup_time_to?: string; max_passengers?: number;
};
type Page = { rides: RideRequest[]; has_more: boolean; next_cursor: Cursor | null };
const KM_PER_MILE = 1.609344;

export default function RideRequestsTable({ searchCenter }: { searchCenter: [number, number] }) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [pickup, setPickup] = useState<LocationSelection | null>(null);
  const [query, setQuery] = useState("");
  const [radius, setRadius] = useState("25");
  const [date, setDate] = useState("");
  const [timeOpen, setTimeOpen] = useState(false);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [passengers, setPassengers] = useState("");
  const [applied, setApplied] = useState<Filters>({});
  const [page, setPage] = useState<Page>({ rides: [], has_more: false, next_cursor: null });
  const [history, setHistory] = useState<(Cursor | null)[]>([null]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [searchVersion, setSearchVersion] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const activeFilterCount = [applied.pickup_location_id, applied.departure_date, applied.max_passengers].filter(Boolean).length;

  const load = useCallback(async (filters: Filters, cursors: (Cursor | null)[]) => {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setBusy(true); setError("");
    try {
      const result = await apiRequest<Page>("/rides/requests/table-search", {
        method: "POST", signal: request.signal,
        body: JSON.stringify({ ...filters, limit: 20, cursor: cursors[cursors.length - 1] }),
      });
      if (request.signal.aborted) return;
      setPage(result); setApplied(filters); setHistory(cursors);
    } catch (err) {
      if (!request.signal.aborted) setError(rideError(err));
    } finally {
      if (!request.signal.aborted) setBusy(false);
    }
  }, []);

  useEffect(() => {
    const request = new AbortController();
    controller.current = request;
    apiRequest<Page>("/rides/requests/table-search", {
      method: "POST", signal: request.signal, body: JSON.stringify({ limit: 20 }),
    }).then(result => {
      if (!request.signal.aborted) setPage(result);
    }).catch((err: unknown) => {
      if (!request.signal.aborted) setError(rideError(err));
    }).finally(() => {
      if (!request.signal.aborted) setBusy(false);
    });
    return () => controller.current?.abort();
  }, []);

  function apply(event: FormEvent) {
    event.preventDefault();
    if (query.trim() && !pickup) { setError("Select a pickup suggestion or clear the pickup filter."); return; }
    if (timeOpen && (!date || !from || !to || to <= from)) {
      setError("Select both times with To later than From on the same day."); return;
    }
    void load({
      ...(pickup ? { pickup_location_id: pickup.locationId, radius_km: Number(radius) * KM_PER_MILE } : {}),
      ...(date ? { departure_date: date } : {}),
      ...(timeOpen ? { pickup_time_from: from, pickup_time_to: to } : {}),
      ...(passengers ? { max_passengers: Number(passengers) } : {}),
    }, [null]);
  }

  function clear() {
    setPickup(null); setQuery(""); setRadius("25"); setDate(""); setTimeOpen(false);
    setFrom(""); setTo(""); setPassengers(""); setSearchVersion(version => version + 1);
    void load({}, [null]);
  }

  return <section className="ride-table-section" aria-labelledby="ride-table-title">
    <div className="community-results-heading"><div><h2 id="ride-table-title">All active requests</h2>
    </div></div>
    <div className="ride-table-toolbar">
      <button type="button" className="button button-secondary" aria-expanded={filtersOpen} aria-controls="ride-table-filter-panel" onClick={() => setFiltersOpen(open => !open)}>
        <SlidersHorizontal size={16} />{filtersOpen ? "Hide filters" : "Show filters"}
      </button>
      {activeFilterCount > 0 && <span className="field-hint">{activeFilterCount} active filter{activeFilterCount === 1 ? "" : "s"}</span>}
      <button type="button" className="community-icon-button" title="Refresh table" aria-label="Refresh table" disabled={busy} onClick={() => void load(applied, [null])}><RefreshCw size={17} /></button>
    </div>
    <div id="ride-table-filter-panel" hidden={!filtersOpen}>
    <form className="ride-table-filters" onSubmit={apply}>
      <ExploreLocationSearch key={searchVersion} label="Table pickup area" center={searchCenter} onSelectionChange={setPickup} onQueryChange={setQuery} />
      <label className="form-field"><span>Pickup radius (miles)</span><select value={radius} disabled={!pickup} onChange={e => setRadius(e.target.value)}>
        {[5, 10, 25, 50].map(value => <option key={value} value={value}>{value} miles</option>)}
      </select></label>
      <label className="form-field"><span>Table departure date</span><input type="date" value={date} onChange={e => {
        setDate(e.target.value); if (!e.target.value) { setTimeOpen(false); setFrom(""); setTo(""); }
      }} /></label>
      <label className="form-field"><span>Maximum passengers</span><select value={passengers} onChange={e => setPassengers(e.target.value)}>
        <option value="">Any</option>{[1, 2, 3, 4, 5, 6, 7, 8].map(value => <option key={value}>{value}</option>)}
      </select></label>
      <button type="button" className="text-link" disabled={!date} aria-expanded={timeOpen} onClick={() => setTimeOpen(open => !open)}>
        {timeOpen ? "Remove table time range" : "Add table time range"}
      </button>
      {timeOpen && <><label className="form-field"><span>Table From</span><input type="time" value={from} onChange={e => setFrom(e.target.value)} required /></label>
        <label className="form-field"><span>Table To</span><input type="time" value={to} onChange={e => setTo(e.target.value)} required /></label></>}
      <p className="field-hint">Local ride times / straight-line radius</p>
      <div className="form-actions"><button className="button button-primary" disabled={busy}>Apply filters</button>
        <button type="button" className="button button-secondary" disabled={busy} onClick={clear}>Clear filters</button></div>
    </form>
    </div>
    {error && <div className="form-error" role="alert">{error}</div>}
    <div aria-busy={busy}>
      {busy ? <p role="status">Loading active requests...</p> : error ? <p>Table could not be updated. Retry Apply filters or Refresh table.</p> : <>
        <p className="field-hint" role="status">{page.rides.length} results on page {history.length}. Earliest pickup first.</p>
        {page.rides.length ? <div className="ride-table-scroll" tabIndex={0} role="region" aria-label="Active ride requests table">
          <table className="ride-requests-table"><caption className="sr-only">Active ride requests, ordered by earliest pickup</caption>
            <thead><tr>{["Pickup", "Drop-off", "Pickup window", "Passengers", "Bags", "Action"].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead>
            <tbody>{page.rides.map(ride => <tr key={ride.id}>
              <td>{ride.pickup.location}</td><td>{ride.dropoff.location}</td>
              <td>{rideDate(ride.pickup_start, ride.timezone)}<br />to {rideDate(ride.pickup_end, ride.timezone)}<br /><small>{ride.timezone}</small></td>
              <td>{ride.passengers}</td><td>{ride.bags}</td><td><Link className="text-link" href={`/rides/${ride.id}`}>View ride</Link></td>
            </tr>)}</tbody>
          </table>
        </div> : <div className="community-state"><h3>No matching requests</h3><button type="button" className="button button-secondary" onClick={clear}>Clear filters</button></div>}
      </>}
    </div>
    <div className="form-actions">
      <button className="community-icon-button" title="Previous requests" aria-label="Previous requests" disabled={busy || history.length === 1} onClick={() => void load(applied, history.slice(0, -1))}><ArrowLeft size={18} /></button>
      <button className="community-icon-button" title="Next requests" aria-label="Next requests" disabled={busy || !!error || !page.has_more} onClick={() => {
        if (page.next_cursor) void load(applied, [...history, page.next_cursor]);
      }}><ArrowRight size={18} /></button>
    </div>
  </section>;
}
