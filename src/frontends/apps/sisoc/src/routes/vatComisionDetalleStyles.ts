/**
 * Stylesheet of `comision_detail.html` (the `<style>` block of the native template, verbatim).
 */
export const COMISION_DETALLE_CSS = `
        .app-content-header { display: none; }

        .sisoc-centro-page {
            --cnav: #232D4F;
            --cpanel: #1e2e40;
            --cline: rgba(255, 255, 255, 0.14);
            --ctext: #F2F2F2;
            --cmuted: #a9b5c7;
            --cteal: #3B8681;
            --cblue: #7eb3ff;
            /* Reasignación de variables de Bootstrap para los estilos en línea heredados */
            --bs-body-color: #F2F2F2;
            --bs-secondary-color: #a9b5c7;
            --bs-tertiary-bg: #1e2e40;
            --bs-secondary-bg: #243650;
            --bs-card-bg: #1e2e40;
            --bs-body-bg: #16243a;
            --bs-border-color: #2a3a4a;
            --bs-border-color-translucent: rgba(255, 255, 255, 0.1);
            font-family: 'Montserrat', Inter, Roboto, sans-serif;
            color: #ffffff;
            max-width: 1620px;
            margin: 0 auto 1rem;
            background: transparent;
            border-radius: 20px;
            padding: 1rem;
        }

        .sisoc-page-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: .7rem;
            flex-wrap: wrap;
            background: #4f6e94;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: .55rem .7rem;
        }

        .sisoc-back-link {
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

        .sisoc-back-link:hover {
            color: #243244;
            background: #f6f8fb;
        }

        .sisoc-header-actions {
            display: flex;
            align-items: center;
            gap: .55rem;
            flex-wrap: wrap;
        }

        .sisoc-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 40px;
            flex-wrap: nowrap;
            background: var(--cnav);
            border: 0;
            border-radius: 20px;
            padding: 20px 30px;
            margin-bottom: 1.1rem;
        }

        .sisoc-title-block {
            flex: 1 1 auto;
            min-width: 0;
        }

        .sisoc-title-block h1 {
            margin: 0;
            font-family: 'Lora', Georgia, 'Times New Roman', serif;
            font-size: 36px;
            font-weight: 700;
            color: #ffffff;
            line-height: 40px;
            letter-spacing: 1px;
        }

        .sisoc-title-sub {
            margin: .35rem 0 0;
            color: rgba(255, 255, 255, 0.72);
            font-size: 14px;
            letter-spacing: .5px;
        }

        .sisoc-title-meta {
            display: inline-flex;
            flex: 0 0 auto;
            align-items: center;
            justify-content: flex-end;
            gap: 20px;
            flex-wrap: nowrap;
            padding: 10px 0;
            align-self: center;
        }

        .sisoc-title-meta .sisoc-cue-text {
            color: #ffffff;
            font-family: 'Lora', Georgia, 'Times New Roman', serif;
            font-size: 22px;
            font-weight: 700;
            line-height: 40px;
            letter-spacing: 1px;
            white-space: nowrap;
        }

        .sisoc-status-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            padding: 8px 10px;
            background: #2F8F5B;
            border: 1px solid rgba(255, 255, 255, 0.22);
            color: #ffffff;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .04em;
            text-transform: uppercase;
            line-height: 1;
        }

        .sisoc-info-shell {
            display: flex;
            align-items: stretch;
            background: var(--cnav);
            border: 1px solid var(--cline);
            border-radius: 20px;
            box-shadow: 0 4px 4px 0 rgba(0, 0, 0, 0.35);
            overflow: hidden;
            min-height: 524px;
        }

        .sisoc-info-content {
            flex: 1 1 auto;
            min-width: 0;
        }

        .sisoc-info-panel {
            display: none;
            padding: 30px;
        }

        .sisoc-info-panel.is-active {
            display: block;
        }

        .sisoc-info-panel--overflow {
            overflow: visible;
        }

        .sisoc-side-tabs {
            display: flex;
            align-items: stretch;
            flex-shrink: 0;
        }

        .sisoc-side-tabs--left { justify-content: flex-start; }
        .sisoc-side-tabs--right { justify-content: flex-end; }
        .sisoc-side-tab[hidden] { display: none; }

        .sisoc-side-tab {
            width: 54px;
            border: 0;
            background: var(--cteal);
            color: #ffffff;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: background-color .2s ease;
        }

        .sisoc-side-tabs--left .sisoc-side-tab + .sisoc-side-tab,
        .sisoc-side-tabs--right .sisoc-side-tab + .sisoc-side-tab {
            border-left: 1px solid rgba(255, 255, 255, 0.08);
        }

        .sisoc-side-tab:hover,
        .sisoc-side-tab:focus {
            background: #347a6b;
            outline: none;
        }

        .sisoc-side-tabs--left .sisoc-side-tab:first-child {
            border-top-left-radius: 20px;
            border-bottom-left-radius: 20px;
        }

        .sisoc-side-tabs--right .sisoc-side-tab:last-child {
            border-top-right-radius: 20px;
            border-bottom-right-radius: 20px;
        }

        .sisoc-side-tab span {
            writing-mode: vertical-rl;
            transform: rotate(180deg);
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 1px;
            white-space: nowrap;
            color: #ffffff;
            line-height: 1;
        }

        .sisoc-panel-section + .sisoc-panel-section { margin-top: 30px; }

        .sisoc-section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }

        .sisoc-section-header h2 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
            color: var(--ctext);
            letter-spacing: 1px;
            line-height: 40px;
        }

        .sisoc-section-divider {
            height: 2px;
            border: 0;
            margin: 0 0 20px;
            background: rgba(255, 255, 255, 0.95);
        }

        .sisoc-general-layout {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 280px;
            gap: 30px;
            align-items: start;
        }

        .sisoc-general-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 18px 40px;
        }

        .sisoc-data-item { min-width: 0; }

        .sisoc-data-label {
            margin: 0 0 .22rem;
            color: var(--ctext);
            font-size: 15px;
            font-weight: 400;
            letter-spacing: 1px;
            line-height: 20px;
        }

        .sisoc-data-value {
            margin: 0;
            color: var(--ctext);
            font-size: 16px;
            font-weight: 600;
            letter-spacing: 1px;
            line-height: 25px;
            word-break: break-word;
        }

        .sisoc-data-value a { color: #ffffff; text-decoration: none; }
        .sisoc-data-value a:hover { text-decoration: underline; }

        .sisoc-referente-list {
            list-style: none;
            margin: 0;
            padding: 0;
            display: grid;
            gap: 10px;
        }

        .sisoc-referente-item {
            display: flex;
            align-items: baseline;
            gap: 10px;
            line-height: 1.3;
        }

        .sisoc-referente-icon {
            width: 20px;
            flex: 0 0 20px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-size: 15px;
        }

        .sisoc-referente-copy span {
            color: var(--ctext);
            font-size: 15px;
            font-weight: 400;
            letter-spacing: 1px;
        }

        .sisoc-referente-copy strong {
            color: var(--ctext);
            font-size: 16px;
            font-weight: 600;
            letter-spacing: 1px;
            margin-left: 6px;
        }

        .sisoc-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: .4rem;
            min-height: 32px;
            padding: 6px 14px;
            border-radius: 6px;
            border: 1px solid transparent;
            text-decoration: none;
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            transition: filter .2s ease;
        }

        .sisoc-btn:hover,
        .sisoc-btn:focus { filter: brightness(1.08); color: #ffffff; outline: none; }
        .sisoc-btn--add { background: #2e7d33; color: #ffffff; }
        .sisoc-btn--edit { background: #4e6f95; border-color: rgba(215, 226, 244, 0.2); color: #ffffff; }
        .sisoc-btn--view { background: #2e6fd1; color: #ffffff; }
        .sisoc-btn--delete { background: #d04545; border-color: rgba(255, 255, 255, 0.2); color: #ffffff; }

        .sisoc-empty-state {
            padding: 2.4rem 1rem;
            text-align: center;
            color: var(--cmuted);
            font-size: 13px;
        }

        /* ── Tarjeta de ocupación de cupo ──────────── */
        .sisoc-cupo-card {
            background: var(--cpanel);
            border: 1px solid #2a3a4a;
            border-radius: 12px;
            padding: 1.1rem 1.25rem;
        }

        .sisoc-cupo-title {
            font-size: .67rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: .06em; color: var(--cmuted); margin: 0 0 .8rem;
        }

        .ci-cupo-num { font-size: 2rem; font-weight: 700; color: var(--cblue); line-height: 1; }
        .ci-cupo-sep { font-size: 1.4rem; color: #2a3a4a; font-weight: 300; }
        .ci-cupo-tot { font-size: 1.4rem; color: var(--cmuted); font-weight: 400; }
        .ci-cupo-lbl { font-size: .76rem; color: var(--cmuted); align-self: center; }
        .ci-prog { height: 7px; border-radius: 99px; background: rgba(255,255,255,.08); overflow: hidden; }
        .ci-prog-bar { height: 100%; border-radius: 99px; transition: width .4s; }

        /* ── Filas de listado (inscriptos, sesiones, horarios) ── */
        .ci-row {
            display: flex; align-items: center; gap: .85rem;
            padding: .8rem .25rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            transition: background .1s;
        }
        .ci-row:last-child { border-bottom: none; }
        .ci-row:hover { background: rgba(255, 255, 255, 0.04); }

        .ci-av {
            width: 32px; height: 32px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: .65rem; font-weight: 700; flex-shrink: 0; color: #fff;
        }
        .ci-av-1 { background: #3b5bdb; }
        .ci-av-2 { background: #7048e8; }
        .ci-av-3 { background: #1098ad; }
        .ci-av-4 { background: #2f9e44; }
        .ci-av-5 { background: #e8590c; }

        .ci-pill { display: inline-block; border-radius: 99px; font-size: .69rem; font-weight: 600; padding: .17em .65em; white-space: nowrap; }
        .ci-pill-green  { background: rgba(34,197,94,.2)  !important; color: #4ade80 !important; }
        .ci-pill-yellow { background: rgba(234,179,8,.2)  !important; color: #facc15 !important; }
        .ci-pill-blue   { background: rgba(74,127,232,.25)!important; color: #7eb3ff !important; }
        .ci-pill-teal   { background: rgba(20,184,166,.2) !important; color: #2dd4bf !important; }
        .ci-pill-red    { background: rgba(239,68,68,.2)  !important; color: #f87171 !important; }
        .ci-pill-gray   { background: rgba(148,163,184,.18)!important; color: #a9b5c7 !important; }

        .ci-sesnum { font-size: .67rem; font-weight: 700; color: var(--cmuted); width: 22px; text-align: right; flex-shrink: 0; }
        .ci-datetile {
            display: flex; flex-direction: column; align-items: center;
            background: rgba(74,127,232,.18); color: #7eb3ff;
            border-radius: 7px; padding: .3rem .5rem;
            min-width: 34px; flex-shrink: 0;
        }
        .ci-datetile .d  { font-size: .9rem; font-weight: 700; line-height: 1; }
        .ci-datetile .m  { font-size: .56rem; text-transform: uppercase; letter-spacing: .04em; }
        .ci-asist {
            font-size: .76rem; font-weight: 500; border-radius: 6px;
            padding: .26rem .6rem; white-space: nowrap;
            background: rgba(74,127,232,.18); color: #7eb3ff;
            text-decoration: none; display: inline-flex; align-items: center; gap: 4px;
            transition: background .12s;
        }
        .ci-asist:hover { background: rgba(74,127,232,.28); color: #7eb3ff; }
        .ci-asist-done { background: rgba(34,197,94,.18) !important; color: #4ade80 !important; }
        .ci-asist-done:hover { background: rgba(34,197,94,.28) !important; }

        .ci-dia {
            background: rgba(74,127,232,.22); color: #7eb3ff;
            border-radius: 6px; font-size: .73rem; font-weight: 700;
            padding: .25rem .6rem; white-space: nowrap; flex-shrink: 0;
        }

        .ci-iconbtn {
            width: 28px; height: 28px; padding: 0;
            display: inline-flex; align-items: center; justify-content: center;
            border-radius: 6px; font-size: .78rem;
            background: rgba(255,255,255,.08); color: var(--cmuted);
            text-decoration: none; border: none; cursor: pointer;
            transition: background .1s;
        }
        .ci-iconbtn:hover { background: rgba(255,255,255,.14); color: #fff; }
        .ci-iconbtn-danger:hover { background: rgba(239,68,68,.2) !important; color: #f87171 !important; }
        .ci-dots { background: transparent; border: none; padding: 3px 5px; color: var(--cmuted); cursor: pointer; border-radius: 5px; transition: background .1s; }
        .ci-dots:hover { background: rgba(255,255,255,.08); color: #fff; }
        .ci-dots::after { display: none !important; }

        .ci-empty { display: flex; flex-direction: column; align-items: center; padding: 3rem 1rem; color: var(--cmuted); text-align: center; }
        .ci-empty i { font-size: 2.2rem; margin-bottom: .65rem; opacity: .4; }
        .ci-empty-t { font-weight: 600; font-size: .9rem; color: #fff; margin-bottom: .2rem; }
        .ci-empty-s { font-size: .8rem; max-width: 250px; }

        .ci-audit { display: flex; flex-wrap: wrap; gap: 1rem; font-size: .73rem; color: var(--cmuted); border-top: 1px solid rgba(255,255,255,.1); padding: .9rem .25rem 0; margin-top: 1rem; }

        /* ── Tabla de inscriptos (diseño "Inscriptos") ──────────── */
        .ci-tbl-card {
            background: #232D4F;
            border-radius: 15px;
            box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .ci-tbl-head {
            display: flex;
            align-items: center;
            gap: .55rem;
            background: #3B8681;
            border-bottom: 2px solid #ffffff;
            padding: .85rem 1.25rem;
            color: #ffffff;
            font-family: 'Montserrat', Inter, Roboto, sans-serif;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
        }

        .ci-tbl-head i { font-size: 20px; line-height: 1; }

        .ci-tbl-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
            padding: 20px 30px;
        }

        .ci-tbl-search {
            position: relative;
            flex: 1 1 320px;
            max-width: 540px;
        }

        .ci-tbl-search i {
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--cmuted);
            font-size: .9rem;
        }

        .ci-tbl-search input {
            width: 100%;
            padding: .6rem .9rem .6rem 2.25rem;
            border-radius: 999px;
            border: 1px solid rgba(255, 255, 255, 0.25);
            background: rgba(255, 255, 255, 0.04);
            color: #ffffff;
            font-size: .9rem;
        }

        .ci-tbl-search input::placeholder { color: var(--cmuted); }
        .ci-tbl-search input:focus { outline: none; border-color: var(--cgold); }

        .ci-tbl-scroll { overflow-x: auto; }

        .ci-tbl {
            width: 100%;
            border-collapse: collapse;
            min-width: 820px;
        }

        .ci-tbl thead th {
            background: #232D4F;
            color: #ffffff;
            font-size: 16px;
            font-weight: 700;
            letter-spacing: .15px;
            text-align: left;
            padding: .65rem 1rem;
            height: 44px;
            border-top: 1px solid #E5E7EB;
            border-bottom: 1px solid #E5E7EB;
            white-space: nowrap;
        }

        .ci-tbl thead th.ci-tbl-col-actions { text-align: right; }

        .ci-tbl tbody td {
            color: #ffffff;
            font-size: 16px;
            font-weight: 400;
            letter-spacing: .15px;
            padding: .75rem 1rem;
            height: 56px;
            border-bottom: 1px solid rgba(229, 231, 235, 0.45);
            white-space: nowrap;
        }

        .ci-tbl tbody tr:hover td { background: rgba(255, 255, 255, 0.04); }
        .ci-tbl tbody td a { color: #ffffff; text-decoration: none; }
        .ci-tbl tbody td a:hover { text-decoration: underline; }

        .ci-tbl-actions {
            display: flex;
            gap: .5rem;
            justify-content: flex-end;
            white-space: nowrap;
        }

        .ci-tbl-empty td {
            text-align: center;
            color: var(--cmuted);
            padding: 2.6rem 1rem;
            font-size: 14px;
        }

        .ci-tbl-foot {
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
        }

        .ci-pager { display: inline-flex; align-items: stretch; }

        .ci-pager button {
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

        .ci-pager button:disabled { opacity: .4; cursor: default; }
        .ci-pager-prev { border-radius: 12px 0 0 12px; border-right: 0; }
        .ci-pager-next { border-radius: 0 12px 12px 0; border-left: 0; }

        .ci-pager-label {
            border-top: 1px solid #ffffff;
            border-bottom: 1px solid #ffffff;
            padding: 0 .95rem;
            min-height: 32px;
            display: inline-flex;
            align-items: center;
            font-size: 14px;
            white-space: nowrap;
        }

        .ci-row-name {
            display: block; font-weight: 600; font-size: .9rem; color: #fff;
            text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .ci-row-name:hover { color: var(--cblue); }
        .ci-row-sub { display: block; font-size: .76rem; color: var(--cmuted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        /* ── Modales (diseño nuevo navy/teal) ──────────── */
        .ci-modal .modal-content {
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            background: #232D4F !important;
            color: #f2f7ff;
            overflow: hidden;
            opacity: 1 !important;
        }
        .ci-modal .modal-header {
            padding: .85rem 1rem;
            background: #3B8681 !important;
            border-bottom: 2px solid #ffffff;
        }
        .ci-modal .modal-title { font-size: .98rem; font-weight: 600; color: #ffffff; }
        .ci-modal .btn-close { filter: brightness(0) invert(1); opacity: 1; }
        .ci-modal .modal-body { padding: 1rem; background: #232D4F !important; }
        .ci-modal .modal-footer {
            padding: .75rem 1rem;
            border-top: 1px solid rgba(255, 255, 255, 0.16);
            background: #232D4F !important;
        }
        /* ── Inputs dentro de los modales (diseño nuevo) ── */
        .ci-modal .form-label,
        .ci-modal .modal-body label {
            color: #e7eefb;
            font-weight: 600;
        }
        .ci-modal .form-control,
        .ci-modal .form-select,
        .ci-modal textarea,
        .ci-modal select,
        .ci-modal input[type="text"],
        .ci-modal input[type="email"],
        .ci-modal input[type="number"],
        .ci-modal input[type="date"],
        .ci-modal input[type="time"],
        .ci-modal input[type="tel"] {
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.55);
            background: rgba(255, 255, 255, 0.06);
            color: #ffffff;
            min-height: 40px;
            box-shadow: none;
            color-scheme: dark;
        }
        .ci-modal .form-control::placeholder,
        .ci-modal input::placeholder,
        .ci-modal textarea::placeholder {
            color: rgba(255, 255, 255, 0.55);
        }
        /* Solo las esquinas externas: las internas las achata Bootstrap para
           que el input-group se vea como un único control continuo. */
        .ci-modal .input-group > .btn:last-child {
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
        }
        .ci-modal .form-control:focus,
        .ci-modal .form-select:focus,
        .ci-modal textarea:focus,
        .ci-modal select:focus,
        .ci-modal input:focus {
            border-color: #3B8681;
            background: rgba(59, 134, 129, 0.12);
            box-shadow: 0 0 0 .18rem rgba(59, 134, 129, 0.25);
            color: #ffffff;
            outline: none;
        }
        .ci-modal select option {
            color: #ffffff;
            background: #1e2e40;
        }
        .ci-modal input[type="checkbox"],
        .ci-modal input[type="radio"] {
            accent-color: #3B8681;
        }

        @media (max-width: 991.98px) {
            .sisoc-general-layout { grid-template-columns: 1fr; }
        }

        @media (max-width: 767.98px) {
            .sisoc-centro-page { padding: .85rem; border-radius: 14px; }
            .sisoc-title-row { flex-wrap: wrap; align-items: flex-start; }
            .sisoc-title-block h1 { font-size: 30px; line-height: 34px; }
            .sisoc-info-shell { flex-direction: column; }
            .sisoc-side-tabs { order: -1; min-width: 100%; flex: 0 0 auto; }
            .sisoc-side-tab {
                flex: 1;
                min-height: 42px;
                border-left: 0;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
            }
            .sisoc-side-tab span { writing-mode: horizontal-tb; transform: none; font-size: 12px; }
            .sisoc-general-grid { grid-template-columns: 1fr; }
        }

        .sisoc-centro-page {
            --cnav: #232D4F;
            --cpanel: #273455;
            --cteal: #3B8681;
            --cblue: #E7BA61;
            --cgold: #E7BA61;
            --ctext: #F2F2F2;
            --cmuted: rgba(255, 255, 255, 0.76);
            max-width: 100%;
            margin: 0 auto 1rem;
            border-radius: 0;
            padding: 0 0 1rem;
        }

        .sisoc-page-top {
            background: transparent;
            border: 0;
            border-radius: 0;
            padding: .2rem .75rem 0;
            margin-bottom: .65rem;
        }

        .sisoc-title-row {
            align-items: flex-start;
            gap: 1rem;
            flex-wrap: wrap;
            background: var(--cnav);
            border-radius: 0 0 14px 14px;
            padding: 1.25rem 1.5rem 1.15rem;
            box-shadow: 0 14px 20px rgba(18, 28, 46, 0.16);
        }

        .sisoc-title-block h1 {
            font-size: 36px;
            line-height: 40px;
            letter-spacing: 1px;
        }

        .sisoc-title-sub {
            margin-top: .35rem;
            color: #ffffff;
            font-family: 'Lora', Georgia, 'Times New Roman', serif;
            font-size: 24px;
            font-weight: 700;
            line-height: 40px;
            letter-spacing: 1px;
        }

        .sisoc-title-meta {
            gap: .75rem;
            padding: 0;
        }

        .sisoc-title-meta .sisoc-cue-text {
            display: none;
        }

        .sisoc-status-pill {
            padding: .42rem .75rem;
            background: #2f9f51;
            font-size: .72rem;
            text-transform: none;
        }

        .sisoc-tabs-rail {
            display: flex;
            align-items: center;
            gap: .85rem;
            padding: 1rem .75rem .75rem;
            margin-bottom: 2rem;
            border-bottom: 2px solid rgba(224, 182, 74, 0.95);
            overflow-x: auto;
        }

        .sisoc-tab-chip {
            border: 0;
            border-radius: 10px;
            background: rgba(43, 59, 98, 0.92);
            color: #f7f8fb;
            font-size: .88rem;
            font-weight: 600;
            padding: .55rem 1rem;
            min-width: max-content;
            transition: background-color .2s ease, color .2s ease;
        }

        .sisoc-tab-chip.is-active {
            background: var(--cblue);
            color: #28405f;
        }

        .sisoc-metric-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 30px;
            padding: .75rem;
            margin-bottom: 2.5rem;
        }

        .sisoc-metric-grid--pair {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            padding: 0;
            margin-bottom: 30px;
        }

        .sisoc-metric-grid--triple {
            grid-template-columns: repeat(3, minmax(0, 1fr));
            padding: 0;
            margin-bottom: 30px;
        }

        .sisoc-metric-grid--quad {
            grid-template-columns: repeat(4, minmax(0, 1fr));
            padding: 0;
            margin-bottom: 30px;
        }

        .sisoc-btn--gold { background: var(--cgold); color: #28405f; }
        .sisoc-btn--gold:hover, .sisoc-btn--gold:focus { color: #28405f; }
        .sisoc-btn--light { background: #ffffff; color: #37465b; }
        .sisoc-btn--light:hover, .sisoc-btn--light:focus { color: #243244; }

        /* ── Pestaña Resultados ──────────── */
        .ci-acta-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 20px 30px;
        }

        .ci-field-label {
            display: block;
            margin-bottom: .4rem;
            color: var(--ctext);
            font-size: 15px;
            font-weight: 400;
            letter-spacing: 1px;
        }

        .ci-field-input {
            width: 100%;
            min-height: 44px;
            padding: .5rem .85rem;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.35);
            background: rgba(255, 255, 255, 0.06);
            color: #ffffff;
            font-size: .95rem;
            color-scheme: dark;
        }

        .ci-field-input::placeholder { color: rgba(255, 255, 255, 0.5); }

        .ci-field-input:focus {
            outline: none;
            border-color: var(--cteal);
            box-shadow: 0 0 0 .18rem rgba(59, 134, 129, 0.25);
        }

        .ci-prof-input-wrap { position: relative; }

        .ci-prof-results {
            position: absolute;
            z-index: 20;
            top: calc(100% + 4px);
            left: 0;
            right: 0;
            max-height: 240px;
            overflow-y: auto;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.25);
            background: #1e2e40;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.45);
        }

        .ci-prof-results button {
            display: block;
            width: 100%;
            padding: .6rem .85rem;
            border: 0;
            background: transparent;
            color: #ffffff;
            text-align: left;
            font-size: .88rem;
            cursor: pointer;
        }

        .ci-prof-results button:hover { background: rgba(255, 255, 255, 0.09); }
        .ci-prof-results .ci-prof-results-empty {
            padding: .6rem .85rem;
            color: var(--cmuted);
            font-size: .85rem;
        }

        .ci-prof-chip {
            display: inline-flex;
            align-items: center;
            gap: .6rem;
            margin-top: .6rem;
            padding: .4rem .5rem .4rem .85rem;
            border-radius: 999px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            background: rgba(255, 255, 255, 0.08);
            color: #ffffff;
            font-size: .85rem;
        }

        .ci-prof-chip button {
            border: 0;
            background: transparent;
            color: #ffffff;
            padding: 0 .2rem;
            font-size: .9rem;
            line-height: 1;
            cursor: pointer;
        }

        .ci-filtro-group { display: inline-flex; gap: .4rem; flex-wrap: wrap; }

        .ci-filtro-btn {
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 999px;
            background: transparent;
            color: #ffffff;
            font-size: .8rem;
            font-weight: 600;
            padding: .35rem .85rem;
            cursor: pointer;
        }

        .ci-filtro-btn.is-active { background: var(--cgold); border-color: var(--cgold); color: #28405f; }

        .ci-resultado-acciones { display: flex; gap: .5rem; justify-content: flex-end; }

        /* ── Selección múltiple de inscriptos ──────────── */
        .ci-lote-acciones {
            display: inline-flex;
            align-items: center;
            gap: .55rem;
            flex-wrap: wrap;
        }

        .ci-lote-conteo {
            color: var(--cmuted);
            font-size: .82rem;
            font-weight: 600;
            white-space: nowrap;
        }

        .sisoc-btn:disabled {
            opacity: .45;
            cursor: not-allowed;
            filter: none;
        }

        .ci-tbl .ci-tbl-col-check { width: 44px; text-align: center; }

        .ci-lote-check,
        #inscriptosLoteTodos {
            width: 17px;
            height: 17px;
            accent-color: var(--cteal);
            cursor: pointer;
            vertical-align: middle;
        }

        @media (max-width: 767.98px) {
            .ci-acta-grid { grid-template-columns: 1fr; }
        }

        .sisoc-metric-card {
            position: relative;
            background: var(--cteal);
            border-radius: 20px;
            border-left: 8px solid var(--cgold);
            box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
            min-height: 120px;
            padding: 1rem 1rem .85rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .sisoc-metric-value {
            display: block;
            font-family: 'Lora', Georgia, 'Times New Roman', serif;
            font-size: 36px;
            line-height: 1.1;
            font-weight: 600;
            text-align: center;
            color: #ffffff;
        }

        .sisoc-metric-label {
            margin-top: .45rem;
            font-family: 'Montserrat', Inter, Roboto, sans-serif;
            font-size: 20px;
            font-weight: 500;
            text-align: center;
            color: #ffffff;
        }

        .sisoc-info-shell {
            background: transparent;
            border: 0;
            box-shadow: none;
            border-radius: 0;
            min-height: 0;
        }

        .sisoc-side-tabs {
            display: none;
        }

        .sisoc-info-panel {
            padding: 0 .75rem;
        }

        .sisoc-block-card {
            background: var(--cnav);
            border-radius: 15px;
            box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .sisoc-block-card + .sisoc-block-card {
            margin-top: 30px;
        }

        /* El buscador de profesor abre un dropdown en position:absolute y el
           \`overflow: hidden\` del card lo recortaba contra el borde inferior.
           Se libera el overflow y el radio superior pasa al title, que es el
           unico hijo con fondo propio que necesitaba el recorte. */
        .sisoc-block-card--overflow {
            overflow: visible;
        }

        .sisoc-block-card--overflow .sisoc-block-title {
            border-top-left-radius: 15px;
            border-top-right-radius: 15px;
        }

        .sisoc-block-title {
            display: flex;
            align-items: center;
            gap: .5rem;
            background: var(--cteal);
            border-bottom: 2px solid #ffffff;
            padding: .85rem 1.25rem;
            color: #ffffff;
            font-family: 'Montserrat', Inter, Roboto, sans-serif;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
        }

        .sisoc-block-title i {
            font-size: 20px;
            line-height: 1;
        }

        .sisoc-block-body {
            padding: 30px;
        }

        .sisoc-general-layout {
            grid-template-columns: 1fr;
            gap: 1rem;
        }

        .sisoc-general-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 1rem;
        }

        .sisoc-horarios-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 20px 40px;
        }

        .sisoc-data-label {
            color: #F2F2F2;
            font-size: 16px;
            font-weight: 400;
            letter-spacing: 1px;
            line-height: 20px;
        }

        .sisoc-data-value {
            color: #F2F2F2;
            font-size: 16px;
            font-weight: 600;
            letter-spacing: 1px;
            line-height: 25px;
        }

        .sisoc-section-header {
            margin-bottom: .75rem;
        }

        .sisoc-section-header h2 {
            font-size: 1.15rem;
            line-height: 1.35;
            letter-spacing: 0;
        }

        .sisoc-section-divider {
            margin-bottom: 1rem;
            background: rgba(224, 182, 74, 0.95);
        }

        @media (max-width: 991.98px) {
            .sisoc-metric-grid {
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }

            .sisoc-general-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 767.98px) {
            .sisoc-centro-page {
                padding: 0 0 .85rem;
            }

            .sisoc-page-top,
            .sisoc-tabs-rail,
            .sisoc-metric-grid,
            .sisoc-info-panel {
                padding-left: .75rem;
                padding-right: .75rem;
            }

            .sisoc-title-row {
                padding: 1.1rem .95rem 1rem;
            }

            .sisoc-title-block h1 {
                font-size: 1.75rem;
                line-height: 1.15;
            }

            .sisoc-title-sub {
                font-size: 1.1rem;
                line-height: 1.3;
            }

            .sisoc-metric-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 1rem;
            }

            .sisoc-general-grid,
            .sisoc-horarios-grid {
                grid-template-columns: 1fr;
            }
        }
`;
