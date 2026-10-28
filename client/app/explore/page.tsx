"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import {
  useCallback,
  useEffect,
  useEffectEvent,
  useRef,
  useState,
} from "react";
import {
  ArrowDownWideNarrow,
  ArrowUpRight,
  BriefcaseBusiness,
  CalendarDays,
  ChevronDown,
  ChevronUp,
  Globe2,
  House,
  List,
  LocateFixed,
  Map as MapIcon,
  MapPin,
  Maximize2,
  MessageCircle,
  MessagesSquare,
  Minimize2,
  Plus,
  Search,
  ShoppingBag,
  Utensils,
  Users,
  X,
  Car,
} from "lucide-react";
import ProtectedPage from "../../components/ProtectedPage";
import ExploreLocationSearch from "../../components/ExploreLocationSearch";
import SavePostButton from "../../components/SavePostButton";
import PostReactions from "../../components/PostReactions";
import EditPostButton from "../../components/EditPostButton";
import DeletePostButton from "../../components/DeletePostButton";
import PostVisibilityButton from "../../components/PostVisibilityButton";
import {
  apiRequest,
  POST_CATEGORIES,
  POST_CATEGORY_LABELS,
  POST_TYPE_LABELS,
  type Post,
  type PostCategory,
  type PostReactionSummary,
  type PostSearchBounds,
  type PostSearchRequest,
  type PostSearchResponse,
  type PostType,
  type User,
} from "../../lib/api";

const ExploreMap = dynamic(() => import("../../components/ExploreMap"), {
  ssr: false,
  loading: () => (
    <div className="explore-map-loading">
      <span className="spinner" /> Loading map...
    </div>
  ),
});

const CATEGORY_ICONS = {
  HOUSING: House,
  RIDES: Car,
  JOBS: BriefcaseBusiness,
  FOOD: Utensils,
  EVENTS: CalendarDays,
  IMMIGRATION: Globe2,
  MARKETPLACE: ShoppingBag,
  GENERAL: MessagesSquare,
};
const STORAGE_KEY = "community-view-v1";
type Preferences = {
  view: "feed" | "map";
  category: PostCategory | "";
  postType: PostType | "";
  query: string;
  area: string;
  bounds: PostSearchBounds | null;
  center: [number, number];
  zoom: number;
};
const DEFAULT_PREFERENCES: Preferences = {
  view: "feed",
  category: "",
  postType: "",
  query: "",
  area: "Everywhere",
  bounds: null,
  center: [20, 0],
  zoom: 2,
};

function readPreferences(): Preferences {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "null");
    if (
      !saved ||
      !["feed", "map"].includes(saved.view) ||
      !["", ...POST_CATEGORIES].includes(saved.category) ||
      !["", "OFFER", "REQUEST", "DISCUSSION"].includes(saved.postType) ||
      typeof saved.query !== "string" ||
      typeof saved.area !== "string" ||
      !Array.isArray(saved.center) ||
      saved.center.length !== 2 ||
      !saved.center.every(Number.isFinite) ||
      !Number.isFinite(saved.zoom) ||
      (saved.bounds !== null &&
        (!saved.bounds ||
          !["north", "south", "east", "west"].every((key) =>
            Number.isFinite(saved.bounds[key]),
          )))
    )
      return DEFAULT_PREFERENCES;
    return saved;
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

