"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import RideLayout from "../../../../components/RideLayout";
import CarpoolCard from "../../../../components/CarpoolCard";
import { apiRequest, type User } from "../../../../lib/api";
import type { CarpoolDetail } from "../../../../lib/carpools";
import { refreshNotifications } from "../../../../lib/notifications";
import { rideDate, rideError, rideMoney } from "../../../../lib/rides";

export default function CarpoolDetailPage() {
  const { id } = useParams<{ id: string }>();
  const tripId = Number(id);
  return <RideLayout>{Number.isSafeInteger(tripId) && tripId > 0 ? <CarpoolContent key={tripId} id={tripId} /> : <p className="form-error" role="alert">Invalid carpool trip.</p>}</RideLayout>;
}

function CarpoolContent({ id }: { id: number }) {
  const [detail, setDetail] = useState<CarpoolDetail | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [cancelPath, setCancelPath] = useState<string | null>(null);
  const [includeReturn, setIncludeReturn] = useState(false);
  const [passengers, setPassengers] = useState(1);
  const load = useCallback((signal?: AbortSignal) => Promise.all([
    apiRequest<CarpoolDetail>(`/rides/carpools/trips/${id}`, { signal }),
    apiRequest<User>("/users/me", { signal }),
  ]), [id]);
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).then(([data, me]) => {
      if (!controller.signal.aborted) { setDetail(data); setUser(me); }
    }).catch((err: unknown) => { if (!controller.signal.aborted) setError(rideError(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [load]);
  async function refresh() {
    setLoading(true); setError(""); setSuccess(""); setCancelPath(null);
    try {
      const [data, me] = await load();
      setDetail(data); setUser(me); setIncludeReturn(false);
    } catch (err) { setError(rideError(err)); }
    finally { setLoading(false); }
  }
  async function act(path: string, body?: object, message = "Carpool updated. The other member has an in-app notification.") {
    setBusy(true); setError(""); setSuccess("");
    try {
      const data = await apiRequest<CarpoolDetail>(`/rides/carpools/trips/${id}/${path}`, {
        method: "POST", ...(body ? { body: JSON.stringify(body) } : {}),
      });
      setDetail(data); setCancelPath(null); setIncludeReturn(false); setSuccess(message); refreshNotifications();
    } catch (err) { setError(rideError(err)); }
    finally { setBusy(false); }
  }
  function request(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    void act("requests", {
      passengers, bags: Number(form.get("bags")), message: form.get("message"),
      rider_phone: form.get("phone"), include_return: includeReturn,
    }, includeReturn ? "Seat requests sent for both directions. Each needs its own driver approval; neither is reserved yet." : "Seat request sent. Your seats are not reserved until the driver approves.");
  }
  const trip = detail?.trip;
  const linked = detail?.linked_trip;
  const owner = user?.id === trip?.driver_id;
  const ownRequest = detail?.requests.find(item => item.rider.id === user?.id);
  const open = trip?.status === "OPEN" || trip?.status === "FULL";
  const canRequest = trip?.status === "OPEN" && !ownRequest && !owner;
  const canIncludeReturn = linked?.status === "OPEN" && !linked.my_request_status;
  const withdrawing = cancelPath !== null && cancelPath !== "cancel" &&
    detail?.requests.some(item => `requests/${item.id}/cancel` === cancelPath && item.status === "PENDING");

  return <>
    <div className="ride-between"><Link className="button button-quiet" href="/rides/mine">Back to My rides</Link><button className="button button-secondary" disabled={loading || busy} onClick={() => void refresh()}>Refresh carpool</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {success && <p className="ride-notice" role="status">{success}</p>}
    {loading ? <p role="status">Loading carpool...</p> : detail && trip && user && <>
      <section className="page-heading"><div><p className="eyebrow">{owner ? "Your planned trip" : `${trip.driver.name}'s planned trip`}</p><h1>{trip.pickup.city} to {trip.dropoff.city}</h1><p className="muted">{trip.is_return ? "Return direction" : "Outbound direction"} &middot; {trip.status}</p></div></section>
      <div className="ride-columns"><div>
        <CarpoolCard trip={trip} />
        <div className="ride-card"><h2>The plan</h2>
          <p>Meet between {rideDate(trip.pickup_start, trip.timezone)} and {rideDate(trip.pickup_end, trip.timezone)}.</p>
          <p className="field-hint">Times in {trip.timezone}. Coordinate your exact departure within this window after confirmation.</p>
          <p className="ride-message">{trip.notes || "No additional trip notes."}</p>
          <p>One pickup and one drop-off meeting point. No intermediate stops or door-to-door pickup are included.</p>
          <p className="ride-notice">Contribution: {rideMoney(trip.amount, trip.currency)} per passenger for this direction, arranged outside the app. No payment is collected here. Vehicle details are self-reported; drivers and phone numbers are not verified.</p>
          {trip.cancellation_reason && <p role="status">Driver cancellation reason: {trip.cancellation_reason}</p>}
          {owner && trip.can_cancel && <button className="button button-secondary" disabled={busy} onClick={() => setCancelPath("cancel")}>Cancel this direction</button>}
          {trip.status === "DEPARTED" && trip.can_cancel && <p className="field-hint">The departure window has started. New requests and approvals are closed, but cancellations are available until the window ends.</p>}
          {owner && <p className="field-hint">Published terms cannot be edited. Cancel and publish a new trip if plans change. Cancelling this direction does not cancel its linked trip.</p>}
        </div>
        {linked && <section><h2>{trip.is_return ? "Linked outbound trip" : "Linked return trip"}</h2><p className="field-hint">Separate seat availability and approval. A confirmed booking here does not confirm the other direction.</p><CarpoolCard trip={linked} /></section>}
      </div><div>
        <h2>{owner ? "Passenger requests" : "Your seat request"}</h2>
        {detail.requests.length === 0 && <p className="muted">{owner ? "No requests yet. Pending requests do not reserve seats." : "You have not requested this direction."}</p>}
        {detail.requests.map(item => <article className="ride-card" key={item.id}>
          <div className="ride-between"><h3>{item.rider.name}</h3><span className="ride-badge">{item.status}</span></div>
          <p>{item.passengers} passenger(s) &middot; {item.bags} bag(s)</p>
          <p><strong>{rideMoney(String(Number(trip.amount) * item.passengers), trip.currency)}</strong> total contribution for this direction.</p>
          {item.message && <p className="ride-message">{item.message}</p>}
          {item.status === "CONFIRMED" && <div className="ride-notice"><h3>This direction is confirmed</h3><p>Driver: {trip.driver.name} &middot; <a href={`tel:${item.driver_phone}`}>{item.driver_phone}</a></p><p>Passenger: {item.rider.name} &middot; <a href={`tel:${item.rider_phone}`}>{item.rider_phone}</a></p><p className="field-hint">Contact numbers were saved at confirmation. Coordinate the exact departure directly. Check the linked trip separately.</p></div>}
          {item.cancellation_reason && <p>Cancellation reason: {item.cancellation_reason}</p>}
          <div className="form-actions carpool-request-actions">
            {open && owner && item.status === "PENDING" && <><button className="button button-primary" disabled={busy || item.passengers > trip.available_seats} onClick={() => void act(`requests/${item.id}/accept`)}>Accept request</button><button className="button button-secondary" disabled={busy} onClick={() => void act(`requests/${item.id}/decline`)}>Decline request</button></>}
            {trip.can_cancel && (item.status === "CONFIRMED" || (!owner && item.status === "PENDING")) && <button className="button button-secondary" disabled={busy} onClick={() => setCancelPath(`requests/${item.id}/cancel`)}>{item.status === "PENDING" ? "Withdraw request" : "Cancel booking"}</button>}
          </div>
          {owner && item.status === "PENDING" && <p className="field-hint">Accepting confirms {item.passengers} {item.passengers === 1 ? "seat" : "seats"} and shares contact numbers. Declining closes this request without reserving seats.</p>}
        </article>)}
        {canRequest && <form className="form-card" onSubmit={request}>
          <fieldset className="carpool-fields" disabled={busy}><legend>Request seats</legend>
            <label className="form-field"><span>Passengers</span><input type="number" min={1} max={trip.available_seats} value={passengers} required onChange={event => setPassengers(Number(event.target.value))} /></label>
            <label className="form-field"><span>Total bags</span><input name="bags" type="number" min={0} max={passengers * Math.min(trip.bags_per_person, includeReturn && linked ? linked.bags_per_person : trip.bags_per_person)} defaultValue={0} required /></label>
            <label className="form-field"><span>Your phone number</span><input name="phone" type="tel" autoComplete="tel" pattern={"\\+[1-9][0-9]{7,14}"} placeholder="+14155550123" required /><span className="field-hint">Shared with the driver only after approval. The driver&apos;s contact is shared with you then too.</span></label>
            <label className="form-field"><span>Message (optional)</span><textarea name="message" rows={3} maxLength={500} placeholder="Luggage size or meeting point coordination. Do not include your phone here." /></label>
            {linked && <label className="ride-check"><input type="checkbox" checked={includeReturn} disabled={!canIncludeReturn || busy} onChange={event => setIncludeReturn(event.target.checked)} /><span>Also request the linked {trip.is_return ? "outbound" : "return"} direction{!canIncludeReturn && " (unavailable or already requested)"}</span></label>}
            <p><strong>{rideMoney(String(Number(trip.amount) * passengers), trip.currency)}</strong> for this direction.</p>
            {includeReturn && linked && <p><strong>{rideMoney(String(Number(linked.amount) * passengers), linked.currency)}</strong> for the linked direction. {linked.available_seats} seat(s) available.</p>}
            <p className="field-hint">Fixed contributions, paid outside the app. A request is not a booking. Each direction requires driver approval. Pending requests do not hold seats.</p>
            <button className="button button-primary" disabled={includeReturn && !!linked && passengers > linked.available_seats}>Request {includeReturn ? "both directions" : "seats"}</button>
          </fieldset>
        </form>}
        {ownRequest && ["CANCELLED", "DECLINED", "EXPIRED"].includes(ownRequest.status) && <p className="ride-notice">This seat request is closed. <Link className="text-link" href="/rides/carpools">Find another carpool</Link>.</p>}
        {cancelPath && <form className="form-card ride-confirm" onSubmit={event => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          void act(cancelPath, { reason: form.get("reason") });
        }}><h2>{withdrawing ? "Withdraw your request?" : "Confirm cancellation"}</h2>
          <p>{cancelPath === "cancel" ? "All pending requests and confirmed bookings for this direction will be cancelled and passengers notified in-app." : withdrawing ? "Your pending request for this direction will be withdrawn and the driver notified in-app. No seats have been reserved." : "Only this confirmed booking for this direction will be cancelled. Its seats will become available again and the other member will be notified in-app."} The linked direction is unchanged.</p>
          <label className="form-field"><span>Reason</span><textarea name="reason" minLength={1} maxLength={500} rows={3} required /></label>
          <div className="form-actions carpool-request-actions"><button className="button button-primary" disabled={busy}>{withdrawing ? "Confirm withdrawal" : "Confirm cancellation"}</button><button type="button" className="button button-secondary" disabled={busy} onClick={() => setCancelPath(null)}>{withdrawing ? "Keep request" : "Keep it"}</button></div>
        </form>}
      </div></div>
    </>}
  </>;
}
