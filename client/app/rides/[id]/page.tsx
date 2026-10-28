"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import RideLayout, { RideRoute } from "../../../components/RideLayout";
import { apiRequest, type User } from "../../../lib/api";
import { localDateTime, localToISO, rideDate, rideError, rideMoney, type DriverProfile, type RideDetail, type RideOffer } from "../../../lib/rides";

export default function RideDetailPage() {
  const { id } = useParams<{ id: string }>();
  const requestId = Number(id);
  return <RideLayout>{Number.isInteger(requestId) && requestId > 0 ? <RideContent key={requestId} id={requestId} /> : <p className="form-error" role="alert">Invalid ride request.</p>}</RideLayout>;
}

function RideContent({ id }: { id: number }) {
  const [data, setData] = useState<RideDetail | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [chosen, setChosen] = useState<RideOffer | null>(null);
  const [cancelMode, setCancelMode] = useState(false);
  const [reason, setReason] = useState("");
  const [now, setNow] = useState(() => Date.now());
  const load = useCallback((signal?: AbortSignal) =>
    Promise.all([apiRequest<RideDetail>(`/rides/requests/${id}`, { signal }), apiRequest<User>("/users/me", { signal }), apiRequest<DriverProfile | null>("/rides/driver-profile", { signal })]), [id]);
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).then(([detail, me, driver]) => {
      if (!controller.signal.aborted) { setData(detail); setUser(me); setProfile(driver); setNow(Date.now()); }
    }).catch((err: unknown) => { if (!controller.signal.aborted) setError(rideError(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [load]);
  async function refresh() {
    setLoading(true); setError(""); setChosen(null); setCancelMode(false);
    try {
      const [detail, me, driver] = await load();
      setData(detail); setUser(me); setProfile(driver); setNow(Date.now());
    } catch (err) { setError(rideError(err)); }
    finally { setLoading(false); }
  }

  async function act(path: string, body?: object) {
    setBusy(true); setError(""); setSuccess("");
    try {
      const result = await apiRequest<RideDetail>(`/rides/requests/${id}/${path}`, { method: "POST", ...(body ? { body: JSON.stringify(body) } : {}) });
      setData(result); setChosen(null); setCancelMode(false); setNow(Date.now());
      setSuccess("Ride updated. No notifications were sent. Share any changes with the other member directly.");
    } catch (err) { setError(rideError(err)); }
    finally { setBusy(false); }
  }
  async function offer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try { await act("offers", { pickup_time: localToISO(String(form.get("time"))), amount: form.get("amount"), message: form.get("message") }); }
    catch (err) { setError(rideError(err)); }
  }
  const ride = data?.request;
  const booking = data?.booking;
  const owner = user?.id === ride?.rider_id;
  const ownOffer = data?.offers.find(item => item.driver_id === user?.id);
  const isOpen = ride?.status === "OPEN" && new Date(ride.pickup_end).getTime() > now;

  return <>
    <div className="ride-between"><Link className="button button-quiet" href="/rides/mine">Back to My rides</Link><button className="button button-secondary" disabled={busy || loading} onClick={() => void refresh()}>Refresh ride</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {success && <p className="ride-notice" role="status">{success}</p>}
    {loading ? <p role="status">Loading ride...</p> : data && ride && user && <>
      <section className="page-heading"><div><p className="eyebrow">{owner ? "Your ride request" : `${ride.rider.name}'s ride request`}</p><h1>{booking?.status === "CONFIRMED" ? "Your ride is confirmed." : "Let's get there together."}</h1><p className="muted">Check this page for updates. No notifications are sent.</p></div><span className="ride-badge">{booking?.status ?? ride.status}</span></section>
      <div className="ride-columns"><div>
        <div className="ride-card"><h2>The route</h2><RideRoute ride={ride} /><p><strong>{rideDate(ride.pickup_start, ride.timezone)} - {rideDate(ride.pickup_end, ride.timezone)}</strong></p><p className="muted">Pickup window in {ride.timezone}</p><div className="ride-meta"><span>{ride.passengers} passenger(s)</span><span>{ride.bags} bag(s)</span><span>Offers in {ride.currency}</span></div>{ride.notes && <p className="ride-message">{ride.notes}</p>}</div>
        {booking ? <div className="ride-card"><h2>{booking.status === "CONFIRMED" ? "The agreed plan" : `Booking ${booking.status.toLowerCase()}`}</h2><p><strong>Pickup: {rideDate(booking.pickup_time, ride.timezone)}</strong></p><p>{booking.vehicle} / {rideMoney(booking.amount, booking.currency)} agreed contribution</p><p className="field-hint">No payment collected by the platform. Booking details and phone numbers are snapshots taken at confirmation.</p>
          <div className="ride-notice"><h3>Contact each other directly</h3><p>Driver: {booking.driver.name} &middot; <a href={`tel:${booking.driver_phone}`}>{booking.driver_phone}</a></p><p>Rider: {booking.rider.name} &middot; <a href={`tel:${booking.rider_phone}`}>{booking.rider_phone}</a></p><p>Phone numbers are not verified.</p></div>
          {booking.cancellation_reason && <p className="form-error">Cancellation reason: {booking.cancellation_reason}</p>}
          {booking.status === "CONFIRMED" && <div className="form-actions"><button className="button button-secondary" disabled={busy} onClick={() => setCancelMode(true)}>Cancel booking</button>{owner && <button className="button button-secondary" disabled={busy || new Date(ride.pickup_end).getTime() > now} onClick={() => void act("booking/complete")}>Mark completed</button>}</div>}
          {owner && booking.status === "CONFIRMED" && <p className="field-hint">Mark completed after the pickup window ends and the ride has taken place.</p>}
          {booking.status === "CANCELLED" && <Link href="/rides/new" className="button button-primary">Create a new request</Link>}
        </div> : <>
          <h2>{owner ? "Driver offers" : "Your driver offer"}</h2>
          {data.offers.length === 0 && <div className="ride-card"><p className="muted">{owner ? "No offers yet. Check back or refresh to see new offers." : "You have not offered a ride yet."}</p></div>}
          {data.offers.map(item => <article className="ride-card" key={item.id}><div className="ride-between"><h3>{item.driver.name}</h3><span className="ride-badge">{item.status}</span></div><p>{item.vehicle} &middot; {item.passenger_capacity} passenger seats</p><p><strong>{rideDate(item.pickup_time, ride.timezone)}</strong></p><p><strong>{rideMoney(item.amount, ride.currency)}</strong> proposed contribution</p><p className="ride-message">{item.message}</p><p className="field-hint">Self-reported vehicle information. This driver is not verified or vetted by the platform.</p>
            {isOpen && item.status === "PENDING" && (owner ? <button className="button button-primary" disabled={busy} onClick={() => setChosen(item)}>Choose {item.driver.name}</button> : <button className="button button-secondary" disabled={busy} onClick={() => void act(`offers/${item.id}/withdraw`)}>Withdraw offer</button>)}
          </article>)}
          {chosen && <section className="ride-card ride-confirm" aria-label="Confirm chosen driver"><h2>Confirm {chosen.driver.name}?</h2><p>{rideDate(chosen.pickup_time, ride.timezone)} &middot; {rideMoney(chosen.amount, ride.currency)} contribution.</p><p>This closes all other offers and shares both contact numbers. No money is collected. Check the details before confirming.</p><div className="form-actions"><button className="button button-primary" disabled={busy} onClick={() => void act("confirm", { offer_id: chosen.id })}>Confirm ride</button><button className="button button-secondary" disabled={busy} onClick={() => setChosen(null)}>Keep comparing</button></div></section>}
          {!owner && isOpen && !profile && <Link className="button button-primary" href={`/rides/driver?request=${id}`}>Register as a driver to offer</Link>}
          {!owner && profile && isOpen && (!ownOffer || ownOffer.status === "WITHDRAWN" || ownOffer.status === "EXPIRED") && <form className="ride-card" onSubmit={offer}><h2>Offer a ride</h2><p className="field-hint">Your driver profile must have enough passenger seats. This is a commitment if the rider selects you.</p><label className="form-field"><span>Pickup time in your timezone ({Intl.DateTimeFormat().resolvedOptions().timeZone})</span><input key={ride.id} name="time" type="datetime-local" defaultValue={localDateTime(ride.pickup_start)} min={localDateTime(ride.pickup_start)} max={localDateTime(ride.pickup_end)} required /></label><label className="form-field"><span>Proposed contribution ({ride.currency})</span><input name="amount" type="number" min="0" max="9999.99" step="0.01" defaultValue="0.00" required /><span className="field-hint">Total contribution for this trip, not per passenger. Use 0 for a free ride. Arrange any payment outside the platform and comply with local rules.</span></label><label className="form-field"><span>Message to rider</span><textarea name="message" maxLength={500} rows={3} required placeholder="Confirm luggage space and any pickup details. Do not share phone numbers here." /></label><button className="button button-primary" disabled={busy}>Send offer</button></form>}
          {owner && isOpen && <button className="button button-secondary" disabled={busy} onClick={() => setCancelMode(true)}>Cancel request</button>}
        </>}
        {cancelMode && <form className="ride-card" onSubmit={e => { e.preventDefault(); void act(booking ? "booking/cancel" : "cancel", booking ? { reason } : undefined); }}><h2>Cancel this {booking ? "booking" : "request"}?</h2><p>No notifications are sent. If booked, contact the other member directly. This request will not reopen automatically.</p>{booking && <label className="form-field"><span>Reason for cancellation</span><textarea value={reason} onChange={e => setReason(e.target.value)} required maxLength={500} /></label>}<div className="form-actions"><button className="button button-primary" disabled={busy}>Confirm cancellation</button><button className="button button-secondary" type="button" disabled={busy} onClick={() => setCancelMode(false)}>Keep ride</button></div></form>}
      </div><aside><div className="ride-card ride-aside"><h2>Community, not a taxi queue.</h2><p className="muted">A request is not a booking. A driver offers, then the rider chooses.</p><p className="muted">Both exact locations are shared with all signed-in members. Contact numbers are private until confirmation.</p><p className="muted">No live tracking, platform payments, or notifications. Use your agreed contact numbers to coordinate.</p></div></aside></div>
    </>}
  </>;
}
