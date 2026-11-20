/**
 * Stylesheet of `inscripcion_detail.html` (the `<style>` block of the native template, verbatim).
 */
export const INSCRIPCION_DETAIL_CSS = `
/* ── Hero ─────────────────────────────────────── */
.ci-hero {
    background: linear-gradient(135deg, #1a3a6e 0%, #1f3a93 50%, #3a6bc4 100%);
    border-radius: 12px;
    padding: 1.75rem 2rem;
    color: #fff;
    margin-bottom: 1.25rem;
    position: relative;
    overflow: hidden;
}
.ci-hero::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 220px; height: 220px;
    background: rgba(255,255,255,.06);
    border-radius: 50%;
    pointer-events: none;
}
.ci-back {
    display: inline-flex; align-items: center; justify-content: center;
    width: 34px; height: 34px;
    background: rgba(255,255,255,.15);
    border: 1px solid rgba(255,255,255,.25);
    border-radius: 8px;
    color: #fff; text-decoration: none;
    flex-shrink: 0;
    transition: background .15s;
}
.ci-back:hover { background: rgba(255,255,255,.25); color: #fff; }
.ci-hero-title { font-size: 1.5rem; font-weight: 700; line-height: 1.2; margin: .3rem 0 .2rem; }
.ci-hero-sub   { font-size: .83rem; opacity: .65; }
.ci-code-badge {
    font-family: monospace; font-size: .75rem; font-weight: 700;
    background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.25);
    padding: .2em .65em; border-radius: 5px; letter-spacing: .06em;
}
.ci-state-badge {
    font-size: .71rem; font-weight: 600;
    background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.2);
    padding: .2em .65em; border-radius: 5px; color: rgba(255,255,255,.85);
}
.ci-stat-val { font-size: 1rem; font-weight: 700; line-height: 1.1; }
.ci-stat-lbl { font-size: .64rem; opacity: .55; text-transform: uppercase; letter-spacing: .05em; }
.ci-edit-btn {
    background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.3);
    color: #fff; border-radius: 8px; font-size: .83rem;
    padding: .38rem .9rem; text-decoration: none; white-space: nowrap;
    transition: background .15s;
}
.ci-edit-btn:hover { background: rgba(255,255,255,.25); color: #fff; }

/* ── Panel ────────────────────────────────────── */
.ci-panel {
    background: var(--bs-card-bg);
    border: 1px solid var(--bs-border-color);
    border-radius: 10px;
    overflow: hidden;
}

/* ── Info grid ────────────────────────────────── */
.ci-info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: .75rem;
    padding: 1.25rem;
}
.ci-info-item {
    background: var(--bs-tertiary-bg);
    border: 1px solid var(--bs-border-color);
    border-radius: 8px;
    padding: .65rem .85rem;
}
.ci-lbl { font-size: .65rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--bs-secondary-color); display: block; margin-bottom: .2rem; }
.ci-val { font-size: .9rem; color: var(--bs-body-color); }

/* ── Pills ────────────────────────────────────── */
.ci-pill { display: inline-block; border-radius: 99px; font-size: .69rem; font-weight: 600; padding: .17em .65em; white-space: nowrap; }
.ci-pill-green  { background: rgba(34,197,94,.18)  !important; color: #4ade80 !important; }
.ci-pill-yellow { background: rgba(234,179,8,.18)  !important; color: #facc15 !important; }
.ci-pill-blue   { background: rgba(74,127,232,.2)  !important; color: #7eb3ff !important; }
.ci-pill-teal   { background: rgba(20,184,166,.18) !important; color: #2dd4bf !important; }
.ci-pill-red    { background: rgba(239,68,68,.18)  !important; color: #f87171 !important; }
.ci-pill-gray   { background: rgba(148,163,184,.15)!important; color: var(--bs-secondary-color) !important; }

/* ── Sidebar cards ────────────────────────────── */
.ci-scard {
    background: var(--bs-card-bg);
    border: 1px solid var(--bs-border-color);
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
    margin-bottom: .85rem;
}
.ci-scard:last-child { margin-bottom: 0; }
.ci-sc-title { font-size: .67rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--bs-secondary-color); margin: 0 0 .8rem; }

/* ── Audit row ────────────────────────────────── */
.ci-audit { display: flex; flex-wrap: wrap; gap: 1rem; font-size: .73rem; color: var(--bs-secondary-color); border-top: 1px solid var(--bs-border-color-translucent); padding: .75rem 1.25rem 1.25rem; }
    `;
