"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import { HOUSEHOLD_LANGUAGES, type HouseholdLanguage } from "../lib/housing";

export default function HousingLanguages({ label, hint, defaultValue = [], emptyLabel = "Not specified" }: {
  label: string; hint: string; defaultValue?: HouseholdLanguage[]; emptyLabel?: string;
}) {
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<HouseholdLanguage[]>(defaultValue);
  const [query, setQuery] = useState("");
  const options = Object.keys(HOUSEHOLD_LANGUAGES).filter((key): key is HouseholdLanguage => key in HOUSEHOLD_LANGUAGES);
  const matches = options.filter(language => HOUSEHOLD_LANGUAGES[language].toLowerCase().includes(query.trim().toLowerCase()));
  const summary = selected.length > 2 ? `${selected.length} languages selected`
    : selected.length ? selected.map(language => HOUSEHOLD_LANGUAGES[language]).join(" + ") : emptyLabel;
  useEffect(() => {
    const form = root.current?.closest("form");
    const reset = () => { setSelected(defaultValue); setQuery(""); setOpen(false); };
    form?.addEventListener("reset", reset);
    return () => form?.removeEventListener("reset", reset);
  }, [defaultValue]);
  useEffect(() => {
    if (!open) return;
    searchInput.current?.focus();
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !root.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  return <div ref={root} className="form-field housing-languages"
    onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}
    onKeyDown={event => {
      if (event.key === "Escape" && open) {
        event.preventDefault(); event.stopPropagation(); setOpen(false); trigger.current?.focus();
      }
    }}>
    <span id={`${id}-label`}>{label}</span>
    {selected.map(language => <input key={language} type="hidden" name="household_languages" value={language} />)}
    <button ref={trigger} type="button" className="housing-language-trigger"
      aria-labelledby={`${id}-label ${id}-selection`} aria-expanded={open} aria-controls={`${id}-panel`}
      onClick={() => { setQuery(""); setOpen(value => !value); }}>
      <span id={`${id}-selection`}>{summary}</span><ChevronDown size={16} aria-hidden="true" />
    </button>
    {open && <div id={`${id}-panel`} className="housing-language-panel" role="group" aria-labelledby={`${id}-label`} aria-describedby={`${id}-hint`}>
      <label className="housing-language-search"><Search size={16} aria-hidden="true" /><input ref={searchInput} type="search" aria-label="Search languages" placeholder="Search languages..." value={query} onChange={event => setQuery(event.target.value)}
        onKeyDown={event => { if (event.key === "Enter") event.preventDefault(); }} /></label>
      <div className="housing-language-options">
        {matches.map(language => <label key={language} className="housing-language-option">
          <input type="checkbox" value={language} checked={selected.includes(language)} onChange={event => {
            const checked = event.target.checked;
            setSelected(current => checked ? [...current, language] : current.filter(value => value !== language));
          }} /><span>{HOUSEHOLD_LANGUAGES[language]}</span>
        </label>)}
      </div>
      {!matches.length && <p className="housing-language-empty" role="status">No languages found. Try another search.</p>}
      <footer className="housing-language-footer">
        <div className="housing-language-actions">
          <span role="status">{selected.length} selected</span>
          <button type="button" className="text-link" disabled={!selected.length && !query} onClick={() => { setSelected([]); setQuery(""); searchInput.current?.focus(); }}>Clear selections</button>
          <button type="button" className="housing-language-done" onClick={() => { setOpen(false); trigger.current?.focus(); }}>Done</button>
        </div>
        <details className="housing-language-info"><summary>About language information</summary><p id={`${id}-hint`}>{hint}</p></details>
      </footer>
    </div>}
  </div>;
}
