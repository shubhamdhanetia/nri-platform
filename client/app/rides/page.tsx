"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowUpRight, CalendarDays, Car, ChevronDown, ChevronUp, Clock3, List, LocateFixed, Luggage, Map as MapIcon, MapPin, Maximize2, Minimize2, Plus, Search, Users } from "lucide-react";
import { useCallback, useEffect, useEffectEvent, useMemo, useRef, useState } from "react";
import RideLayout from "../../components/RideLayout";
import ExploreLocationSearch from "../../components/ExploreLocationSearch";
import { apiRequest, type PostSearchBounds } from "../../lib/api";
import { locationSearchBounds } from "../../lib/map";
import { rideDate, rideError, type RideRequest } from "../../lib/rides";

const RideMap = dynamic(() => import("../../components/CommunityMap"), {
  ssr: false,
  loading: () => <div className="explore-map-loading">Loading map...</div>,
});
const DEFAULT_CENTER: [number, number] = [20, 0];
const RESULT_LIMIT = 50;

export default function RidesPage() {
  const [searchCenter, setSearchCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [view, setView] = useState<"feed" | "map">("map");
  const [rides, setRides] = useState<RideRequest[]>([]);
  const [bounds, setBounds] = useState<PostSearchBounds | null>(null);
  const [mapBounds, setMapBounds] = useState<PostSearchBounds | null>(null);
  const [mapVersion, setMapVersion] = useState(0);
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [zoom, setZoom] = useState(2);
  const [date, setDate] = useState("");
  const [timeRangeOpen, setTimeRangeOpen] = useState(false);
  const [timeFrom, setTimeFrom] = useState("");
  const [timeTo, setTimeTo] = useState("");
  const [searched, setSearched] = useState(false);
  const [lastSearch, setLastSearch] = useState("");
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [locationError, setLocationError] = useState("");
  const [locating, setLocating] = useState(false);
  const [autoSearchPending, setAutoSearchPending] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [resultsOpen, setResultsOpen] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectionVersion, setSelectionVersion] = useState(0);
  const locationVersion = useRef(0);
  const locationStarted = useRef(false);
  const mounted = useRef(false);
  const searchController = useRef<AbortController | null>(null);
  const mapViewport = useRef<{ center: [number, number]; zoom: number } | null>(null);

  const onBoundsChange = useCallback((next: PostSearchBounds) => setMapBounds(next), []);
  const onCenterChange = useCallback((next: [number, number]) => setSearchCenter(next), []);
  const onViewportChange = useCallback((center: [number, number], zoom: number) => {
    mapViewport.current = { center, zoom };
  }, []);
  const onLocationSelected = useCallback((next: [number, number]) => {
    locationVersion.current += 1;
    mapViewport.current = null;
    setMapBounds(null); setMapVersion(version => version + 1);
    setCenter(next); setSearchCenter(next); setZoom(11); setLocationError("");
    setBounds(locationSearchBounds(next)); setLocating(false); setSelectedId(null);
    setAutoSearchPending(true);
  }, []);
  const selectRide = useCallback((id: number) => {
    setView("map"); setResultsOpen(true);
    setSelectedId(id); setSelectionVersion(version => version + 1);
  }, []);

  function changeView(next: "feed" | "map") {
    if (mapViewport.current) {
      setCenter(mapViewport.current.center);
      setZoom(mapViewport.current.zoom);
    }
    setView(next); setResultsOpen(true);
    if (next === "feed") setFullscreen(false);
  }

  function toggleFullscreen() {
    if (!fullscreen) changeView("map");
    setFullscreen(!fullscreen);
  }

  const locate = useCallback(() => {
    const version = ++locationVersion.current;
    if (!navigator.geolocation) { setLocationError("Location access is unavailable. Search for a city or move the map."); return; }
    setLocating(true); setLocationError("");
    navigator.geolocation.getCurrentPosition(position => {
      if (!mounted.current || version !== locationVersion.current) return;
      const next: [number, number] = [position.coords.latitude, position.coords.longitude];
      onLocationSelected(next);
    }, () => {
      if (!mounted.current || version !== locationVersion.current) return;
      setLocationError("Unable to get your location. Search for a city or move the map instead.");
      setLocating(false);
    }, { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 });
  }, [onLocationSelected]);

  useEffect(() => {
    mounted.current = true;
    if (!locationStarted.current) { locationStarted.current = true; locate(); }
    return () => { mounted.current = false; searchController.current?.abort(); };
  }, [locate]);
  const searchAutomatically = useEffectEvent((searchBounds: PostSearchBounds) => {
    void searchArea(searchBounds);
  });
  useEffect(() => {
    if (!autoSearchPending || locating) return;
    const searchBounds = view === "map" ? mapBounds : bounds;
    if (!searchBounds) return;
    const timer = window.setTimeout(() => searchAutomatically(searchBounds), 150);
    return () => window.clearTimeout(timer);
  }, [autoSearchPending, locating, view, mapBounds, bounds]);
  useEffect(() => {
    if (!fullscreen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function escape(event: KeyboardEvent) { if (event.key === "Escape") setFullscreen(false); }
    document.addEventListener("keydown", escape);
    return () => { document.body.style.overflow = previous; document.removeEventListener("keydown", escape); };
  }, [fullscreen]);

  const signature = JSON.stringify({ bounds, date, timeFrom: timeRangeOpen ? timeFrom : "", timeTo: timeRangeOpen ? timeTo : "" });
  const changed = searched && (lastSearch !== signature || (
    view === "map" && mapBounds !== null && JSON.stringify(mapBounds) !== JSON.stringify(bounds)
  ));
  const points = useMemo(() => rides.map(ride => ({
    id: ride.id, latitude: ride.pickup.latitude, longitude: ride.pickup.longitude,
    title: `${ride.rider.name}: ${ride.pickup.location}`,
    description: `To ${ride.dropoff.location} / ${rideDate(ride.pickup_start, ride.timezone)} (${ride.timezone})`,
    href: `/rides/${ride.id}`, linkLabel: "View ride details",
  })), [rides]);

  async function searchArea(searchBounds = bounds, filters = { date, timeRangeOpen, timeFrom, timeTo }) {
    const { date: departureDate, timeRangeOpen: hasTimeRange, timeFrom: from, timeTo: to } = filters;
    setAutoSearchPending(false);
    if (!searchBounds) { setError("Select a pickup area or use your location before searching."); return; }
    if (hasTimeRange && (!departureDate || !from || !to || to <= from)) {
      setError("Select a departure date and a time range ending after it starts on the same day."); return;
    }
    searchController.current?.abort();
    const controller = new AbortController();
    searchController.current = controller;
    setBounds(searchBounds); setBusy(true); setError(""); setResultsOpen(true);
    const searchSignature = JSON.stringify({ bounds: searchBounds, date: departureDate, timeFrom: hasTimeRange ? from : "", timeTo: hasTimeRange ? to : "" });
    try {
      const result = await apiRequest<{ rides: RideRequest[]; has_more: boolean }>("/rides/requests/search", {
        method: "POST", signal: controller.signal,
        body: JSON.stringify({
          bounds: searchBounds, limit: RESULT_LIMIT,
          ...(departureDate ? { departure_date: departureDate } : {}),
          ...(hasTimeRange ? { pickup_time_from: from, pickup_time_to: to } : {}),
        }),
      });
      if (controller.signal.aborted) return;
      setRides(result.rides); setMore(result.has_more); setSearched(true); setLastSearch(searchSignature); setSelectedId(null);
    } catch (err) { if (!controller.signal.aborted) setError(rideError(err)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }

  const resultsLoading = busy || locating || autoSearchPending;
  const filterBounds = view === "map" ? mapBounds : bounds;

  function resetFilters() {
    setDate(""); setTimeRangeOpen(false); setTimeFrom(""); setTimeTo("");
    void searchArea(filterBounds, { date: "", timeRangeOpen: false, timeFrom: "", timeTo: "" });
  }

  return <RideLayout><div className={`community-page rides-browse rides-map-browser${fullscreen ? " community-expanded" : ""}`}>
    <header className="community-heading">
      <div><p className="eyebrow">GO TOGETHER. YOUR COMMUNITY.</p><h1>Ride requests</h1></div>
      <div className="community-heading-actions">
        <button className="button button-secondary" aria-pressed={fullscreen} onClick={toggleFullscreen}>
          {fullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}{fullscreen ? "Exit full screen" : "Full screen map"}
        </button>
        <Link className="button button-primary" href="/rides/new"><Plus size={18} />Request a ride</Link>
      </div>
    </header>
    <section className="rides-discovery" aria-label="Search ride requests">
      <div className="community-location"><MapPin size={18} />
        <ExploreLocationSearch label="Pickup area" center={searchCenter} onLocationSelected={onLocationSelected} />
        <button className="community-icon-button" title="Center on my location" aria-label="Center on my location" disabled={locating} onClick={locate}>
          {locating ? <span className="spinner" /> : <LocateFixed size={18} />}
        </button>
      </div>
      <form className="rides-filter-form" aria-label="Ride date and time filters" onSubmit={event => {
        event.preventDefault();
        if (!resultsLoading) void searchArea(filterBounds);
      }}>
      <label className="rides-date-field"><CalendarDays size={18} /><span>Departure date<input type="date" value={date} onChange={event => {
        setDate(event.target.value); if (!event.target.value) { setTimeRangeOpen(false); setTimeFrom(""); setTimeTo(""); }
      }} /></span></label>
      <label className="rides-time-toggle"><input type="checkbox" disabled={!date} checked={timeRangeOpen} onChange={event => setTimeRangeOpen(event.target.checked)} />Time range</label>
      {timeRangeOpen && <div className="rides-time-fields">
        <label className="rides-date-field"><span>From<input type="time" value={timeFrom} onChange={event => setTimeFrom(event.target.value)} /></span></label>
        <label className="rides-date-field"><span>To<input type="time" value={timeTo} onChange={event => setTimeTo(event.target.value)} /></span></label>
      </div>}
      <div className="rides-filter-actions">
        <button type="submit" className="button button-primary" disabled={!filterBounds || resultsLoading}>Apply filters</button>
        <button type="button" className="button button-secondary" disabled={!filterBounds || resultsLoading} onClick={resetFilters}>Reset filters</button>
      </div>
      </form>
    </section>
    {locationError && <p className="community-error" role="alert">{locationError}</p>}
    <div className="community-controls rides-map-status">
      <span className="community-scope"><MapPin size={15} />{changed ? "Area or filters changed. Apply filters or search this area to update." : bounds ? "Selected pickup area" : "Choose a pickup area"}</span>
      <div className="community-view-toggle" role="group" aria-label="Ride requests view">
        <button type="button" aria-pressed={view === "feed"} onClick={() => changeView("feed")}><List size={17} />Feed</button>
        <button type="button" aria-pressed={view === "map"} onClick={() => changeView("map")}><MapIcon size={17} />Map</button>
      </div>
    </div>
    <div className="rides-search-summary">
      <p className="field-hint">{date || "All upcoming dates"} / local ride times / earliest pickup first</p>
      {view === "feed" && <button className="button button-primary" disabled={!bounds || busy || locating} onClick={() => void searchArea()}><Search size={16} />{busy ? "Searching..." : "Search requests"}</button>}
    </div>
    <section className={`community-content community-${view} rides-${view}`} aria-label="Explore rides by pickup location">
      {view === "map" && <div className="community-map-panel">
        <RideMap key={mapVersion} posts={resultsLoading || error ? [] : points} center={center} initialZoom={zoom} fullscreen={fullscreen} onBoundsChange={onBoundsChange} onCenterChange={onCenterChange} onViewportChange={onViewportChange} onSelectPost={selectRide} selectedPostId={selectedId} selectionVersion={selectionVersion} />
        <div className="community-map-actions">
          <button className="button button-primary" disabled={!mapBounds || busy || locating} onClick={() => void searchArea(mapBounds)}><Search size={16} />{busy ? "Searching..." : "Search this area"}</button>
          <button className="community-icon-button" title="Center map on my location" aria-label="Center map on my location" disabled={locating} onClick={locate}>{locating ? <span className="spinner" /> : <LocateFixed size={19} />}</button>
          <button className="community-icon-button" title={fullscreen ? "Exit full screen" : "Full screen map"} aria-label={fullscreen ? "Exit full screen" : "Full screen map"} onClick={toggleFullscreen}>{fullscreen ? <Minimize2 size={19} /> : <Maximize2 size={19} />}</button>
        </div>
      </div>}
      <section className={`community-results${!resultsOpen && view === "map" ? " community-results-collapsed" : ""}`} aria-label="Rides in this area" aria-busy={resultsLoading}>
        <div className="community-results-heading"><div><h2>Upcoming rides</h2><span aria-live="polite">{resultsLoading ? "Searching..." : error ? "Search unavailable" : `${rides.length}${more ? "+" : ""} ${rides.length === 1 && !more ? "request" : "requests"}`}</span></div>
          {view === "map" && <button className="community-icon-button community-sheet-toggle" aria-expanded={resultsOpen} aria-label={resultsOpen ? "Collapse ride results" : "Expand ride results"} onClick={() => setResultsOpen(!resultsOpen)}>{resultsOpen ? <ChevronDown size={20} /> : <ChevronUp size={20} />}</button>}
        </div>
        <div className="community-result-body">
          {resultsLoading ? <div className="community-state" role="status"><span className="spinner" /><p>{locating ? "Finding your location..." : "Searching this area..."}</p></div> : error ? <div className="community-state" role="alert"><h3>Could not load ride requests</h3><p>{error}</p><button className="button button-secondary" onClick={() => void searchArea()}>Try again</button></div> : !searched ? <div className="community-state"><MapPin size={30} /><h3>Where are you headed?</h3><p>Select a pickup area or use your location to automatically see nearby ride requests. You can also move the map and select Search this area.</p></div> : rides.length === 0 ? <div className="community-state"><Car size={30} /><h3>No upcoming rides here</h3><Link className="button button-secondary" href="/rides/new">Request a ride</Link></div> : <>
            {rides.map(ride => <article className={`community-post rides-result${selectedId === ride.id ? " is-selected" : ""}`} key={ride.id}>
              <div className="community-post-top"><span className="community-category-icon"><Car size={21} /></span><div className="community-post-context"><span>{ride.rider.name}</span><time dateTime={ride.pickup_start}>{rideDate(ride.pickup_start, ride.timezone)}</time></div><span className="post-type-pill">Open</span></div>
              <h3><Link href={`/rides/${ride.id}`}>{ride.pickup.city} to {ride.dropoff.city}<ArrowUpRight size={18} /></Link></h3>
              <dl className="rides-result-route"><div><dt>Pickup</dt><dd>{ride.pickup.location}</dd></div><div><dt>Drop-off</dt><dd>{ride.dropoff.location}</dd></div></dl>
              <p className="rides-result-window"><Clock3 size={14} /><span>{rideDate(ride.pickup_start, ride.timezone)} - {rideDate(ride.pickup_end, ride.timezone)}<small>{ride.timezone}</small></span></p>
              <div className="community-post-footer"><span title="Passengers" aria-label={`${ride.passengers} passengers`}><Users size={15} />{ride.passengers}</span><span title="Bags" aria-label={`${ride.bags} bags`}><Luggage size={15} />{ride.bags}</span><button className="community-icon-button" title="Show on map" aria-label={`Show ${ride.rider.name}'s request on map`} onClick={() => selectRide(ride.id)}><LocateFixed size={17} /></button><Link className="text-link" href={`/rides/${ride.id}`}>View ride<ArrowUpRight size={15} /></Link></div>
            </article>)}
            {more && <p className="field-hint">Showing the first {RESULT_LIMIT} requests. {view === "map" ? "Zoom in and search this area" : "Use Map to narrow the area"} or add a date/time filter to find more specific rides.</p>}
          </>}
        </div>
      </section>
    </section>
    <p className="ride-notice">Community members are not vetted by this platform. Cost-sharing is agreed between members; no payments are collected here. No notifications are sent: check My rides and refresh for updates.</p>
  </div></RideLayout>;
}
