"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import RideLayout from "../../components/RideLayout";
import ExploreLocationSearch from "../../components/ExploreLocationSearch";
import { apiRequest, type PostSearchBounds } from "../../lib/api";
import { rideDate, rideError, type DriverProfile, type RideRequest } from "../../lib/rides";

const RideMap = dynamic(() => import("../../components/CommunityMap"), {
  ssr: false,
  loading: () => <div className="explore-map-loading">Loading map...</div>,
});
const DEFAULT_CENTER: [number, number] = [20, 0];
const RESULT_LIMIT = 50;

export default function RidesPage() {
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [ready, setReady] = useState(false);
  const [profileError, setProfileError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<DriverProfile | null>("/rides/driver-profile", { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) { setProfile(result); setReady(true); } })
      .catch((err: unknown) => { if (!controller.signal.aborted) setProfileError(rideError(err)); });
    return () => controller.abort();
  }, []);

  return <RideLayout>
    {!ready ? profileError ? <div className="state-card error-state" role="alert"><p>{profileError}</p><button className="button button-secondary" onClick={() => window.location.reload()}>Retry loading rides</button></div> : <p role="status">Loading rides...</p> : !profile ? <>
      <section className="page-heading"><div><p className="eyebrow">Go together</p><h1>Browse ride requests</h1><p className="muted">Find members who need a ride. Search pickup locations and send an offer.</p></div><Link className="button button-primary" href="/rides/new">Request a ride</Link></section>
      <div className="ride-card"><h2>Offer a little help.</h2><p className="muted">Complete your driver profile to browse the map and exact pickup/drop-off addresses. You can request a ride without becoming a driver.</p><Link className="button button-primary" href="/rides/driver">Set up driver profile</Link></div>
    </> : <RideMapSearch />}
    <p className="ride-notice">Community members are not vetted by this platform. Cost-sharing is agreed between members; no payments are collected here. No notifications are sent: check My rides and refresh for updates.</p>
  </RideLayout>;
}

