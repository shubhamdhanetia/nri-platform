"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type FormEvent } from "react";
import { List, LocateFixed, Map as MapIcon, MapPin, Maximize2, Minimize2, Plus, Search, SlidersHorizontal } from "lucide-react";
import { apiRequest, type PostSearchBounds } from "../lib/api";
import { ARRANGEMENTS, BATHROOMS, FURNISHINGS, KITCHENS, PRICE_PERIODS, ROOM_TYPES, STAY_TYPES, housingError, type HousingCollection, type HousingItem } from "../lib/housing";
import { locationSearchBounds } from "../lib/map";
import ExploreLocationSearch from "./ExploreLocationSearch";
import HousingCard from "./HousingCard";

const HousingMap = dynamic(() => import("./HousingMap"), { ssr: false, loading: () => <div className="explore-map-loading">Loading housing map...</div> });
type SearchParams = Record<string, string | number | boolean | PostSearchBounds>;
const VIEW_EVENT = "housing-view-change";
function subscribeView(listener: () => void) {
  window.addEventListener(VIEW_EVENT, listener);
  return () => window.removeEventListener(VIEW_EVENT, listener);
}
function readView(): "map" | "list" { return sessionStorage.getItem("housing-view") === "list" ? "list" : "map"; }
function serverView(): "map" | "list" { return "map"; }
export function HousingSelect({ name, label, options, defaultValue = "", anyLabel = "Any" }: {
  name: string; label: string; options: Record<string, string>; defaultValue?: string; anyLabel?: string;
}) {
  return <label className="form-field"><span>{label}</span><select name={name} defaultValue={defaultValue}>
    {anyLabel && <option value="">{anyLabel}</option>}
    {Object.entries(options).map(([value, text]) => <option key={value} value={value}>{text}</option>)}
  </select></label>;
}

