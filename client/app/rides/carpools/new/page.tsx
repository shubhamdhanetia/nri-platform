"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import RideLayout, { useRideTimezone } from "../../../../components/RideLayout";
import LocationAutocomplete from "../../../../components/LocationAutocomplete";
import { apiRequest } from "../../../../lib/api";
import type { CarpoolDetail } from "../../../../lib/carpools";
import { localToISO, RIDE_CURRENCIES, rideError, type LocationSelection } from "../../../../lib/rides";

export default function NewCarpoolPage() {
  const router = useRouter();
  const timezone = useRideTimezone();
  const [pickup, setPickup] = useState<LocationSelection | null>(null);
  const [dropoff, setDropoff] = useState<LocationSelection | null>(null);
  const [returnPickup, setReturnPickup] = useState<LocationSelection | null>(null);
  const [returnDropoff, setReturnDropoff] = useState<LocationSelection | null>(null);
  const [returning, setReturning] = useState(false);
  const [customReturn, setCustomReturn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (!pickup || !dropoff || (returning && customReturn && (!returnPickup || !returnDropoff))) {
      setError("Select each meeting point from the location suggestions."); return;
    }
    const returnFrom = customReturn ? returnPickup : dropoff;
    const returnTo = customReturn ? returnDropoff : pickup;
    if (returning && (!returnFrom || !returnTo)) {
      setError("Select both return meeting points."); return;
    }
    const form = new FormData(event.currentTarget);
    function leg(prefix: string, from: LocationSelection, to: LocationSelection) {
      return {
        pickup_location_id: from.locationId, dropoff_location_id: to.locationId,
        pickup_start: localToISO(String(form.get(`${prefix}start`))),
        pickup_end: localToISO(String(form.get(`${prefix}end`))), timezone,
        seats: Number(form.get(`${prefix}seats`)), bags_per_person: Number(form.get(`${prefix}bags`)),
        amount: form.get(`${prefix}amount`), currency: form.get(`${prefix}currency`),
        notes: form.get(`${prefix}notes`),
      };
    }
    setBusy(true);
    try {
      const detail = await apiRequest<CarpoolDetail>("/rides/carpools/trips", { method: "POST", body: JSON.stringify({
        outbound: leg("", pickup, dropoff),
        return_trip: returning && returnFrom && returnTo ? leg("return-", returnFrom, returnTo) : null,
        public_meeting_point_consent: form.get("consent") === "on",
      }) });
      router.push(`/rides/carpools/${detail.trip.id}`);
    } catch (err) { setError(rideError(err)); }
    finally { setBusy(false); }
  }
  return <RideLayout>
    <section className="page-heading"><div><p className="eyebrow">Room for company</p><h1>Offer a carpool.</h1><p className="muted">You are already making this trip. Share the passenger seats you have available.</p></div></section>
    <p className="ride-notice">First, complete your <Link className="text-link" href="/rides/driver">driver profile</Link>. Vehicle details are saved with the trip. Your phone is shared only after approval. Published trips cannot be edited; cancel and republish if plans change.</p>
    <form className="form-card" onSubmit={submit}>
      <fieldset className="carpool-fields" disabled={busy}>
        <legend>Outbound trip</legend>
        <LocationAutocomplete label="Public pickup meeting point" onAddressSelected={setPickup} />
        <LocationAutocomplete label="Public drop-off meeting point" onAddressSelected={setDropoff} />
        <LegFields prefix="" timezone={timezone} />
        <label className="ride-check"><input type="checkbox" checked={returning} onChange={event => setReturning(event.target.checked)} /><span>Add a return trip</span></label>
        {returning && <section aria-label="Return trip">
          <h2>Return trip</h2>
          <p>Default route: {dropoff?.location ?? "Outbound destination"} to {pickup?.location ?? "Outbound origin"}. Seats, date, and contribution are independent.</p>
          <label className="ride-check"><input type="checkbox" checked={customReturn} onChange={event => setCustomReturn(event.target.checked)} /><span>Use different return meeting points</span></label>
          {customReturn && <><LocationAutocomplete label="Return pickup meeting point" onAddressSelected={setReturnPickup} /><LocationAutocomplete label="Return drop-off meeting point" onAddressSelected={setReturnDropoff} /></>}
          <LegFields prefix="return-" timezone={timezone} />
        </section>}
        <label className="ride-check"><input name="consent" type="checkbox" required /><span>I selected public meeting points and agree that their full addresses are visible to signed-in members. This is community cost sharing, not guaranteed transport. Payments are arranged outside the platform.</span></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-actions"><button className="button button-primary">{busy ? "Publishing..." : "Publish carpool"}</button><Link className="button button-secondary" href="/rides/carpools">Cancel</Link></div>
      </fieldset>
    </form>
  </RideLayout>;
}

function LegFields({ prefix, timezone }: { prefix: string; timezone: string }) {
  return <>
    <p className="field-hint">Times are in {timezone} (your browser timezone), not automatically the meeting point&apos;s timezone. Departure window: up to two hours. Requests and approvals close when the window starts; cancellations remain available until it ends.</p>
    <div className="form-row"><label className="form-field"><span>Earliest departure</span><input name={`${prefix}start`} type="datetime-local" required /></label><label className="form-field"><span>Latest departure</span><input name={`${prefix}end`} type="datetime-local" required /></label></div>
    <div className="form-row"><label className="form-field"><span>Passenger seats available</span><input name={`${prefix}seats`} type="number" min={1} max={8} defaultValue={1} required /></label><label className="form-field"><span>Bags allowed per passenger</span><input name={`${prefix}bags`} type="number" min={0} max={10} defaultValue={1} required /></label></div>
    <div className="form-row"><label className="form-field"><span>Fixed contribution per passenger</span><input name={`${prefix}amount`} type="number" min={0} max="9999.99" step="0.01" defaultValue="0.00" required /></label><label className="form-field"><span>Currency</span><select name={`${prefix}currency`} defaultValue="USD">{RIDE_CURRENCIES.map(currency => <option key={currency}>{currency}</option>)}</select></label></div>
    <label className="form-field"><span>Trip notes and luggage size limits (optional)</span><textarea name={`${prefix}notes`} maxLength={500} rows={3} placeholder="One small suitcase each. Meet at the station entrance. Do not include private addresses or phone numbers." /></label>
  </>;
}