function RideMapSearch() {
  const [rides, setRides] = useState<RideRequest[]>([]);
  const [bounds, setBounds] = useState<PostSearchBounds | null>(null);
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [searchCenter, setSearchCenter] = useState<[number, number]>(DEFAULT_CENTER);
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
  const [fullscreen, setFullscreen] = useState(false);
  const [resultsOpen, setResultsOpen] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectionVersion, setSelectionVersion] = useState(0);
  const locationVersion = useRef(0);
  const locationStarted = useRef(false);
  const mounted = useRef(false);
  const searchController = useRef<AbortController | null>(null);

  const onBoundsChange = useCallback((next: PostSearchBounds) => setBounds(next), []);
  const onCenterChange = useCallback((next: [number, number]) => setSearchCenter(next), []);
  const onLocationSelected = useCallback((next: [number, number]) => {
    locationVersion.current += 1;
    setCenter(next); setSearchCenter(next); setZoom(11); setLocationError("");
    setLocating(false); setSelectedId(null);
  }, []);
  const selectRide = useCallback((id: number) => {
    setSelectedId(id); setSelectionVersion(version => version + 1);
  }, []);

  const locate = useCallback(() => {
    const version = ++locationVersion.current;
    if (!navigator.geolocation) { setLocationError("Location access is unavailable. Search for a city or move the map."); return; }
    setLocating(true); setLocationError("");
    navigator.geolocation.getCurrentPosition(position => {
      if (!mounted.current || version !== locationVersion.current) return;
      const next: [number, number] = [position.coords.latitude, position.coords.longitude];
      setCenter(next); setSearchCenter(next); setZoom(11); setLocating(false);
    }, () => {
      if (!mounted.current || version !== locationVersion.current) return;
      setLocationError("Unable to get your location. Search for a city or move the map instead.");
      setLocating(false);
    }, { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 });
  }, []);

  useEffect(() => {
    mounted.current = true;
    if (!locationStarted.current) { locationStarted.current = true; locate(); }
    return () => { mounted.current = false; searchController.current?.abort(); };
  }, [locate]);
  useEffect(() => {
    if (!fullscreen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function escape(event: KeyboardEvent) { if (event.key === "Escape") setFullscreen(false); }
    document.addEventListener("keydown", escape);
    return () => { document.body.style.overflow = previous; document.removeEventListener("keydown", escape); };
  }, [fullscreen]);

  const signature = JSON.stringify({ bounds, date, timeFrom: timeRangeOpen ? timeFrom : "", timeTo: timeRangeOpen ? timeTo : "" });
  const changed = searched && lastSearch !== signature;
  const points = useMemo(() => rides.map(ride => ({
    id: ride.id, latitude: ride.pickup.latitude, longitude: ride.pickup.longitude,
    title: `${ride.rider.name}: ${ride.pickup.location}`,
    description: `To ${ride.dropoff.location} / ${rideDate(ride.pickup_start, ride.timezone)} (${ride.timezone})`,
    href: `/rides/${ride.id}`, linkLabel: "View ride details",
  })), [rides]);

  async function searchArea() {
    if (!bounds) { setError("Wait for the map to load before searching."); return; }
    if (timeRangeOpen && (!date || !timeFrom || !timeTo || timeTo <= timeFrom)) {
      setError("Select a departure date and a time range ending after it starts on the same day."); return;
    }
    searchController.current?.abort();
    const controller = new AbortController();
    searchController.current = controller;
    setBusy(true); setError(""); setResultsOpen(true);
    try {
      const result = await apiRequest<{ rides: RideRequest[]; has_more: boolean }>("/rides/requests/search", {
        method: "POST", signal: controller.signal,
        body: JSON.stringify({
          bounds, limit: RESULT_LIMIT,
          ...(date ? { departure_date: date } : {}),
          ...(timeRangeOpen ? { pickup_time_from: timeFrom, pickup_time_to: timeTo } : {}),
        }),
      });
      if (controller.signal.aborted) return;
      setRides(result.rides); setMore(result.has_more); setSearched(true); setLastSearch(signature); setSelectedId(null);
    } catch (err) { if (!controller.signal.aborted) setError(rideError(err)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }

  return <div className={fullscreen ? "explore-fullscreen active ride-map-search" : "explore-fullscreen ride-map-search"}>
    <section className="page-heading explore-heading"><div><p className="eyebrow">Go together</p><h1>Browse ride requests</h1><p className="muted">Find members who need a ride. Search pickup locations and send an offer.</p></div><div className="explore-heading-actions"><button className="button button-secondary" aria-pressed={fullscreen} onClick={() => setFullscreen(true)}>Full screen map</button><Link className="button button-primary" href="/rides/new">Request a ride</Link></div></section>
    <section className="explore-layout" aria-label="Explore rides by pickup location">
      <div className="explore-map-panel">
        <div className="explore-map-toolbar">
          <ExploreLocationSearch label="Find pickup area" center={searchCenter} onLocationSelected={onLocationSelected} />
          <label className="explore-category-filter"><span>Departure date</span><input type="date" value={date} onChange={e => { setDate(e.target.value); if (!e.target.value) { setTimeRangeOpen(false); setTimeFrom(""); setTimeTo(""); } }} /></label>
          <button className="text-link ride-map-time-toggle" disabled={!date} aria-expanded={timeRangeOpen} aria-controls="ride-pickup-time-range" onClick={() => setTimeRangeOpen(open => !open)}>{timeRangeOpen ? "Remove time range" : "Add time range"}</button>
          {timeRangeOpen && <div className="ride-map-time-range" id="ride-pickup-time-range">
            <label className="explore-category-filter"><span>From</span><input type="time" value={timeFrom} onChange={e => setTimeFrom(e.target.value)} /></label>
            <label className="explore-category-filter"><span>To</span><input type="time" value={timeTo} onChange={e => setTimeTo(e.target.value)} /></label>
          </div>}
          <p className="ride-map-filter-help">Dates and times use each ride&apos;s timezone, shown in the results. {date ? timeRangeOpen ? "Matches overlapping pickup windows. Select times within the same day." : "Whole day selected." : "All future dates. Select a date to add a time range."}</p>
          <button className="button button-secondary" disabled={locating} onClick={() => locate()}>{locating ? "Finding you..." : "Center on my location"}</button>
          <button className="button button-primary" disabled={!bounds || busy} onClick={() => void searchArea()}>{busy ? "Searching..." : "Search this area"}</button>
          {fullscreen && <button className="button button-secondary explore-exit-fullscreen" onClick={() => setFullscreen(false)}>Exit full screen</button>}
          {locationError && <p className="ride-map-filter-help location-error" role="alert">{locationError}</p>}
        </div>
        <RideMap posts={points} center={center} initialZoom={zoom} fullscreen={fullscreen} onBoundsChange={onBoundsChange} onCenterChange={onCenterChange} onSelectPost={selectRide} selectedPostId={selectedId} selectionVersion={selectionVersion} />
        {changed && <p className="explore-map-hint" role="status">Map or filters changed. Search this area to refresh results.</p>}
      </div>
      <aside className={["explore-results", fullscreen ? "explore-results-overlay" : "", fullscreen && !resultsOpen ? "collapsed" : ""].filter(Boolean).join(" ")} aria-label="Rides in this area">
        <div className="explore-results-heading"><div><h2>Rides in this area</h2><p className="muted">{searched ? `${rides.length}${more ? "+" : ""} results / earliest pickup first` : "Search an area to see matching requests."}</p></div>{fullscreen && <button className="explore-results-toggle" aria-expanded={resultsOpen} aria-label={resultsOpen ? "Collapse ride results" : "Expand ride results"} onClick={() => setResultsOpen(open => !open)}>{resultsOpen ? "Hide" : "Results"}<span aria-hidden="true">{resultsOpen ? "\u2304" : "\u2303"}</span></button>}</div>
        {(!fullscreen || resultsOpen) && <>
          {error && <div className="explore-error" role="alert"><p>{error}</p><button className="button button-secondary" disabled={busy} onClick={() => void searchArea()}>Try again</button></div>}
          {busy ? <div className="state-card" role="status"><span className="spinner" /> Searching this area...</div> : !searched ? <div className="explore-empty"><span aria-hidden="true">&#8982;</span><p>Pan or zoom to a pickup area, then select <strong>Search this area</strong>.</p></div> : rides.length === 0 ? <div className="explore-empty"><span aria-hidden="true">&#8982;</span><p>No matching rides. Try another area, date, or time range.</p></div> : <>
            {more && <p className="explore-map-hint">Showing the first {RESULT_LIMIT} rides. Zoom in or add filters to narrow your search.</p>}
            <div className="explore-post-list">{rides.map(ride => <article className={selectedId === ride.id ? "explore-post-card selected" : "explore-post-card"} key={ride.id}>
              <span className="ride-badge">OPEN REQUEST</span><h3>{ride.rider.name}</h3>
              <p className="explore-post-location"><strong>Pickup:</strong> {ride.pickup.location}</p><p className="explore-post-location"><strong>Drop-off:</strong> {ride.dropoff.location}</p>
              <p className="explore-post-description">{rideDate(ride.pickup_start, ride.timezone)} - {rideDate(ride.pickup_end, ride.timezone)} ({ride.timezone})</p>
              <p className="explore-post-description">{ride.passengers} passenger(s) / {ride.bags} bag(s) / offers in {ride.currency}</p>
              <div className="explore-post-actions"><button className="text-link" onClick={() => selectRide(ride.id)}>Show on map</button><Link className="text-link" href={`/rides/${ride.id}`}>View ride</Link></div>
            </article>)}</div>
          </>}
        </>}
      </aside>
    </section>
  </div>;
}
