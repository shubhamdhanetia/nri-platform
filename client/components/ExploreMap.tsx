"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import MarkerClusterGroup from "react-leaflet-cluster";
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { divIcon, type Marker as LeafletMarker } from "leaflet";
import "leaflet.markercluster";
import "react-leaflet-cluster/dist/assets/MarkerCluster.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.Default.css";
import type { Post, PostSearchBounds } from "../lib/api";

const clusterIcon: NonNullable<
  import("leaflet").MarkerClusterGroupOptions["iconCreateFunction"]
> = (cluster) => {
  const count = cluster.getChildCount();
  return divIcon({
    className: "post-marker-cluster",
    html: `<span aria-label="${count} posts">${count}</span>`,
    iconSize: [42, 42],
    iconAnchor: [21, 21],
  });
};

function MapBoundsReporter({
  onBoundsChange,
  onCenterChange,
}: {
  onBoundsChange: (bounds: PostSearchBounds) => void;
  onCenterChange: (center: [number, number]) => void;
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
  }, [map, onBoundsChange, onCenterChange]);

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
  selectionVersion,
}: {
  post: Post | undefined;
  marker: React.RefObject<LeafletMarker | null>;
  selectionVersion: number;
}) {
  const map = useMap();

  useEffect(() => {
    if (!post) return;
    map.panTo([post.latitude, post.longitude]);
    marker.current?.openPopup();
  }, [map, marker, post, selectionVersion]);

  return null;
}

export default function ExploreMap({
  posts,
  fullscreen,
  selectedPostId,
  selectionVersion,
  onSelectPost,
  onBoundsChange,
  onCenterChange,
  center,
  initialZoom,
}: {
  posts: Post[];
  fullscreen: boolean;
  selectedPostId: number | null;
  selectionVersion: number;
  onSelectPost: (postId: number) => void;
  onBoundsChange: (bounds: PostSearchBounds) => void;
  onCenterChange: (center: [number, number]) => void;
  center: [number, number];
  initialZoom: number;
}) {
  const selectedPost = posts.find((post) => post.id === selectedPostId);
  const selectedMarker = useRef<LeafletMarker>(null);

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
      />
      <MapResizeOnModeChange fullscreen={fullscreen} />
      <MapCenterSync center={center} />
      <SelectedPostPan
        marker={selectedMarker}
        post={selectedPost}
        selectionVersion={selectionVersion}
      />
      <MarkerClusterGroup
        chunkedLoading
        iconCreateFunction={clusterIcon}
        maxClusterRadius={70}
        spiderfyDistanceMultiplier={1.5}
        spiderfyOnMaxZoom
        spiderLegPolylineOptions={{ color: "#226b55", weight: 2, opacity: 0.7 }}
      >
        {posts.map((post) => (
          <PostMarker
            key={post.id}
            post={post}
            selected={post.id === selectedPostId}
            onSelect={onSelectPost}
            markerRef={post.id === selectedPostId ? selectedMarker : undefined}
          />
        ))}
      </MarkerClusterGroup>
    </MapContainer>
  );
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

function PostMarker({
  post,
  selected,
  onSelect,
  markerRef,
}: {
  post: Post;
  selected: boolean;
  onSelect: (postId: number) => void;
  markerRef?: React.RefObject<LeafletMarker | null>;
}) {
  const icon = useMemo(() => divIcon({
    className: "post-map-marker-container",
    html: `<span class="post-map-marker${selected ? " selected" : ""}" aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><path d="M20 10.2c0 5.1-8 11.1-8 11.1S4 15.3 4 10.2a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg></span>`,
    iconSize: [40, 46],
    iconAnchor: [20, 43],
    popupAnchor: [0, -41],
  }), [selected]);

  return (
    <Marker
      position={[post.latitude, post.longitude]}
      eventHandlers={{ click: () => onSelect(post.id) }}
      icon={icon}
      ref={markerRef}
    >
      <Popup>
        <div className="post-map-popup">
          <strong>{post.title}</strong>
          <span>{post.city}</span>
          <Link href={`/posts/${post.id}`}>View post details</Link>
        </div>
      </Popup>
    </Marker>
  );
}

function MapCenterSync({ center }: { center: [number, number] }) {
  const map = useMap();
  const previousCenter = useRef(center);

  useEffect(() => {
    if (previousCenter.current === center) {
      return;
    }
    previousCenter.current = center;
    map.setView(center, Math.max(map.getZoom(), 11));
  }, [center, map]);

  return null;
}
