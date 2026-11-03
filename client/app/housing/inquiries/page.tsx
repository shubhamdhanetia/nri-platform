"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { apiRequest } from "../../../lib/api";
import { housingDate, housingError, useHousingResource, type HousingInquiry } from "../../../lib/housing";
import { HousingLoadState, HousingManageLinks } from "../../../components/HousingControls";

function InquiryThread({ inquiry, onChanged }: { inquiry: HousingInquiry; onChanged: (inquiry: HousingInquiry) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function reply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget;
    setBusy(true); setError("");
    try {
      const updated = await apiRequest<HousingInquiry>(`/housing/inquiries/${inquiry.id}/messages`, { method: "POST", body: JSON.stringify({ message: new FormData(form).get("message") }) });
      onChanged(updated); form.reset();
    } catch (failure) { setError(housingError(failure)); } finally { setBusy(false); }
  }
  return <article className="housing-panel housing-thread">
    <h2><Link href={`/housing/${inquiry.housing_id}`}>{inquiry.housing_title}</Link></h2>
    <p className="field-hint">{inquiry.sender.name} ↔ {inquiry.owner.name} · Started {housingDate(inquiry.created_at)}</p>
    <ol className="housing-messages">{inquiry.messages.map(message => <li key={message.id}>
      <div><strong>{message.sender_id === inquiry.sender.id ? inquiry.sender.name : inquiry.owner.name}</strong><time dateTime={message.created_at}>{housingDate(message.created_at)}</time></div>
      <p className="housing-prose">{message.content}</p>
    </li>)}</ol>
    <form onSubmit={reply}><label className="form-field"><span>Reply about {inquiry.housing_title}</span><textarea required name="message" minLength={1} maxLength={2000} rows={3} /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="button button-primary" disabled={busy}>{busy ? "Sending..." : "Send reply"}</button></form>
  </article>;
}

export default function HousingInquiriesPage() {
  const [page, setPage] = useState(0);
  const { data, setData, error, loading, reload } = useHousingResource<{ items: HousingInquiry[]; has_more: boolean }>(`/housing/inquiries?limit=20&offset=${page * 20}`);
  function change(updated: HousingInquiry) { setData(current => current ? { ...current, items: current.items.map(item => item.id === updated.id ? updated : item) } : current); }
  return <>
    <section className="page-heading"><div><p className="eyebrow">Talk through the details</p><h1>Housing inquiries</h1><p className="muted">Your private conversations about places and housing requests. Check here for replies; there are no email or push alerts.</p></div><button className="button button-secondary" onClick={reload} disabled={loading}>Refresh inquiries</button></section>
    <HousingManageLinks /><HousingLoadState loading={loading} error={error} retry={reload} />
    {!loading && !error && <>
      {data?.items.length ? data.items.map(item => <InquiryThread key={item.id} inquiry={item} onChanged={change} />) : <div className="empty-state"><h2>No inquiries on this page</h2><p className="muted">Start a conversation from a housing post. Posts made private or deleted are no longer accessible to other members.</p><Link className="button button-secondary" href="/housing">Find housing</Link></div>}
      <div className="housing-pagination"><button className="button button-secondary" disabled={page === 0} onClick={() => setPage(current => current - 1)}>Previous</button><span>Page {page + 1}</span><button className="button button-secondary" disabled={!data?.has_more} onClick={() => setPage(current => current + 1)}>Next</button></div>
    </>}
  </>;
}
