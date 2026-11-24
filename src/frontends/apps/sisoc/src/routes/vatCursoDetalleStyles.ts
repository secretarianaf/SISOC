/**
 * Stylesheet of `curso/curso_detail.html` (the `<style>` block of the native template, verbatim).
 */
export const CURSO_DETALLE_CSS = `
        .app-content-header { display: none; }

        .sisoc-curso-page {
            --cnav: #232D4F;
            --cline: rgba(255, 255, 255, 0.14);
            --ctext: #F2F2F2;
            --cteal: #3B8681;
            --cgold: #E7BA61;
            font-family: 'Montserrat', Inter, Roboto, sans-serif;
            color: #ffffff;
            max-width: 1280px;
            margin: 0 auto 1rem;
            padding: 1rem;
        }

        .sisoc-page-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: .7rem;
            flex-wrap: wrap;
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

        .sisoc-back-link:hover { color: #243244; background: #f6f8fb; }

        .sisoc-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 30px;
            flex-wrap: wrap;
            background: var(--cnav);
            border-radius: 20px;
            padding: 20px 30px;
            margin-bottom: 30px;
            box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
        }

        .sisoc-title-block { flex: 1 1 auto; min-width: 0; }

        .sisoc-title-kicker {
            margin: 0 0 .25rem;
            color: rgba(255, 255, 255, 0.72);
            font-size: 13px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .sisoc-title-block h1 {
            margin: 0;
            font-family: 'Lora', Georgia, 'Times New Roman', serif;
            font-size: 32px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
            letter-spacing: 1px;
        }

        .sisoc-title-sub {
            margin: .35rem 0 0;
            color: rgba(255, 255, 255, 0.72);
            font-size: 14px;
            letter-spacing: .5px;
        }

        .sisoc-title-actions {
            display: flex;
            align-items: center;
            gap: 14px;
            flex-wrap: wrap;
        }

        .sisoc-status-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            padding: 8px 12px;
            background: #2F8F5B;
            border: 1px solid rgba(255, 255, 255, 0.22);
            color: #ffffff;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .04em;
            text-transform: uppercase;
            line-height: 1;
        }

        .sisoc-status-pill--planificado { background: #4f6e94; }
        .sisoc-status-pill--finalizado { background: #6c757d; }
        .sisoc-status-pill--cancelado { background: #d04545; }

        .sisoc-edit-btn {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            border-radius: 999px;
            padding: 9px 18px;
            background: #4e6f95;
            border: 1px solid rgba(215, 226, 244, 0.25);
            color: #ffffff;
            font-size: 13px;
            font-weight: 700;
            text-decoration: none;
            line-height: 1;
        }

        .sisoc-edit-btn:hover,
        .sisoc-edit-btn:focus { filter: brightness(1.08); color: #ffffff; }

        .sisoc-panels-grid {
            display: grid;
            grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
            gap: 30px;
            align-items: start;
        }

        .sisoc-panel {
            background: var(--cnav);
            border: 1px solid var(--cline);
            border-radius: 15px;
            box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .sisoc-panel + .sisoc-panel { margin-top: 30px; }

        .sisoc-panel-header {
            background: var(--cteal);
            border-bottom: 2px solid #ffffff;
            padding: .85rem 1.4rem;
        }

        .sisoc-panel-header h2 {
            margin: 0;
            color: #ffffff;
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 1px;
            line-height: 1.2;
        }

        .sisoc-panel-body { padding: 26px 30px; }

        .sisoc-data-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 18px 40px;
        }

        .sisoc-data-item { min-width: 0; }
        .sisoc-data-item--full { grid-column: 1 / -1; }

        .sisoc-data-label {
            margin: 0 0 .22rem;
            color: rgba(242, 242, 242, 0.75);
            font-size: 14px;
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

        .sisoc-voucher-list {
            list-style: none;
            margin: .2rem 0 0;
            padding: 0;
            display: grid;
            gap: 8px;
        }

        .sisoc-voucher-list li {
            display: flex;
            align-items: baseline;
            gap: 10px;
            color: var(--ctext);
            font-size: 15px;
            font-weight: 600;
            letter-spacing: .5px;
        }

        .sisoc-voucher-list li i { color: var(--cgold); font-size: 13px; }

        .sisoc-metric-value {
            color: var(--cgold);
            font-family: 'Lora', Georgia, 'Times New Roman', serif;
            font-size: 34px;
            font-weight: 700;
            line-height: 1;
        }

        @media (max-width: 991.98px) {
            .sisoc-panels-grid { grid-template-columns: minmax(0, 1fr); }
            .sisoc-data-grid { grid-template-columns: minmax(0, 1fr); }
        }
`;
