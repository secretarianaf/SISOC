/**
 * Stylesheet of `inscripciones_asistencia.html` (the `<style>` block of the native template, verbatim).
 */
export const REPORTE_CSS = `
.app-content-header { display: none; }

.rep-page {
    --cnav: #232D4F;
    --cteal: #3B8681;
    --cgold: #E7BA61;
    --ctext: #F2F2F2;
    --cmuted: rgba(255, 255, 255, 0.76);
    font-family: 'Montserrat', Inter, Roboto, sans-serif;
    color: #ffffff;
    margin: 0 auto 1rem;
    padding: 0 0 1rem;
}

/* ── Barra de título ── */
.rep-title-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    background: var(--cnav);
    border-radius: 0 0 14px 14px;
    padding: 1.25rem 1.5rem 1.15rem;
    box-shadow: 0 14px 20px rgba(18, 28, 46, 0.16);
    margin-bottom: 30px;
}

.rep-title-block { flex: 1 1 auto; min-width: 0; }

.rep-title-block h1 {
    margin: 0;
    font-family: 'Lora', Georgia, 'Times New Roman', serif;
    font-size: 32px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.2;
    letter-spacing: 1px;
}

.rep-title-sub {
    margin: .55rem 0 0;
    color: rgba(255, 255, 255, 0.78);
    font-size: 14px;
    line-height: 1.4;
    max-width: 760px;
}

.rep-status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    padding: .42rem .75rem;
    background: var(--cteal);
    border: 1px solid rgba(255, 255, 255, 0.22);
    color: #ffffff;
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .04em;
    text-transform: uppercase;
    line-height: 1;
    align-self: center;
    white-space: nowrap;
}

/* ── Tarjeta genérica (filtros + tablas) ── */
.rep-card {
    background: #232D4F;
    border-radius: 15px;
    box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
    overflow: hidden;
    margin: 0 .75rem 30px;
}

.rep-card-head {
    display: flex;
    align-items: center;
    gap: .55rem;
    background: #3B8681;
    border-bottom: 2px solid #ffffff;
    padding: .85rem 1.25rem;
    color: #ffffff;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 1px;
}

.rep-card-head i { font-size: 20px; line-height: 1; }

.rep-card-body { padding: 24px 30px; }

/* ── Filtros ── */
.rep-filter-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: 16px 20px;
}

.rep-field { display: flex; flex-direction: column; min-width: 0; }

.rep-field__label {
    font-size: .72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: var(--cmuted);
    margin-bottom: .35rem;
}

.rep-page select,
.rep-page input[type="date"],
.rep-page input[type="search"],
.rep-page input[type="text"] {
    width: 100%;
    background: #1b2942;
    border: 1px solid #2a3a4a;
    color: #ffffff;
    border-radius: 8px;
    padding: .5rem .7rem;
    font-size: .88rem;
    line-height: 1.3;
}

.rep-page select:focus,
.rep-page input:focus {
    outline: none;
    border-color: var(--cgold);
    box-shadow: 0 0 0 2px rgba(231, 186, 97, 0.18);
}

.rep-page select option { background: #1b2942; color: #ffffff; }

.rep-filter-actions {
    display: flex;
    flex-wrap: wrap;
    gap: .65rem;
    margin-top: 22px;
}

.rep-btn {
    display: inline-flex;
    align-items: center;
    gap: .45rem;
    min-height: 38px;
    padding: 8px 18px;
    border-radius: 8px;
    border: 1px solid transparent;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
    transition: filter .2s ease, background-color .2s ease;
}

.rep-btn--primary { background: #2f8f4f; color: #ffffff; }
.rep-btn--primary:hover { filter: brightness(1.08); color: #ffffff; }
.rep-btn--ghost {
    background: transparent;
    border-color: rgba(255, 255, 255, 0.35);
    color: #ffffff;
}
.rep-btn--ghost:hover { background: rgba(255, 255, 255, 0.08); color: #ffffff; }

.rep-detalle-export {
    margin-left: auto;
    display: flex;
    gap: .5rem;
    flex-wrap: wrap;
}
.rep-detalle-export .rep-btn { min-height: 32px; padding: 5px 12px; font-size: 12px; }

/* ── Filtros dinámicos ── */
.rep-filter-toolbar {
    display: flex;
    align-items: center;
    gap: .65rem;
    flex-wrap: wrap;
    margin-bottom: 1.1rem;
}
.rep-filter-toolbar > .rep-filter-toolbar__title {
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
}
.rep-add-filter {
    min-height: 38px;
    border-radius: 8px;
    border: 1px dashed rgba(255, 255, 255, 0.5);
    background: rgba(255, 255, 255, 0.05);
    color: #ffffff;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
}
.rep-add-filter:focus { outline: none; border-color: #E7BA61; }
.rep-add-filter option { color: #1c2742; background: #ffffff; }
.rep-filter-hint { color: rgba(255, 255, 255, 0.6); font-size: 12px; }
.rep-field.is-hidden { display: none !important; }
.rep-field { position: relative; }
.rep-field__remove {
    position: absolute;
    top: 0; right: 0;
    width: 22px; height: 22px;
    border: 0;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.1);
    color: #ffffff;
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
.rep-field__remove:hover { background: rgba(198, 40, 40, 0.65); }

/* ── Métricas ── */
.rep-metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 24px;
    margin: 0 .75rem 30px;
}

.rep-metric-card {
    position: relative;
    background: var(--cteal);
    border-radius: 20px;
    border-left: 10px solid var(--cgold);
    box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
    min-height: 120px;
    padding: 1.1rem 1.25rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.rep-metric-card--green { border-left-color: #6EA015; }
.rep-metric-card--red   { border-left-color: #C62828; }
.rep-metric-card--gold  { border-left-color: #E7BA61; }

.rep-metric__label {
    margin: 0 0 .3rem;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: rgba(255, 255, 255, 0.85);
}

.rep-metric__value {
    display: block;
    font-family: 'Lora', Georgia, 'Times New Roman', serif;
    font-size: 34px;
    line-height: 1.1;
    font-weight: 700;
    color: #ffffff;
}

.rep-metric__support {
    margin-top: .35rem;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.7);
}

/* ── Toolbar de tabla ── */
.rep-tbl-toolbar {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    padding: 18px 30px;
}

.rep-tbl-toolbar .rep-field { flex: 1 1 320px; max-width: 420px; }

.rep-tbl-counter { font-size: 13px; color: var(--cmuted); white-space: nowrap; }

/* ── Tabla ── */
.rep-tbl-scroll { overflow-x: auto; }

.rep-tbl {
    width: 100%;
    border-collapse: collapse;
}

.rep-tbl thead th {
    background: #232D4F;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: .15px;
    text-align: left;
    padding: .65rem 1rem;
    height: 44px;
    border-top: 1px solid #E5E7EB;
    border-bottom: 1px solid #E5E7EB;
    white-space: nowrap;
}

.rep-tbl tbody td {
    color: #ffffff;
    font-size: 14px;
    font-weight: 400;
    letter-spacing: .15px;
    padding: .65rem 1rem;
    height: 52px;
    border-bottom: 1px solid rgba(229, 231, 235, 0.45);
    white-space: nowrap;
}

.rep-tbl tbody tr:hover td { background: rgba(255, 255, 255, 0.04); }

.rep-tbl-empty td {
    text-align: center;
    color: var(--cmuted);
    padding: 2.6rem 1rem;
    font-size: 14px;
}

.rep-pill {
    display: inline-block;
    border-radius: 99px;
    font-size: .69rem;
    font-weight: 600;
    padding: .17em .65em;
    background: rgba(74, 127, 232, 0.25);
    color: #7eb3ff;
    white-space: nowrap;
}

.rep-pill--vat {
    background: rgba(20, 184, 166, 0.2);
    color: #2dd4bf;
}

.rep-pill--sin-plan {
    background: rgba(148, 163, 184, 0.18);
    color: #a9b5c7;
}

/* ── Pie + paginador ── */
.rep-tbl-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    background: #232D4F;
    border-top: 1px solid #E5E7EB;
    padding: .8rem 1.25rem;
    color: #ffffff;
    font-size: 14px;
    border-radius: 0 0 15px 15px;
}

.rep-pager { display: inline-flex; align-items: stretch; }

.rep-pager > * {
    min-height: 32px;
    border: 1px solid #ffffff;
    background: transparent;
    color: #ffffff;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0 .85rem;
    font-size: 13px;
    text-decoration: none;
}

.rep-pager > *.is-disabled { opacity: .4; cursor: default; pointer-events: none; }
.rep-pager-prev { border-radius: 12px 0 0 12px; border-right: 0; }
.rep-pager-next { border-radius: 0 12px 12px 0; border-left: 0; }
.rep-pager-label {
    border-left: 1px solid #ffffff;
    border-right: 1px solid #ffffff;
    white-space: nowrap;
}

@media (max-width: 991.98px) {
    .rep-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 767.98px) {
    .rep-metric-grid { grid-template-columns: 1fr; }
    .rep-title-block h1 { font-size: 1.6rem; }
    .rep-card-head { font-size: 19px; }
    .rep-card-body { padding: 18px 16px; }
    .rep-tbl-toolbar { padding: 16px; }
}

`;
