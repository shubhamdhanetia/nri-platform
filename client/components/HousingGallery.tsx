"use client";

import { useEffect, useRef, useState, type PointerEvent } from "react";
import { ChevronLeft, ChevronRight, Expand, Home, X, ZoomIn, ZoomOut } from "lucide-react";

export function HousingPhoto({ url, title }: { url?: string; title: string }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  return url && failedUrl !== url
    // External photo URLs are loaded directly, never through an image proxy.
    // eslint-disable-next-line @next/next/no-img-element
    ? <img className="housing-photo" src={url} alt={title} loading="lazy" referrerPolicy="no-referrer" draggable={false} onError={() => setFailedUrl(url)} />
    : <div className="housing-photo housing-photo-placeholder" role="img" aria-label={url ? `${title}: photo unavailable` : "No photos added"}><Home size={30} aria-hidden="true" /><span>{url ? "Photo unavailable" : "No photos added"}</span></div>;
}

function PhotoViewer({ urls, title, index, onChange, onClose }: {
  urls: string[]; title: string; index: number; onChange: (index: number) => void; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [natural, setNatural] = useState({ width: 0, height: 0 });
  const [failed, setFailed] = useState(false);
  const drag = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const fit = natural.width && size.width ? Math.min(size.width / natural.width, size.height / natural.height, 1) : 1;
  const maxZoom = Math.min(3, 1 / fit);
  const displayZoom = Math.min(zoom, maxZoom);
  const width = natural.width * fit * displayZoom;
  const height = natural.height * fit * displayZoom;

  useEffect(() => {
    const element = dialog.current;
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    element?.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      element?.close();
      document.body.style.overflow = previousOverflow;
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus({ preventScroll: true });
    };
  }, []);
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setSize({ width: element.clientWidth, height: element.clientHeight }));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const neighbours = [urls[index - 1], urls[index + 1]].filter(Boolean);
    for (const url of neighbours) {
      const image = new Image();
      image.referrerPolicy = "no-referrer";
      image.src = url;
    }
  }, [index, urls]);

  function move(next: number) {
    if (next < 0 || next >= urls.length) return;
    setZoom(1); setNatural({ width: 0, height: 0 }); setFailed(false);
    if (viewport.current) viewport.current.scrollTo(0, 0);
    onChange(next);
  }
  function pointerDown(event: PointerEvent<HTMLDivElement>) {
    if (!event.isPrimary || event.button !== 0) return;
    drag.current = { x: event.clientX, y: event.clientY, left: event.currentTarget.scrollLeft, top: event.currentTarget.scrollTop };
    if (displayZoom > 1) event.currentTarget.setPointerCapture(event.pointerId);
  }
  function pointerUp(event: PointerEvent<HTMLDivElement>) {
    const start = drag.current;
    drag.current = null;
    if (!start || displayZoom > 1 || event.pointerType === "mouse") return;
    const dx = event.clientX - start.x, dy = event.clientY - start.y;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) move(index + (dx < 0 ? 1 : -1));
  }

  return <dialog ref={dialog} className="housing-lightbox" aria-label={`Photos of ${title}`} onCancel={event => {
    event.preventDefault(); event.stopPropagation(); onClose();
  }} onKeyDown={event => {
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); onClose(); }
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault(); event.stopPropagation(); move(index + (event.key === "ArrowRight" ? 1 : -1));
    }
  }}>
    <header className="housing-lightbox-header">
      <div><h2>{title}</h2><p aria-live="polite">Photo {index + 1} of {urls.length}</p></div>
      <div className="housing-lightbox-tools">
        <button type="button" aria-label="Zoom out" disabled={displayZoom <= 1} onClick={() => setZoom(Math.max(1, displayZoom - .5))}><ZoomOut size={21} /></button>
        <span aria-live="polite">{Math.round(displayZoom * 100)}%</span>
        <button type="button" aria-label="Zoom in" title="Zoom in (up to original resolution or 3x)" disabled={failed || !natural.width || displayZoom >= maxZoom} onClick={() => setZoom(Math.min(maxZoom, displayZoom + .5))}><ZoomIn size={21} /></button>
        <button type="button" aria-label="Close photo viewer" autoFocus onClick={onClose}><X size={24} /></button>
      </div>
    </header>
    <div ref={viewport} className={`housing-lightbox-viewport${displayZoom > 1 ? " zoomed" : ""}`} onPointerDown={pointerDown} onPointerUp={pointerUp} onPointerCancel={() => { drag.current = null; }} onPointerMove={event => {
      const start = drag.current;
      if (!start || displayZoom <= 1) return;
      event.currentTarget.scrollLeft = start.left - (event.clientX - start.x);
      event.currentTarget.scrollTop = start.top - (event.clientY - start.y);
    }}>
      <div className="housing-lightbox-canvas" style={{ minWidth: width || "100%", minHeight: height || "100%" }}>
        {failed ? <div className="housing-lightbox-error" role="status"><Home size={36} /><p>Photo unavailable. Try another photo.</p></div>
          // eslint-disable-next-line @next/next/no-img-element
          : <img key={`${index}-${urls[index]}`} src={urls[index]} alt={`${title}, photo ${index + 1} of ${urls.length}`} referrerPolicy="no-referrer" draggable={false}
            style={{ width: width || undefined, height: height || undefined, visibility: natural.width ? "visible" : "hidden" }}
            onLoad={event => setNatural({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })} onError={() => setFailed(true)} />}
        {!failed && !natural.width && <p className="housing-lightbox-loading" role="status">Loading photo...</p>}
      </div>
    </div>
    <footer className="housing-lightbox-footer">
      {urls.length > 1 && <button type="button" aria-label="Previous photo" disabled={index === 0} onClick={() => move(index - 1)}><ChevronLeft size={22} />Previous</button>}
      <p>{displayZoom > 1 ? "Drag or scroll to pan. Zoom out to browse photos." : urls.length > 1 ? "Use arrows or swipe to browse photos." : "Use zoom controls to inspect this photo."}</p>
      {urls.length > 1 && <button type="button" aria-label="Next photo" disabled={index === urls.length - 1} onClick={() => move(index + 1)}>Next<ChevronRight size={22} /></button>}
    </footer>
  </dialog>;
}

