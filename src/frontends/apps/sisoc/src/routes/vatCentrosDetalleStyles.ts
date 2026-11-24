/**
 * Stylesheet of `centro_detail.html` (the first `<style>` block of the native template, verbatim).
 */
export const CENTRO_DETALLE_CSS = `
        .ci-hero {
            border-radius: 12px;
            padding: 0;
            color: #fff;
            margin-bottom: 1.25rem;
            position: relative;
            overflow: visible;
            background: transparent;
        }

        .ci-stats {
            display: flex;
            flex-wrap: wrap;
            gap: 1.25rem;
            margin-top: 1.25rem;
        }

        .ci-stat {
            display: flex;
            flex-direction: column;
        }

        .ci-stat-val {
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.1;
        }

        .ci-stat-lbl {
            font-size: 0.64rem;
            opacity: 0.55;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .ci-stat-sep {
            width: 1px;
            background: rgba(255, 255, 255, 0.18);
            align-self: stretch;
        }

        .ig-list {
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.65rem;
        }

        .ig-row {
            display: grid;
            grid-template-columns: minmax(180px, 240px) 1fr;
            align-items: center;
            gap: 0.85rem;
            background: linear-gradient(180deg, rgba(16, 35, 59, 0.94) 0%, rgba(20, 42, 70, 0.92) 100%) !important;
            border: 1px solid rgba(126, 179, 255, 0.22);
            border-left: 4px solid #4a8ddb;
            border-radius: 10px;
            padding: 0.7rem 0.85rem;
        }

        .ig-key {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: #cfe1f8;
        }

        .ig-key i {
            width: 18px;
            text-align: center;
            color: #7cb2f2;
        }

        .ig-data {
            font-size: 0.97rem;
            color: #f2f7ff;
            font-weight: 600;
            line-height: 1.35;
            word-break: break-word;
        }

        .ig-data a {
            color: #9fcbff;
            text-decoration: none;
            font-weight: 700;
        }

        .ig-data a:hover {
            text-decoration: underline;
        }

        @media (max-width: 767.98px) {
            .ig-row {
                grid-template-columns: 1fr;
                gap: 0.35rem;
            }
        }

        .bg-gradient-primary {
            background: linear-gradient(135deg, #183a67 0%, #25518b 55%, #3b74b8 100%);
        }

        .bg-gradient-success {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }

        .bg-gradient-warning {
            background: linear-gradient(135deg, #fcb045 0%, #fd1d1d 100%);
        }

        .bg-gradient-info {
            background: linear-gradient(135deg, #183a67 0%, #25518b 55%, #3b74b8 100%);
        }

        .nav-pills .nav-link {
            border-radius: 8px;
            margin: 2px;
            transition: all 0.3s ease;
            font-weight: 500;
        }

        .nav-pills .nav-link {
            color: #4b6890 !important;
        }

        .nav-pills .nav-link.active {
            background: linear-gradient(135deg, #1f4d86 0%, #2f6db4 100%);
            box-shadow: 0 4px 8px rgba(31, 77, 134, 0.35);
            color: white !important;
        }

        .nav-pills .nav-link:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .nav-pills .nav-link.disabled,
        .nav-pills .nav-link:disabled {
            color: #8ea0b8 !important;
            background: rgba(255, 255, 255, 0.04);
            border-color: rgba(255, 255, 255, 0.08);
            opacity: 0.6;
            cursor: not-allowed;
            pointer-events: none;
            transform: none;
            box-shadow: none;
        }

        .card {
            border: none;
            border-radius: 12px;
            box-shadow: 0 8px 26px rgba(7, 18, 34, 0.22);
            transition: all 0.3s ease;
            background: transparent;
        }

        .card:hover {
            box-shadow: 0 12px 32px rgba(7, 18, 34, 0.3);
        }

        .card-header {
            border-radius: 12px 12px 0 0 !important;
            border: none;
            background: linear-gradient(135deg, #132c4d 0%, #1d446f 55%, #2d649e 100%);
            color: #ffffff;
        }

        .card-body {
            background: linear-gradient(180deg, rgba(14, 31, 53, 0.96) 0%, rgba(18, 38, 64, 0.95) 100%);
            color: #e6f1ff;
        }

        .card-body a {
            color: #9fcbff;
        }

        .card-body .text-muted,
        .card-body small,
        .card-body .form-label,
        .card-body label {
            color: #c9ddf6 !important;
        }

        .detalles-centro-header,
        .info-general-header,
        .referente-header,
        .centro-section-header {
            background: linear-gradient(135deg, #1f3b6d 0%, #2b4f8c 100%) !important;
            color: #ffffff !important;
        }

        .detalles-centro-header h5,
        .detalles-centro-header h6,
        .detalles-centro-header i,
        .detalles-centro-header span,
        .detalles-centro-header strong,
        .info-general-header h5,
        .info-general-header h6,
        .info-general-header i,
        .info-general-header span,
        .info-general-header strong,
        .referente-header h5,
        .referente-header h6,
        .referente-header i,
        .referente-header span,
        .referente-header strong,
        .centro-section-header h5,
        .centro-section-header h6,
        .centro-section-header i,
        .centro-section-header span,
        .centro-section-header strong {
            color: #ffffff !important;
        }

        .card-header.d-flex {
            gap: 0.75rem;
        }

        .card-header.d-flex > .btn,
        .card-header.d-flex > .btn-group {
            margin-left: auto;
            flex-shrink: 0;
        }

        .detalles-centro-header {
            background: linear-gradient(135deg, #1f3b6d 0%, #2b4f8c 100%) !important;
            color: #ffffff !important;
        }

        .info-general-header {
            background: linear-gradient(135deg, #1f3b6d 0%, #2b4f8c 100%) !important;
            color: #ffffff !important;
        }

        .referente-header {
            background: linear-gradient(135deg, #1f3b6d 0%, #2b4f8c 100%) !important;
            color: #ffffff !important;
        }

        .table th {
            border-top: none;
            font-weight: 600;
            color: #d5e7ff;
            background-color: rgba(14, 31, 53, 0.88);
        }

        .table > :not(caption) > thead.table-light > tr > th {
            background-color: rgba(20, 45, 74, 0.95);
            color: #d8e8fb;
            border-bottom: 1px solid rgba(126, 179, 255, 0.25);
        }

        .table td,
        .table tbody th {
            color: #f2f7ff;
            border-color: rgba(126, 179, 255, 0.16);
            background: rgba(17, 37, 62, 0.78);
        }

        .table-hover tbody tr:hover {
            background-color: rgba(74, 141, 219, 0.12);
        }

        #tablaCursosCentro .curso-row {
            cursor: pointer;
        }

        #tablaCursosCentro .curso-row.curso-row-selected {
            background: rgba(74, 141, 219, 0.28) !important;
        }

        #tablaCursosCentro .curso-row.curso-row-selected > td {
            background: transparent !important;
        }

        #tablaCursosCentro .curso-row.curso-row-selected > td:first-child {
            box-shadow: inset 3px 0 0 #7cb2f2;
        }

        .badge {
            font-size: 0.75em;
            font-weight: 500;
        }

        .btn-group-sm .btn {
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
        }

        .modal-content {
            border-radius: 12px;
            border: none;
            background: #232D4F !important;
            opacity: 1 !important;
        }

        .modal-header {
            border-radius: 12px 12px 0 0;
            background: #3B8681 !important;
            color: white;
            opacity: 1 !important;
            border-bottom: 2px solid #ffffff;
        }

        .modal-header .btn-close {
            filter: invert(1);
            opacity: 1 !important;
        }

        .modal-body {
            background: #232D4F !important;
            color: #F2F2F2 !important;
            opacity: 1 !important;
        }

        .modal-footer {
            background: #232D4F !important;
            opacity: 1 !important;
            border-top: 1px solid rgba(255, 255, 255, 0.16);
        }

        #modalContacto .modal-content,
        #modalIdentificador .modal-content,
        #modalUbicacion .modal-content {
            background: #232D4F !important;
            opacity: 1 !important;
        }

        #modalContacto .modal-header,
        #modalIdentificador .modal-header,
        #modalUbicacion .modal-header {
            background: #3B8681 !important;
            opacity: 1 !important;
        }

        #modalContacto .modal-body,
        #modalIdentificador .modal-body,
        #modalUbicacion .modal-body {
            background: #232D4F !important;
            opacity: 1 !important;
        }

        #modalContacto .modal-footer,
        #modalIdentificador .modal-footer,
        #modalUbicacion .modal-footer {
            background: #232D4F !important;
            opacity: 1 !important;
        }

        .form-label {
            color: #495057;
            font-weight: 500;
        }

        .text-muted {
            color: #6c757d !important;
        }

        .info-card {
            transition: all 0.3s ease;
            border-radius: 12px;
        }

        .info-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        }

        .bg-primary.bg-gradient {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
        }

        .bg-success.bg-gradient {
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
        }

        .bg-warning.bg-gradient {
            background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%);
        }

        .bg-info.bg-gradient {
            background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
        }

        .btn {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }

        .h1, .h3 {
            font-weight: 700;
        }

        .section-separator {
            border-top: 2px solid #e9ecef;
            margin: 1.5rem 0;
        }

        .sub-section-title {
            font-size: 1rem;
            font-weight: 600;
            color: #495057;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #667eea;
            display: inline-block;
        }

        .details-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.8rem;
        }

        .details-item {
            border: 1px solid rgba(126, 179, 255, 0.24);
            border-radius: 10px;
            padding: 0.8rem 0.9rem;
            height: 100%;
            background: linear-gradient(180deg, rgba(20, 44, 73, 0.82) 0%, rgba(18, 39, 65, 0.8) 100%);
        }

        .details-label {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            margin-bottom: 0.35rem;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #cfe1f8;
        }

        .details-label.text-muted {
            color: #cfe1f8 !important;
        }

        .details-value {
            margin: 0;
            font-size: 0.96rem;
            font-weight: 600;
            line-height: 1.35;
            word-break: break-word;
            color: #f2f7ff;
        }

        .details-item--wide {
            grid-column: 1 / -1;
        }

        @media (max-width: 575.98px) {
            .details-grid {
                grid-template-columns: 1fr;
            }

            .details-item--wide {
                grid-column: auto;
            }
        }

        .app-content-header {
            display: none;
        }

        .sisoc-legacy-centro-tabs,
        #datos-generales {
            display: none !important;
        }

        .sisoc-centro-page {
            font-family: 'Montserrat', Inter, Roboto, sans-serif;
            color: #ffffff;
            max-width: 1620px;
            margin: 0 auto 1rem;
            background: transparent;
            border-radius: 0;
            padding: 0;
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
            gap: 0;
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
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.16);
        }

        .sisoc-header-actions {
            display: flex;
            align-items: center;
            gap: .85rem;
            flex-wrap: wrap;
        }

        .sisoc-header-action-link {
            color: #dbe6f8;
            text-decoration: none;
            font-size: 12px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: .3rem;
        }

        .sisoc-header-action-link:hover {
            color: #ffffff;
        }

        .sisoc-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 40px;
            flex-wrap: nowrap;
            background: #232D4F;
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

        .sisoc-title-meta {
            display: inline-flex;
            flex: 0 0 auto;
            align-items: center;
            justify-content: flex-end;
            gap: 20px;
            flex-wrap: nowrap;
            padding: 10px 0;
        }

        .sisoc-title-meta .sisoc-cue-text {
            color: #ffffff;
            font-family: 'Lora', Georgia, 'Times New Roman', serif;
            font-size: 24px;
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

        .sisoc-title-meta {
            align-self: center;
        }

        .sisoc-status-pill.is-inactive {
            background: #B42318;
        }

        .sisoc-info-shell {
            display: flex;
            align-items: stretch;
            background: #232D4F;
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 20px;
            box-shadow: 0 4px 4px 0 rgba(0, 0, 0, 0.35);
            overflow: hidden;
            min-height: 524px;
            font-family: 'Montserrat', Inter, Roboto, sans-serif;
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

        .sisoc-side-tabs {
            display: flex;
            align-items: stretch;
            flex-shrink: 0;
        }

        .sisoc-side-tabs--left {
            justify-content: flex-start;
        }

        .sisoc-side-tabs--right {
            justify-content: flex-end;
        }

        .sisoc-side-tab[hidden] {
            display: none;
        }

        .sisoc-side-tab {
            width: 54px;
            border: 0;
            background: #3B8681;
            color: #ffffff;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: background-color .2s ease;
        }

        .sisoc-side-tabs--left .sisoc-side-tab + .sisoc-side-tab {
            border-left: 1px solid rgba(255, 255, 255, 0.08);
        }

        .sisoc-side-tabs--right .sisoc-side-tab + .sisoc-side-tab {
            border-left: 1px solid rgba(255, 255, 255, 0.08);
        }

        .sisoc-side-tab:hover,
        .sisoc-side-tab:focus {
            background: #347a6b;
            outline: none;
        }

        .sisoc-side-tab.is-active {
            background: #3B8681;
        }

        .sisoc-side-tab[data-sisoc-tab-target="general"] {
            background: #3B8681;
        }

        .sisoc-side-tab[data-sisoc-tab-target="general"]:hover,
        .sisoc-side-tab[data-sisoc-tab-target="general"]:focus,
        .sisoc-side-tab[data-sisoc-tab-target="general"].is-active {
            background: #3B8681;
        }

        .sisoc-side-tab[data-sisoc-tab-target="ubicaciones"] {
            background: #3B8681;
        }

        .sisoc-side-tab[data-sisoc-tab-target="ubicaciones"]:hover,
        .sisoc-side-tab[data-sisoc-tab-target="ubicaciones"]:focus,
        .sisoc-side-tab[data-sisoc-tab-target="ubicaciones"].is-active {
            background: #3B8681;
        }

        .sisoc-side-tab[data-sisoc-tab-target="contactos"] {
            background: #3B8681;
        }

        .sisoc-side-tab[data-sisoc-tab-target="contactos"]:hover,
        .sisoc-side-tab[data-sisoc-tab-target="contactos"]:focus,
        .sisoc-side-tab[data-sisoc-tab-target="contactos"].is-active {
            background: #3B8681;
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
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
            white-space: nowrap;
            color: #ffffff;
            line-height: 1;
        }

        .sisoc-panel-section + .sisoc-panel-section {
            margin-top: 30px;
        }

        .sisoc-section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }

        .sisoc-section-header h2,
        .sisoc-section-header h3 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
            color: #F2F2F2;
            letter-spacing: 1px;
            line-height: 40px;
        }

        .sisoc-section-divider {
            height: 2px;
            border: 0;
            margin: 0 0 20px;
            background: #ffffff;
        }

        .sisoc-general-layout {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 195px;
            gap: 30px;
            align-items: stretch;
        }

        .sisoc-general-main {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }

        .sisoc-general-main .sisoc-general-grid {
            flex: 1 1 auto;
        }

        .sisoc-general-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 20px 60px;
            align-content: space-between;
            min-height: 110px;
        }

        .sisoc-data-item {
            min-width: 0;
        }

        .sisoc-data-label {
            margin: 0 0 .22rem;
            color: #F2F2F2;
            font-size: 16px;
            font-weight: 400;
            text-transform: none;
            letter-spacing: 1px;
            line-height: 20px;
        }

        .sisoc-data-value {
            margin: 0;
            color: #F2F2F2;
            font-size: 16px;
            font-weight: 600;
            letter-spacing: 1px;
            line-height: 25px;
            word-break: break-word;
        }

        .sisoc-data-value a {
            color: #ffffff;
            text-decoration: none;
        }

        .sisoc-data-value a:hover {
            text-decoration: underline;
        }

        .sisoc-map-preview {
            width: 100%;
            min-height: 170px;
            overflow: hidden;
            border-radius: 12.56px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: #1b2a4a;
            box-shadow: 0 2.51px 2.51px 0 rgba(0, 0, 0, 0.35);
            align-self: stretch;
        }

        .sisoc-map-preview iframe,
        .sisoc-map-placeholder {
            width: 100%;
            height: 100%;
        }

        .sisoc-map-placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: .45rem;
            color: #8b9bb4;
            font-size: 11px;
            text-align: center;
            padding: .75rem;
        }

        .sisoc-referente-list {
            list-style: none;
            margin: 0;
            padding: 0;
            display: grid;
            gap: 10px;
            align-content: space-between;
        }

        .sisoc-referente-item {
            display: flex;
            align-items: baseline;
            gap: 10px;
            line-height: 1.3;
        }

        .sisoc-referente-icon {
            width: 20px;
            height: 20px;
            flex: 0 0 20px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-size: 16px;
        }

        .sisoc-referente-copy {
            display: inline-flex;
            align-items: baseline;
            gap: 10px;
            flex-wrap: wrap;
            min-width: 0;
        }

        .sisoc-referente-copy span {
            display: inline;
            margin-bottom: 0;
            color: #F2F2F2;
            font-size: 16px;
            font-weight: 400;
            letter-spacing: 1px;
            line-height: 20px;
        }

        .sisoc-referente-copy strong,
        .sisoc-referente-copy div {
            color: #F2F2F2;
            font-size: 16px;
            font-weight: 600;
            letter-spacing: 1px;
            line-height: 25px;
            display: inline;
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
            transition: filter .2s ease, background-color .2s ease;
        }

        .sisoc-btn:hover,
        .sisoc-btn:focus {
            filter: brightness(1.08);
            color: #ffffff;
            outline: none;
        }

        .sisoc-btn--add {
            background: #2e7d33;
            color: #ffffff;
        }

        .sisoc-btn--edit {
            background: #4e6f95;
            border-color: rgba(215, 226, 244, 0.2);
            color: #ffffff;
        }

        .sisoc-btn--view {
            background: #2e6fd1;
            color: #ffffff;
        }

        .sisoc-btn--delete {
            background: #d04545;
            border-color: rgba(255, 255, 255, 0.2);
            color: #ffffff;
        }

        .sisoc-btn--edit:hover,
        .sisoc-btn--edit:focus {
            color: #ffffff;
        }

        .sisoc-btn--delete:hover,
        .sisoc-btn--delete:focus {
            color: #ffffff;
        }

        .sisoc-btn--ghost {
            background: transparent;
            border-color: #2a3a4a;
            color: #8b9bb4;
        }

        .sisoc-table-shell {
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 15px;
            overflow: hidden;
            background: #232D4F;
        }

        .sisoc-table-wrap {
            overflow-x: auto;
        }

        .sisoc-table {
            width: 100%;
            border-collapse: collapse;
            border-spacing: 0;
        }

        .sisoc-table thead th {
            padding: 12px 14px;
            background: #232D4F;
            border-top: 1px solid rgba(255, 255, 255, 0.18);
            border-bottom: 1px solid rgba(255, 255, 255, 0.18);
            color: #ffffff;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .04em;
            text-align: left;
            white-space: nowrap;
        }

        .sisoc-table tbody td {
            padding: 10px 14px;
            border-bottom: 1px solid rgba(229, 231, 235, 0.16);
            color: #ffffff;
            font-size: 13px;
            vertical-align: middle;
        }

        .sisoc-table tbody tr:last-child td {
            border-bottom: 0;
        }

        .sisoc-table-actions {
            display: flex;
            justify-content: flex-end;
            gap: .3rem;
            flex-wrap: wrap;
        }

        .sisoc-table-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: .75rem 0 0;
            color: #8b9bb4;
            font-size: 12px;
            flex-wrap: wrap;
        }

        .sisoc-pager {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            background: #16242f;
            border: 1px solid #2a3a4a;
            border-radius: 6px;
            padding: 3px;
        }

        .sisoc-pager button {
            width: 26px;
            height: 26px;
            border: 0;
            border-radius: 4px;
            background: transparent;
            color: #d8e0eb;
            font-size: 12px;
            line-height: 1;
            cursor: pointer;
        }

        .sisoc-pager button:hover {
            background: #22364a;
        }

        .sisoc-pager span {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 38px;
            min-height: 26px;
            padding: 0 8px;
            border-radius: 4px;
            background: #22364a;
            color: #d8e0eb;
            font-size: 12px;
            font-weight: 600;
        }

        .sisoc-page-buttons {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            flex-wrap: wrap;
        }

        .sisoc-page-buttons button {
            min-width: 30px;
            height: 30px;
            border: 1px solid #2a3a4a;
            border-radius: 6px;
            background: #16242f;
            color: #d8e0eb;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            padding: 0 8px;
            line-height: 1;
        }

        .sisoc-page-buttons button:hover {
            background: #22364a;
        }

        .sisoc-page-buttons button.is-active {
            background: #2f6aa3;
            border-color: #2f6aa3;
            color: #ffffff;
        }

        .sisoc-empty-state {
            padding: 1.4rem 1rem;
            text-align: center;
            color: #8b9bb4;
            font-size: 13px;
        }

        .sisoc-section-stack {
            display: grid;
            gap: 1rem;
        }

        .sisoc-section-header-bar {
            display: flex;
            align-items: center;
            padding: 10px 30px;
            border-radius: 15px 15px 0 0;
            background: #3B8681;
            border-bottom: 2px solid #ffffff;
            color: #ffffff;
            font-size: 20px;
            font-weight: 700;
            letter-spacing: .5px;
        }

        .sisoc-section-card {
            background: #232D4F;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-top: 0;
            border-radius: 0 0 15px 15px;
            padding: 1rem;
        }

        .sisoc-data-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 26px;
            padding: 3px 14px;
            border-radius: 5px;
            color: #ffffff;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }

        .sisoc-data-badge--commission {
            background: rgba(231, 186, 97, 0.5);
            border: 1px solid #E7BA61;
            border-radius: 10px;
            color: #ffffff;
        }

        .sisoc-data-badge--no-commission {
            background: rgba(198, 40, 40, 0.5);
            border: 1px solid #C62828;
            border-radius: 10px;
            color: #ffffff;
        }

        .sisoc-toolbar,
        .sisoc-toolbar-left {
            display: flex;
            align-items: center;
            gap: .75rem;
            flex-wrap: wrap;
        }

        .sisoc-toolbar {
            justify-content: space-between;
        }

        .sisoc-toolbar-field {
            display: flex;
            align-items: center;
            gap: .55rem;
            min-height: 36px;
            padding: 0 12px;
            border: 1px solid #2a3a4a;
            border-radius: 6px;
            background: #16242f;
            color: #ffffff;
        }

        .sisoc-toolbar-field > i {
            color: #8b9bb4;
            font-size: 12px;
        }

        .sisoc-toolbar-field input,
        .sisoc-toolbar-field select {
            border: 0;
            outline: none;
            background: transparent;
            color: #ffffff;
            font-size: 12px;
            min-width: 170px;
        }

        .sisoc-toolbar-field input::placeholder {
            color: #8b9bb4;
        }

        .sisoc-toolbar-field select option {
            background: #1e2e40;
            color: #ffffff;
        }

        .sisoc-section-card .select2-container {
            min-width: 210px !important;
        }

        .sisoc-section-card .select2-container--default .select2-selection--single {
            height: 32px;
            border: 1px solid #2a3a4a;
            background: #1e2e40;
            border-radius: 4px;
        }

        .sisoc-section-card .select2-container--default .select2-selection--single .select2-selection__rendered {
            color: #ffffff;
            line-height: 30px;
            padding-left: 10px;
        }

        .sisoc-section-card .select2-container--default .select2-selection--single .select2-selection__arrow {
            height: 30px;
        }

        .sisoc-section-card .select2-dropdown {
            border: 1px solid #2a3a4a;
            background: #1e2e40;
        }

        .sisoc-section-card .select2-search--dropdown .select2-search__field {
            background: #1b2b3a;
            border: 1px solid #2a3a4a;
            color: #ffffff;
        }

        .sisoc-section-card .select2-results__option {
            color: #ffffff;
        }

        .sisoc-section-card .select2-container--default .select2-results__option--highlighted[aria-selected] {
            background: #2e7d6a;
            color: #ffffff;
        }

        .sisoc-hidden-control {
            display: none;
        }

        .sisoc-panel-note {
            color: #8b9bb4;
            font-size: 12px;
        }

        .sisoc-cursos-pane {
            display: block;
            margin-top: 1rem;
        }

        @media (max-width: 991.98px) {
            .sisoc-general-layout {
                grid-template-columns: 1fr;
            }

            .sisoc-general-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 767.98px) {
            .sisoc-centro-page {
                padding: .85rem;
                border-radius: 14px;
            }

            .sisoc-title-row {
                flex-wrap: wrap;
                align-items: flex-start;
            }

            .sisoc-title-block h1 {
                font-size: 30px;
                line-height: 34px;
            }

            .sisoc-title-meta .sisoc-cue-text {
                font-size: 16px;
            }

            .sisoc-info-shell {
                flex-direction: column;
            }

            .sisoc-side-tabs {
                order: -1;
                min-width: 100%;
                flex: 0 0 auto;
            }

            .sisoc-side-tab {
                width: 33.3333%;
                min-height: 42px;
                border-left: 0;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
            }

            .sisoc-side-tab span {
                writing-mode: horizontal-tb;
                transform: none;
                font-size: 11px;
            }

            .sisoc-general-grid {
                grid-template-columns: 1fr;
                gap: .85rem;
            }

            .sisoc-table-footer,
            .sisoc-toolbar {
                align-items: stretch;
            }

            .sisoc-toolbar-left,
            .sisoc-toolbar,
            .sisoc-header-actions {
                width: 100%;
            }

            .sisoc-toolbar-field {
                width: 100%;
            }

            .sisoc-toolbar-field input,
            .sisoc-toolbar-field select {
                min-width: 0;
                width: 100%;
            }
        }
`;
