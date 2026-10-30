"use client";

import { useCallback, useEffect, useEffectEvent, useMemo, useRef, useState, type FormEvent } from "react";
import dynamic from "next/dynamic";
import { ArrowLeft, ArrowRight, ArrowUpRight, CalendarDays, Car, ChevronDown, ChevronUp, List, LocateFixed, Luggage, Map as MapIcon, MapPin, Maximize2, Minimize2, Plus, RefreshCw, Search, Users } from "lucide-react";
import Link from "next/link";
import { apiRequest, type PostSearchBounds } from "../lib/api";
import type { CarpoolPage, CarpoolSearchFilters } from "../lib/carpools";
import { locationSearchBounds } from "../lib/map";
import { rideDate, rideError, rideMoney, type LocationSelection } from "../lib/rides";
import CarpoolCard from "./CarpoolCard";
import ExploreLocationSearch from "./ExploreLocationSearch";

const CarpoolMap = dynamic(() => import("./CommunityMap"), {
  ssr: false,
  loading: () => <div className="explore-map-loading">Loading map...</div>,
});
const DEFAULT_CENTER: [number, number] = [20, 0];
const KM_PER_MILE = 1.609344;
const DEFAULT_RADIUS_MILES = "25";
const DEFAULT_FILTERS: CarpoolSearchFilters = { passengers: 1 };
type SearchScope = "pickup" | "destination";

