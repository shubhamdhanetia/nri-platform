"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { apiRequest, type User } from "../lib/api";
import { ALCOHOL, APPROVALS, ARRANGEMENTS, BATHROOMS, FURNISHINGS, HOUSING_KINDS, KITCHENS, PETS, ROOM_TYPES, SMOKING, STAY_TYPES, UTILITIES, housingDate, housingError, housingExpired, housingLayout, housingMoney, useHousingResource, type HousingInquiry, type HousingItem } from "../lib/housing";
import { HousingStatusBadge } from "./HousingCard";
import HousingGallery from "./HousingGallery";
import { HousingLoadState, HousingOwnerActions, HousingSaveButton } from "./HousingControls";

function yesNo(value: boolean | null): string { return value === null ? "Not specified" : value ? "Yes" : "No"; }

function HousingInquiryForm({ item }: { item: HousingItem }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sentInquiryId, setSentInquiryId] = useState<string | null>(null);
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true); setError(""); setSentInquiryId(null);
    try {
      const inquiry = await apiRequest<HousingInquiry>(`/housing/${item.id}/inquiries`, { method: "POST", body: JSON.stringify({ message: data.get("message") }) });
      form.reset(); setSentInquiryId(inquiry.id);
    } catch (failure) { setError(housingError(failure)); } finally { setBusy(false); }
  }
  return <section className="housing-panel"><h2>Ask about this {item.kind === "LISTING" ? "place" : "housing request"}</h2><p className="muted">Introduce yourself, confirm dates, and ask about next steps. Inquiries are private between you and the poster; they do not reserve accommodation.</p>
    {sentInquiryId && <p className="housing-callout" role="status">Inquiry sent. <Link href={`/housing/inquiries?inquiry_id=${sentInquiryId}`}>Open your conversation</Link> to follow up and check replies.</p>}
    <form onSubmit={send}><label className="form-field"><span>Your message</span><textarea name="message" rows={4} minLength={1} maxLength={2000} required placeholder="Hi! Is this still available? I'm looking to move..." /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-primary" disabled={busy}>{busy ? "Sending..." : "Send inquiry"}</button></form>
  </section>;
}

function HousingReportForm({ id }: { id: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reported, setReported] = useState(false);
  async function report(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      await apiRequest<{ id: string; detail: string }>(`/housing/${id}/reports`, { method: "POST", body: JSON.stringify({ reason: data.get("reason"), details: data.get("details") }) });
      setReported(true);
    } catch (failure) { setError(housingError(failure)); } finally { setBusy(false); }
  }
  return <details className="housing-report"><summary>Report this housing post</summary>
    {reported ? <p role="status">Report recorded. Reporting does not automatically remove a post. For urgent safety concerns, contact the appropriate local authorities.</p>
      : <form onSubmit={report}><label className="form-field"><span>Reason</span><select name="reason"><option value="SCAM">Suspected scam</option><option value="INACCURATE">Inaccurate information</option><option value="DISCRIMINATION">Discriminatory content</option><option value="OTHER">Another concern</option></select></label>
        <label className="form-field"><span>Details</span><textarea required name="details" minLength={5} maxLength={2000} rows={3} /></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="button button-secondary" disabled={busy}>{busy ? "Sending report..." : "Submit report"}</button>
      </form>}
  </details>;
}

