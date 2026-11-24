/**
 * Stylesheet of `oferta_institucional/comision_form.html` (the `<style>` block of the native template, verbatim).
 */
export const COMISION_FORM_CSS = `
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

/* ── Panel ────────────────────────────────────── */
.ci-panel {
    background: var(--bs-card-bg);
    border: 1px solid var(--bs-border-color);
    border-radius: 10px;
    overflow: hidden;
}

/* ── Section header ───────────────────────────── */
.ci-sec-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: .8rem 1.25rem;
    background: var(--bs-tertiary-bg);
    border-bottom: 1px solid var(--bs-border-color);
}
.ci-sec-title { font-weight: 600; font-size: .9rem; color: var(--bs-body-color); }

/* ── Form styles ──────────────────────────────── */
.ci-form { padding: 1.25rem; }
.ci-form .form-label {
    font-size: .72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; color: var(--bs-secondary-color); margin-bottom: .35rem;
}
.ci-form .form-control,
.ci-form .form-select {
    border: 1px solid var(--bs-border-color);
    border-radius: 8px;
    padding: .6rem .85rem;
    font-size: .88rem;
    background: var(--bs-body-bg);
    color: var(--bs-body-color);
}
.ci-form .form-control:focus,
.ci-form .form-select:focus {
    border-color: #4a7fe8;
    box-shadow: 0 0 0 2px rgba(74,127,232,.15);
}
.ci-form .text-danger { font-size: .78rem; }

/* ── Footer actions ───────────────────────────── */
.ci-footer {
    display: flex; align-items: center; justify-content: flex-end; gap: .5rem;
    padding: .85rem 1.25rem;
    border-top: 1px solid var(--bs-border-color);
    background: var(--bs-tertiary-bg);
}

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
`;
