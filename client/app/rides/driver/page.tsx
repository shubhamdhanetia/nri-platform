"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import RideLayout from "../../../components/RideLayout";
import { apiRequest, isUuid } from "../../../lib/api";
import { rideError, VEHICLE_COLORS, type DriverProfile, type VehicleColor } from "../../../lib/rides";

export default function DriverPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [ready, setReady] = useState(false);
  const [vehicle, setVehicle] = useState("");
  const [vehicleColor, setVehicleColor] = useState<VehicleColor | "">("");
  const [capacity, setCapacity] = useState("3");
  const [phone, setPhone] = useState("");
  const [licensePlate, setLicensePlate] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    apiRequest<DriverProfile | null>("/rides/driver-profile", { signal: controller.signal }).then(result => {
      setProfile(result);
      if (result) { setVehicle(result.vehicle); setVehicleColor(result.vehicle_color ?? ""); setCapacity(String(result.passenger_capacity)); setPhone(result.phone); setLicensePlate(result.license_plate ?? ""); }
      setReady(true);
    }).catch((err: unknown) => { if (!controller.signal.aborted) setError(rideError(err)); });
    return () => controller.abort();
  }, []);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setSuccess("");
    try {
      const result = await apiRequest<DriverProfile>("/rides/driver-profile", { method: "PUT", body: JSON.stringify({ vehicle, vehicle_color: vehicleColor || null, passenger_capacity: Number(capacity), phone, license_plate: licensePlate, eligibility_acknowledged: acknowledged }) });
      setProfile(result); setSuccess("Driver profile saved. You can now offer rides.");
      const request = new URLSearchParams(window.location.search).get("request");
      if (request && isUuid(request)) {
        router.push(`/rides/${request}`);
      }
    } catch (err) { setError(rideError(err)); } finally { setBusy(false); }
  }
  return <RideLayout>
    <section className="page-heading"><div><p className="eyebrow">One account, both roles</p><h1>Driver settings</h1><p className="muted">Manage your vehicle and contact details to offer community cost-sharing rides.</p></div></section>
    {error && <p className="form-error" role="alert">{error}</p>}
    {!ready ? <p role="status">{error ? "Reload the page to retry loading your profile." : "Loading profile..."}</p> : <form className="form-card" onSubmit={save}>
      <label className="form-field"><span>Vehicle make and model</span><input required maxLength={100} value={vehicle} onChange={e => setVehicle(e.target.value)} placeholder="Toyota Camry" /></label>
      <label className="form-field"><span>Vehicle color (optional)</span><select value={vehicleColor} onChange={e => setVehicleColor(e.target.value as VehicleColor | "")}><option value="">Not specified</option>{VEHICLE_COLORS.map(color => <option key={color} value={color}>{color}</option>)}</select></label>
      <label className="form-field"><span>Passenger seats (excluding driver)</span><input type="number" min={1} max={8} required value={capacity} onChange={e => setCapacity(e.target.value)} /></label>
      <label className="form-field"><span>Contact phone number</span><input type="tel" autoComplete="tel" required pattern={"\\+[1-9][0-9]{7,14}"} placeholder="+14155550123" value={phone} onChange={e => setPhone(e.target.value)} /><span className="field-hint">International format, + and digits only. Shared with a rider only after confirmation. Not verified by the platform.</span></label>
      <label className="form-field"><span>License plate (optional)</span><input autoComplete="off" maxLength={20} value={licensePlate} onChange={e => setLicensePlate(e.target.value)} placeholder="ABC 1234" /><span className="field-hint">Private to you until a driver accepts a rider&apos;s request. Shared only with confirmed ride participants.</span></label>
      <label className="ride-check"><input type="checkbox" required checked={acknowledged} aria-describedby={!acknowledged ? "driver-acknowledgement-hint" : undefined} onChange={e => setAcknowledged(e.target.checked)} /><span><strong>Required:</strong> I have a valid driving licence, suitable insurance, and permission to offer these rides under local rules. I understand the platform does not verify my eligibility or collect payments. I will use members&apos; exact addresses only to arrange their ride.</span></label>
      {!acknowledged && <p className="field-hint" id="driver-acknowledgement-hint">Please accept the eligibility and address-use acknowledgement to continue.</p>}
      <p className="field-hint">Profile changes apply to new offers and trips. Existing offers keep their vehicle details, and confirmed bookings keep the agreed vehicle, plate, and contact numbers.</p>
      {success && <p className="ride-notice" role="status">{success}</p>}
      <div className="form-actions"><button className="button button-primary" disabled={busy || !acknowledged}>{busy ? "Saving..." : profile ? "Update profile" : "Create driver profile"}</button><Link className="button button-secondary" href="/rides/mine">Back to My rides</Link></div>
    </form>}
  </RideLayout>;
}
