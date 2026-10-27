import type { PostAuthor } from "./api";

export type RideStatus = "OPEN" | "CONFIRMED" | "EXPIRED" | "CANCELLED";
export const RIDE_CURRENCIES = ["USD", "CAD", "INR", "GBP", "EUR", "AUD"] as const;
export interface RideLocation {
  location_id: string;
  location: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
}
export interface DriverProfile {
  user_id: number;
  vehicle: string;
  passenger_capacity: number;
  phone: string;
}
export interface RideRequest {
  id: number;
  rider_id: number;
  rider: PostAuthor;
  pickup: RideLocation;
  dropoff: RideLocation;
  pickup_start: string;
  pickup_end: string;
  timezone: string;
  passengers: number;
  bags: number;
  notes: string;
  currency: string;
  status: RideStatus;
  booking_status: RideBooking["status"] | null;
  my_offer_status: RideOffer["status"] | null;
  created_at: string;
}
export interface RideOffer {
  id: number;
  request_id: number;
  driver_id: number;
  driver: PostAuthor;
  pickup_time: string;
  amount: string;
  message: string;
  vehicle: string;
  passenger_capacity: number;
  status: "PENDING" | "ACCEPTED" | "WITHDRAWN" | "NOT_SELECTED" | "EXPIRED";
}
export interface RideBooking {
  id: number;
  offer_id: number;
  rider_id: number;
  driver_id: number;
  rider: PostAuthor;
  driver: PostAuthor;
  driver_phone: string;
  rider_phone: string;
  vehicle: string;
  pickup_time: string;
  amount: string;
  currency: string;
  status: "CONFIRMED" | "COMPLETED" | "CANCELLED";
  cancellation_reason: string | null;
}
export interface RideDetail {
  request: RideRequest;
  offers: RideOffer[];
  booking: RideBooking | null;
}
export type LocationSelection = { locationId: string; location: string };

export function rideDate(value: string, timeZone: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short", timeZone }).format(new Date(value));
}
export function rideMoney(value: string, currency: string) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(Number(value));
}
export function localDateTime(value: string) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}
export function localToISO(value: string) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime()) || localDateTime(date.toISOString()) !== value) {
    throw new Error("This local time does not exist. Choose another time (check daylight saving changes).");
  }
  return date.toISOString();
}
export function rideError(error: unknown) {
  return error instanceof Error ? error.message : "Unable to update rides. Please try again.";
}
