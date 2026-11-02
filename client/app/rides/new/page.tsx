"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CalendarDays, Clock3, Globe2 } from "lucide-react";
import RideLayout, { useRideTimezone } from "../../../components/RideLayout";
import LocationAutocomplete from "../../../components/LocationAutocomplete";
import { apiRequest } from "../../../lib/api";
import { localDateTime, localToISO, RIDE_CURRENCIES, rideError, type LocationSelection, type RideRequest } from "../../../lib/rides";

function localDateTimeInput(date: string, time: string, nextDay = false) {
  if (!nextDay) return `${date}T${time}`;
  const followingDate = new Date(`${date}T12:00:00`);
  followingDate.setDate(followingDate.getDate() + 1);
  return `${localDateTime(followingDate.toISOString()).slice(0, 10)}T${time}`;
}

export default function NewRidePage() {
  const router = useRouter();
  const [pickup, setPickup] = useState<LocationSelection | null>(null);
  const [dropoff, setDropoff] = useState<LocationSelection | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const timezone = useRideTimezone();
  const [pickupDate, setPickupDate] = useState("");
  const [earliestTime, setEarliestTime] = useState("");
  const [latestTime, setLatestTime] = useState("");
  const [currency, setCurrency] = useState<(typeof RIDE_CURRENCIES)[number]>("USD");
  const today = localDateTime(new Date().toISOString()).slice(0, 10);
  const timezoneLabel = (() => {
    try {
      const sampleDate = pickupDate ? new Date(`${pickupDate}T12:00:00`) : new Date();
      return new Intl.DateTimeFormat(undefined, { timeZone: timezone, timeZoneName: "long" })
        .formatToParts(sampleDate).find(part => part.type === "timeZoneName")?.value ?? timezone;
    } catch {
      return timezone;
    }
  })();
  const pickupWindowSummary = (() => {
    if (!pickupDate || !earliestTime || !latestTime) return "Choose a date and time range to see a summary.";
    try {
      const start = new Date(localToISO(localDateTimeInput(pickupDate, earliestTime)));
      const end = new Date(localToISO(localDateTimeInput(pickupDate, latestTime, latestTime < earliestTime)));
      const dateFormatter = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric", timeZone: timezone });
      const timeFormatter = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit", timeZone: timezone });
      const startDate = dateFormatter.format(start);
      const endDate = dateFormatter.format(end);
      return `${startDate}${startDate === endDate ? "" : ` – ${endDate}`}, ${timeFormatter.format(start)} – ${timeFormatter.format(end)} ${timezoneLabel}`;
    } catch {
      return "That time falls during a clock change. Choose a different time.";
    }
  })();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (!pickup || !dropoff) { setError("Select both pickup and drop-off from the location suggestions."); return; }
    const data = new FormData(event.currentTarget);
    const date = String(data.get("pickup-date"));
    const startTime = String(data.get("start-time"));
    const endTime = String(data.get("end-time"));
    const startLocal = localDateTimeInput(date, startTime);
    const endLocal = localDateTimeInput(date, endTime, endTime < startTime);
    let startISO: string;
    let endISO: string;
    try {
      startISO = localToISO(startLocal);
      endISO = localToISO(endLocal);
    } catch (timeError) {
      setError(rideError(timeError));
      return;
    }
    const startDateTime = new Date(startISO);
    const endDateTime = new Date(endISO);
    const windowLength = endDateTime.getTime() - startDateTime.getTime();
    if (!date || !startTime || !endTime || startDateTime.getTime() <= Date.now() || !Number.isFinite(windowLength) || windowLength <= 0 || windowLength > 2 * 60 * 60 * 1000) {
      setError("Choose a future pickup window no longer than two hours. If it continues after midnight, enter an end time earlier than the start time.");
      return;
    }
    setBusy(true);
    try {
      const ride = await apiRequest<RideRequest>("/rides/requests", { method: "POST", body: JSON.stringify({
        pickup_location_id: pickup.locationId, dropoff_location_id: dropoff.locationId,
        pickup_start: startISO, pickup_end: endISO,
        timezone, passengers: Number(data.get("passengers")), bags: Number(data.get("bags")),
        rider_phone: data.get("phone"), notes: data.get("notes"), currency: data.get("currency"),
        preferred_amount: data.get("preferred_amount") ? String(data.get("preferred_amount")) : null,
        exact_location_consent: data.get("consent") === "on",
      }) });
      router.push(`/rides/${ride.id}`);
    } catch (err) { setError(rideError(err)); } finally { setBusy(false); }
  }
  return <RideLayout>
    <section className="page-heading"><div><p className="eyebrow">For the plans ahead</p><h1>Where do you need to go?</h1><p className="muted">Drivers offer to help. You choose one driver to confirm your ride.</p></div></section>
    <form className="form-card" onSubmit={submit}>
      <h2>Your route</h2><LocationAutocomplete label="Exact pickup location" onAddressSelected={setPickup} /><LocationAutocomplete label="Exact drop-off location" onAddressSelected={setDropoff} />
      <p className="ride-notice">Both full addresses will be visible to all signed-in members, even before you choose a driver. Select a public meeting point if you prefer not to share your home address.</p>
      <fieldset className="ride-pickup-window">
        <legend><Clock3 size={18} aria-hidden="true" /> Pickup time window</legend>
        <p className="ride-window-description">Choose one date and the earliest and latest times that work. Your driver can arrive anytime in between, for up to two hours.</p>
        <div className="ride-timezone-note"><Globe2 size={16} aria-hidden="true" /><span>Times use <strong>{timezoneLabel}</strong> from your device settings.</span></div>
        <div className="form-field ride-date-field"><label htmlFor="pickup-date"><CalendarDays size={15} aria-hidden="true" /> Date</label><input id="pickup-date" name="pickup-date" type="date" min={today} value={pickupDate} onChange={event => setPickupDate(event.target.value)} required /></div>
        <div className="form-row ride-time-fields">
          <label className="form-field" htmlFor="start-time"><span>From <small>Earliest pickup</small></span><input id="start-time" name="start-time" type="time" step={300} value={earliestTime} onChange={event => setEarliestTime(event.target.value)} required /></label>
          <label className="form-field" htmlFor="end-time"><span>Until <small>Latest pickup</small></span><input id="end-time" name="end-time" type="time" step={300} value={latestTime} onChange={event => setLatestTime(event.target.value)} required /></label>
        </div>
        <p className={`ride-window-summary${pickupDate && earliestTime && latestTime ? " is-complete" : ""}`} aria-live="polite">{pickupWindowSummary}</p>
      </fieldset>
      <div className="form-row"><label className="form-field"><span>Passengers</span><input name="passengers" type="number" min={1} max={8} defaultValue={1} required /></label><label className="form-field"><span>Bags</span><input name="bags" type="number" min={0} max={10} defaultValue={0} required /></label></div>
      <label className="form-field"><span>Currency for cost-sharing offers</span><select name="currency" value={currency} onChange={event => setCurrency(event.target.value as (typeof RIDE_CURRENCIES)[number])}>{RIDE_CURRENCIES.map(option => <option key={option}>{option}</option>)}</select><span className="field-hint">Drivers propose an amount in this currency. Review before confirming. Payment arrangements are outside the platform.</span></label>
      <label className="form-field"><span>Preferred total contribution ({currency}) <small>Optional</small></span><input name="preferred_amount" type="number" min="0" max="9999.99" step="0.01" placeholder="Leave blank if flexible" /><span className="field-hint">Your preference for the whole ride, not per passenger. Drivers may propose a different amount. No payment is collected by the platform.</span></label>
      <label className="form-field"><span>Your contact phone number</span><input name="phone" type="tel" autoComplete="tel" pattern={"\\+[1-9][0-9]{7,14}"} placeholder="+14155550123" required /><span className="field-hint">Only shared with your chosen driver after confirmation. Not verified.</span></label>
      <label className="form-field"><span>Notes (optional)</span><textarea name="notes" maxLength={500} rows={3} placeholder="Luggage needs, terminal, or pickup flexibility. Do not include phone numbers here." /></label>
      <label className="ride-check"><input type="checkbox" name="consent" required /><span>I agree to share these exact locations with all signed-in members. I understand this is a request, not a guaranteed booking, and community drivers are not vetted by the platform.</span></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions"><button className="button button-primary" disabled={busy}>{busy ? "Publishing..." : "Publish request"}</button><Link className="button button-secondary" href="/rides">Cancel</Link></div>
    </form>
  </RideLayout>;
}
