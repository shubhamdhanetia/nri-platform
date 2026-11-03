"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MapPin } from "lucide-react";
import { apiRequest } from "../lib/api";
import { ALCOHOL, APPROVALS, ARRANGEMENTS, BATHROOMS, FURNISHINGS, HOUSING_KINDS, KITCHENS, PETS, PRICE_PERIODS, ROOM_TYPES, SMOKING, STAY_TYPES, UTILITIES, housingError, type HousingDraft, type HousingItem, type HousingKind } from "../lib/housing";
import { HousingSelect } from "./HousingBrowse";
import ExploreLocationSearch from "./ExploreLocationSearch";

function text(data: FormData, key: string): string {
  const value = data.get(key);
  return typeof value === "string" ? value.trim() : "";
}
function choice<T extends string>(data: FormData, key: string, options: Record<T, string>): T {
  const value = text(data, key);
  for (const option in options) if (option === value) return option;
  throw new Error(`Choose a valid ${key.replaceAll("_", " ")}.`);
}
function optionalNumber(data: FormData, key: string): number | null {
  return text(data, key) === "" ? null : Number(text(data, key));
}
function optionalBool(data: FormData, key: string): boolean | null {
  return text(data, key) === "" ? null : text(data, key) === "true";
}

export default function HousingForm({ item, initialKind = "LISTING" }: { item?: HousingItem; initialKind?: HousingKind }) {
  const router = useRouter();
  const [kind, setKind] = useState<HousingKind>(item?.kind ?? initialKind);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selection, setSelection] = useState<{ locationId: string; location: string } | null>(
    item?.location_id && item.location ? { locationId: item.location_id, location: item.location } : null,
  );
  const [locationCenter, setLocationCenter] = useState<[number, number]>(
    item?.latitude !== null && item?.latitude !== undefined && item.longitude !== null ? [item.latitude, item.longitude] : [20, 0],
  );
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError(""); setBusy(true);
    try {
      if (!selection) throw new Error("Select an address or preferred area from the location suggestions.");
      const payload: HousingDraft = {
        kind, title: text(data, "title"), description: text(data, "description"),
        location_id: selection.locationId, area: text(data, "area"),
        room_type: choice(data, "room_type", ROOM_TYPES), arrangement: choice(data, "arrangement", ARRANGEMENTS),
        stay_type: choice(data, "stay_type", STAY_TYPES), amount: text(data, "amount"), currency: text(data, "currency").toUpperCase(),
        price_period: choice(data, "price_period", PRICE_PERIODS), available_from: text(data, "available_from"),
        available_until: text(data, "available_until") || null, minimum_stay_days: Number(text(data, "minimum_stay_days")),
        furnishing: choice(data, "furnishing", FURNISHINGS), bathroom: choice(data, "bathroom", BATHROOMS),
        occupants: optionalNumber(data, "occupants"), available_spaces: Number(text(data, "available_spaces")),
        utilities: choice(data, "utilities", UTILITIES), deposit: text(data, "deposit") || null, fees: text(data, "fees") || null,
        approval: choice(data, "approval", APPROVALS), kitchen: choice(data, "kitchen", KITCHENS),
        smoking: choice(data, "smoking", SMOKING), alcohol: choice(data, "alcohol", ALCOHOL), pets: choice(data, "pets", PETS),
        parking: optionalBool(data, "parking"), laundry: optionalBool(data, "laundry"), kitchen_access: optionalBool(data, "kitchen_access"),
        work_from_home: optionalBool(data, "work_from_home"), household_notes: text(data, "household_notes"),
        accessibility_notes: text(data, "accessibility_notes"), photo_urls: text(data, "photo_urls").split(/\r?\n/).map(url => url.trim()).filter(Boolean),
        is_private: data.get("is_private") === "on",
      };
      const saved = await apiRequest<HousingItem>(item ? `/housing/${item.id}` : "/housing", { method: item ? "PUT" : "POST", body: JSON.stringify(payload) });
      router.push(`/housing/${saved.id}`);
    } catch (failure) { setError(housingError(failure)); } finally { setBusy(false); }
  }
  return <>
    <section className="page-heading"><div><p className="eyebrow">Housing, your way</p><h1>{item ? "Edit housing post" : "Share a place or a housing need"}</h1><p className="muted">Share useful details, choose a location, and arrange the next steps through inquiries.</p></div></section>
    <form className="housing-form form-card" onSubmit={submit}>
      <fieldset disabled={busy}>
        <legend>1. The basics</legend>
        <label className="form-field"><span>What would you like to post?</span><select value={kind} onChange={event => {
          const value = event.target.value;
          if (value === "LISTING" || value === "REQUEST" || value === "TOGETHER") setKind(value);
        }}>{Object.entries(HOUSING_KINDS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="form-field"><span>Title</span><input name="title" required minLength={5} maxLength={150} defaultValue={item?.title} placeholder="e.g. Furnished private room near downtown" /></label>
        <label className="form-field"><span>Description</span><textarea name="description" rows={5} required minLength={10} maxLength={5000} defaultValue={item?.description} placeholder="Describe the place or what you are looking for. Do not include access codes." /></label>
        <div className="housing-location-field">
          <div className="community-location housing-location-input"><MapPin size={18} aria-hidden="true" />
          <ExploreLocationSearch
            center={locationCenter}
            label={kind === "LISTING" ? "Where is the place?" : kind === "REQUEST" ? "Where would you like to live?" : "Where would you like to search together?"}
            placeholder={kind === "LISTING" ? "Search an address or place" : "Search a preferred city, neighborhood, or landmark"}
            initialSelection={item?.location_id && item.location ? { locationId: item.location_id, location: item.location } : undefined}
            onSelectionChange={setSelection}
            onLocationSelected={setLocationCenter}
          />
          </div>
          <p className="field-hint">{kind === "LISTING" ? "The selected address and exact map point will be visible to signed-in members while public." : "Choose where you want to live, not your current home. The selected address and map point show your preferred area, not a confirmed property."} City, state, and country are filled from the selected place. Browser location access is not required.</p>
          {!selection && <p className="field-hint">Select a suggestion and wait for its details before publishing.</p>}
          {item && !item.location_id && <p className="housing-callout">This existing post has no map location. Select one to include it in area searches.</p>}
        </div>
        <div className="housing-filter-grid">
          <label className="form-field"><span>Neighborhood / landmark note (optional)</span><input name="area" maxLength={150} defaultValue={item?.area} placeholder="e.g. Near BART, walking distance to shops" /></label>
          <HousingSelect name="room_type" label="Space" anyLabel="" options={kind === "LISTING" ? { SHARED: ROOM_TYPES.SHARED, PRIVATE: ROOM_TYPES.PRIVATE, ENTIRE: ROOM_TYPES.ENTIRE } : ROOM_TYPES} defaultValue={item?.room_type ?? "PRIVATE"} />
          <HousingSelect name="arrangement" label="Arrangement" anyLabel="" options={kind === "LISTING" ? { HOUSEHOLD: ARRANGEMENTS.HOUSEHOLD, RENTAL: ARRANGEMENTS.RENTAL, SUBLET: ARRANGEMENTS.SUBLET, TAKEOVER: ARRANGEMENTS.TAKEOVER } : ARRANGEMENTS} defaultValue={item?.arrangement ?? "HOUSEHOLD"} />
          <HousingSelect name="stay_type" label="Stay length" anyLabel="" options={STAY_TYPES} defaultValue={item?.stay_type ?? "FLEXIBLE"} />
        </div>
      </fieldset>
      <fieldset disabled={busy}><legend>2. Price & availability</legend>
        <p className="field-hint">For requests and searching together, enter your budget. For available places, enter rent per space offered. Currency and price period always travel with the amount.</p>
        <div className="housing-filter-grid">
          <label className="form-field"><span>{kind === "LISTING" ? "Rent amount" : "Budget amount"}</span><input name="amount" type="number" min="0" max="999999.99" step="0.01" required defaultValue={item?.amount} /></label>
          <label className="form-field"><span>Currency</span><input name="currency" required pattern="[A-Za-z]{3}" maxLength={3} defaultValue={item?.currency ?? "USD"} /></label>
          <HousingSelect name="price_period" label="Per" options={PRICE_PERIODS} anyLabel="" defaultValue={item?.price_period ?? "MONTH"} />
          <HousingSelect name="utilities" label="Utilities" options={UTILITIES} anyLabel="" defaultValue={item?.utilities ?? "UNKNOWN"} />
          <label className="form-field"><span>Deposit (optional)</span><input name="deposit" type="number" min="0" max="999999.99" step="0.01" defaultValue={item?.deposit ?? ""} /></label>
          <label className="form-field"><span>Other one-time fees (optional)</span><input name="fees" type="number" min="0" max="999999.99" step="0.01" defaultValue={item?.fees ?? ""} /></label>
          <label className="form-field"><span>{kind === "LISTING" ? "Available from" : "Preferred move-in"}</span><input name="available_from" type="date" required defaultValue={item?.available_from} /></label>
          <label className="form-field"><span>Available / needed until (optional)</span><input name="available_until" type="date" defaultValue={item?.available_until ?? ""} /></label>
          <label className="form-field"><span>Minimum stay (days)</span><input name="minimum_stay_days" type="number" min="1" max="3650" required defaultValue={item?.minimum_stay_days ?? 30} /></label>
          <label className="form-field"><span>Spaces available / needed</span><input name="available_spaces" type="number" min="1" max="20" required defaultValue={item?.available_spaces ?? 1} /></label>
          <label className="form-field"><span>Current occupants (optional)</span><input name="occupants" type="number" min="0" max="50" defaultValue={item?.occupants ?? ""} /></label>
          <HousingSelect name="approval" label="Landlord / property-manager approval" anyLabel="" options={APPROVALS} defaultValue={item?.approval ?? "NOT_APPLICABLE"} />
        </div>
        <p className="field-hint">Sublets and lease takeovers may require permission. State the actual approval status; the platform does not verify it. Short-term inquiries do not reserve dates.</p>
      </fieldset>
      <fieldset disabled={busy}><legend>3. Home & household</legend>
        <p className="field-hint">Optional practical details, not identity-based eligibility. Follow local fair-housing rules. Describe shared-space practices rather than excluding people by background.</p>
        <div className="housing-filter-grid">
          <HousingSelect name="furnishing" label="Furnishing" anyLabel="" options={FURNISHINGS} defaultValue={item?.furnishing ?? "UNSPECIFIED"} />
          <HousingSelect name="bathroom" label="Bathroom" anyLabel="" options={BATHROOMS} defaultValue={item?.bathroom ?? "UNSPECIFIED"} />
          <HousingSelect name="kitchen" label="Shared kitchen food policy" anyLabel="" options={KITCHENS} defaultValue={item?.kitchen ?? "UNSPECIFIED"} />
          <HousingSelect name="smoking" label="Smoking / vaping" anyLabel="" options={SMOKING} defaultValue={item?.smoking ?? "UNSPECIFIED"} />
          <HousingSelect name="alcohol" label="Alcohol" anyLabel="" options={ALCOHOL} defaultValue={item?.alcohol ?? "UNSPECIFIED"} />
          <HousingSelect name="pets" label="Pets" anyLabel="" options={PETS} defaultValue={item?.pets ?? "UNSPECIFIED"} />
          {([["parking", "Parking"], ["laundry", "Laundry"], ["kitchen_access", "Kitchen access"], ["work_from_home", "Suitable for working from home"]] as const).map(([key, label]) =>
            <HousingSelect key={key} name={key} label={label} options={{ true: "Yes", false: "No" }} anyLabel="Not specified" defaultValue={item?.[key] === null || item?.[key] === undefined ? "" : String(item[key])} />)}
        </div>
        <label className="form-field"><span>Household notes (optional)</span><textarea name="household_notes" rows={3} maxLength={2000} defaultValue={item?.household_notes} placeholder="Quiet hours, cleaning expectations, guests, parking costs, kitchen use..." /></label>
        <label className="form-field"><span>Accessibility details (optional)</span><textarea name="accessibility_notes" rows={2} maxLength={1000} defaultValue={item?.accessibility_notes} placeholder="Step-free entry, stairs, lift, doorway details..." /></label>
      </fieldset>
      <fieldset disabled={busy}><legend>4. Photos & visibility</legend>
        <label className="form-field"><span>Photo links (optional, up to 8)</span><textarea name="photo_urls" rows={3} defaultValue={item?.photo_urls.join("\n")} placeholder="https://...&#10;One direct image URL per line" /><span className="field-hint">Use HTTPS links to photos you have permission to share. Images load from the linked host; do not include private documents, people without consent, or access codes. Uploads are not available yet.</span></label>
        <label className="ride-check"><input name="is_private" type="checkbox" defaultChecked={item?.is_private} /><span>Only me — keep this post private. Others cannot view it or send inquiries.</span></label>
        <p className="housing-callout">Public active posts appear for 30 days. Renew to confirm availability, or mark them filled/resolved when done. Existing saved links remain accessible unless private or deleted.</p>
      </fieldset>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="housing-actions"><button className="button button-primary" disabled={busy || !selection}>{busy ? "Saving..." : item ? "Save changes" : "Publish housing post"}</button><Link className="button button-secondary" href={item ? `/housing/${item.id}` : "/housing"}>Cancel</Link></div>
    </form>
  </>;
}
