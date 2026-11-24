import { useEffect, useRef, useState } from "react";

/**
 * `TourHelp` of `vatTour.tsx` drawn in place instead of in a `<body>` portal: the `vat/partials/tour.html` include that sits in a
 * template's `{% block content %}` (the course commission wizard) is part of the page content, before the footer, so the Tab order
 * and the DOM order of the help button follow the include.
 */
const loaded = new Map<string, Promise<void>>();
function loadScript(src: string) {
  if (!loaded.has(src)) loaded.set(src, new Promise<void>((resolve) => {
    const element = document.createElement("script");
    element.src = src;
    element.onload = () => resolve();
    element.onerror = () => { loaded.delete(src); resolve(); };
    document.body.appendChild(element);
  }));
  return loaded.get(src)!;
}

type VatTour = { runSection: () => void; runGeneral: () => void; resetSeen: () => void };
const tour = () => (window as Window & { SisocVatTour?: VatTour }).SisocVatTour;

const TOUR_CSS = `
    #sisoc-vat-tour-btn {
        position: fixed;
        right: 1.5rem;
        bottom: 1.5rem;
        z-index: 1080;
        border-radius: 999px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        padding: 0.65rem 1.1rem;
        font-weight: 600;
    }
    #sisoc-vat-tour-btn .dropdown-menu {
        min-width: 14rem;
    }
`;

/** The floating help menu and the driver.js tour of the screen, in place (it never starts by itself). */
export function TourHelpInline({ section }: { section: string }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    (window as Window & { SISOC_VAT_TOUR?: unknown }).SISOC_VAT_TOUR = { section, autoStart: true };
    void loadScript("/static/custom/js/driver.js.iife.js").then(() => loadScript("/static/custom/js/vat_tour.js?v=20260607b"));
  }, [section]);
  useEffect(() => {
    if (!open) return undefined;
    const outside = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", outside);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("click", outside); document.removeEventListener("keydown", escape); };
  }, [open]);
  const run = (action: "section" | "general" | "reset") => (e: { preventDefault: () => void }) => {
    e.preventDefault();
    setOpen(false);
    const t = tour();
    if (!t) return;
    if (action === "general") t.runGeneral();
    else if (action === "reset") { t.resetSeen(); t.runSection(); } else t.runSection();
  };
  // The native partial sits in `customJS`, at the end of `<body>`: same DOM and Tab position.
  return (<>
    <link rel="stylesheet" href="/static/custom/css/driver.css" />
    <style>{TOUR_CSS}</style>
    <div ref={root} className={`dropup${open ? " show" : ""}`} id="sisoc-vat-tour-container">
      <button id="sisoc-vat-tour-btn" type="button" className={`btn btn-primary dropdown-toggle${open ? " show" : ""}`} data-vat-tour="help-button" aria-expanded={open}
        onClick={() => setOpen((v) => !v)}>
        <i className="fas fa-question-circle me-1" />{" "}Tour de ayuda{" "}
      </button>
      <ul className={`dropdown-menu dropdown-menu-end${open ? " show" : ""}`} style={open ? { position: "fixed", right: "1.5rem", bottom: "4.6rem", left: "auto", top: "auto", margin: 0 } : undefined}>
        <li><a className="dropdown-item" href="#" data-vat-tour-action="section" onClick={run("section")}><i className="fas fa-location-arrow me-2" />{" "}Tour de esta pantalla</a></li>
        <li><a className="dropdown-item" href="#" data-vat-tour-action="general" onClick={run("general")}><i className="fas fa-map me-2" />{" "}Tour general del modulo VAT</a></li>
        <li><hr className="dropdown-divider" /></li>
        <li><a className="dropdown-item text-muted" href="#" data-vat-tour-action="reset" onClick={run("reset")}><i className="fas fa-rotate-left me-2" />{" "}Reiniciar tours vistos</a></li>
      </ul>
    </div>
  </>);
}
