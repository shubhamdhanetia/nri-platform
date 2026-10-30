"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import {
  BriefcaseBusiness, CalendarDays, Check, ChevronDown, Globe2, HeartPulse,
  House, MessagesSquare, Plane, ShoppingBag, Trophy, Users, Utensils, X,
} from "lucide-react";
import { POST_CATEGORIES, POST_CATEGORY_LABELS, type PostCategory } from "../lib/api";

export const CATEGORY_ICONS = {
  HOUSING: House, TRAVEL: Plane, JOBS: BriefcaseBusiness, FOOD: Utensils,
  EVENTS: CalendarDays, SPORTS: Trophy, IMMIGRATION: Globe2,
  MARKETPLACE: ShoppingBag, MEDICAL_SUPPORT: HeartPulse, GENERAL: MessagesSquare,
};

const OPTIONS = ["", ...POST_CATEGORIES] as const;
type Category = PostCategory | "";

function label(category: Category) {
  return category ? POST_CATEGORY_LABELS[category] : "All categories";
}

function CategoryIcon({ category }: { category: Category }) {
  const Icon = category ? CATEGORY_ICONS[category] : Users;
  return <Icon size={17} aria-hidden="true" />;
}

export default function CategoryFilter({
  value, onChange,
}: {
  value: Category;
  onChange: (category: Category) => void;
}) {
  const [visibleCount, setVisibleCount] = useState<number>(1);
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const measurements = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const sheet = useRef<HTMLDialogElement>(null);
  const id = useId();
  const hidden = OPTIONS.slice(visibleCount);
  const hiddenSelected = hidden.includes(value);

  useLayoutEffect(() => {
    const container = root.current;
    const measure = measurements.current;
    if (!container || !measure) return;
    const resize = () => {
      const buttons = Array.from(measure.querySelectorAll<HTMLElement>("[data-option]"));
      const widths = buttons.map(button => button.getBoundingClientRect().width);
      const available = container.getBoundingClientRect().width;
      const gap = 22;
      const total = widths.reduce((sum, width) => sum + width, 0) + gap * (widths.length - 1);
      if (total <= available) {
        setVisibleCount(OPTIONS.length);
        return;
      }
      let used = 0;
      let count = 0;
      for (let index = 0; index < widths.length; index++) {
        const next = used + (index ? gap : 0) + widths[index];
        const selectedHidden = OPTIONS.indexOf(value) > index;
        const reserve = measure.querySelector<HTMLElement>(
          selectedHidden ? "[data-selected-trigger]" : "[data-more-trigger]",
        )?.getBoundingClientRect().width ?? 0;
        if (next + gap + reserve > available) break;
        used = next;
        count = index + 1;
      }
      setVisibleCount(Math.max(1, count));
    };
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    observer.observe(measure);
    resize();
    return () => observer.disconnect();
  }, [value]);

  useEffect(() => {
    if (!open) return;
    menu.current?.querySelector<HTMLButtonElement>('[aria-checked="true"]')?.focus();
    if (!menu.current?.contains(document.activeElement)) {
      menu.current?.querySelector<HTMLButtonElement>("button")?.focus();
    }
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !root.current?.contains(event.target)) setOpen(false);
    };
    const media = window.matchMedia("(max-width: 760px)");
    const close = () => setOpen(false);
    document.addEventListener("pointerdown", dismiss);
    media.addEventListener("change", close);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      media.removeEventListener("change", close);
    };
  }, [open]);

  function choose(category: Category) {
    onChange(category);
    setOpen(false);
    sheet.current?.close();
    trigger.current?.focus();
  }

  return (
    <div className="category-filter" ref={root}>
      <div className="category-measurements" ref={measurements} aria-hidden="true" inert>
        {OPTIONS.map(category => (
          <button key={category} data-option className="category-tab" type="button">
            <CategoryIcon category={category} />{category ? label(category) : "All"}
          </button>
        ))}
        <button data-more-trigger className="category-tab" type="button">More <ChevronDown size={16} /></button>
        <button data-selected-trigger className="category-tab is-active" type="button">
          <CategoryIcon category={value} />{label(value)} <ChevronDown size={16} />
        </button>
      </div>
      <div className="category-desktop" role="group" aria-label="Post categories">
        {OPTIONS.slice(0, visibleCount).map(category => (
          <button className="category-tab" type="button" key={category}
            aria-pressed={value === category} onClick={() => onChange(category)}>
            <CategoryIcon category={category} />{category ? label(category) : "All"}
          </button>
        ))}
        {hidden.length > 0 && (
          <button ref={trigger} className={`category-tab${hiddenSelected ? " is-active" : ""}`}
            type="button" aria-haspopup="menu" aria-expanded={open} aria-controls={`${id}-menu`}
            onClick={() => setOpen(!open)}
            onKeyDown={event => {
              if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                setOpen(true);
              }
            }}>
            {hiddenSelected && <CategoryIcon category={value} />}
            {hiddenSelected ? label(value) : "More"} <ChevronDown size={16} aria-hidden="true" />
          </button>
        )}
        {open && hidden.length > 0 && (
          <div className="category-menu" id={`${id}-menu`} role="menu" aria-label="More categories" ref={menu}
            onBlur={event => {
              if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
            }}
            onKeyDown={event => {
              if (event.key === "Escape") {
                event.preventDefault();
                setOpen(false);
                trigger.current?.focus();
                return;
              }
              const items = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button"));
              const index = items.indexOf(document.activeElement as HTMLButtonElement);
              const next = event.key === "ArrowDown" ? (index + 1) % items.length
                : event.key === "ArrowUp" ? (index - 1 + items.length) % items.length
                : event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : -1;
              if (next >= 0) { event.preventDefault(); items[next].focus(); }
            }}>
            {hidden.map(category => (
              <button type="button" role="menuitemradio" aria-checked={value === category}
                key={category} onClick={() => choose(category)}>
                <CategoryIcon category={category} />{label(category)}
                {value === category && <Check size={17} aria-hidden="true" />}
              </button>
            ))}
          </div>
        )}
      </div>
      <button className="category-mobile-trigger" type="button" aria-haspopup="dialog"
        onClick={() => {
          sheet.current?.showModal();
          sheet.current?.querySelector<HTMLButtonElement>('[aria-pressed="true"]')?.focus();
        }}>
        <CategoryIcon category={value} />
        <span>Category: <strong>{label(value)}</strong></span>
        <ChevronDown size={17} aria-hidden="true" />
      </button>
      <dialog className="category-sheet" ref={sheet} aria-labelledby={`${id}-title`}
        onClick={event => { if (event.target === event.currentTarget) sheet.current?.close(); }}>
        <div className="category-sheet-content">
          <header><h2 id={`${id}-title`}>Choose a category</h2>
            <button type="button" className="community-icon-button" aria-label="Close categories"
              onClick={() => sheet.current?.close()}><X size={20} /></button>
          </header>
          <div className="category-sheet-options" role="group" aria-label="Post categories">
            {OPTIONS.map(category => (
              <button key={category} type="button" aria-pressed={value === category}
                onClick={() => choose(category)}>
                <CategoryIcon category={category} />{label(category)}
                {value === category && <Check size={17} aria-hidden="true" />}
              </button>
            ))}
          </div>
        </div>
      </dialog>
    </div>
  );
}
