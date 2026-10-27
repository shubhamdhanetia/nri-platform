"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import RideLayout, { useRideTimezone } from "../../../components/RideLayout";
import LocationAutocomplete from "../../../components/LocationAutocomplete";
import { apiRequest } from "../../../lib/api";
import { localToISO, RIDE_CURRENCIES, rideError, type LocationSelection, type RideRequest } from "../../../lib/rides";

export default function NewRidePage() {
  const router = useRouter();
  const [pickup, setPickup] = useState<LocationSelection | null>(null);
  const [dropoff, setDropoff] = useState<LocationSelection | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const timezone = useRideTimezone();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (!pickup || !dropoff) { setError("Select both pickup and drop-off from the location suggestions."); return; }
    const data = new FormData(event.currentTarget);
    setBusy(true);
    try {
      const ride = await apiRequest<RideRequest>("/rides/requests", { method: "POST", body: JSON.stringify({
        pickup_location_id: pickup.locationId, dropoff_location_id: dropoff.locationId,
        pickup_start: localToISO(String(data.get("start"))), pickup_end: localToISO(String(data.get("end"))),
        timezone, passengers: Number(data.get("passengers")), bags: Number(data.get("bags")),
        rider_phone: data.get("phone"), notes: data.get("notes"), currency: data.get("currency"),
        exact_location_consent: data.get("consent") === "on",
      }) });
      router.push(`/rides/${ride.id}`);
    } catch (err) { setError(rideError(err)); } finally { setBusy(false); }
  }
  return <RideLayout>
    <section className="page-heading"><div><p className="eyebrow">For the plans ahead</p><h1>Where do you need to go?</h1><p className="muted">Drivers offer to help. You choose one driver to confirm your ride.</p></div></section>
    <form className="form-card" onSubmit={submit}>
      <h2>Your route</h2><LocationAutocomplete label="Exact pickup location" onAddressSelected={setPickup} /><LocationAutocomplete label="Exact drop-off location" onAddressSelected={setDropoff} />
      <p className="ride-notice">Both full addresses will be visible to signed-in members with a driver profile, even before you choose a driver. Select a public meeting point if you prefer not to share your home address.</p>
      <h2>Your pickup window</h2><p className="field-hint">Enter times in your browser&apos;s timezone: {timezone}. The window may be up to two hours. Drivers will see this timezone.</p>
      <div className="form-row"><label className="form-field"><span>Earliest pickup</span><input name="start" type="datetime-local" required /></label><label className="form-field"><span>Latest pickup</span><input name="end" type="datetime-local" required /></label></div>
      <div className="form-row"><label className="form-field"><span>Passengers</span><input name="passengers" type="number" min={1} max={8} defaultValue={1} required /></label><label className="form-field"><span>Bags</span><input name="bags" type="number" min={0} max={10} defaultValue={0} required /></label></div>
      <label className="form-field"><span>Currency for cost-sharing offers</span><select name="currency" defaultValue="USD">{RIDE_CURRENCIES.map(currency => <option key={currency}>{currency}</option>)}</select><span className="field-hint">Drivers propose an amount in this currency. Review before confirming. Payment arrangements are outside the platform.</span></label>
      <label className="form-field"><span>Your contact phone number</span><input name="phone" type="tel" autoComplete="tel" pattern={"\\+[1-9][0-9]{7,14}"} placeholder="+14155550123" required /><span className="field-hint">Only shared with your chosen driver after confirmation. Not verified.</span></label>
      <label className="form-field"><span>Notes (optional)</span><textarea name="notes" maxLength={500} rows={3} placeholder="Luggage needs, terminal, or pickup flexibility. Do not include phone numbers here." /></label>
      <label className="ride-check"><input type="checkbox" name="consent" required /><span>I agree to share these exact locations with members who have a driver profile. I understand this is a request, not a guaranteed booking, and community drivers are not vetted by the platform.</span></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions"><button className="button button-primary" disabled={busy}>{busy ? "Publishing..." : "Publish request"}</button><Link className="button button-secondary" href="/rides">Cancel</Link></div>
    </form>
  </RideLayout>;
}
