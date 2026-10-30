import Link from "next/link";
import type { CarpoolTrip } from "../lib/carpools";
import { rideDate, rideMoney } from "../lib/rides";

export default function CarpoolCard({ trip, role }: { trip: CarpoolTrip; role?: "Driver" | "Passenger" }) {
  return <article className="ride-card">
    <div className="ride-between"><strong><Link className="member-profile-link" href={`/profile/${trip.driver.id}`}>{trip.driver.name}</Link></strong><span className="ride-badge">{trip.status}</span></div>
    {role && <p className="field-hint">Your role: <span className="ride-badge">{role}</span></p>}
    <div className="ride-route"><div><span>Meeting point</span><strong>{trip.pickup.location}</strong></div><div><span>Drop-off point</span><strong>{trip.dropoff.location}</strong></div></div>
    <p><strong>{rideDate(trip.pickup_start, trip.timezone)}</strong></p>
    <p className="field-hint">Departure window ends {rideDate(trip.pickup_end, trip.timezone)}. Times in {trip.timezone}.</p>
    <div className="ride-meta"><span>{trip.available_seats} of {trip.seats} seats available</span><span>{rideMoney(trip.amount, trip.currency)} / person</span></div>
    <p>{trip.vehicle} &middot; Up to {trip.bags_per_person} bag(s) per person</p>
    {trip.linked_trip_id && <p className="field-hint">{trip.is_return ? "Return direction" : "Return trip available"} &middot; Each direction is booked separately.</p>}
    {trip.my_request_status && <p className="ride-notice">Your seat request: {trip.my_request_status}</p>}
    <Link className="button button-secondary" href={`/rides/carpools/${trip.id}`}>View carpool</Link>
  </article>;
}
