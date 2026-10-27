"use client";

import { useEffect, useId, useRef, useState } from "react";
import {
  apiRequest,
  type LocationDetailsResponse,
  type LocationSearchResult,
  type LocationSearchResponse,
} from "../lib/api";

type Coordinates = [number, number];

function suggestionLabel(location: LocationSearchResult): string {
  return [location.addressLine1, location.addressLine2]
    .filter(Boolean)
    .join(", ");
}

export default function ExploreLocationSearch({
  center,
  onLocationSelected,
  label = "Find location",
  onSelectionChange,
  onQueryChange,
}: {
  center: Coordinates;
  onLocationSelected?: (coordinates: Coordinates) => void;
  label?: string;
  onSelectionChange?: (selection: { locationId: string; location: string } | null) => void;
  onQueryChange?: (query: string) => void;
}) {
  const inputId = useId();
  const suggestionsId = `${inputId}-suggestions`;
  const [query, setQuery] = useState("");
  const [latitude, longitude] = center;
  const [suggestions, setSuggestions] = useState<LocationSearchResult[]>([]);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [selectedPlace, setSelectedPlace] = useState<LocationSearchResult | null>(null);
  const [hasSelection, setHasSelection] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState("");
  const detailsRequestVersion = useRef(0);

  useEffect(() => {
    const normalizedQuery = query.trim();
    if (normalizedQuery.length < 2 || hasSelection || selectedPlace) {
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setSearching(true);
      setSearchError("");
      void apiRequest<LocationSearchResponse>("/locations/search", {
        method: "POST",
        body: JSON.stringify({
          latitude,
          longitude,
          query: normalizedQuery,
        }),
        signal: controller.signal,
      })
        .then((response) => {
          if (controller.signal.aborted) return;
          setSuggestions(response.data.filter((location) => location.id));
          setSearchedQuery(normalizedQuery);
        })
        .catch((requestError: unknown) => {
          if (!controller.signal.aborted) {
            setSearchError(
              requestError instanceof Error
                ? requestError.message
                : "Unable to search locations.",
            );
            setSuggestions([]);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setSearching(false);
          }
        });
    }, 500);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [hasSelection, query, latitude, longitude, selectedPlace]);

  async function selectLocation(location: LocationSearchResult) {
    if (!location.id) {
      setDetailsError("This location suggestion is missing its provider ID.");
      return;
    }

    const requestVersion = ++detailsRequestVersion.current;
    setSelectedPlace(location);
    setSuggestions([]);
    setDetailsError("");
    setLoadingDetails(true);

    try {
      const response = await apiRequest<LocationDetailsResponse>("/locations/details", {
        method: "POST",
        body: JSON.stringify({ id: location.id }),
      });
      if (requestVersion !== detailsRequestVersion.current) return;
      setQuery(response.data.fullAddress);
      setHasSelection(true);
      onLocationSelected?.([response.data.lat, response.data.long]);
      onSelectionChange?.({ locationId: response.data.id, location: response.data.fullAddress });
    } catch (requestError) {
      if (requestVersion !== detailsRequestVersion.current) return;
      setDetailsError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load this location's details.",
      );
    } finally {
      if (requestVersion === detailsRequestVersion.current) {
        setLoadingDetails(false);
      }
    }
  }

  function handleChange(value: string) {
    detailsRequestVersion.current += 1;
    setQuery(value);
    setSuggestions([]);
    setSearching(false);
    setSearchedQuery("");
    setSearchError("");
    setDetailsError("");
    setLoadingDetails(false);
    setSelectedPlace(null);
    setHasSelection(false);
    onQueryChange?.(value);
    onSelectionChange?.(null);
  }

  return (
    <div className="explore-location-search">
      <label htmlFor={inputId}>{label}</label>
      <input
        aria-autocomplete="list"
        aria-controls={suggestionsId}
        aria-expanded={suggestions.length > 0}
        autoComplete="off"
        id={inputId}
        onChange={(event) => handleChange(event.target.value)}
        placeholder="Search a city or area"
        role="combobox"
        value={query}
      />
      {suggestions.length > 0 && (
        <ul
          className="location-suggestions explore-location-suggestions"
          id={suggestionsId}
          role="listbox"
        >
          {suggestions.map((location) => (
            <li key={location.id} role="presentation">
              <button
                aria-selected="false"
                className="location-suggestion"
                onClick={() => void selectLocation(location)}
                role="option"
                type="button"
              >
                <span aria-hidden="true">⌖</span>
                {suggestionLabel(location)}
              </button>
            </li>
          ))}
        </ul>
      )}
      {searching && <p className="location-helper">Searching locations…</p>}
      {loadingDetails && <p className="location-helper">Loading selected location…</p>}
      {searchError && <p className="location-helper location-error" role="alert">{searchError}</p>}
      {detailsError && (
        <div className="location-helper location-error">
          <span role="alert">{detailsError}</span>
          {selectedPlace && (
            <button
              className="location-retry-button"
              onClick={() => void selectLocation(selectedPlace)}
              type="button"
            >
              Retry
            </button>
          )}
        </div>
      )}
      {query.trim().length >= 2
        && searchedQuery === query.trim()
        && !suggestions.length
        && !searching
        && !searchError
        && !hasSelection && (
          <p className="location-helper">No locations found. Try a different search.</p>
        )}
    </div>
  );
}