export default function HousingDetail({ id }: { id: string }) {
  const { data: item, setData, error, loading, reload } = useHousingResource<HousingItem>(`/housing/${id}`);
  const user = useHousingResource<User>("/users/me");
  if (loading || error || !item) return <HousingLoadState loading={loading} error={error} retry={reload} />;
  const owner = user.data?.id === item.owner_id;
  const unavailable = item.status !== "ACTIVE" || housingExpired(item);
  const facts: [string, string][] = [
    ["Space", ROOM_TYPES[item.room_type]], ["Arrangement", ARRANGEMENTS[item.arrangement]],
    ...(item.bedroom_count !== null ? [[item.kind === "LISTING" ? "Bedrooms in home" : "Minimum bedrooms wanted", housingLayout({ kind: item.kind, bedroom_count: item.bedroom_count, bathroom_count: null })] as [string, string]] : []),
    ...(item.bathroom_count !== null ? [[item.kind === "LISTING" ? "Bathrooms in home" : "Minimum bathrooms wanted", housingLayout({ kind: item.kind, bedroom_count: null, bathroom_count: item.bathroom_count })] as [string, string]] : []),
    ["Stay", STAY_TYPES[item.stay_type]], ["Furnishing", FURNISHINGS[item.furnishing]],
    ["Bathroom", BATHROOMS[item.bathroom]], ["Utilities", UTILITIES[item.utilities]],
    ["Minimum stay", `${item.minimum_stay_days} days`], ["Spaces available / needed", String(item.available_spaces)],
    ["Current occupants", item.occupants === null ? "Not specified" : String(item.occupants)],
    ["Deposit", item.deposit === null ? "Not specified" : housingMoney(item.deposit, item.currency)],
    ["One-time fees", item.fees === null ? "Not specified" : housingMoney(item.fees, item.currency)],
    ["Approval", APPROVALS[item.approval]],
  ];
  const household: [string, string][] = [
    ["Kitchen food policy", KITCHENS[item.kitchen]], ["Smoking / vaping", SMOKING[item.smoking]],
    ["Alcohol", ALCOHOL[item.alcohol]], ["Pets", PETS[item.pets]], ["Parking", yesNo(item.parking)],
    ["Laundry", yesNo(item.laundry)], ["Kitchen access", yesNo(item.kitchen_access)], ["Work-from-home suitable", yesNo(item.work_from_home)],
  ];
  return <>
    <Link className="text-link" href="/housing">← Back to housing</Link>
    <header className="housing-detail-heading">
      <div className="post-badges"><span className="category-pill">{HOUSING_KINDS[item.kind]}</span><HousingStatusBadge item={item} /></div>
      <h1>{item.title}</h1><p className="muted">{item.kind !== "LISTING" ? "Preferred area: " : ""}{item.location || [item.area, item.city, item.country_code].filter(Boolean).join(", ")}</p>
      {item.location && item.area && <p className="field-hint">{item.area}</p>}
      {item.kind !== "LISTING" && <p className="field-hint">This location is a search preference, not the address of an available home.</p>}
      <div className="housing-results-heading"><p className="housing-price">{housingMoney(item.amount, item.currency)} <span>/ {item.price_period.toLowerCase()}{item.kind !== "LISTING" ? " budget" : ""}</span></p><HousingSaveButton item={item} onChanged={setData} /></div>
      <p className="muted">Posted by <Link className="text-link" href={`/profile/${item.owner.id}`}>{item.owner.name}</Link> · {housingDate(item.created_at)}</p>
    </header>
    {unavailable && <p className="housing-callout">This post is {item.status === "FILLED" ? "filled or resolved" : item.status === "ARCHIVED" ? "archived" : "expired"}. It is no longer in discovery and new inquiries are disabled. Existing conversations remain available while the post is public.</p>}
    {owner && <section className="housing-panel"><h2>Manage your post</h2><p className="field-hint">Discovery expires {housingDate(item.expires_at)}. Renew only if the details and availability are still accurate. Making it public does not reopen or renew it.</p><HousingOwnerActions item={item} onChanged={setData} /><Link className="text-link" href="/housing/inquiries">Check housing inquiries →</Link></section>}
    <div className="housing-detail-columns">
      <div>
        <HousingGallery urls={item.photo_urls} title={item.title} detail />
        <section className="housing-panel"><h2>{item.kind === "LISTING" ? "About this place" : "What I'm looking for"}</h2><p className="housing-prose">{item.description}</p><p><strong>{item.kind === "LISTING" ? "Available" : "Move-in"}:</strong> {housingDate(item.available_from)}{item.available_until ? ` through ${housingDate(item.available_until)}` : " onward"}</p><dl className="housing-fact-list">{facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section>
        <section className="housing-panel"><h2>Home & household</h2><dl className="housing-fact-list">{household.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>{item.household_notes && <><h3>Household notes</h3><p className="housing-prose">{item.household_notes}</p></>}{item.accessibility_notes && <><h3>Accessibility</h3><p className="housing-prose">{item.accessibility_notes}</p></>}</section>
      </div>
      <aside className="housing-detail-sidebar">
        <HousingLoadState loading={user.loading} error={user.error} retry={user.reload} />
        {!user.loading && !user.error && !owner && !unavailable && <HousingInquiryForm item={item} />}
        <section className="housing-panel housing-safety"><h2>Before you commit</h2><p>Confirm the place, total charges, agreement, and permission to rent or sublet. Prices, photos, addresses, and approval claims are provided by members, not verified by the platform.</p><p>No booking, deposit collection, payments, or screening happens here. Share access instructions and contact details deliberately in private inquiries.</p></section>
        {!user.loading && !user.error && !owner && <HousingReportForm id={item.id} />}
      </aside>
    </div>
  </>;
}
