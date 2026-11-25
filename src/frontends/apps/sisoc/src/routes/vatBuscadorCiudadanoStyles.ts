/**
 * Stylesheet of `ciudadano.html` (the `<style>` block of the native template, verbatim).
 */
export const BUSCADOR_CSS = `
        .app-content-header { display: none; }

        .busc-page {
            --cnav: #232D4F;
            --cteal: #3B8681;
            --cgold: #E7BA61;
            --cgreen: #2e7d33;
            --cred: #c8484c;
            --cblue: #2e6fd1;
            --cmuted: rgba(255, 255, 255, 0.76);
            font-family: 'Montserrat', Inter, Roboto, sans-serif;
            color: #ffffff;
            margin: 0 auto 1rem;
            padding: 0 0 1rem;
        }

        .busc-title-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
            background: var(--cnav);
            border-radius: 0 0 14px 14px;
            padding: 1.25rem 1.5rem 1.15rem;
            box-shadow: 0 14px 20px rgba(18, 28, 46, 0.16);
            margin-bottom: 22px;
        }

        .busc-title-block h1 {
            margin: 0;
            font-family: 'Lora', Georgia, 'Times New Roman', serif;
            font-size: 30px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: 1px;
        }

        .busc-title-sub {
            margin: .55rem 0 0;
            color: rgba(255, 255, 255, 0.78);
            font-size: 13.5px;
            line-height: 1.45;
            max-width: 780px;
        }

        .busc-note {
            display: flex;
            gap: 11px;
            align-items: flex-start;
            background: rgba(231, 186, 97, 0.12);
            border: 1px solid var(--cgold);
            border-left: 5px solid var(--cgold);
            border-radius: 10px;
            padding: 12px 16px;
            margin: 0 .75rem 20px;
            font-size: 12.8px;
            color: #f3e4c4;
            line-height: 1.45;
        }

        .busc-note i { font-size: 16px; margin-top: 1px; }

        .busc-card {
            background: var(--cnav);
            border-radius: 15px;
            box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
            overflow: hidden;
            margin: 0 .75rem 22px;
        }

        .busc-card-head {
            display: flex;
            align-items: center;
            gap: .55rem;
            background: var(--cteal);
            border-bottom: 2px solid #ffffff;
            padding: .85rem 1.25rem;
            color: #ffffff;
            font-size: 19px;
            font-weight: 700;
            letter-spacing: .5px;
        }

        .busc-card-head__right { margin-left: auto; display: flex; gap: 8px; }
        .busc-inline-form { margin: 0; }

        .busc-card-body { padding: 22px 26px; }

        .busc-field { display: flex; flex-direction: column; min-width: 0; }

        .busc-field__label {
            font-size: .72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: .05em;
            color: var(--cmuted);
            margin-bottom: .35rem;
        }

        .busc-page input[type="search"] {
            width: 100%;
            background: #1b2942;
            border: 1px solid #2a3a4a;
            color: #ffffff;
            border-radius: 8px;
            padding: .6rem .8rem;
            font-size: .9rem;
        }

        .busc-page input:focus {
            outline: none;
            border-color: var(--cgold);
            box-shadow: 0 0 0 2px rgba(231, 186, 97, 0.18);
        }

        .busc-search-row {
            display: flex;
            gap: 14px;
            align-items: flex-end;
            flex-wrap: wrap;
        }

        .busc-search-row .busc-field { flex: 1 1 380px; min-width: 280px; }

        .busc-hint { margin: 10px 0 0; font-size: 12px; color: #9aa4c2; }
        .busc-hint code {
            background: #1b2942;
            border: 1px solid #2a3a4a;
            border-radius: 5px;
            padding: 1px 6px;
            color: var(--cgold);
            font-size: 11.5px;
        }

        .busc-btn {
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 9px 18px;
            font-family: inherit;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 7px;
            min-height: 40px;
            text-decoration: none;
        }

        .busc-btn--primary { background: #2f8f4f; color: #ffffff; }
        .busc-btn--primary:hover { filter: brightness(1.08); color: #ffffff; }
        .busc-btn--ghost { background: transparent; color: #ffffff; border-color: rgba(255, 255, 255, 0.35); }
        .busc-btn--ghost:hover { background: rgba(255, 255, 255, 0.08); color: #ffffff; }
        .busc-btn--sm { min-height: 30px; padding: 5px 11px; font-size: 11.5px; }

        .busc-ficha { display: flex; gap: 22px; align-items: flex-start; flex-wrap: wrap; }
        .busc-avatar {
            width: 64px; height: 64px;
            border-radius: 50%;
            background: #2b3760;
            border: 2px solid var(--cgold);
            display: flex; align-items: center; justify-content: center;
            font-family: 'Lora', serif;
            font-size: 23px;
            color: var(--cgold);
            font-weight: 700;
            flex: 0 0 auto;
            text-transform: uppercase;
        }
        .busc-dgrid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px 26px;
            flex: 1 1 520px;
            margin: 0;
        }
        .busc-dgrid > div { min-width: 0; }
        .busc-dgrid dt { font-size: 10.5px; text-transform: uppercase; letter-spacing: .6px; color: var(--cmuted); }
        .busc-dgrid dd {
            margin: 3px 0 0;
            font-size: 14px;
            color: #fff;
            font-weight: 500;
            overflow-wrap: break-word;
            word-break: break-word;
        }

        .busc-kpis {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            margin: 0 .75rem 22px;
        }
        .busc-kpi {
            background: var(--cnav);
            border: 1px solid rgba(255, 255, 255, .16);
            border-left: 6px solid var(--cgold);
            border-radius: 14px;
            padding: 13px 15px;
        }
        .busc-kpi--blue { border-left-color: var(--cblue); }
        .busc-kpi--green { border-left-color: var(--cgreen); }
        .busc-kpi--red { border-left-color: var(--cred); }
        .busc-kpi--grey { border-left-color: #8b93ad; }
        .busc-kpi--teal { border-left-color: var(--cteal); }
        .busc-kpi__n { font-size: 25px; font-weight: 700; font-family: 'Lora', serif; color: #fff; line-height: 1.1; }
        .busc-kpi__l { font-size: 10.5px; text-transform: uppercase; letter-spacing: .7px; color: var(--cmuted); margin-top: 3px; }

        .busc-tbl-wrap { overflow-x: auto; }
        .busc-tbl { width: 100%; border-collapse: collapse; min-width: 1120px; }
        .busc-tbl th {
            font-size: 10.5px;
            text-transform: uppercase;
            letter-spacing: .7px;
            color: var(--cgold);
            text-align: left;
            padding: 11px 12px;
            border-bottom: 2px solid rgba(255, 255, 255, .16);
            white-space: nowrap;
            font-weight: 700;
        }
        .busc-tbl td {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, .08);
            font-size: 12.8px;
            color: #e8ebf5;
            vertical-align: top;
        }
        .busc-tbl tbody tr:hover td { background: rgba(59, 134, 129, .10); }
        .busc-sub { display: block; font-size: 11px; color: #9aa4c2; margin-top: 3px; }
        .busc-nowrap { white-space: nowrap; }

        .busc-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 20px;
            padding: 3px 10px;
            font-size: 10.8px;
            font-weight: 600;
            white-space: nowrap;
        }
        .busc-badge--inscripta,
        .busc-badge--validada_presencial { background: rgba(46, 111, 209, .22); color: #9dc0f5; border: 1px solid var(--cblue); }
        .busc-badge--completada { background: rgba(46, 125, 51, .25); color: #7fd685; border: 1px solid var(--cgreen); }
        .busc-badge--abandonada { background: rgba(200, 72, 76, .22); color: #f29b9e; border: 1px solid var(--cred); }
        .busc-badge--pre_inscripta,
        .busc-badge--en_espera,
        .busc-badge--rechazada,
        .busc-badge--grey { background: rgba(255, 255, 255, .08); color: var(--cmuted); border: 1px solid rgba(255, 255, 255, .16); }
        .busc-badge--aprobado { background: rgba(46, 125, 51, .25); color: #7fd685; border: 1px solid var(--cgreen); }
        .busc-badge--desaprobado { background: rgba(200, 72, 76, .22); color: #f29b9e; border: 1px solid var(--cred); }
        .busc-badge--sin-calificar { background: rgba(255, 255, 255, .08); color: var(--cmuted); border: 1px solid rgba(255, 255, 255, .16); }

        .busc-empty { text-align: center; padding: 52px 20px; color: #9aa4c2; }
        .busc-empty .bi { font-size: 46px; color: #3d4a72; display: block; margin-bottom: 14px; }
        .busc-empty h4 { margin: 0 0 8px; font-family: 'Lora', serif; font-size: 19px; color: #dfe5f5; font-weight: 600; }
        .busc-empty p { margin: 0 auto; max-width: 460px; font-size: 13px; line-height: 1.5; }

        .busc-cand {
            display: flex;
            align-items: center;
            gap: 16px;
            background: #2b3760;
            border: 1px solid rgba(255, 255, 255, .16);
            border-radius: 12px;
            padding: 14px 18px;
            margin-bottom: 12px;
        }
        .busc-cand:hover { border-color: var(--cgold); }
        .busc-cand-who { flex: 1 1 auto; }
        .busc-cand-who b { display: block; font-size: 15px; color: #fff; font-weight: 600; }
        .busc-cand-who span { font-size: 12px; color: #9aa4c2; }

        @media (max-width: 767.98px) {
            .busc-title-block h1 { font-size: 1.6rem; }
            .busc-card-head { font-size: 17px; }
            .busc-card-body { padding: 18px 16px; }
        }
    `;