export default function HousingBrowse({ people = false }: { people?: boolean }) {
  const [params, setParams] = useState<SearchParams>({ view: people ? "PEOPLE" : "PLACES", limit: 20, offset: 0 });
  const [result, setResult] = useState<HousingCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [revision, setRevision] = useState(0);
  const [ready, setReady] = useState(false);
  const [autoSearchPending, setAutoSearchPending] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const view = useSyncExternalStore(subscribeView, readView, serverView);
  const [mapCenter, setMapCenter] = useState<[number, number]>([20, 0]);
  const [searchCenter, setSearchCenter] = useState<[number, number]>([20, 0]);
  const [zoom, setZoom] = useState(2);
  const [mapVersion, setMapVersion] = useState(0);
  const [mapBounds, setMapBounds] = useState<PostSearchBounds | null>(null);
  const [areaLabel, setAreaLabel] = useState("");
  const [locationVersion, setLocationVersion] = useState(0);
  const [locationError, setLocationError] = useState("");
  const [locating, setLocating] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectionVersion, setSelectionVersion] = useState(0);
  const viewport = useRef<{ center: [number, number]; zoom: number } | null>(null);
  const locationRequest = useRef(0);
  const locationStarted = useRef(false);
  const mounted = useRef(false);
  const fullscreenButton = useRef<HTMLButtonElement>(null);
  const browserPanel = useRef<HTMLElement>(null);
  const selectedCard = useRef<HTMLDivElement>(null);
  const appliedBounds = typeof params.bounds === "object" ? params.bounds : null;
  const onBoundsChange = useCallback((bounds: PostSearchBounds) => setMapBounds(bounds), []);
  const onCenterChange = useCallback((center: [number, number]) => setSearchCenter(center), []);
  const onViewportChange = useCallback((center: [number, number], zoom: number) => { viewport.current = { center, zoom }; }, []);
  const selectItem = useCallback((id: string) => { setSelectedId(id); setSelectionVersion(value => value + 1); }, []);
  useEffect(() => {
    if (view === "map" && selectedId) selectedCard.current?.scrollIntoView({ block: "nearest", behavior: "instant" });
  }, [selectedId, selectionVersion, view]);
  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    apiRequest<HousingCollection>("/housing/search", { method: "POST", body: JSON.stringify(params), signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) { setResult(data); setError(""); } })
      .catch((failure: unknown) => { if (!controller.signal.aborted) setError(housingError(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [params, revision, ready]);

  function search(next: SearchParams) {
    locationRequest.current += 1;
    setLocating(false); setAutoSearchPending(false); setReady(true);
    setError(""); setSelectedId(null); setLoading(true); setParams(next);
  }
  const chooseArea = useCallback((center: [number, number]) => {
    locationRequest.current += 1;
    setLocating(false); setLocationError(""); setMapBounds(null);
    setMapCenter(center); setSearchCenter(center); setZoom(11); setMapVersion(value => value + 1);
    viewport.current = null;
    setError(""); setSelectedId(null); setLoading(true); setReady(false);
    setAutoSearchPending(true);
    setParams(current => ({ ...current, offset: 0, bounds: locationSearchBounds(center) }));
  }, []);
  const locate = useCallback(() => {
    const version = ++locationRequest.current;
    setLocating(true); setLocationError(""); setAutoSearchPending(false);
    if (!navigator.geolocation) {
      setLocationError("Location access is unavailable. Search a city or area instead.");
      setLocating(false); setLoading(false); return;
    }
    navigator.geolocation.getCurrentPosition(position => {
      if (!mounted.current || locationRequest.current !== version) return;
      setLocationVersion(value => value + 1);
      setAreaLabel("Near my location");
      chooseArea([position.coords.latitude, position.coords.longitude]);
    }, () => {
      if (!mounted.current || locationRequest.current !== version) return;
      setLocating(false); setLoading(false);
      setLocationError("Unable to get your location. Search a city or area, or move the map and select Search this area.");
    }, { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 });
  }, [chooseArea]);
  useEffect(() => {
    mounted.current = true;
    if (!locationStarted.current) { locationStarted.current = true; locate(); }
    return () => { mounted.current = false; };
  }, [locate]);
  useEffect(() => {
    if (!autoSearchPending || locating) return;
    const bounds = view === "map" ? mapBounds : appliedBounds;
    if (!bounds) return;
    const timer = window.setTimeout(() => {
      setParams(current => ({ ...current, bounds, offset: 0 }));
      setAutoSearchPending(false); setReady(true);
    }, 150);
    return () => window.clearTimeout(timer);
  }, [autoSearchPending, locating, view, mapBounds, appliedBounds]);
  useEffect(() => {
    if (!fullscreen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    if (browserPanel.current) browserPanel.current.scrollTop = 0;
    fullscreenButton.current?.focus({ preventScroll: true });
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.defaultPrevented && !document.querySelector("dialog:modal")) setFullscreen(false);
    };
    document.addEventListener("keydown", escape);
    return () => { document.body.style.overflow = previous; document.removeEventListener("keydown", escape); };
  }, [fullscreen]);
  function changeView(next: "map" | "list") {
    if (next === "list") setFullscreen(false);
    if (viewport.current) { setMapCenter(viewport.current.center); setZoom(viewport.current.zoom); }
    else if (next === "map" && !appliedBounds) {
      const item = result?.items.find(item => item.id === selectedId) ?? result?.items.find(item => item.latitude !== null && item.longitude !== null);
      if (item?.latitude !== null && item?.latitude !== undefined && item.longitude !== null) {
        setMapCenter([item.latitude, item.longitude]); setZoom(12);
      }
    }
    sessionStorage.setItem("housing-view", next); window.dispatchEvent(new Event(VIEW_EVENT));
  }
  function searchViewport() {
    if (!mapBounds) return;
    setAreaLabel("Selected map area");
    search({ ...params, bounds: mapBounds, offset: 0 });
  }
  function showOnMap(item: HousingItem) {
    if (item.latitude === null || item.longitude === null) return;
    changeView("map");
    setMapCenter([item.latitude, item.longitude]); setZoom(13);
    setSelectedId(item.id); setSelectionVersion(value => value + 1);
  }
  function clearArea() {
    locationRequest.current += 1; setLocating(false); setLocationError(""); setAreaLabel("");
    setLocationVersion(value => value + 1);
    const next: SearchParams = { ...params, offset: 0 };
    delete next.bounds;
    search(next);
  }
  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const filters: SearchParams = { view: people ? "PEOPLE" : "PLACES", limit: 20, offset: 0 };
    if (view === "map" && mapBounds) filters.bounds = mapBounds;
    else if (appliedBounds) filters.bounds = appliedBounds;
    for (const [key, value] of data.entries()) {
      if (typeof value !== "string" || !value.trim()) continue;
      filters[key] = key === "min_amount" || key === "max_amount" || key === "min_bedrooms" || key === "min_bathrooms" ? Number(value)
        : key === "parking" || key === "laundry" ? value === "true" : value.trim();
    }
    if ((filters.min_amount !== undefined || filters.max_amount !== undefined) && (!filters.currency || !filters.price_period)) {
      setFormError("Choose a currency and price period when filtering by budget.");
      return;
    }
    setFormError("");
    if (view === "map" && mapBounds) setAreaLabel("Selected map area");
    search(filters);
  }
  function paginate(direction: number) {
    setLoading(true);
    setParams(current => ({ ...current, offset: Math.max(0, Number(current.offset) + direction * 20) }));
  }
  const pagination = <div className="housing-pagination"><button className="button button-secondary" disabled={loading || !Number(params.offset)} onClick={() => paginate(-1)}>Previous</button><span>Page {Math.floor(Number(params.offset) / 20) + 1}</span><button className="button button-secondary" disabled={loading || !result?.has_more} onClick={() => paginate(1)}>Next</button></div>;
  return <section ref={browserPanel} className={`housing-browser${fullscreen ? " community-expanded" : ""}`} aria-label={people ? "Find people" : "Find a place"}>
    <header className="page-heading housing-heading community-heading">
      <div><p className="eyebrow">A place to belong</p><h1>{people ? "Find people" : "Find a place"}</h1>
        <p className="muted">{people ? "Meet people looking for accommodation or wanting to find a home together." : "Browse available rooms, homes, sublets, lease takeovers, and temporary stays."}</p></div>
      <div className="housing-actions">
        <button ref={fullscreenButton} className="button button-secondary" type="button" aria-pressed={fullscreen} onClick={() => { if (view !== "map") changeView("map"); setFullscreen(value => !value); }}>{fullscreen ? <Minimize2 size={18} aria-hidden="true" /> : <Maximize2 size={18} aria-hidden="true" />}{fullscreen ? "Exit full screen" : "Full screen map"}</button>
        <Link className="button button-primary" href={`/housing/new?kind=${people ? "TOGETHER" : "LISTING"}`}><Plus size={17} aria-hidden="true" />Post housing</Link>
      </div>
    </header>
    <p className="housing-callout">{people ? <>Have a room to fill, or want someone to rent with? Browse housing needs below. <Link href="/housing/new?kind=TOGETHER">Post that you want to search together</Link>. For available rooms and homes, use <Link href="/housing">Find a place</Link>.</> : <>These posts offer accommodation. To find potential tenants or people to rent with, use <Link href="/housing/people">Find people</Link>.</>}</p>
    <div className="housing-area-search">
      <div className="community-location housing-location-input"><MapPin size={18} aria-hidden="true" />
        <ExploreLocationSearch key={locationVersion} center={searchCenter} label="Search location" onQueryChange={() => { locationRequest.current += 1; setLocating(false); if (locating || autoSearchPending) { setAutoSearchPending(false); setLoading(false); } }} onLocationSelected={chooseArea} onSelectionChange={selection => { if (selection) setAreaLabel(selection.location); }} />
        <button className="community-icon-button" type="button" title="Use my current location" aria-label="Use my current location" onClick={locate} disabled={locating}>{locating ? <span className="spinner" /> : <LocateFixed size={19} aria-hidden="true" />}</button>
      </div>
      {locationError && <p className="form-error" role="alert">{locationError}</p>}
      <p className="field-hint housing-area-caption" role="status">{locating ? "Finding your location..." : appliedBounds ? `Searching: ${areaLabel || "selected area"}` : ready ? "Searching all areas. Choose a location to narrow your results." : "Choose a location or search the map to find nearby housing."}{appliedBounds && <button className="text-link" type="button" onClick={clearArea}>Search all areas</button>}</p>
    </div>
    <form className="housing-search" aria-label="Housing filters" onSubmit={apply}>
      <div className="housing-filter-grid">
        {people && <HousingSelect name="kind" label="Looking for" options={{ REQUEST: "People needing a place", TOGETHER: "People searching together" }} anyLabel="All housing needs" />}
        <label className="form-field"><span>Keywords</span><input name="query" maxLength={200} placeholder="Title, address, description" /></label>
        <HousingSelect name="room_type" label="Space" options={ROOM_TYPES} />
        <HousingSelect name="min_bedrooms" label="Minimum bedrooms" options={{ 1: "1+", 2: "2+", 3: "3+", 4: "4+" }} />
        <HousingSelect name="min_bathrooms" label="Minimum bathrooms" options={{ 0.5: "0.5+", 1: "1+", 1.5: "1.5+", 2: "2+", 2.5: "2.5+", 3: "3+" }} />
        <label className="form-field"><span>Move-in date</span><input name="available_from" type="date" /></label>
      </div>
      <details className="housing-filters-more">
        <summary><SlidersHorizontal size={15} aria-hidden="true" /> Budget, stay & household filters</summary>
        <div className="housing-filter-grid">
          <label className="form-field"><span>Minimum rent / budget</span><input name="min_amount" type="number" min="0" step="0.01" /></label>
          <label className="form-field"><span>Maximum rent / budget</span><input name="max_amount" type="number" min="0" step="0.01" /></label>
          <HousingSelect name="currency" label="Currency" options={{ USD: "USD", CAD: "CAD", GBP: "GBP", INR: "INR", AUD: "AUD", EUR: "EUR", SGD: "SGD", AED: "AED" }} />
          <HousingSelect name="price_period" label="Price period" options={PRICE_PERIODS} />
          <HousingSelect name="arrangement" label="Arrangement" options={ARRANGEMENTS} />
          <HousingSelect name="stay_type" label="Stay length" options={STAY_TYPES} />
          <label className="form-field"><span>Stay through</span><input name="available_until" type="date" /></label>
          <HousingSelect name="furnishing" label="Furnishing" options={FURNISHINGS} />
          <HousingSelect name="bathroom" label="Bathroom" options={BATHROOMS} />
          <HousingSelect name="kitchen" label="Shared kitchen food policy" options={KITCHENS} />
          <HousingSelect name="parking" label="Parking" options={{ true: "Available", false: "Not available" }} />
          <HousingSelect name="laundry" label="Laundry" options={{ true: "Available", false: "Not available" }} />
        </div>
        <p className="field-hint">Prices are compared only within your selected currency and period. Dates find availability covering your requested stay. Household information is user-provided.</p>
      </details>
      {formError && <p className="form-error" role="alert">{formError}</p>}
      <div className="housing-actions"><button className="button button-primary" disabled={loading}><Search size={16} aria-hidden="true" /> Search housing</button>
        <button className="button button-secondary" type="reset" onClick={() => { setFormError(""); search({ view: people ? "PEOPLE" : "PLACES", limit: 20, offset: 0, ...(appliedBounds ? { bounds: appliedBounds } : {}) }); }}>Reset filters</button></div>
    </form>
    <div className="housing-results-heading"><h2>{people ? "People looking for housing" : "Available places"}</h2>
      <div className="housing-view-toggle" role="group" aria-label="Housing view">
        <button type="button" aria-pressed={view === "list"} onClick={() => changeView("list")}><List size={16} aria-hidden="true" />List</button>
        <button type="button" aria-pressed={view === "map"} onClick={() => changeView("map")}><MapIcon size={16} aria-hidden="true" />Map</button>
      </div>
    </div>
    <p className="field-hint">{people ? "Markers show preferred search areas, not available properties. " : ""}Selected addresses and exact map points are visible while public. Results are newest first.</p>
    {error && <div className="state-card error-state" role="alert"><p>{error}</p><button className="button button-secondary" type="button" onClick={() => { setLoading(true); setRevision(value => value + 1); }}>Retry search</button></div>}
    {loading && <p className="housing-loading" role="status">Finding housing...</p>}
    {view === "map" && <div className="housing-map-layout">
      <div className="housing-map-panel">
        <HousingMap key={mapVersion} fullscreen={fullscreen} items={error || loading ? [] : result?.items ?? []} center={mapCenter} initialZoom={zoom} selectedPostId={selectedId} selectionVersion={selectionVersion}
          onSelectPost={selectItem} onBoundsChange={onBoundsChange} onCenterChange={onCenterChange} onViewportChange={onViewportChange} />
        <div className="housing-map-toolbar community-map-actions"><button className="button button-primary" disabled={loading || !mapBounds} onClick={searchViewport}><Search size={16} aria-hidden="true" />Search this area</button>
          <button className="community-icon-button" type="button" title="Center map on my location" aria-label="Center map on my location" disabled={locating} onClick={locate}>{locating ? <span className="spinner" /> : <LocateFixed size={19} aria-hidden="true" />}</button>
          <button className="community-icon-button" type="button" title={fullscreen ? "Exit full screen" : "Full screen map"} aria-label={fullscreen ? "Exit full screen" : "Full screen map"} aria-pressed={fullscreen} onClick={() => setFullscreen(value => !value)}>{fullscreen ? <Minimize2 size={19} aria-hidden="true" /> : <Maximize2 size={19} aria-hidden="true" />}</button>
          {selectedId && <button className="button button-secondary" onClick={() => setSelectedId(null)}>Clear selection</button>}
        </div>
      </div>
      <section className="housing-map-results" aria-label="Housing map results" aria-busy={loading}>
        {fullscreen && <div className="community-results-heading"><div><h2>{people ? "People looking for housing" : "Available places"}</h2><span aria-live="polite">{loading ? "Searching..." : error ? "Search unavailable" : `${result?.items.length ?? 0}${result?.has_more ? "+" : ""} matches`}</span></div></div>}
        {!error && result?.items.map(item => <div key={item.id} ref={selectedId === item.id ? selectedCard : undefined} className={selectedId === item.id ? "housing-map-result selected" : "housing-map-result"}>
          <HousingCard item={item}><div className="housing-actions">
            {item.latitude !== null && item.longitude !== null ? <button className="button button-secondary" type="button" aria-pressed={selectedId === item.id} onClick={() => selectItem(item.id)}>Show on map</button> : <span className="field-hint">No map location added yet</span>}
            <Link className="text-link" href={`/housing/${item.id}`}>View details →</Link>
          </div></HousingCard>
        </div>)}
        {!loading && !error && !result?.items.length && <div className="state-card"><p>{ready ? "No matches in this search. Try another area or fewer filters." : "Choose a location or search the map to find nearby housing."}</p></div>}
        {fullscreen && result?.has_more && <p className="field-hint">More matches are available. Use Next to see the next page of cards and markers.</p>}
        {fullscreen && result && pagination}
      </section>
    </div>}
    {!loading && !error && result && <>
        {result.has_more && <p className="housing-callout">More matches are available. This page shows up to 20 results{view === "map" ? " and their map markers" : ""}. Use Next or narrow your area and filters.</p>}
        {view === "list" && (result.items.length ? <div className="housing-grid">{result.items.map(item => <HousingCard key={item.id} item={item}>
          <div className="housing-actions">{item.latitude !== null && item.longitude !== null && <button className="button button-secondary" onClick={() => showOnMap(item)}>Show on map</button>}<Link className="text-link" href={`/housing/${item.id}`}>View details →</Link></div>
        </HousingCard>)}</div>
          : <div className="empty-state"><h2>No matches yet</h2><p className="muted">Try a wider area or fewer filters, or post what you&apos;re looking for.</p><Link className="button button-secondary" href={`/housing/new?kind=${people ? "TOGETHER" : "REQUEST"}`}>{people ? "Find a place together" : "Post a housing request"}</Link></div>
        )}
        {!fullscreen && pagination}
      </>}
    <p className="field-hint housing-footer-note">Housing connects members, not bookings. Availability, permission to sublet, fees, and household details are not verified. Confirm arrangements directly before paying.</p>
  </section>;
}
