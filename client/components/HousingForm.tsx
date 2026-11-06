"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MapPin } from "lucide-react";
import { apiRequest } from "../lib/api";
import { ALCOHOL, APPROVALS, ARRANGEMENTS, BATHROOMS, CURRENCIES, FURNISHINGS, KITCHENS, PETS, PRICE_PERIODS, ROOM_TYPES, SMOKING, STAY_TYPES, UTILITIES, housingError, readHouseholdLanguages, type HousingDraft, type HousingItem, type HousingKind } from "../lib/housing";
import { HousingSelect } from "./HousingBrowse";
import HousingLanguages from "./HousingLanguages";
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

function FormSection({ title, busy, children }: { title: string; busy: boolean; children: ReactNode }) {
  return <details className="housing-form-section">
    <summary>{title}<span>Optional</span></summary>
    <fieldset disabled={busy} aria-label={title}>{children}</fieldset>
  </details>;
}

export default function HousingForm({ item, initialKind = "LISTING" }: { item?: HousingItem; initialKind?: HousingKind }) {
  const router = useRouter();
  const [kind, setKind] = useState<HousingKind>(item?.kind ?? initialKind);
  const [hallSpace, setHallSpace] = useState(item?.room_type === "HALL");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [invalidFields, setInvalidFields] = useState<Record<string, string>>({});
  const [locationMissing, setLocationMissing] = useState(false);
  const compact = kind !== "LISTING";
  function fieldError(name: string) {
    return invalidFields[name] ? <span className="form-error" role="alert">{invalidFields[name]}</span> : null;
  }
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
      if (!selection) {
        setLocationMissing(true);
        throw new Error("Select an address or preferred area from the location suggestions.");
      }
      const payload: HousingDraft = {
        kind, title: text(data, "title"), description: text(data, "description"),
        location_id: selection.locationId, area: text(data, "area"),
        room_type: choice(data, "room_type", ROOM_TYPES), arrangement: choice(data, "arrangement", ARRANGEMENTS),
        bedroom_count: optionalNumber(data, "bedroom_count"), bathroom_count: optionalNumber(data, "bathroom_count"),
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
        household_languages: readHouseholdLanguages(data),
        accessibility_notes: text(data, "accessibility_notes"), photo_urls: text(data, "photo_urls").split(/\r?\n/).map(url => url.trim()).filter(Boolean),
        is_private: data.get("is_private") === "on",
      };
      const saved = await apiRequest<HousingItem>(item ? `/housing/${item.id}` : "/housing", { method: item ? "PUT" : "POST", body: JSON.stringify(payload) });
      router.push(`/housing/${saved.id}`);
    } catch (failure) { setError(housingError(failure)); } finally { setBusy(false); }
  }
  return <>
    <section className="page-heading"><div><p className="eyebrow">Housing, your way</p><h1>{item ? "Edit housing post" : compact ? "Create a housing request" : "Create a housing post"}</h1><p className="muted">Complete the required fields. Optional preferences help people understand your needs.</p></div></section>
    <form className={`housing-form form-card${compact ? " housing-form-compact" : ""}`} onSubmit={submit}
      onInvalidCapture={event => {
        const input = event.target;
        if (input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement || input instanceof HTMLSelectElement) {
          let section = input.closest("details");
          while (section) {
            section.open = true;
            section = section.parentElement?.closest("details") ?? null;
          }
          setInvalidFields(current => ({ ...current, [input.name]: input.validationMessage }));
        }
      }}
      onChange={event => {
        const input = event.target;
        if (input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement || input instanceof HTMLSelectElement) {
          setInvalidFields(current => { const next = { ...current }; delete next[input.name]; return next; });
        }
      }}>
      <fieldset disabled={busy}>
        <legend>1. Choose your post</legend>
        <div className="housing-kind-choice" role="radiogroup" aria-labelledby="housing-kind-label">
          <p id="housing-kind-label" className="housing-kind-prompt">What would you like to do?</p>
          <div className="housing-kind-options">
            <label className="housing-kind-option">
              <input type="radio" name="kind" value="LISTING" checked={kind === "LISTING"} onChange={() => setKind("LISTING")} required />
              <span><strong>I have a place</strong><small>List a room, home, sublet, or lease takeover.</small></span>
            </label>
            <label className="housing-kind-option">
              <input type="radio" name="kind" value="REQUEST" checked={kind === "REQUEST"} onChange={() => setKind("REQUEST")} />
              <span><strong>I&apos;m looking for a place</strong><small>Share your budget, area, and move-in needs.</small></span>
            </label>
            <label className="housing-kind-option">
              <input type="radio" name="kind" value="TOGETHER" checked={kind === "TOGETHER"} onChange={() => setKind("TOGETHER")} />
              <span><strong>I want to find roommates</strong><small>Find people to search for a place together.</small></span>
            </label>
          </div>
        </div>
        <h2 className="housing-basics-heading">{compact ? "Request essentials" : "2. Add the details"}</h2>
        <label className="form-field"><span>Title <small className="housing-required">Required</small></span><input name="title" required minLength={5} maxLength={150} defaultValue={item?.title} placeholder={compact ? "e.g. Looking for a private room near Sunnyvale" : "e.g. Furnished private room near downtown"} aria-invalid={!!invalidFields.title} />{fieldError("title")}</label>
        <label className="form-field"><span>Description <small className="housing-required">Required</small></span><textarea name="description" rows={compact ? 3 : 5} required minLength={10} maxLength={5000} defaultValue={item?.description} placeholder={compact ? "Tell people what you need, your timing, and any important preferences." : "Describe the place or what you are looking for. Do not include access codes."} aria-invalid={!!invalidFields.description} />{fieldError("description")}</label>
        <div className="housing-location-field">
          <div className="community-location housing-location-input"><MapPin size={18} aria-hidden="true" />
          <ExploreLocationSearch
            center={locationCenter}
            label={kind === "LISTING" ? "Where is the place? (Required)" : kind === "REQUEST" ? "Preferred area (Required)" : "Area to search together (Required)"}
            placeholder={kind === "LISTING" ? "Search an address or place" : "Search a preferred city, neighborhood, or landmark"}
            initialSelection={item?.location_id && item.location ? { locationId: item.location_id, location: item.location } : undefined}
            onSelectionChange={value => { setSelection(value); if (value) setLocationMissing(false); }}
            onLocationSelected={setLocationCenter}
          />
          </div>
          {locationMissing && !selection && <p className="form-error" role="alert">Select a preferred area from the location suggestions.</p>}
          {item && !item.location_id && <p className="housing-callout">This existing post has no map location. Select one to include it in area searches.</p>}
        </div>
        <div className="housing-filter-grid">
          <HousingSelect name="room_type" label={compact ? "Space wanted" : "Space offered"} anyLabel="" options={kind === "LISTING" ? { SHARED: ROOM_TYPES.SHARED, PRIVATE: ROOM_TYPES.PRIVATE, HALL: ROOM_TYPES.HALL, ENTIRE: ROOM_TYPES.ENTIRE } : ROOM_TYPES} defaultValue={item?.room_type ?? "PRIVATE"} onChange={event => setHallSpace(event.target.value === "HALL")} />
          <HousingSelect name="stay_type" label="Stay length" anyLabel="" options={STAY_TYPES} defaultValue={item?.stay_type ?? "FLEXIBLE"} />
        </div>
        {hallSpace && <p className="housing-callout">{kind === "LISTING"
          ? "For hall / living-room space, describe in the description whether it is open or partitioned, whether others pass through, storage, and access to shared facilities."
          : "For hall / living-room space, describe the privacy, storage, and shared-facility access you need."} Confirm lease permission, occupancy limits, and local safety requirements before agreeing. This option does not mean the space is approved for sleeping.</p>}
      </fieldset>
      <fieldset disabled={busy}><legend>{compact ? "Budget & move-in" : "3. Price & availability"}</legend>
        <div className="housing-filter-grid">
          <label className="form-field"><span>{kind === "LISTING" ? "Rent amount" : "Budget amount"} <small className="housing-required">Required</small></span><input name="amount" type="number" min="0" max="999999.99" step="0.01" required defaultValue={item?.amount} aria-invalid={!!invalidFields.amount} />{fieldError("amount")}</label>
          <label className="form-field"><span>Currency <small className="housing-required">Required</small></span><select name="currency" required defaultValue={item?.currency ?? "USD"} aria-invalid={!!invalidFields.currency}>
            {Object.entries(item?.currency ? { ...CURRENCIES, [item.currency]: item.currency } : CURRENCIES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>{fieldError("currency")}</label>
          <HousingSelect name="price_period" label="Per" options={PRICE_PERIODS} anyLabel="" defaultValue={item?.price_period ?? "MONTH"} />
          <label className="form-field"><span>{kind === "LISTING" ? "Available from" : "Preferred move-in"} <small className="housing-required">Required</small></span><input name="available_from" type="date" required defaultValue={item?.available_from} aria-invalid={!!invalidFields.available_from} />{fieldError("available_from")}</label>
        </div>
      </fieldset>
      <FormSection title="Space & stay preferences" busy={busy}>
        <p className="field-hint">Leave these preferences at their defaults if you do not need to change them. Minimum stay defaults to 30 days and spaces needed to 1.</p>
        <div className="housing-filter-grid">
          <label className="form-field"><span>{kind === "LISTING" ? "Bedrooms in home (optional)" : "Minimum bedrooms desired (optional)"}</span><input name="bedroom_count" type="number" min="0" max="20" step="1" defaultValue={item?.bedroom_count ?? ""} /><span className="field-hint">Count actual bedrooms, not hall / living-room sleeping spaces. Enter 0 for a studio.</span>{fieldError("bedroom_count")}</label>
          <label className="form-field"><span>{kind === "LISTING" ? "Bathrooms in home (optional)" : "Minimum bathrooms desired (optional)"}</span><input name="bathroom_count" type="number" min="0.5" max="20" step="0.5" defaultValue={item?.bathroom_count ?? ""} />{fieldError("bathroom_count")}</label>
          <HousingSelect name="arrangement" label="Arrangement" anyLabel="" options={kind === "LISTING" ? { HOUSEHOLD: ARRANGEMENTS.HOUSEHOLD, RENTAL: ARRANGEMENTS.RENTAL, SUBLET: ARRANGEMENTS.SUBLET, TAKEOVER: ARRANGEMENTS.TAKEOVER } : ARRANGEMENTS} defaultValue={item?.arrangement ?? "HOUSEHOLD"} />
          <label className="form-field"><span>{compact ? "Needed until (optional)" : "Available until (optional)"}</span><input name="available_until" type="date" defaultValue={item?.available_until ?? ""} />{fieldError("available_until")}</label>
          <label className="form-field"><span>Minimum stay (days)</span><input name="minimum_stay_days" type="number" min="1" max="3650" required defaultValue={item?.minimum_stay_days ?? 30} />{fieldError("minimum_stay_days")}</label>
          <label className="form-field"><span>{compact ? "Spaces needed" : "Spaces available"}</span><input name="available_spaces" type="number" min="1" max="20" required defaultValue={item?.available_spaces ?? 1} />{fieldError("available_spaces")}</label>
        </div>
      </FormSection>
      <FormSection title={compact ? "Home & household preferences" : "Home & household"} busy={busy}>
        <p className="field-hint">Optional practical details, not identity-based eligibility. Describe shared-space practices rather than excluding people by background.</p>
        <div className="housing-filter-grid">
          <HousingSelect name="utilities" label="Utilities" options={UTILITIES} anyLabel="" defaultValue={item?.utilities ?? "UNKNOWN"} />
          <HousingSelect name="furnishing" label="Furnishing" anyLabel="" options={FURNISHINGS} defaultValue={item?.furnishing ?? "UNSPECIFIED"} />
          <HousingSelect name="bathroom" label="Bathroom" anyLabel="" options={BATHROOMS} defaultValue={item?.bathroom ?? "UNSPECIFIED"} />
          <HousingSelect name="kitchen" label="Shared kitchen food policy" anyLabel="" options={KITCHENS} defaultValue={item?.kitchen ?? "UNSPECIFIED"} />
          <HousingSelect name="smoking" label="Smoking / vaping" anyLabel="" options={SMOKING} defaultValue={item?.smoking ?? "UNSPECIFIED"} />
          <HousingSelect name="alcohol" label="Alcohol" anyLabel="" options={ALCOHOL} defaultValue={item?.alcohol ?? "UNSPECIFIED"} />
          <HousingSelect name="pets" label="Pets" anyLabel="" options={PETS} defaultValue={item?.pets ?? "UNSPECIFIED"} />
          {([["parking", "Parking"], ["laundry", "Laundry"], ["kitchen_access", "Kitchen access"], ["work_from_home", "Suitable for working from home"]] as const).map(([key, label]) =>
            <HousingSelect key={key} name={key} label={label} options={{ true: "Yes", false: "No" }} anyLabel="Not specified" defaultValue={item?.[key] === null || item?.[key] === undefined ? "" : String(item[key])} />)}
          <HousingLanguages
            label={kind === "LISTING" ? "Languages spoken in the household (optional)" : "Languages you speak (optional)"}
            hint="Share languages commonly spoken to help with communication. Select multiple for a multilingual household; leave blank if not specified. This does not restrict who may inquire."
            defaultValue={item?.household_languages}
          />
        </div>
      </FormSection>
      <FormSection title="More details" busy={busy}>
        <div className="housing-filter-grid">
          <label className="form-field"><span>Neighborhood / landmark note (optional)</span><input name="area" maxLength={150} defaultValue={item?.area} placeholder="e.g. Near BART, walking distance to shops" /></label>
          <label className="form-field"><span>Deposit (optional)</span><input name="deposit" type="number" min="0" max="999999.99" step="0.01" defaultValue={item?.deposit ?? ""} />{fieldError("deposit")}</label>
          <label className="form-field"><span>Other one-time fees (optional)</span><input name="fees" type="number" min="0" max="999999.99" step="0.01" defaultValue={item?.fees ?? ""} />{fieldError("fees")}</label>
        </div>
        <details className="housing-property-help">
          <summary>Existing household / property details (optional)</summary>
          <p className="field-hint">Only relevant if you already have a household or a property arrangement. Otherwise leave these unchanged.</p>
          <div className="housing-filter-grid">
            <label className="form-field"><span>Current occupants (optional)</span><input name="occupants" type="number" min="0" max="50" defaultValue={item?.occupants ?? ""} />{fieldError("occupants")}</label>
            <HousingSelect name="approval" label="Landlord / property-manager approval" anyLabel="" options={APPROVALS} defaultValue={item?.approval ?? "NOT_APPLICABLE"} />
          </div>
          <p className="field-hint">Sublets and lease takeovers may require permission. State the actual approval status; the platform does not verify it.</p>
        </details>
        <label className="form-field"><span>Household notes (optional)</span><textarea name="household_notes" rows={3} maxLength={2000} defaultValue={item?.household_notes} placeholder="Quiet hours, cleaning expectations, guests, parking costs, kitchen use..." /></label>
        <label className="form-field"><span>Accessibility details (optional)</span><textarea name="accessibility_notes" rows={2} maxLength={1000} defaultValue={item?.accessibility_notes} placeholder="Step-free entry, stairs, lift, doorway details..." /></label>
        <label className="form-field"><span>Photo links (optional, up to 8)</span><textarea name="photo_urls" rows={3} defaultValue={item?.photo_urls.join("\n")} placeholder="https://...&#10;One direct image URL per line" /><span className="field-hint">Use HTTPS links to photos you have permission to share. Images load from the linked host; do not include private documents, people without consent, or access codes. Uploads are not available yet.</span></label>
      </FormSection>
      <fieldset disabled={busy}><legend>Visibility</legend>
        <label className="ride-check"><input name="is_private" type="checkbox" defaultChecked={item?.is_private} /><span>Only me — keep this post private. Others cannot view it or send inquiries.</span></label>
        <p className="housing-callout">Public active posts appear for 30 days. Renew to confirm availability, or mark them filled/resolved when done. Existing saved links remain accessible unless private or deleted.</p>
      </fieldset>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="housing-actions"><button className="button button-primary" disabled={busy}>{busy ? "Saving..." : item ? "Save changes" : kind === "REQUEST" ? "Publish housing request" : kind === "TOGETHER" ? "Publish roommate request" : "Publish housing post"}</button><Link className="button button-secondary" href={item ? `/housing/${item.id}` : "/housing"}>Cancel</Link></div>
    </form>
  </>;
}