export default function HousingGallery({ urls, title, detail = false }: { urls: string[]; title: string; detail?: boolean }) {
  const [index, setIndex] = useState(0);
  const [open, setOpen] = useState(false);
  const swipe = useRef<{ x: number; y: number } | null>(null);
  const suppressClick = useRef(false);
  const current = Math.min(index, Math.max(0, urls.length - 1));
  function move(next: number) { setIndex(Math.max(0, Math.min(urls.length - 1, next))); }
  if (!urls.length) return null;
  return <div className={`housing-photo-gallery${detail ? " housing-photo-gallery-detail" : ""}`}>
    <div className="housing-photo-preview">
      <button className="housing-photo-open" type="button" aria-label={`Open photo ${current + 1} of ${urls.length}: ${title}`} onClick={() => {
        if (suppressClick.current) { suppressClick.current = false; return; }
        setOpen(true);
      }} onPointerDown={event => {
        suppressClick.current = false;
        if (event.pointerType !== "mouse" && event.isPrimary) swipe.current = { x: event.clientX, y: event.clientY };
      }} onPointerCancel={() => { swipe.current = null; }} onPointerUp={event => {
        const start = swipe.current; swipe.current = null;
        if (!start) return;
        const dx = event.clientX - start.x, dy = event.clientY - start.y;
        if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
          suppressClick.current = true; move(current + (dx < 0 ? 1 : -1));
        }
      }}>
        <HousingPhoto key={urls[current]} url={urls[current]} title={`${title}, photo ${current + 1}`} />
        <span className="housing-photo-expand" aria-hidden="true"><Expand size={16} /></span>
      </button>
      <span className="housing-photo-count" aria-live="polite">{current + 1} / {urls.length}</span>
      {urls.length > 1 && <>
        <button type="button" className="housing-photo-arrow previous" aria-label="Previous preview photo" disabled={current === 0} onClick={() => move(current - 1)}><ChevronLeft size={21} /></button>
        <button type="button" className="housing-photo-arrow next" aria-label="Next preview photo" disabled={current === urls.length - 1} onClick={() => move(current + 1)}><ChevronRight size={21} /></button>
      </>}
    </div>
    {detail && <>
      {urls.length > 1 && <div className="housing-photo-thumbnails" aria-label="Choose a photo">{urls.map((url, photoIndex) => <button key={`${photoIndex}-${url}`} type="button" aria-label={`Show photo ${photoIndex + 1}`} aria-pressed={current === photoIndex} onClick={() => move(photoIndex)}>
        <HousingPhoto url={url} title={`Photo ${photoIndex + 1}`} />
      </button>)}</div>}
      <button className="housing-gallery-button" type="button" aria-label={urls.length === 1 ? "View photo" : `View all ${urls.length} photos`} onClick={() => setOpen(true)}>
        <Expand size={18} aria-hidden="true" />
        <span>{urls.length === 1 ? "View photo" : "View all photos"}</span>
        <span className="housing-gallery-button-count" aria-hidden="true">{urls.length}</span>
      </button>
    </>}
    {open && <PhotoViewer urls={urls} title={title} index={current} onChange={setIndex} onClose={() => setOpen(false)} />}
  </div>;
}
