"use client";

import { useState } from "react";
import Link from "next/link";
import HousingCard from "./HousingCard";
import { HousingLoadState, HousingManageLinks, HousingOwnerActions, HousingSaveButton } from "./HousingControls";
import { HOUSING_STATUSES, useHousingResource, type HousingCollection, type HousingItem } from "../lib/housing";

export default function HousingMyPosts({ saved = false }: { saved?: boolean }) {
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState("ALL");
  const statusQuery = saved || filter === "ALL" ? "" : filter === "EXPIRED" ? "&status=ACTIVE&expired=true" : `&status=${filter}${filter === "ACTIVE" ? "&expired=false" : ""}`;
  const { data, setData, error, loading, reload } = useHousingResource<HousingCollection>(`/housing/${saved ? "saved" : "me"}?limit=20&offset=${page * 20}${statusQuery}`);
  const items = data?.items;
  function change(updated: HousingItem) {
    setData(current => current ? { ...current, items: current.items.flatMap(item => item.id !== updated.id ? [item] : saved && !updated.my_saved ? [] : [updated]) } : current);
    if (!saved && filter !== "ALL") reload();
  }
  function removed(id: string) { setData(current => current ? { ...current, items: current.items.filter(item => item.id !== id) } : current); }
  return <>
    <section className="page-heading"><div><p className="eyebrow">Your housing corner</p><h1>{saved ? "Saved housing" : "My housing"}</h1><p className="muted">{saved ? "Keep track of places and people. Saved access still respects privacy and deletion." : "Keep availability fresh, manage visibility, and close posts when your search is over."}</p></div><Link className="button button-primary" href="/housing/new">New housing post</Link></section>
    <HousingManageLinks />
    {!saved && <label className="form-field housing-status-select"><span>Post status</span><select value={filter} onChange={event => { setFilter(event.target.value); setPage(0); }}><option value="ALL">All statuses</option>{Object.entries(HOUSING_STATUSES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}<option value="EXPIRED">Expired</option></select></label>}
    <HousingLoadState loading={loading} error={error} retry={reload} />
    {!loading && !error && <>
      {items?.length ? <div className="housing-grid">{items.map(item => <HousingCard key={item.id} item={item}>{saved ? <HousingSaveButton item={item} onChanged={change} /> : <HousingOwnerActions item={item} onChanged={change} onDeleted={removed} />}</HousingCard>)}</div>
        : <div className="empty-state"><h2>{saved ? "No saved housing on this page" : "No housing posts with this status on this page"}</h2><p className="muted">Browse housing or share a place or a housing request.</p><Link className="button button-secondary" href="/housing">Explore housing</Link></div>}
      <div className="housing-pagination"><button className="button button-secondary" disabled={page === 0} onClick={() => setPage(current => current - 1)}>Previous</button><span>Page {page + 1}</span><button className="button button-secondary" disabled={!data?.has_more} onClick={() => setPage(current => current + 1)}>Next</button></div>
    </>}
    {!saved && <p className="housing-callout">Active public posts leave discovery after 30 days unless renewed. Filled, archived, and expired posts keep their saved links and inquiries while public. Private posts are visible only to you.</p>}
  </>;
}
