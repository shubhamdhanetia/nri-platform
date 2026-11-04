import { useEffect, useState } from "react";
import { apiRequest } from "./api";

export const HOUSING_KINDS = { LISTING: "I have a place available", REQUEST: "I'm looking for a place", TOGETHER: "I want to find a place together" } as const;
export const ROOM_TYPES = { SHARED: "Shared room", PRIVATE: "Private room", ENTIRE: "Entire place", ANY: "Flexible / any space" } as const;
export const ARRANGEMENTS = { HOUSEHOLD: "Join an existing household", RENTAL: "New rental", SUBLET: "Sublet", TAKEOVER: "Lease takeover", ANY: "Flexible arrangement" } as const;
export const STAY_TYPES = { SHORT_TERM: "Short-term", LONG_TERM: "Long-term", FLEXIBLE: "Flexible" } as const;
export const PRICE_PERIODS = { MONTH: "Month", WEEK: "Week", NIGHT: "Night" } as const;
export const FURNISHINGS = { UNSPECIFIED: "Not specified", FURNISHED: "Furnished", PARTLY: "Partly furnished", UNFURNISHED: "Unfurnished" } as const;
export const BATHROOMS = { UNSPECIFIED: "Not specified", PRIVATE: "Private bathroom", SHARED: "Shared bathroom" } as const;
export const UTILITIES = { UNKNOWN: "Ask about utilities", INCLUDED: "Utilities included", EXTRA: "Utilities extra", PARTLY: "Some utilities included" } as const;
export const APPROVALS = { NOT_APPLICABLE: "Not applicable", REQUIRED: "Approval required", PENDING: "Approval pending", OBTAINED: "Approval obtained (owner-reported)" } as const;
export const KITCHENS = { UNSPECIFIED: "Not specified", VEGETARIAN: "Vegetarian cooking only", EGGS_ALLOWED: "Vegetarian cooking + eggs", UNRESTRICTED: "No food restrictions" } as const;
export const SMOKING = { UNSPECIFIED: "Not specified", NO: "No smoking / vaping", OUTSIDE: "Outside only", YES: "Smoking allowed" } as const;
export const ALCOHOL = { UNSPECIFIED: "Not specified", NO: "No alcohol", YES: "Alcohol allowed" } as const;
export const PETS = { UNSPECIFIED: "Not specified", NO: "No pets", ALLOWED: "Pets allowed", PRESENT: "Pets already in the home" } as const;
export const HOUSING_STATUSES = { ACTIVE: "Active", FILLED: "Filled / resolved", ARCHIVED: "Archived" } as const;
export type HousingKind = keyof typeof HOUSING_KINDS;
export type HousingStatus = keyof typeof HOUSING_STATUSES;
export type HousingMember = { id: string; name: string; picture: string | null };
export interface HousingDraft {
  title: string;
  description: string;
  kind: HousingKind;
  room_type: keyof typeof ROOM_TYPES;
  bedroom_count: number | null;
  bathroom_count: number | null;
  arrangement: keyof typeof ARRANGEMENTS;
  stay_type: keyof typeof STAY_TYPES;
  location_id: string;
  area: string;
  amount: string | number;
  currency: string;
  price_period: keyof typeof PRICE_PERIODS;
  available_from: string;
  available_until: string | null;
  minimum_stay_days: number;
  furnishing: keyof typeof FURNISHINGS;
  bathroom: keyof typeof BATHROOMS;
  occupants: number | null;
  available_spaces: number;
  utilities: keyof typeof UTILITIES;
  deposit: string | number | null;
  fees: string | number | null;
  approval: keyof typeof APPROVALS;
  kitchen: keyof typeof KITCHENS;
  smoking: keyof typeof SMOKING;
  alcohol: keyof typeof ALCOHOL;
  pets: keyof typeof PETS;
  parking: boolean | null;
  laundry: boolean | null;
  kitchen_access: boolean | null;
  work_from_home: boolean | null;
  household_notes: string;
  accessibility_notes: string;
  photo_urls: string[];
  is_private: boolean;
}
export interface HousingItem extends Omit<HousingDraft, "location_id"> {
  id: string;
  owner_id: string;
  status: HousingStatus;
  created_at: string;
  updated_at: string | null;
  expires_at: string;
  my_saved: boolean;
  owner: HousingMember;
  city: string;
  country_code: string;
  location_id: string | null;
  location: string | null;
  latitude: number | null;
  longitude: number | null;
  h3_cell_id: string | null;
  state: string | null;
  postal_code: string | null;
}

export function housingLayout(item: Pick<HousingItem, "kind" | "bedroom_count" | "bathroom_count">): string {
  const details: string[] = [];
  if (item.bedroom_count !== null) {
    details.push(item.kind === "LISTING"
      ? item.bedroom_count === 0 ? "Studio" : `${item.bedroom_count} ${item.bedroom_count === 1 ? "bedroom" : "bedrooms"}`
      : item.bedroom_count === 0 ? "Studio or larger wanted" : `At least ${item.bedroom_count} ${item.bedroom_count === 1 ? "bedroom" : "bedrooms"} wanted`);
  }
  if (item.bathroom_count !== null) {
    const count = Number(item.bathroom_count);
    details.push(item.kind === "LISTING"
      ? `${count} ${count === 1 ? "bathroom" : "bathrooms"}`
      : `At least ${count} ${count === 1 ? "bathroom" : "bathrooms"} wanted`);
  }
  return details.join(" · ");
}
export interface HousingCollection { items: HousingItem[]; has_more: boolean }
export interface HousingInquiry {
  id: string;
  housing_id: string;
  housing_title: string;
  sender: HousingMember;
  owner: HousingMember;
  created_at: string;
  messages: { id: string; sender_id: string; content: string; created_at: string }[];
}
export function housingError(error: unknown): string {
  return error instanceof Error ? error.message : "Unable to complete this Housing request.";
}
export function housingMoney(amount: string | number, currency: string): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(amount));
}
export function housingDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(`${value.slice(0, 10)}T12:00:00`));
}
export function housingExpired(item: HousingItem): boolean {
  return (item.available_until !== null && item.available_until < new Date().toISOString().slice(0, 10))
    || new Date(item.expires_at.endsWith("Z") || /[+-]\d\d:\d\d$/.test(item.expires_at) ? item.expires_at : `${item.expires_at}Z`).getTime() <= Date.now();
}
export function useHousingResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const [loadedPath, setLoadedPath] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    apiRequest<T>(path, { signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) { setData(result); setError(""); }
    }).catch((failure: unknown) => {
      if (!controller.signal.aborted) setError(housingError(failure));
    }).finally(() => { if (!controller.signal.aborted) { setLoading(false); setLoadedPath(path); } });
    return () => controller.abort();
  }, [path, revision]);
  function reload() { setError(""); setLoading(true); setRevision(value => value + 1); }
  return { data, setData, error: loadedPath === path ? error : "", loading: loading || loadedPath !== path, reload };
}
