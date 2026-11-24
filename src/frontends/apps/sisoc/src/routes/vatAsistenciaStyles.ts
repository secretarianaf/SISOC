/**
 * Stylesheet of `asistencia_sesion.html` (the `<style>` block of the native template, verbatim).
 */
export const ASISTENCIA_CSS = `
.app-content-header { display: none; }

.asis-page {
    --cnav: #232D4F;
    --cteal: #3B8681;
    --ctext: #F2F2F2;
    --cmuted: rgba(255, 255, 255, 0.76);
    font-family: 'Montserrat', Inter, Roboto, sans-serif;
    color: #ffffff;
    margin: 0 auto 1rem;
    padding: 0 0 1rem;
}

/* ── Barra superior ── */
.asis-page-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    padding: .2rem .75rem 0;
    margin-bottom: .65rem;
}

.asis-back-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: .4rem;
    min-height: 32px;
    padding: 6px 16px;
    border-radius: 999px;
    border: 1px solid rgba(196, 201, 209, 0.9);
    background: #ffffff;
    color: #37465b;
    text-decoration: none;
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.asis-back-link:hover { color: #243244; background: #f6f8fb; }

/* ── Barra de título ── */
.asis-title-row {
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

.asis-title-block { flex: 1 1 auto; min-width: 0; }

.asis-title-block h1 {
    margin: 0;
    font-family: 'Lora', Georgia, 'Times New Roman', serif;
    font-size: 36px;
    font-weight: 700;
    color: #ffffff;
    line-height: 40px;
    letter-spacing: 1px;
}

.asis-title-sub {
    margin: .35rem 0 0;
    color: #ffffff;
    font-family: 'Lora', Georgia, 'Times New Roman', serif;
    font-size: 24px;
    font-weight: 700;
    line-height: 40px;
    letter-spacing: 1px;
}

.asis-status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    padding: .42rem .75rem;
    background: #2f9f51;
    border: 1px solid rgba(255, 255, 255, 0.22);
    color: #ffffff;
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .04em;
    line-height: 1;
    align-self: center;
}

/* ── Tarjetas de métricas ── */
.asis-metric-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 30px;
    margin-bottom: 30px;
    padding: 0 .75rem;
}

.asis-metric-card {
    position: relative;
    background: var(--cteal);
    border-radius: 20px;
    border-left: 10px solid #E7BA61;
    box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
    min-height: 120px;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.asis-metric-card--green { border-left-color: #6EA015; }
.asis-metric-card--red   { border-left-color: #C62828; }
.asis-metric-card--gold  { border-left-color: #E7BA61; }

.asis-metric-value {
    display: block;
    font-family: 'Lora', Georgia, 'Times New Roman', serif;
    font-size: 36px;
    line-height: 1.1;
    font-weight: 600;
    text-align: center;
    color: #ffffff;
}

.asis-metric-label {
    margin-top: .45rem;
    font-size: 20px;
    font-weight: 500;
    text-align: center;
    color: #ffffff;
}

/* ── Tarjeta de tabla ── */
.asis-card {
    background: #232D4F;
    border-radius: 15px;
    box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
    overflow: hidden;
    margin: 0 .75rem;
}

.asis-card-head {
    display: flex;
    align-items: center;
    gap: .55rem;
    background: #3B8681;
    border-bottom: 2px solid #ffffff;
    padding: .85rem 1.25rem;
    color: #ffffff;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 1px;
}

.asis-card-head i { font-size: 20px; line-height: 1; }

.asis-subhead {
    display: flex;
    align-items: center;
    gap: 30px;
    flex-wrap: wrap;
    background: #232D4F;
    padding: 20px 30px;
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1px;
    border-bottom: 1px solid rgba(229, 231, 235, 0.45);
}

.asis-subhead span { display: inline-flex; align-items: center; gap: .5rem; }
.asis-subhead i { font-size: 18px; }

.asis-tbl-scroll { overflow-x: auto; }

.asis-tbl {
    width: 100%;
    border-collapse: collapse;
    min-width: 720px;
}

.asis-tbl thead th {
    background: #232D4F;
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: .15px;
    text-align: left;
    padding: .65rem 1.25rem;
    height: 44px;
    border-top: 1px solid #E5E7EB;
    border-bottom: 1px solid #E5E7EB;
    white-space: nowrap;
}

.asis-tbl thead th.asis-col-check { width: 200px; }

.asis-tbl tbody td {
    color: #ffffff;
    font-size: 16px;
    font-weight: 400;
    letter-spacing: .15px;
    padding: .75rem 1.25rem;
    height: 56px;
    border-bottom: 1px solid rgba(229, 231, 235, 0.45);
    white-space: nowrap;
}

.asis-tbl tbody tr:hover td { background: rgba(255, 255, 255, 0.04); }

.asis-tbl-empty td {
    text-align: center;
    color: var(--cmuted);
    padding: 2.6rem 1rem;
    font-size: 14px;
}

/* ── Checkbox de presentismo ── */
.asis-mark {
    display: inline-flex;
    align-items: center;
    gap: .55rem;
    cursor: pointer;
    user-select: none;
    font-weight: 600;
    white-space: nowrap;
}

.asis-check {
    appearance: none;
    -webkit-appearance: none;
    width: 22px;
    height: 22px;
    border: 1.25px solid #ffffff;
    border-radius: 5px;
    background: transparent;
    cursor: pointer;
    position: relative;
    flex-shrink: 0;
    margin: 0;
    transition: background-color .12s ease, border-color .12s ease;
}

.asis-check::after {
    content: '';
    position: absolute;
    left: 7px;
    top: 3px;
    width: 6px;
    height: 11px;
    border: solid #ffffff;
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
    opacity: 0;
    transition: opacity .12s ease;
}

.asis-check:checked::after { opacity: 1; }
.asis-check--present:checked { background: #6EA015; border-color: #6EA015; }
.asis-check--absent:checked  { background: #C62828; border-color: #C62828; }
.asis-check:focus-visible { outline: 2px solid #E7BA61; outline-offset: 2px; }

.asis-mark-all { color: #ffffff; font-size: 16px; font-weight: 700; }

/* ── Tipo de alumno ── */
.asis-chip-vat {
    display: inline-block;
    border-radius: 6px;
    padding: .2em .7em;
    background: #ffffff;
    color: #232D4F;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .04em;
    line-height: 1.2;
}

.asis-tipo-sin-plan { color: var(--cmuted); font-size: .85rem; }

/* ── Pie de tabla ── */
.asis-foot {
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

.asis-pager { display: inline-flex; align-items: stretch; }

.asis-pager button {
    width: 36px;
    min-height: 32px;
    border: 1px solid #ffffff;
    background: transparent;
    color: #ffffff;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.asis-pager button:disabled { opacity: .4; cursor: default; }
.asis-pager-prev { border-radius: 12px 0 0 12px; border-right: 0; }
.asis-pager-next { border-radius: 0 12px 12px 0; border-left: 0; }

.asis-pager-label {
    border-top: 1px solid #ffffff;
    border-bottom: 1px solid #ffffff;
    padding: 0 .95rem;
    min-height: 32px;
    display: inline-flex;
    align-items: center;
    font-size: 14px;
    white-space: nowrap;
}

/* ── Acciones ── */
.asis-actions {
    display: flex;
    justify-content: flex-end;
    padding: 30px .75rem 0;
}

.asis-save {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 0;
    border-radius: 8px;
    background: #2f8f4f;
    color: #ffffff;
    font-size: 16px;
    font-weight: 600;
    padding: 12px 20px;
    cursor: pointer;
    transition: filter .2s ease;
}

.asis-save:hover { filter: brightness(1.08); }

.asis-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 3rem 1rem;
    color: var(--cmuted);
    text-align: center;
}
.asis-empty i { font-size: 2.2rem; margin-bottom: .65rem; opacity: .4; }
.asis-empty-t { font-weight: 600; font-size: .95rem; color: #fff; margin-bottom: .25rem; }
.asis-empty-s { font-size: .82rem; max-width: 320px; }

@media (max-width: 767.98px) {
    .asis-metric-grid { grid-template-columns: 1fr; gap: 1rem; }
    .asis-title-block h1 { font-size: 1.75rem; line-height: 1.15; }
    .asis-title-sub { font-size: 1.1rem; line-height: 1.3; }
    .asis-card-head { font-size: 20px; }
    .asis-subhead { font-size: 16px; gap: 1rem; }
}
`;
