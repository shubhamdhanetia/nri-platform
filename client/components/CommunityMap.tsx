"use client";

import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { renderToStaticMarkup } from "react-dom/server";
import { Flag } from "lucide-react";
import MarkerClusterGroup from "react-leaflet-cluster";
import {
  MapContainer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { divIcon, type Marker as LeafletMarker, type MarkerClusterGroup as LeafletCluster } from "leaflet";
import "leaflet.markercluster";
import "react-leaflet-cluster/dist/assets/MarkerCluster.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.Default.css";
import type { PostSearchBounds } from "../lib/api";

export interface MapPoint {
  id: string;
  latitude: number;
  longitude: number;
  title: string;
  description: string;
  href: string;
  linkLabel: string;
  destination?: { latitude: number; longitude: number; title: string; description: string };
}

const clusterIcon: NonNullable<
  import("leaflet").MarkerClusterGroupOptions["iconCreateFunction"]
> = (cluster) => {
  const count = cluster.getChildCount();
  return divIcon({
    className: "post-marker-cluster",
    html: `<span aria-label="${count} locations">${count}</span>`,
    iconSize: [42, 42],
    iconAnchor: [21, 21],
  });
};

const destinationClusterIcon: typeof clusterIcon = (cluster) => divIcon({
  className: "post-marker-cluster destination-marker-cluster",
  html: `<span aria-label="${cluster.getChildCount()} destinations">${renderToStaticMarkup(<Flag size={14} aria-hidden="true" />)}${cluster.getChildCount()}</span>`,
  iconSize: [46, 46], iconAnchor: [23, 23],
});

function MapBoundsReporter({
  onBoundsChange,
  onCenterChange,
  onViewportChange,
}: {
  onBoundsChange: (bounds: PostSearchBounds) => void;
  onCenterChange: (center: [number, number]) => void;
  onViewportChange?: (center: [number, number], zoom: number) => void;
}) {
  const map = useMap();
  const lastReportedBounds = useRef<PostSearchBounds | null>(null);
  const lastReportedCenter = useRef<[number, number] | null>(null);

  const reportBounds = useCallback(() => {
    const bounds = map.getBounds();
    const nextBounds = {
      north: bounds.getNorth(),
      east: bounds.getEast(),
      south: bounds.getSouth(),
      west: bounds.getWest(),
    };
    const center = map.getCenter();
    const nextCenter: [number, number] = [center.lat, center.lng];
    onViewportChange?.(nextCenter, map.getZoom());
    const previousCenter = lastReportedCenter.current;
    if (
      !previousCenter
      || previousCenter[0] !== nextCenter[0]
      || previousCenter[1] !== nextCenter[1]
    ) {
      lastReportedCenter.current = nextCenter;
      onCenterChange(nextCenter);
    }

    const previousBounds = lastReportedBounds.current;
    if (
      previousBounds
      && previousBounds.north === nextBounds.north
      && previousBounds.east === nextBounds.east
      && previousBounds.south === nextBounds.south
      && previousBounds.west === nextBounds.west
    ) {
      return;
    }

    lastReportedBounds.current = nextBounds;
    onBoundsChange(nextBounds);
  }, [map, onBoundsChange, onCenterChange, onViewportChange]);

  useEffect(() => {
    reportBounds();
  }, [reportBounds]);

  useMapEvents({
    moveend: reportBounds,
    resize: reportBounds,
    zoomend: reportBounds,
  });

  return null;
}

function SelectedPostPan({
  post,
  marker,
  cluster,
  selectionVersion,
}: {
  post: MapPoint | undefined;
  marker: React.RefObject<LeafletMarker | null>;
  cluster: React.RefObject<LeafletCluster | null>;
  selectionVersion: number;
}) {
  const map = useMap();

  useEffect(() => {
    if (!post) return;
    const selectedMarker = marker.current;
    const markerCluster = cluster.current;
    if (!selectedMarker || !markerCluster) {
      map.panTo([post.latitude, post.longitude]);
      return;
    }
    let revealed = false;
    const reveal = () => {
      if (revealed || !markerCluster.getVisibleParent(selectedMarker)) return;
      revealed = true;
      markerCluster.zoomToShowLayer(selectedMarker, () => selectedMarker.openPopup());
    };
    markerCluster.on("layeradd", reveal);
    const frame = requestAnimationFrame(reveal);
    return () => {
      cancelAnimationFrame(frame);
      markerCluster.off("layeradd", reveal);
    };
  }, [cluster, map, marker, post, selectionVersion]);

  return null;
}

export default function CommunityMap({
  posts,
  fullscreen,
  selectedPostId,
  selectionVersion,
  onSelectPost,
  onBoundsChange,
  onCenterChange,
  onViewportChange,
  center,
  initialZoom,
  fitPosts = false,
  onClearSelection,
}: {
  posts: MapPoint[];
  fullscreen: boolean;
  selectedPostId: string | null;
  selectionVersion: number;
  onSelectPost: (postId: string) => void;
  onBoundsChange: (bounds: PostSearchBounds) => void;
  onCenterChange: (center: [number, number]) => void;
  onViewportChange?: (center: [number, number], zoom: number) => void;
  center: [number, number];
  initialZoom: number;
  fitPosts?: boolean;
  onClearSelection?: () => void;
}) {
  const selectedPost = posts.find((post) => post.id === selectedPostId);
  const selectedMarker = useRef<LeafletMarker>(null);
  const cluster = useRef<LeafletCluster>(null);
  const [popupSelection, setPopupSelection] = useState<{ id: string; destination: boolean } | null>(null);
  const selectPickup = useCallback((id: string) => {
    setPopupSelection({ id, destination: false }); onSelectPost(id);
  }, [onSelectPost]);
  const selectDestination = useCallback((id: string) => {
    setPopupSelection({ id, destination: true }); onSelectPost(id);
  }, [onSelectPost]);
  const clearSelection = useCallback(() => {
    setPopupSelection(null); onClearSelection?.();
  }, [onClearSelection]);

  return (
    <MapContainer
      center={center}
      maxBounds={[[-85, -180], [85, 180]]}
      maxBoundsViscosity={1}
      minZoom={2}
      scrollWheelZoom
      zoom={initialZoom}
      className="explore-map"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapBoundsReporter
        onBoundsChange={onBoundsChange}
        onCenterChange={onCenterChange}
        onViewportChange={onViewportChange}
      />
      <MapResizeOnModeChange fullscreen={fullscreen} />
      <MapCenterSync center={center} />
      {fitPosts && <FitPostLocations posts={posts} />}
      {onClearSelection && <TripConnection post={selectedPost} selectionVersion={selectionVersion} onClearSelection={clearSelection} />}
      {!onClearSelection && <SelectedPostPan
        marker={selectedMarker}
        cluster={cluster}
        post={selectedPost}
        selectionVersion={selectionVersion}
      />}
      <MarkerClusterGroup
        ref={cluster}
        chunkedLoading
        iconCreateFunction={clusterIcon}
        maxClusterRadius={70}
        spiderfyDistanceMultiplier={1.5}
        spiderfyOnMaxZoom
        spiderLegPolylineOptions={{ color: "#226b55", weight: 2, opacity: 0.7 }}
      >
        {posts.filter(post => !onClearSelection || post.id !== selectedPostId).map((post) => (
          <PostMarker
            key={post.id}
            post={post}
            selected={post.id === selectedPostId}
            onSelect={onClearSelection ? selectPickup : onSelectPost}
            markerRef={post.id === selectedPostId ? selectedMarker : undefined}
            dimmed={!!onClearSelection && selectedPostId !== null && post.id !== selectedPostId}
          />
        ))}
      </MarkerClusterGroup>
      {onClearSelection && <MarkerClusterGroup
        iconCreateFunction={destinationClusterIcon}
        maxClusterRadius={50}
        spiderfyDistanceMultiplier={1.8}
        spiderfyOnMaxZoom
        spiderLegPolylineOptions={{ color: "#b33e45", weight: 2, opacity: 0.7 }}
      >
        {posts.filter(post => post.destination && post.id !== selectedPostId).map(post => <PostMarker
          key={`destination-${post.id}`} post={post} destination
          selected={post.id === selectedPostId} dimmed={selectedPostId !== null && post.id !== selectedPostId}
          onSelect={selectDestination}
        />)}
      </MarkerClusterGroup>}
      {onClearSelection && selectedPost && <>
        <PostMarker key={`selected-pickup-${selectedPost.id}`} post={selectedPost} selected onSelect={selectPickup}
          openPopup={popupSelection?.id === selectedPost.id && !popupSelection.destination} />
        {selectedPost.destination && <PostMarker key={`selected-destination-${selectedPost.id}`} post={selectedPost} selected destination onSelect={selectDestination}
          openPopup={popupSelection?.id === selectedPost.id && popupSelection.destination} />}
      </>}
    </MapContainer>
  );
}

function TripConnection({ post, selectionVersion, onClearSelection }: {
  post: MapPoint | undefined;
  selectionVersion: number;
  onClearSelection: () => void;
}) {
  const map = useMapEvents({ click: onClearSelection });
  const lastFit = useRef(0);
  const destination = post?.destination;
  const curve = useMemo(() => {
    if (!post || !destination) return null;
    const pickup = map.project([post.latitude, post.longitude], 0);
    const dropoff = map.project([destination.latitude, destination.longitude], 0);
    const deltaX = dropoff.x - pickup.x;
    const deltaY = dropoff.y - pickup.y;
    const controlX = (pickup.x + dropoff.x) / 2 - deltaY * 0.18;
    const controlY = (pickup.y + dropoff.y) / 2 + deltaX * 0.18;
    const positions = Array.from({ length: 49 }, (_, index) => {
      const fraction = index / 48;
      const remaining = 1 - fraction;
      return map.unproject([
        remaining ** 2 * pickup.x + 2 * remaining * fraction * controlX + fraction ** 2 * dropoff.x,
        remaining ** 2 * pickup.y + 2 * remaining * fraction * controlY + fraction ** 2 * dropoff.y,
      ], 0);
    });
    return positions;
  }, [map, post, destination]);

  useEffect(() => {
    if (selectionVersion === lastFit.current) return;
    lastFit.current = selectionVersion;
    if (!post || !destination) return;
    map.closePopup();
    map.fitBounds([[post.latitude, post.longitude], [destination.latitude, destination.longitude]], {
      paddingTopLeft: [48, 80], paddingBottomRight: [48, 48], maxZoom: 14, animate: false,
    });
  }, [map, post, destination, selectionVersion]);

  if (!post || !destination || !curve) return null;
  return <>
    <Polyline positions={curve} interactive={false} pathOptions={{ color: "white", weight: 6, opacity: 0.85 }} />
    <Polyline positions={curve} interactive={false} pathOptions={{ className: "carpool-connection", color: "#42685e", weight: 3, dashArray: "3 9", lineCap: "round", opacity: 1 }} />
    <ConnectionArrow positions={curve} />
    <CircleMarker center={[post.latitude, post.longitude]} radius={8} interactive={false} pathOptions={{ color: "white", weight: 2, fillColor: "#226b55", fillOpacity: 1 }} />
    <CircleMarker center={[destination.latitude, destination.longitude]} radius={8} interactive={false} pathOptions={{ color: "white", weight: 2, fillColor: "#b33e45", fillOpacity: 1 }} />
  </>;
}

function ConnectionArrow({ positions }: { positions: import("leaflet").LatLng[] }) {
  const map = useMap();
  const arrowRef = useRef<import("leaflet").Polyline>(null);
  const update = useCallback(() => {
    const tip = map.latLngToLayerPoint(positions[32]);
    const previous = map.latLngToLayerPoint(positions[31]);
    const angle = Math.atan2(tip.y - previous.y, tip.x - previous.x);
    arrowRef.current?.setLatLngs([
      map.layerPointToLatLng([tip.x - 10 * Math.cos(angle - 0.55), tip.y - 10 * Math.sin(angle - 0.55)]),
      positions[32],
      map.layerPointToLatLng([tip.x - 10 * Math.cos(angle + 0.55), tip.y - 10 * Math.sin(angle + 0.55)]),
    ]);
  }, [map, positions]);
  useMapEvents({ zoomend: update });
  useEffect(update, [update]);
  return <Polyline ref={arrowRef} positions={[]} interactive={false} pathOptions={{ color: "#42685e", weight: 3 }} />;
}

function FitPostLocations({ posts }: { posts: MapPoint[] }) {
  const map = useMap();

  useEffect(() => {
    if (!posts.length) return;
    map.fitBounds(posts.map(post => [post.latitude, post.longitude] as [number, number]), {
      paddingTopLeft: [48, 80], paddingBottomRight: [48, 48], maxZoom: 11, animate: false,
    });
  }, [map, posts]);

  return null;
}

function MapResizeOnModeChange({ fullscreen }: { fullscreen: boolean }) {
  const map = useMap();

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      map.invalidateSize({ pan: false, debounceMoveend: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [fullscreen, map]);

  return null;
}

const PostMarker = memo(function PostMarker({
  post,
  selected,
  onSelect,
  markerRef,
  destination = false,
  dimmed = false,
  openPopup = false,
}: {
  post: MapPoint;
  selected: boolean;
  onSelect: (postId: string) => void;
  markerRef?: React.RefObject<LeafletMarker | null>;
  destination?: boolean;
  dimmed?: boolean;
  openPopup?: boolean;
}) {
  const popupMarker = useRef<LeafletMarker>(null);
  const activeRef = markerRef ?? popupMarker;
  useEffect(() => {
    if (openPopup) activeRef.current?.openPopup();
  }, [openPopup, activeRef]);
  const location = destination && post.destination ? post.destination : post;
  const position = useMemo<[number, number]>(
    () => [location.latitude, location.longitude],
    [location.latitude, location.longitude],
  );
  const icon = useMemo(() => divIcon({
    className: "post-map-marker-container",
    html: `<span class="post-map-marker${destination ? " destination-map-marker" : ""}${selected ? " selected" : ""}" aria-hidden="true">${destination ? renderToStaticMarkup(<Flag size={24} />) : '<svg viewBox="0 0 24 24" focusable="false"><path d="M20 10.2c0 5.1-8 11.1-8 11.1S4 15.3 4 10.2a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>'}</span>`,
    iconSize: [40, 46],
    iconAnchor: [20, 43],
    popupAnchor: [0, -41],
  }), [selected, destination]);

  return (
    <Marker
      position={position}
      title={location.title}
      alt={location.title}
      opacity={dimmed ? 0.45 : 1}
      zIndexOffset={selected ? 1000 : 0}
      eventHandlers={{ click: () => onSelect(post.id) }}
      icon={icon}
      ref={activeRef}
    >
      <Popup autoPan={!post.destination}>
        <div className="post-map-popup">
          <strong>{location.title}</strong>
          <span>{location.description}</span>
          <Link href={post.href}>{post.linkLabel}</Link>
        </div>
      </Popup>
    </Marker>
  );
});

function MapCenterSync({ center }: { center: [number, number] }) {
  const map = useMap();
  const previousCenter = useRef(center);

  useEffect(() => {
    if (previousCenter.current === center) {
      return;
    }
    previousCenter.current = center;
    map.setView(center, Math.max(map.getZoom(), 11), { animate: false });
  }, [center, map]);

  return null;
}
