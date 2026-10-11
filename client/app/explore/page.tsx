"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useState } from "react";
import ProtectedPage from "../../components/ProtectedPage";
import {
  apiRequest,
  POST_CATEGORIES,
  POST_CATEGORY_LABELS,
  POST_TYPE_LABELS,
  type Post,
  type PostCategory,
  type PostSearchBounds,
  type PostSearchRequest,
  type PostSearchResponse,
} from "../../lib/api";

const ExploreMap = dynamic(() => import("../../components/ExploreMap"), {
  ssr: false,
  loading: () => <div className="explore-map-loading">Loading map…</div>,
});

const SEARCH_RESULT_LIMIT = 50;
const DEFAULT_CENTER: [number, number] = [20, 0];

function isPostCategory(value: string): value is PostCategory {
  return POST_CATEGORIES.some((category) => category === value);
}

function boundsHaveChanged(
  current: PostSearchBounds,
  searched: PostSearchBounds,
): boolean {
  return current.north !== searched.north
    || current.east !== searched.east
    || current.south !== searched.south
    || current.west !== searched.west;
}

export default function ExplorePage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [bounds, setBounds] = useState<PostSearchBounds | null>(null);
  const [searched, setSearched] = useState(false);
  const [searchPending, setSearchPending] = useState(false);
  const [error, setError] = useState("");
  const [selectedPostId, setSelectedPostId] = useState<number | null>(null);
  const [category, setCategory] = useState<PostCategory | "">("");
  const [lastSearchedCategory, setLastSearchedCategory] = useState<PostCategory | "">("");
  const [selectionVersion, setSelectionVersion] = useState(0);
  const [locating, setLocating] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [resultsOpen, setResultsOpen] = useState(true);
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [locateOnMap, setLocateOnMap] = useState<
    ((coordinates: [number, number]) => void) | null
  >(null);
  const [lastSearchedBounds, setLastSearchedBounds] = useState<PostSearchBounds | null>(null);

  const onBoundsChange = useCallback((nextBounds: PostSearchBounds) => {
    setBounds(nextBounds);
  }, []);

  const onMapReady = useCallback((
    locate: (coordinates: [number, number]) => void,
  ) => {
    setLocateOnMap(() => locate);
  }, []);

  const selectPost = useCallback((postId: number) => {
    setSelectedPostId(postId);
    setSelectionVersion((version) => version + 1);
  }, []);

  async function searchArea() {
    if (!bounds) return;
    setSearchPending(true);
    setError("");

    try {
      const request: PostSearchRequest = {
        bounds,
        limit: SEARCH_RESULT_LIMIT,
        ...(category ? { category } : {}),
      };
      const response = await apiRequest<PostSearchResponse>("/posts/search", {
        method: "POST",
        body: JSON.stringify(request),
      });
      setPosts(response.posts);
      setHasMore(response.has_more);
      setSelectedPostId(null);
      setLastSearchedBounds(bounds);
      setLastSearchedCategory(category);
      setSearched(true);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to search posts in this area.",
      );
    } finally {
      setSearchPending(false);
    }
  }

  function centerOnUser() {
    if (!navigator.geolocation) {
      setError("Location access is unavailable in this browser.");
      return;
    }

    setLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const coordinates: [number, number] = [
          position.coords.latitude,
          position.coords.longitude,
        ];
        setCenter(coordinates);
        setSelectedPostId(null);
        locateOnMap?.(coordinates);
        setLocating(false);
      },
      (locationError) => {
        setError(
          locationError.code === locationError.PERMISSION_DENIED
            ? "Allow location access in your browser to center the map on you."
            : "Unable to get your location. Check your device settings and try again.",
        );
        setLocating(false);
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 },
    );
  }

  const filtersChanged = Boolean(
    searched
    && (
      category !== lastSearchedCategory
      || (bounds && lastSearchedBounds && boundsHaveChanged(bounds, lastSearchedBounds))
    ),
  );

  return (
    <ProtectedPage>
      <div className={isFullscreen ? "explore-fullscreen active" : "explore-fullscreen"}>
        <section className="page-heading explore-heading">
          <div>
            <p className="eyebrow">Discover nearby</p>
            <h1>Explore posts</h1>
            <p className="muted">Move the map to an area and search for community posts there.</p>
          </div>
          <div className="explore-heading-actions">
            <button
              aria-pressed={isFullscreen}
              className="button button-secondary"
              onClick={() => setIsFullscreen(true)}
              type="button"
            >
              Full screen map
            </button>
            <Link className="button button-primary" href="/create-post">
              <span aria-hidden="true">＋</span> Share something
            </Link>
          </div>
        </section>

        <section className="explore-layout" aria-label="Explore posts by location">
          <div className="explore-map-panel">
            <div className="explore-map-toolbar">
              <label className="explore-category-filter">
                <span>Category</span>
                <select
                  aria-label="Filter posts by category"
                  onChange={(event) => {
                    const value = event.target.value;
                    setCategory(isPostCategory(value) ? value : "");
                  }}
                  value={category}
                >
                  <option value="">All categories</option>
                  {Object.entries(POST_CATEGORY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </label>
              <button
                className="button button-secondary"
                disabled={locating}
                onClick={centerOnUser}
                type="button"
              >
                {locating ? "Finding you…" : "Center on my location"}
              </button>
              <button
                className="button button-primary"
                disabled={!bounds || searchPending}
                onClick={() => void searchArea()}
                type="button"
              >
                {searchPending ? "Searching…" : "Search this area"}
              </button>
              {isFullscreen && (
                <button
                  className="button button-secondary explore-exit-fullscreen"
                  onClick={() => setIsFullscreen(false)}
                  type="button"
                >
                  Exit full screen
                </button>
              )}
            </div>
            <ExploreMap
              center={center}
              fullscreen={isFullscreen}
              onBoundsChange={onBoundsChange}
              onMapReady={onMapReady}
              onSelectPost={selectPost}
              posts={posts}
              selectionVersion={selectionVersion}
              selectedPostId={selectedPostId}
            />
            {filtersChanged && (
              <p className="explore-map-hint">Map or category changed. Search this area to refresh results.</p>
            )}
          </div>

          <aside
            className={[
              "explore-results",
              isFullscreen ? "explore-results-overlay" : "",
              isFullscreen && !resultsOpen ? "collapsed" : "",
            ].filter(Boolean).join(" ")}
            aria-label="Posts in this area"
          >
            <div className="explore-results-heading">
              <div>
                <h2>Posts in this area</h2>
                <p className="muted">
                  {searched
                    ? `${posts.length}${hasMore ? "+" : ""} results`
                    : "Search an area to see matching posts."}
                </p>
              </div>
              {isFullscreen && (
                <button
                  aria-expanded={resultsOpen}
                  aria-label={resultsOpen ? "Collapse post results" : "Expand post results"}
                  className="explore-results-toggle"
                  onClick={() => setResultsOpen((open) => !open)}
                  type="button"
                >
                  {resultsOpen ? "Hide" : "Results"}
                  <span aria-hidden="true">{resultsOpen ? "⌄" : "⌃"}</span>
                </button>
              )}
            </div>
            {(!isFullscreen || resultsOpen) && error && (
              <div className="explore-error" role="alert">
                <p>{error}</p>
                {searched && (
                  <button
                    className="button button-secondary"
                    disabled={searchPending}
                    onClick={() => void searchArea()}
                    type="button"
                  >
                    Try again
                  </button>
                )}
              </div>
            )}
            {(!isFullscreen || resultsOpen) && searchPending ? (
              <div className="state-card"><span className="spinner" /> Searching this area…</div>
            ) : isFullscreen && !resultsOpen ? null : !searched ? (
              <div className="explore-empty">
                <span aria-hidden="true">⌖</span>
                <p>Pan or zoom the map, then select <strong>Search this area</strong>.</p>
              </div>
            ) : posts.length === 0 ? (
              <div className="explore-empty">
                <span aria-hidden="true">⌖</span>
                <p>No posts found here yet. Try moving the map to another area.</p>
              </div>
            ) : (
              <>
                {hasMore && (
                  <p className="explore-map-hint">
                    Showing the first {SEARCH_RESULT_LIMIT} posts. Zoom in to narrow your search.
                  </p>
                )}
                <div className="explore-post-list">
                  {posts.map((post) => (
                    <article
                      className={post.id === selectedPostId
                        ? "explore-post-card selected"
                        : "explore-post-card"}
                      key={post.id}
                    >
                      <div className="post-badges">
                        <span className="category-pill">{POST_CATEGORY_LABELS[post.category]}</span>
                        <span className={`post-type-pill post-type-${post.post_type.toLowerCase()}`}>
                          {POST_TYPE_LABELS[post.post_type]}
                        </span>
                      </div>
                      <h3>{post.title}</h3>
                      <p className="explore-post-location">{post.location}</p>
                      <p className="explore-post-description">{post.description}</p>
                      <div className="explore-post-actions">
                        <button
                          className="text-link"
                          onClick={() => selectPost(post.id)}
                          type="button"
                        >
                          Show on map
                        </button>
                        <Link className="text-link" href={`/posts/${post.id}`}>
                          View post
                        </Link>
                      </div>
                    </article>
                  ))}
                </div>
              </>
            )}
          </aside>
        </section>
      </div>
    </ProtectedPage>
  );
}