function postAge(value: string) {
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(elapsed / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
  if (minutes < 10080) return `${Math.floor(minutes / 1440)}d ago`;
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export default function CommunityPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [preferences, setPreferences] =
    useState<Preferences>(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [resultKey, setResultKey] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState("");
  const searchController = useRef<AbortController | null>(null);
  const nextOffset = useRef(0);
  const [error, setError] = useState("");
  const [locationError, setLocationError] = useState("");
  const [locating, setLocating] = useState(false);
  const [searchCenter, setSearchCenter] = useState<[number, number]>(
    DEFAULT_PREFERENCES.center,
  );
  const [mapBounds, setMapBounds] = useState<PostSearchBounds | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<number | null>(null);
  const [selectionVersion, setSelectionVersion] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [resultsOpen, setResultsOpen] = useState(true);
  const [locationSearchVersion, setLocationSearchVersion] = useState(0);
  const locationVersion = useRef(0);
  const mapViewport = useRef<{ center: [number, number]; zoom: number } | null>(
    null,
  );
  const searchRequest: PostSearchRequest = {
    bounds: preferences.bounds,
    limit: 50,
    query: preferences.query.trim(),
    ...(preferences.category ? { category: preferences.category } : {}),
    ...(preferences.postType ? { post_type: preferences.postType } : {}),
  };
  const searchKey = JSON.stringify(searchRequest);
  const resultsLoading =
    !ready || loading || locating || resultKey !== searchKey;
  const locateAutomatically = useEffectEvent(() => locate(true));

  useEffect(() => {
    let active = true;
    const initialLocationVersion = locationVersion.current;
    const savedPreferences = readPreferences();
    apiRequest<User>("/users/me")
      .then((currentUser) => {
        if (!active) return;
        setUser(currentUser);
      })
      .catch((failure: unknown) => {
        if (active) {
          setError(
            failure instanceof Error
              ? failure.message
              : "Unable to load community posts.",
          );
        }
      })
      .finally(() => {
        if (!active) return;
        if (locationVersion.current === initialLocationVersion) {
          setPreferences(savedPreferences);
          setSearchCenter(savedPreferences.center);
          if (!savedPreferences.bounds || savedPreferences.area === "Near me") {
            locateAutomatically();
          }
        }
        setReady(true);
      });
    return () => {
      active = false;
      locationVersion.current += 1;
    };
  }, []);

  const requestPosts = useCallback(
    async (offset = 0, append = false) => {
      searchController.current?.abort();
      const controller = new AbortController();
      searchController.current = controller;
      if (append) setLoadingMore(true);
      else {
        setLoading(true);
        setLoadingMore(false);
        setPosts([]);
        setHasMore(false);
        setSelectedPostId(null);
        setError("");
      }
      setMoreError("");
      try {
        const response = await apiRequest<PostSearchResponse>("/posts/search", {
          method: "POST",
          body: JSON.stringify({ ...JSON.parse(searchKey), offset }),
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setPosts((current) =>
          append
            ? [
                ...current,
                ...response.posts.filter(
                  (post) =>
                    !current.some((existing) => existing.id === post.id),
                ),
              ]
            : response.posts,
        );
        nextOffset.current = offset + response.posts.length;
        setHasMore(response.has_more);
      } catch (failure) {
        if (controller.signal.aborted) return;
        const message =
          failure instanceof Error
            ? failure.message
            : "Unable to load community posts.";
        if (append) setMoreError(message);
        else setError(message);
      } finally {
        if (!controller.signal.aborted) {
          setResultKey(searchKey);
          setLoading(false);
          setLoadingMore(false);
        }
      }
    },
    [searchKey],
  );

  useEffect(() => {
    if (!ready || locating) return;
    const timer = window.setTimeout(() => void requestPosts(), 300);
    return () => {
      window.clearTimeout(timer);
      searchController.current?.abort();
    };
  }, [ready, locating, requestPosts]);

  useEffect(() => {
    if (!ready) return;
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          ...preferences,
          ...(preferences.view === "map" ? mapViewport.current : null),
        }),
      );
    } catch {}
  }, [ready, preferences]);

  useEffect(() => {
    if (resultsLoading) return;
    const frame = requestAnimationFrame(() => {
      try {
        const scroll = sessionStorage.getItem("community-scroll");
        if (scroll !== null) window.scrollTo(0, Number(scroll));
        sessionStorage.removeItem("community-scroll");
      } catch {}
    });
    return () => cancelAnimationFrame(frame);
  }, [resultsLoading]);

  useEffect(() => {
    if (!fullscreen) return;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setFullscreen(false);
    };
    window.addEventListener("keydown", close);
    return () => {
      document.body.style.overflow = overflow;
      window.removeEventListener("keydown", close);
    };
  }, [fullscreen]);

  function updatePreferences(next: Partial<Preferences>) {
    setPreferences((current) => ({
      ...current,
      ...(current.view === "map" && next.view === "feed"
        ? mapViewport.current
        : null),
      ...next,
    }));
    setSelectedPostId(null);
  }

  async function retry() {
    await requestPosts();
  }

  const selectPost = useCallback((postId: number) => {
    setSelectedPostId(postId);
    setSelectionVersion((version) => version + 1);
    setResultsOpen(true);
    requestAnimationFrame(() =>
      document
        .getElementById(`community-post-${postId}`)
        ?.scrollIntoView({ block: "nearest", behavior: "smooth" }),
    );
  }, []);
  const onMapCenterChange = useCallback((center: [number, number]) => {
    setSearchCenter(center);
  }, []);
  const onViewportChange = useCallback(
    (center: [number, number], zoom: number) => {
      mapViewport.current = { center, zoom };
      try {
        sessionStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ ...readPreferences(), center, zoom }),
        );
      } catch {}
    },
    [],
  );

  function selectLocation(center: [number, number], area = "Selected area") {
    locationVersion.current += 1;
    mapViewport.current = null;
    setSearchCenter(center);
    setLocating(false);
    setLocationError("");
    const longitudeSpan = Math.min(
      180,
      0.25 / Math.max(0.01, Math.cos((center[0] * Math.PI) / 180)),
    );
    const wrap = (longitude: number) => ((longitude + 540) % 360) - 180;
    updatePreferences({
      center,
      zoom: 11,
      area,
      bounds: {
        north: Math.min(90, center[0] + 0.25),
        south: Math.max(-90, center[0] - 0.25),
        east: wrap(center[1] + longitudeSpan),
        west: wrap(center[1] - longitudeSpan),
      },
    });
  }

  function locate(automatic = false) {
    if (!navigator.geolocation) {
      setLocationError("Location is unavailable. Search for a city instead.");
      return;
    }
    const version = ++locationVersion.current;
    setLocating(true);
    setLocationError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (version !== locationVersion.current) return;
        selectLocation(
          [position.coords.latitude, position.coords.longitude],
          "Near me",
        );
        if (!automatic) setLocationSearchVersion((current) => current + 1);
      },
      () => {
        if (version !== locationVersion.current) return;
        setLocating(false);
        setLocationError(
          "Couldn't access your location. Search for a city instead.",
        );
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 },
    );
  }

  function clearArea() {
    locationVersion.current += 1;
    mapViewport.current = null;
    setSearchCenter(DEFAULT_PREFERENCES.center);
    setLocating(false);
    setLocationError("");
    setLocationSearchVersion((current) => current + 1);
    updatePreferences({
      area: "Everywhere",
      bounds: null,
      center: [20, 0],
      zoom: 2,
    });
  }

  function updatePost(post: Post) {
    setPosts((current) =>
      post.is_private
        ? current.filter((item) => item.id !== post.id)
        : current.map((item) => (item.id === post.id ? post : item)),
    );
    void requestPosts();
  }

  function updateReactions(summary: PostReactionSummary) {
    setPosts((current) =>
      current.map((post) =>
        post.id === summary.post_id
          ? {
              ...post,
              like_count: summary.like_count,
              dislike_count: summary.dislike_count,
              my_reaction: summary.my_reaction,
            }
          : post,
      ),
    );
  }

  function rememberPosition() {
    try {
      sessionStorage.setItem("community-scroll", String(window.scrollY));
    } catch {}
  }

  const visiblePosts = resultsLoading ? [] : posts;
  const hasFilters = Boolean(
    preferences.category || preferences.postType || preferences.query,
  );

  return (
    <ProtectedPage>
      <div
        className={`community-page${fullscreen ? " community-expanded" : ""}`}
      >
        <header className="community-heading">
          <div>
            <p className="eyebrow">YOUR PEOPLE. YOUR PLACES.</p>
            <h1>Community</h1>
          </div>
          <div className="community-heading-actions">
            <button
              type="button"
              className="button button-secondary"
              aria-pressed={fullscreen}
              onClick={() => {
                updatePreferences({ view: "map" });
                setFullscreen(!fullscreen);
              }}
            >
              {fullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
              {fullscreen ? "Exit full screen" : "Full screen map"}
            </button>
            <Link className="button button-primary" href="/create-post">
              <Plus size={18} /> Create post
            </Link>
          </div>
        </header>

        <section className="community-discovery" aria-label="Search community">
          <div className="community-location">
            <MapPin size={18} />
            <ExploreLocationSearch
              key={locationSearchVersion}
              center={searchCenter}
              label="Location"
              onLocationSelected={(center) => selectLocation(center)}
              onSelectionChange={(selection) => {
                if (selection)
                  setPreferences((current) => ({
                    ...current,
                    area: selection.location,
                  }));
              }}
            />
            <button
              className="community-icon-button"
              type="button"
              onClick={() => locate()}
              disabled={locating}
              title="Use my location"
              aria-label="Use my location"
            >
              {locating ? (
                <span className="spinner" />
              ) : (
                <LocateFixed size={19} />
              )}
            </button>
          </div>
          <label className="community-search">
            <Search size={19} />
            <span className="sr-only">Search posts</span>
            <input
              type="search"
              placeholder="Search your community"
              value={preferences.query}
              onChange={(event) =>
                updatePreferences({ query: event.target.value })
              }
            />
          </label>
        </section>
        {locationError && (
          <p className="community-error" role="alert">
            {locationError}
          </p>
        )}

        <div className="community-categories" aria-label="Post categories">
          <button
            type="button"
            aria-pressed={!preferences.category}
            onClick={() => updatePreferences({ category: "" })}
          >
            <Users size={17} /> All
          </button>
          {POST_CATEGORIES.map((category) => {
            const Icon = CATEGORY_ICONS[category];
            return (
              <button
                type="button"
                key={category}
                aria-pressed={preferences.category === category}
                onClick={() => updatePreferences({ category })}
              >
                <Icon size={17} />
                {POST_CATEGORY_LABELS[category]}
              </button>
            );
          })}
        </div>

        <div className="community-controls">
          <div className="community-scope">
            <Globe2 size={15} />
            <span title={preferences.area}>{preferences.area}</span>
            {preferences.bounds && (
              <button
                className="community-icon-button"
                type="button"
                onClick={clearArea}
                title="Show everywhere"
                aria-label="Show everywhere"
              >
                <X size={15} />
              </button>
            )}
          </div>
          <label className="community-type">
            <span className="sr-only">Post type</span>
            <select
              value={preferences.postType}
              onChange={(event) =>
                updatePreferences({
                  postType: event.target.value as PostType | "",
                })
              }
            >
              <option value="">All post types</option>
              {Object.entries(POST_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <div
            className="community-view-toggle"
            role="group"
            aria-label="Community view"
          >
            <button
              type="button"
              aria-pressed={preferences.view === "feed"}
              onClick={() => {
                updatePreferences({ view: "feed" });
                setFullscreen(false);
              }}
            >
              <List size={17} />
              Feed
            </button>
            <button
              type="button"
              aria-pressed={preferences.view === "map"}
              onClick={() => updatePreferences({ view: "map" })}
            >
              <MapIcon size={17} />
              Map
            </button>
          </div>
        </div>

        <div className={`community-content community-${preferences.view}`}>
          {preferences.view === "map" && (
            <section className="community-map-panel" aria-label="Community map">
              <ExploreMap
                key={`${preferences.center.join(",")}:${preferences.zoom}`}
                posts={visiblePosts}
                fullscreen={fullscreen}
                center={preferences.center}
                initialZoom={preferences.zoom}
                selectedPostId={selectedPostId}
                selectionVersion={selectionVersion}
                onSelectPost={selectPost}
                onBoundsChange={setMapBounds}
                onCenterChange={onMapCenterChange}
                onViewportChange={onViewportChange}
              />
              <div className="community-map-actions">
                <button
                  type="button"
                  className="button button-primary"
                  disabled={!mapBounds || !ready || locating}
                  onClick={() => {
                    locationVersion.current += 1;
                    setLocating(false);
                    updatePreferences({ bounds: mapBounds, area: "Map area" });
                    if (preferences.bounds === mapBounds) void requestPosts();
                  }}
                >
                  <Search size={16} /> Search this area
                </button>
                <button
                  type="button"
                  className="community-icon-button"
                  title="Center on my location"
                  aria-label="Center on my location"
                  aria-busy={locating}
                  disabled={locating}
                  onClick={() => locate()}
                >
                  {locating ? (
                    <span className="spinner" aria-hidden="true" />
                  ) : (
                    <LocateFixed size={19} />
                  )}
                </button>
                <button
                  type="button"
                  className="community-icon-button"
                  title={fullscreen ? "Exit full screen" : "Full screen map"}
                  aria-label={
                    fullscreen ? "Exit full screen" : "Full screen map"
                  }
                  onClick={() => setFullscreen(!fullscreen)}
                >
                  {fullscreen ? (
                    <Minimize2 size={19} />
                  ) : (
                    <Maximize2 size={19} />
                  )}
                </button>
              </div>
            </section>
          )}

          <section
            className={`community-results${!resultsOpen && preferences.view === "map" ? " community-results-collapsed" : ""}`}
            aria-label="Community posts"
          >
            <div className="community-results-heading">
              <div>
                <h2>
                  {preferences.category
                    ? POST_CATEGORY_LABELS[preferences.category]
                    : "The latest"}
                </h2>
                <span aria-live="polite">
                  {resultsLoading
                    ? "Loading..."
                    : `${visiblePosts.length}${hasMore ? "+" : ""} ${visiblePosts.length === 1 && !hasMore ? "post" : "posts"}`}
                </span>
              </div>
              <span className="community-sort">
                <ArrowDownWideNarrow size={15} />
                Newest first
              </span>
              {preferences.view === "map" && (
                <button
                  type="button"
                  className="community-icon-button community-sheet-toggle"
                  aria-expanded={resultsOpen}
                  aria-label={
                    resultsOpen ? "Collapse results" : "Expand results"
                  }
                  onClick={() => setResultsOpen(!resultsOpen)}
                >
                  {resultsOpen ? (
                    <ChevronDown size={20} />
                  ) : (
                    <ChevronUp size={20} />
                  )}
                </button>
              )}
            </div>
            <div className="community-result-body">
              {resultsLoading ? (
                <div className="community-state" role="status">
                  <span className="spinner" /> Loading community posts...
                </div>
              ) : error ? (
                <div className="community-state" role="alert">
                  <h3>Could not load the community</h3>
                  <p>{error}</p>
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => void retry()}
                  >
                    Try again
                  </button>
                </div>
              ) : !visiblePosts.length ? (
                <div className="community-state">
                  <MessagesSquare size={32} />
                  <h3>
                    {hasFilters
                      ? "No matching posts"
                      : preferences.bounds
                        ? "It's quiet in this area"
                        : "Start the conversation"}
                  </h3>
                  <p>
                    {hasFilters
                      ? "Try another search or clear your filters."
                      : preferences.bounds
                        ? "See what's happening in the wider community."
                        : "A question, a recommendation, or something to share?"}
                  </p>
                  {hasFilters ? (
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() =>
                        updatePreferences({
                          category: "",
                          postType: "",
                          query: "",
                        })
                      }
                    >
                      Clear filters
                    </button>
                  ) : preferences.bounds ? (
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={clearArea}
                    >
                      Browse everywhere
                    </button>
                  ) : (
                    <Link className="button button-primary" href="/create-post">
                      <Plus size={16} />
                      Create post
                    </Link>
                  )}
                </div>
              ) : (
                visiblePosts.map((post) => {
                  const Icon = CATEGORY_ICONS[post.category];
                  return (
                    <article
                      id={`community-post-${post.id}`}
                      key={post.id}
                      className={`community-post community-category-${post.category.toLowerCase()}${selectedPostId === post.id ? " is-selected" : ""}`}
                    >
                      <div className="community-post-top">
                        <span className="community-category-icon">
                          <Icon size={20} />
                        </span>
                        <div className="community-post-context">
                          <span>
                            {POST_CATEGORY_LABELS[post.category]}
                            {post.user_id === user?.id && (
                              <span className="community-you">You</span>
                            )}
                          </span>
                          <time
                            dateTime={post.created_at}
                            title={new Date(post.created_at).toLocaleString()}
                          >
                            {postAge(post.created_at)}
                            {post.updated_at ? " · Edited" : ""}
                          </time>
                        </div>
                        <span
                          className={`post-type-pill post-type-${post.post_type.toLowerCase()}`}
                        >
                          {POST_TYPE_LABELS[post.post_type]}
                        </span>
                      </div>
                      <h3>
                        <Link
                          href={`/posts/${post.id}`}
                          onClick={rememberPosition}
                        >
                          {post.title}
                          <ArrowUpRight size={17} />
                        </Link>
                      </h3>
                      <p className="community-post-description">
                        {post.description}
                      </p>
                      <div className="community-post-location">
                        <MapPin size={13} />
                        <span>{post.location}</span>
                        {preferences.view === "map" && (
                          <button
                            type="button"
                            className="text-link"
                            onClick={() => selectPost(post.id)}
                          >
                            Locate
                          </button>
                        )}
                      </div>
                      <footer className="community-post-footer">
                        <PostReactions
                          canReact={post.user_id !== user?.id}
                          dislikeCount={post.dislike_count}
                          likeCount={post.like_count}
                          myReaction={post.my_reaction}
                          onChanged={updateReactions}
                          postId={post.id}
                        />
                        <Link
                          className="community-comments"
                          aria-label={`${post.comment_count} comments on ${post.title}`}
                          href={`/posts/${post.id}`}
                          onClick={rememberPosition}
                        >
                          <MessageCircle size={16} />
                          {post.comment_count}
                          <span> comments</span>
                        </Link>
                        <SavePostButton
                          isSaved={post.my_saved}
                          onChanged={(isSaved) =>
                            setPosts((current) =>
                              current.map((item) =>
                                item.id === post.id
                                  ? { ...item, my_saved: isSaved }
                                  : item,
                              ),
                            )
                          }
                          postId={post.id}
                        />
                      </footer>
                      {post.user_id === user?.id && (
                        <div className="community-owner-actions">
                          <PostVisibilityButton
                            onChanged={updatePost}
                            post={post}
                          />
                          <EditPostButton onUpdated={updatePost} post={post} />
                          <DeletePostButton
                            onDeleted={(postId) => {
                              setPosts((current) =>
                                current.filter((item) => item.id !== postId),
                              );
                              void requestPosts();
                            }}
                            postId={post.id}
                          />
                        </div>
                      )}
                    </article>
                  );
                })
              )}
              {!resultsLoading && !error && hasMore && (
                <div>
                  {moreError && (
                    <p className="community-error" role="alert">
                      {moreError}
                    </p>
                  )}
                  <button
                    className="button button-secondary"
                    type="button"
                    disabled={loadingMore}
                    onClick={() => void requestPosts(nextOffset.current, true)}
                  >
                    {loadingMore
                      ? "Loading..."
                      : moreError
                        ? "Retry loading more"
                        : "Load more"}
                  </button>
                </div>
              )}
            </div>
          </section>

          {preferences.view === "feed" && (
            <aside className="community-sidebar">
              <div className="community-sidebar-heading">
                <MapPin size={18} />
                <h2>Around you</h2>
              </div>
              <p className="community-sidebar-place">{preferences.area}</p>
              <button
                type="button"
                className="community-map-preview"
                aria-label="Explore community on the map"
                onClick={() => updatePreferences({ view: "map" })}
              >
                <Image
                  unoptimized
                  loading="eager"
                  src="https://tile.openstreetmap.org/0/0/0.png"
                  width={256}
                  height={256}
                  alt="World map"
                />
                <span>
                  <MapIcon size={17} />
                  Explore the map
                  <ArrowUpRight size={17} />
                </span>
              </button>
              <a
                className="community-map-credit"
                href="https://www.openstreetmap.org/copyright"
              >
                Map data: OpenStreetMap contributors
              </a>
              <div className="community-sidebar-heading community-topics-heading">
                <MessagesSquare size={18} />
                <h2>Browse by intention</h2>
              </div>
              {Object.entries(POST_TYPE_LABELS).map(([value, label]) => (
                <button
                  className="community-intention"
                  type="button"
                  key={value}
                  aria-pressed={preferences.postType === value}
                  onClick={() =>
                    updatePreferences({
                      postType:
                        preferences.postType === value
                          ? ""
                          : (value as PostType),
                    })
                  }
                >
                  <span>{label}</span>
                  <span>
                    <ArrowUpRight size={15} />
                  </span>
                </button>
              ))}
              <Link className="community-saved-link" href="/saved">
                Saved posts
                <ArrowUpRight size={16} />
              </Link>
            </aside>
          )}
        </div>
      </div>
    </ProtectedPage>
  );
}