export default function CarpoolList({ mine = false }: { mine?: boolean }) {
  const [page, setPage] = useState<CarpoolPage | null>(null);
  const [pickup, setPickup] = useState<LocationSelection | null>(null);
  const [dropoff, setDropoff] = useState<LocationSelection | null>(null);
  const [filters, setFilters] = useState<CarpoolSearchFilters>(DEFAULT_FILTERS);
  const [scope, setScope] = useState<SearchScope>("pickup");
  const scopeRef = useRef<SearchScope>("pickup");
  const [appliedScope, setAppliedScope] = useState<SearchScope>("pickup");
  const [destinationMap, setDestinationMap] = useState(false);
  const [appliedMap, setAppliedMap] = useState(true);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(mine);
  const [error, setError] = useState("");
  const [view, setView] = useState<"feed" | "map">("map");
  const [fullscreen, setFullscreen] = useState(false);
  const [resultsOpen, setResultsOpen] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectionVersion, setSelectionVersion] = useState(0);
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [zoom, setZoom] = useState(2);
  const [searchCenter, setSearchCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [pickupQuery, setPickupQuery] = useState("");
  const [dropoffQuery, setDropoffQuery] = useState("");
  const [date, setDate] = useState("");
  const [passengers, setPassengers] = useState("1");
  const [radius, setRadius] = useState(DEFAULT_RADIUS_MILES);
  const [filterVersion, setFilterVersion] = useState(0);
  const [pickupVersion, setPickupVersion] = useState(0);
  const [dropoffVersion, setDropoffVersion] = useState(0);
  const [mapVersion, setMapVersion] = useState(0);
  const [bounds, setBounds] = useState<PostSearchBounds | null>(null);
  const [mapBounds, setMapBounds] = useState<PostSearchBounds | null>(null);
  const [locating, setLocating] = useState(!mine);
  const [locationError, setLocationError] = useState("");
  const [autoSearchPending, setAutoSearchPending] = useState(false);
  const locationVersion = useRef(0);
  const locationStarted = useRef(false);
  const mounted = useRef(false);
  const filterForm = useRef<HTMLFormElement | null>(null);
  const requestController = useRef<AbortController | null>(null);
  const viewport = useRef<{ center: [number, number]; zoom: number } | null>(null);
  const onViewportChange = useCallback((next: [number, number], nextZoom: number) => {
    viewport.current = { center: next, zoom: nextZoom };
  }, []);
  const onLocationSelected = useCallback((next: [number, number]) => {
    if (scopeRef.current !== "pickup") return;
    locationVersion.current += 1;
    requestController.current?.abort();
    viewport.current = null;
    setCenter(next); setSearchCenter(next); setZoom(11);
    setMapVersion(version => version + 1); setMapBounds(null);
    setBounds(locationSearchBounds(next)); setSelectedId(null);
    setLocationError(""); setLocating(false); setBusy(false); setAutoSearchPending(true);
  }, []);
  const locate = useCallback(() => {
    const version = ++locationVersion.current;
    if (!navigator.geolocation) {
      setLocationError("Location access is unavailable. Select an area or move the map.");
      setLocating(false); return;
    }
    setLocating(true); setLocationError("");
    navigator.geolocation.getCurrentPosition(position => {
      if (!mounted.current || version !== locationVersion.current) return;
      if (scopeRef.current === "destination") {
        const next: [number, number] = [position.coords.latitude, position.coords.longitude];
        setCenter(next); setSearchCenter(next); setSelectedId(null); setLocating(false);
        return;
      }
      setPickup(null); setPickupQuery(""); setPickupVersion(value => value + 1);
      onLocationSelected([position.coords.latitude, position.coords.longitude]);
    }, () => {
      if (!mounted.current || version !== locationVersion.current) return;
      setLocationError("Unable to get your location. Select an area or move the map instead.");
      setLocating(false);
    }, { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 });
  }, [onLocationSelected]);
  useEffect(() => {
    mounted.current = true;
    if (!mine && !locationStarted.current) { locationStarted.current = true; locate(); }
    return () => { mounted.current = false; requestController.current?.abort(); };
  }, [mine, locate]);
  useEffect(() => {
    if (!mine) return;
    const controller = new AbortController();
    requestController.current = controller;
    apiRequest<CarpoolPage>("/rides/carpools/mine?limit=20&offset=0", { signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) setPage(result);
    }).catch((err: unknown) => { if (!controller.signal.aborted) setError(rideError(err)); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => requestController.current?.abort();
  }, [mine]);
  const searchAutomatically = useEffectEvent((searchBounds: PostSearchBounds | null) => { searchArea(searchBounds); });
  useEffect(() => {
    if (!autoSearchPending || locating) return;
    const searchBounds = view === "map" ? mapBounds : bounds;
    if (scope === "pickup" && !searchBounds) return;
    const timer = window.setTimeout(() => searchAutomatically(searchBounds), 150);
    return () => window.clearTimeout(timer);
  }, [autoSearchPending, locating, view, mapBounds, bounds, scope]);
  useEffect(() => {
    if (!fullscreen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setFullscreen(false); };
    document.addEventListener("keydown", escape);
    return () => { document.body.style.overflow = previous; document.removeEventListener("keydown", escape); };
  }, [fullscreen]);
  async function refresh(nextOffset: number, query = filters, searchBounds = bounds, searchScope = appliedScope, searchOnMap = appliedMap) {
    locationVersion.current += 1;
    setLocating(false); setAutoSearchPending(false);
    if (!mine && searchOnMap && !searchBounds) { setError("Select an area or search the map first."); return; }
    if (!mine && !searchOnMap && searchScope === "destination" && !query.dropoff_location_id) { setError("Select a destination suggestion before searching."); return; }
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setBusy(true); setError(""); setResultsOpen(true);
    setOffset(nextOffset); setFilters(query); setAppliedScope(searchScope); setAppliedMap(searchOnMap);
    if (searchOnMap) setBounds(searchBounds);
    try {
      const destinationQuery = new URLSearchParams({ limit: "20", offset: String(nextOffset) });
      for (const [key, value] of Object.entries(query)) {
        if (value !== undefined) destinationQuery.set(key, String(value));
      }
      const path = mine ? `/rides/carpools/mine?limit=20&offset=${nextOffset}`
        : !searchOnMap ? `/rides/carpools/trips?${destinationQuery}` : "/rides/carpools/trips/search";
      const result = await apiRequest<CarpoolPage>(path, mine || !searchOnMap ? { signal: controller.signal } : {
        method: "POST", signal: controller.signal,
        body: JSON.stringify({ ...query, scope: searchScope, bounds: searchBounds, limit: 20, offset: nextOffset }),
      });
      if (!controller.signal.aborted) { setPage(result); setSelectedId(null); }
    } catch (err) { if (!controller.signal.aborted) setError(rideError(err)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  const draftFilters: CarpoolSearchFilters = {
    ...(dropoff && !(scope === "destination" && destinationMap) ? { dropoff_location_id: dropoff.locationId, radius_km: Number(radius) * KM_PER_MILE } : {}),
    ...(date ? { departure_date: date } : {}),
    passengers: Number(passengers),
  };
  const filterBounds = view === "map" ? mapBounds : bounds;
  const searchOnMap = scope === "pickup" || destinationMap;
  const resultsLoading = busy || locating || autoSearchPending;
  const changed = page !== null && (
    scope !== appliedScope || searchOnMap !== appliedMap || JSON.stringify(filters) !== JSON.stringify(draftFilters)
    || (searchOnMap && JSON.stringify(bounds) !== JSON.stringify(filterBounds))
    || (scope === "pickup" && pickupQuery.trim() !== "" && !pickup) || (dropoffQuery.trim() !== "" && !dropoff)
  );
  function searchArea(searchBounds = filterBounds, searchScope = scope) {
    setAutoSearchPending(false);
    if (!filterForm.current?.reportValidity()) return;
    if ((searchScope === "pickup" && pickupQuery.trim() && !pickup) || (dropoffQuery.trim() && !dropoff)) {
      setError("Select an area suggestion or clear the location field."); return;
    }
    void refresh(0, draftFilters, searchBounds, searchScope, searchScope === "pickup" || destinationMap);
  }
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); searchArea();
  }
  function interruptLocation() {
    locationVersion.current += 1;
    setLocating(false); setAutoSearchPending(false);
  }
  function changeScope(next: SearchScope) {
    if (next === scope) return;
    scopeRef.current = next;
    interruptLocation(); requestController.current?.abort();
    setScope(next); setPage(null); setError(""); setLocationError(""); setBusy(false); setOffset(0); setSelectedId(null);
    setDestinationMap(false);
    if (next === "destination") {
      setPickup(null); setPickupQuery(""); setPickupVersion(version => version + 1);
    }
    if (next === "destination" && dropoff) setAutoSearchPending(true);
  }
  const onPickupSelected = useCallback((selection: LocationSelection | null) => {
    if (scopeRef.current === "pickup") setPickup(selection);
  }, []);
  const onDestinationLocationSelected = useCallback((next: [number, number]) => {
    if (scopeRef.current !== "destination") return;
    locationVersion.current += 1;
    viewport.current = { center: next, zoom: 11 };
    setCenter(next); setSearchCenter(next); setZoom(11);
    setMapVersion(version => version + 1); setMapBounds(null);
    setSelectedId(null); setLocationError(""); setLocating(false);
  }, []);
  const onDestinationSelected = useCallback((selection: LocationSelection | null) => {
    setDropoff(selection);
    setDestinationMap(false);
    if (scopeRef.current === "destination" && selection) setAutoSearchPending(true);
  }, []);
  function searchMapArea() {
    if (!filterForm.current?.reportValidity() || !mapBounds) return;
    interruptLocation();
    if (scope === "destination") {
      setDestinationMap(true); setDropoff(null); setDropoffQuery("");
      setDropoffVersion(version => version + 1);
      void refresh(0, {
        ...(date ? { departure_date: date } : {}), passengers: Number(passengers),
      }, mapBounds, scope, true);
    } else searchArea(mapBounds, scope);
  }
  function resetFilters() {
    setPickup(null); setDropoff(null); setPickupQuery(""); setDropoffQuery("");
    setDate(""); setPassengers("1"); setRadius(DEFAULT_RADIUS_MILES); setFilterVersion(version => version + 1);
    if (scope === "destination" && !destinationMap) {
      interruptLocation(); requestController.current?.abort();
      setPage(null); setError(""); setBusy(false); setOffset(0); setSelectedId(null);
    } else void refresh(0, DEFAULT_FILTERS, filterBounds, scope, true);
  }
  function changeView(next: "feed" | "map") {
    if (viewport.current) { setCenter(viewport.current.center); setZoom(viewport.current.zoom); }
    setView(next); setResultsOpen(true);
    if (next === "feed") setFullscreen(false);
  }
  function toggleFullscreen() {
    if (!fullscreen) changeView("map");
    setFullscreen(!fullscreen);
  }
  const selectTrip = useCallback((id: string) => {
    locationVersion.current += 1;
    setLocating(false);
    setView("map"); setResultsOpen(true); setSelectedId(id); setSelectionVersion(version => version + 1);
  }, []);
  const selectMapTrip = useCallback((id: string) => { setSelectedId(id); }, []);
  const clearMapSelection = useCallback(() => { setSelectedId(null); }, []);
  const points = useMemo(() => (page?.trips ?? []).map(trip => ({
    id: trip.id, latitude: trip.pickup.latitude, longitude: trip.pickup.longitude,
    title: `${trip.driver.name}: ${trip.pickup.location}`,
    description: `To ${trip.dropoff.location} / ${rideDate(trip.pickup_start, trip.timezone)}`,
    href: `/rides/carpools/${trip.id}`, linkLabel: "View carpool",
    destination: {
      latitude: trip.dropoff.latitude, longitude: trip.dropoff.longitude,
      title: `Destination: ${trip.dropoff.location}`,
      description: `${trip.driver.name} / From ${trip.pickup.location} / ${rideDate(trip.pickup_start, trip.timezone)}`,
    },
  })), [page]);

  if (!mine) return <section className={`community-page rides-browse rides-map-browser carpool-browse${fullscreen ? " community-expanded" : ""}`} aria-label="Find a carpool">
    <header className="community-heading">
      <div><p className="eyebrow">GOING THE SAME WAY</p><h1>Find a carpool</h1></div>
      <div className="community-heading-actions">
        <button className="button button-secondary" aria-pressed={fullscreen} onClick={toggleFullscreen}>{fullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}{fullscreen ? "Exit full screen" : "Full screen map"}</button>
        <Link className="button button-primary" href="/rides/carpools/new"><Plus size={18} />Offer a carpool</Link>
      </div>
    </header>
    <div className="community-controls">
      <div className="community-view-toggle carpool-scope-toggle" role="group" aria-label="Carpool search scope">
        <button type="button" aria-pressed={scope === "pickup"} onClick={() => changeScope("pickup")}><MapIcon size={17} />Pickups in this map</button>
        <button type="button" aria-pressed={scope === "destination"} onClick={() => changeScope("destination")}><MapPin size={17} />Going to a destination</button>
      </div>
    </div>
    <form ref={filterForm} className="rides-discovery" aria-label="Carpool filters" onSubmit={search} onChange={interruptLocation}>
      <div className="community-location" hidden={scope === "destination"}><MapPin size={18} /><ExploreLocationSearch key={`pickup-${filterVersion}-${pickupVersion}`} label="Pickup area (optional)" center={searchCenter} onLocationSelected={onLocationSelected} onSelectionChange={onPickupSelected} onQueryChange={setPickupQuery} /></div>
      <div className="community-location"><MapPin size={18} /><ExploreLocationSearch key={`dropoff-${filterVersion}-${dropoffVersion}`} label={scope === "destination" ? "Destination area" : "Destination area (optional)"} center={searchCenter} onLocationSelected={onDestinationLocationSelected} onSelectionChange={onDestinationSelected} onQueryChange={setDropoffQuery} /></div>
      <div className="rides-filter-form carpool-filter-fields">
        <label className="rides-date-field"><CalendarDays size={18} /><span>Departure date<input type="date" value={date} onChange={event => setDate(event.target.value)} /></span></label>
        <label className="rides-date-field"><Users size={18} /><span>Seats needed<input type="number" min={1} max={8} required value={passengers} onChange={event => setPassengers(event.target.value)} /></span></label>
        {dropoff && <label className="rides-date-field"><span>Distance from destination<select value={radius} onChange={event => setRadius(event.target.value)}>{[5, 10, 25, 50].map(value => <option key={value} value={value}>Within {value} miles</option>)}</select></span></label>}
        <div className="rides-filter-actions"><button type="submit" className="button button-primary" disabled={resultsLoading || (searchOnMap ? !filterBounds : !dropoff)}><Search size={16} />{scope === "destination" ? "Search carpools" : "Apply filters"}</button><button type="button" className="button button-secondary" disabled={resultsLoading || (searchOnMap && !filterBounds)} onClick={resetFilters}>Reset filters</button></div>
      </div>
    </form>
    {locationError && <p className="community-error" role="alert">{locationError}</p>}
    <div className="community-controls rides-map-status">
      <span className="community-scope"><MapPin size={15} />{changed ? "Area or filters changed" : scope === "destination" ? destinationMap ? "Selected destination area" : "Any pickup area" : bounds ? "Selected pickup area" : "Choose a pickup area"}</span>
      <div className="community-view-toggle" role="group" aria-label="Carpool view"><button type="button" aria-pressed={view === "feed"} onClick={() => changeView("feed")}><List size={17} />Feed</button><button type="button" aria-pressed={view === "map"} onClick={() => changeView("map")}><MapIcon size={17} />Map</button></div>
    </div>
    <div className="rides-search-summary"><p className="field-hint">Page {offset / 20 + 1} / local trip times / contribution per person, per direction</p><button className="community-icon-button" aria-label="Refresh carpools" title="Refresh carpools" disabled={resultsLoading || !page} onClick={() => void refresh(offset)}><RefreshCw size={18} /></button></div>
    <div className={`community-content community-${view} rides-${view}`}>
      {view === "map" && <div className="community-map-panel">
        <CarpoolMap key={mapVersion} posts={busy || autoSearchPending || error ? [] : points} center={center} initialZoom={zoom} fullscreen={fullscreen} selectedPostId={selectedId} selectionVersion={selectionVersion} onSelectPost={selectMapTrip} onClearSelection={clearMapSelection} onBoundsChange={setMapBounds} onCenterChange={setSearchCenter} onViewportChange={onViewportChange} />
        <div className="community-map-actions">
          <button className="button button-primary" title={scope === "destination" ? "Search destinations here" : "Search pickups here"} disabled={resultsLoading || !mapBounds} onClick={searchMapArea}><Search size={16} />{busy ? "Searching..." : scope === "destination" ? "Search destinations here" : "Search pickups here"}</button>
          <button className="community-icon-button" title="Center map on my location" aria-label="Center map on my location" disabled={locating} onClick={locate}>{locating ? <span className="spinner" /> : <LocateFixed size={19} />}</button>
          {selectedId !== null && !resultsLoading && !error && <button className="community-icon-button" title="Show both locations" aria-label="Show both locations" onClick={() => setSelectionVersion(version => version + 1)}><MapIcon size={19} /></button>}
          <button className="community-icon-button" title={fullscreen ? "Exit full screen" : "Full screen map"} aria-label={fullscreen ? "Exit full screen" : "Full screen map"} onClick={toggleFullscreen}>{fullscreen ? <Minimize2 size={19} /> : <Maximize2 size={19} />}</button>
        </div>
      </div>}
      <section className={`community-results${view === "map" && !resultsOpen ? " community-results-collapsed" : ""}`} aria-label="Available carpools" aria-busy={resultsLoading}>
        <div className="community-results-heading"><div><h2>Available carpools</h2><span aria-live="polite">{resultsLoading ? "Searching..." : error ? "Search unavailable" : !page ? "" : `${page.trips.length}${page.has_more ? "+" : ""} trips`}</span></div>{view === "map" && <button className="community-icon-button community-sheet-toggle" aria-label={resultsOpen ? "Collapse carpools" : "Expand carpools"} aria-expanded={resultsOpen} onClick={() => setResultsOpen(!resultsOpen)}>{resultsOpen ? <ChevronDown size={20} /> : <ChevronUp size={20} />}</button>}</div>
        <div className="community-result-body">
          {resultsLoading ? <div className="community-state" role="status"><span className="spinner" /><p>{locating ? "Finding your location..." : "Searching carpools..."}</p></div> : error ? <div className="community-state" role="alert"><h3>Could not load carpools</h3><p>{error}</p><button className="button button-secondary" onClick={() => void refresh(offset)}>Try again</button></div> : !page ? <div className="community-state"><MapPin size={30} /><h3>{scope === "destination" ? "Choose a destination" : "Choose a pickup area"}</h3></div> : !page.trips.length ? <div className="community-state"><Car size={30} /><h3>No matching carpools</h3><Link className="button button-secondary" href="/rides/new">Request a ride</Link></div> : page.trips.map(trip => <article className={`community-post rides-result${selectedId === trip.id ? " is-selected" : ""}`} key={trip.id} onClick={event => {
            if ((event.target as HTMLElement).closest("a, button") || window.getSelection()?.toString()) return;
            if (view === "feed") selectTrip(trip.id); else selectMapTrip(trip.id);
          }}>
            <div className="community-post-top"><span className="community-category-icon"><Car size={21} /></span><div className="community-post-context"><Link className="member-profile-link" href={`/profile/${trip.driver.id}`}>{trip.driver.name}</Link><time dateTime={trip.pickup_start}>{rideDate(trip.pickup_start, trip.timezone)}</time></div><span className="post-type-pill">{trip.status}</span></div>
            <h3><Link href={`/rides/carpools/${trip.id}`}>{trip.pickup.city} to {trip.dropoff.city}<ArrowUpRight size={18} /></Link></h3>
            <dl className="rides-result-route"><div><dt>Meeting point</dt><dd>{trip.pickup.location}</dd></div><div><dt>Drop-off point</dt><dd>{trip.dropoff.location}</dd></div></dl>
            <p className="rides-result-window">Until {rideDate(trip.pickup_end, trip.timezone)} ({trip.timezone})</p>
            <p className="carpool-price"><strong>{rideMoney(trip.amount, trip.currency)}</strong> / person</p><p className="field-hint">{trip.vehicle}</p>
            {trip.linked_trip_id && <p className="field-hint">{trip.is_return ? "Return direction" : "Return trip available"} / booked separately</p>}
            {trip.my_request_status && <p className="field-hint">Your request: {trip.my_request_status}</p>}
            <div className="community-post-footer"><span title="Available seats" aria-label={`${trip.available_seats} of ${trip.seats} seats available`}><Users size={15} />{trip.available_seats}/{trip.seats}</span><span title="Bags per person" aria-label={`${trip.bags_per_person} bags per person`}><Luggage size={15} />{trip.bags_per_person}</span><button className="community-icon-button" title="Show on map" aria-label={`Show ${trip.driver.name}'s carpool on map`} onClick={() => selectTrip(trip.id)}><LocateFixed size={17} /></button><Link className="text-link" href={`/rides/carpools/${trip.id}`}>View carpool<ArrowUpRight size={15} /></Link></div>
          </article>)}
        </div>
      </section>
    </div>
    <div className="carpool-pagination"><button className="community-icon-button" title="Previous carpools" aria-label="Previous carpools" disabled={resultsLoading || !!error || offset === 0} onClick={() => void refresh(offset - 20)}><ArrowLeft size={18} /></button><span>Page {offset / 20 + 1}</span><button className="community-icon-button" title="Next carpools" aria-label="Next carpools" disabled={resultsLoading || !!error || !page?.has_more} onClick={() => void refresh(offset + 20)}><ArrowRight size={18} /></button></div>
    <p className="ride-notice">Fixed cost-sharing contributions are per passenger, per direction. Payment is arranged outside the app. Drivers and phone numbers are not verified; transport is not guaranteed.</p>
  </section>;
  return <section aria-label={mine ? "My carpools" : "Find a carpool"}>
    <div className="ride-between"><h2>{mine ? "My carpools" : "Available carpools"}</h2><Link className="button button-primary" href="/rides/carpools/new">Offer a carpool</Link></div>
    <p className="muted">Trips you published and directions you requested. Outbound and return approvals are independent.</p>
    <button className="button button-secondary" disabled={busy} onClick={() => void refresh(offset)}>Refresh carpools</button>
    {error && <p className="form-error" role="alert">{error}</p>}
    {busy ? <p role="status">Loading carpools...</p> : page && (
      page.trips.length ? <div className="ride-grid">{page.trips.map(trip => <CarpoolCard key={trip.id} trip={trip} role={mine ? (trip.my_request_status ? "Passenger" : "Driver") : undefined} />)}</div> :
        <div className="state-card"><p>{mine ? "No carpools yet. Offer your planned trip or request seats on a community trip." : "No available carpools match. Try another date or area, or request a ride instead."}</p><Link className="text-link" href={mine ? "/rides/carpools" : "/rides/new"}>{mine ? "Find a carpool" : "Request a ride"}</Link></div>
    )}
    <div className="form-actions"><button className="button button-secondary" disabled={busy || offset === 0} onClick={() => void refresh(offset - 20)}>Previous carpools</button><button className="button button-secondary" disabled={busy || !page?.has_more} onClick={() => void refresh(offset + 20)}>Next carpools</button></div>
  </section>;
}
