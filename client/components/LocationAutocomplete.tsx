"use client";

import { useEffect, useRef, useState } from "react";
import {
  apiRequest,
  type LocationDetailsResponse,
  type LocationSearchResult,
  type LocationSearchResponse,
} from "../lib/api";

interface Coordinates {
  latitude: number;
  longitude: number;
}

function suggestionLabel(location: LocationSearchResult): string {
  return [location.addressLine1, location.addressLine2]
    .filter(Boolean)
    .join(", ");
}

export default function LocationAutocomplete({
  onAddressSelected,
  initialSelection,
}: {
  onAddressSelected: (selection: { locationId: string; location: string } | null) => void;
  initialSelection?: { locationId: string; location: string };
}) {
  const [value, setValue] = useState(initialSelection?.location ?? "");
  const [hasSelection, setHasSelection] = useState(Boolean(initialSelection));
  const [coordinates, setCoordinates] = useState<Coordinates | null>(null);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState("");
  const [suggestions, setSuggestions] = useState<LocationSearchResult[]>([]);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [selectedPlace, setSelectedPlace] = useState<LocationSearchResult | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState("");
  const locationRequestInProgress = useRef(false);

  useEffect(() => {
    if (!coordinates || selectedPlace || hasSelection || !value.trim()) {
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setSearching(true);
      setSearchError("");
      void apiRequest<LocationSearchResponse>("/locations/search", {
        method: "POST",
        body: JSON.stringify({
          ...coordinates,
          query: value.trim(),
        }),
        signal: controller.signal,
      })
        .then((response) => {
          setSuggestions(response.data.filter((item) => item.id));
          setSearchedQuery(value.trim());
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
    }, 1000);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [coordinates, hasSelection, selectedPlace, value]);

  function requestBrowserLocation() {
    if (
      coordinates
      || locationRequestInProgress.current
    ) {
      return;
    }
    if (!navigator.geolocation) {
      setLocationError("Location access is unavailable in this browser.");
      return;
    }

    locationRequestInProgress.current = true;
    setLocating(true);
    setLocationError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoordinates({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
        setLocating(false);
        locationRequestInProgress.current = false;
      },
      (error) => {
        setLocationError(
          error.code === error.PERMISSION_DENIED
            ? "Allow location access in your browser to search nearby places."
            : "Unable to get your location. Check your device settings and try again.",
        );
        setLocating(false);
        locationRequestInProgress.current = false;
      },
      {
        enableHighAccuracy: false,
        maximumAge: 300000,
        timeout: 10000,
      },
    );
  }

  async function loadPlaceDetails(location: LocationSearchResult) {
    if (!location.id) {
      setDetailsError("This suggestion does not include a location ID.");
      return;
    }

    setSelectedPlace(location);
    setSuggestions([]);
    setSearching(false);
    setLoadingDetails(true);
    setDetailsError("");
    onAddressSelected(null);

    try {
      const response = await apiRequest<LocationDetailsResponse>("/locations/details", {
        method: "POST",
        body: JSON.stringify({
          id: location.id,
        }),
      });
      setValue(response.data.fullAddress);
      setHasSelection(true);
      onAddressSelected({
        locationId: response.data.id,
        location: response.data.fullAddress,
      });
    } catch (requestError) {
      setDetailsError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load this location's details.",
      );
    } finally {
      setLoadingDetails(false);
    }
  }

  function handleChange(nextValue: string) {
    setValue(nextValue);
    setSuggestions([]);
    setSearching(false);
    setSearchedQuery("");
    setSearchError("");
    setDetailsError("");
    setSelectedPlace(null);
    setHasSelection(false);
    onAddressSelected(null);
    requestBrowserLocation();
  }

  return (
    <div className="form-field location-autocomplete">
      <label className="location-autocomplete-label" htmlFor="post-location">Location</label>
      <input
        aria-autocomplete="list"
        aria-controls="post-location-suggestions"
        aria-expanded={suggestions.length > 0}
        autoComplete="off"
        id="post-location"
        onChange={(event) => handleChange(event.target.value)}
        onFocus={requestBrowserLocation}
        placeholder="Start typing an address or place"
        role="combobox"
        value={value}
      />
      {locating && <p className="location-helper">Getting your location…</p>}
      {locationError && (
        <div className="location-helper location-error">
          <span role="alert">{locationError}</span>
          <button
            className="location-retry-button"
            onClick={requestBrowserLocation}
            type="button"
          >
            Retry
          </button>
        </div>
      )}
      {searching && <p className="location-helper">Searching locations…</p>}
      {searchError && <p className="location-helper location-error" role="alert">{searchError}</p>}
      {loadingDetails && <p className="location-helper">Loading selected location…</p>}
      {detailsError && (
        <div className="location-helper location-error">
          <span role="alert">{detailsError}</span>
          {selectedPlace && (
            <button
              className="location-retry-button"
              onClick={() => void loadPlaceDetails(selectedPlace)}
              type="button"
            >
              Retry
            </button>
          )}
        </div>
      )}
      {suggestions.length > 0 && (
        <ul
          className="location-suggestions"
          id="post-location-suggestions"
          role="listbox"
        >
          {suggestions.map((location) => (
            <li key={location.id} role="presentation">
              <button
                aria-selected="false"
                className="location-suggestion"
                onClick={() => void loadPlaceDetails(location)}
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
      {!coordinates && !locating && !locationError && (
        <p className="location-helper">Allow location access to find nearby matches.</p>
      )}
      {coordinates && searchedQuery === value.trim() && !suggestions.length && !searching && !searchError && !selectedPlace && value.trim() && (
        <p className="location-helper">No locations found. Try a different search.</p>
      )}
    </div>
  );
}
