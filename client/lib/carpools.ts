import type { PostAuthor } from "./api";
import type { RideLocation } from "./rides";

export type SeatStatus = "PENDING" | "CONFIRMED" | "DECLINED" | "CANCELLED" | "EXPIRED";

export interface CarpoolTrip {
  id: number;
  driver_id: number;
  driver: PostAuthor;
  linked_trip_id: number | null;
  is_return: boolean;
  pickup: RideLocation;
  dropoff: RideLocation;
  pickup_start: string;
  pickup_end: string;
  timezone: string;
  seats: number;
  available_seats: number;
  bags_per_person: number;
  amount: string;
  currency: string;
  vehicle: string;
  notes: string;
  status: "OPEN" | "FULL" | "DEPARTED" | "CANCELLED";
  can_cancel: boolean;
  cancellation_reason: string | null;
  my_request_status: SeatStatus | null;
}

export interface CarpoolSeatRequest {
  id: number;
  trip_id: number;
  rider: PostAuthor;
  passengers: number;
  bags: number;
  message: string;
  status: SeatStatus;
  rider_phone: string | null;
  driver_phone: string | null;
  cancellation_reason: string | null;
}

export interface CarpoolDetail {
  trip: CarpoolTrip;
  linked_trip: CarpoolTrip | null;
  requests: CarpoolSeatRequest[];
}

export interface CarpoolPage {
  trips: CarpoolTrip[];
  has_more: boolean;
}

export interface CarpoolSearchFilters {
  dropoff_location_id?: string;
  departure_date?: string;
  passengers: number;
  radius_km?: number;
}
