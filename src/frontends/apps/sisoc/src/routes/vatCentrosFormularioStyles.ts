/**
 * Stylesheet of `centro_create_form.html` (its `<style>` block, verbatim).
 */
export const CENTRO_FORMULARIO_CSS = `
        .app-content-header { display: none; }

        .vp-shell {
            --cnav: #232D4F;
            --cteal: #3B8681;
            --cgold: #E7BA61;
            --vp-stage-bg: transparent;
            --vp-stage-border: transparent;
            --vp-title-bg: #232D4F;
            --vp-panel-bg: #232D4F;
            --vp-panel-border: rgba(255, 255, 255, 0.14);
            --vp-panel-title-bg: #3B8681;
            --vp-text: #ffffff;
            --vp-text-soft: rgba(255, 255, 255, 0.82);
            --vp-input-bg: #232D4F;
            --vp-input-border: #ffffff;
            --vp-input-focus: #E7BA61;
            --vp-save-bg: #2f8f4f;
            --vp-save-hover: #277a43;
            --vp-cancel-bg: #ffffff;
            --vp-cancel-text: #37465b;
            font-family: 'Montserrat', Inter, Roboto, sans-serif;
            max-width: 1280px;
            margin: 0 auto;
            padding: 30px;
            background: var(--vp-stage-bg);
            border: 0;
            border-radius: 0;
            box-shadow: none;
            color: #ffffff;
        }

        .vp-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .vp-back {
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

        .vp-back:hover { color: #243244; background: #f6f8fb; }

        .vp-hero {
            background: var(--vp-title-bg);
            color: var(--vp-text);
            border-radius: 20px;
            padding: 20px 30px;
            margin-bottom: 30px;
            box-shadow: none;
        }

        .vp-hero h1 {
            margin: 0;
            font-family: 'Lora', Georgia, 'Times New Roman', serif;
            font-size: 32px;
            font-weight: 700;
            line-height: 1.2;
            letter-spacing: 1px;
            color: #ffffff;
        }

        .vp-panel-header .card-title i,
        .vp-panel-header .btn i,
        .vp-contact-item .btn i,
        .vp-actions .btn i {
            margin-right: .5rem;
        }

        .vp-panel {
            border: 0;
            border-radius: 15px;
            /* overflow visible para que el desplegable de referentes/revisores no quede recortado por el panel */
            overflow: visible;
            background: var(--vp-panel-bg);
            box-shadow: 4px 4px 4px 0 rgba(0, 0, 0, 0.3);
            margin-bottom: 30px;
        }

        .vp-panel > :first-child {
            border-radius: 15px 15px 0 0;
        }

        .vp-panel > :last-child {
            border-radius: 0 0 15px 15px;
        }

        .vp-panel-header {
            padding: .85rem 1.25rem;
            border-bottom: 2px solid #ffffff;
            background: var(--vp-panel-title-bg);
            color: #ffffff;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: .75rem;
        }

        .vp-panel-header > div {
            display: flex;
            flex-direction: column;
            gap: .35rem;
            min-width: 0;
        }

        .vp-panel-header .card-title {
            color: #ffffff;
            font-weight: 700;
            margin: 0;
            line-height: 1.2;
            font-size: 20px;
            letter-spacing: 1px;
        }

        .vp-panel-header .text-muted,
        .vp-panel-header .small {
            color: rgba(240, 247, 255, 0.82) !important;
            display: none;
            margin: 0;
            line-height: 1.35;
        }

        .vp-panel-header .btn {
            border-radius: 999px;
            padding: .35rem .9rem;
            border: 1px solid rgba(255, 255, 255, 0.55);
            background: rgba(255, 255, 255, 0.12);
            color: #ffffff;
            font-size: .76rem;
            font-weight: 700;
            box-shadow: none;
        }

        .vp-panel-header .btn:hover,
        .vp-panel-header .btn:focus {
            background: rgba(255, 255, 255, 0.22);
            color: #ffffff;
        }

        .vp-section {
            padding: 30px 30px 16px;
            border-bottom: 0;
            background: var(--vp-panel-bg);
            overflow: visible;
        }

        .vp-section:last-child {
            border-bottom: 0;
        }

        .vp-field {
            margin-bottom: 1rem;
        }

        .vp-field label {
            font-weight: 600;
            color: var(--vp-text);
            margin-bottom: .35rem;
            font-size: .9rem;
            letter-spacing: .3px;
        }

        .vp-section .form-group label,
        .vp-section .control-label,
        .vp-section .form-check-label,
        .vp-section small,
        .vp-section .help-block,
        .vp-section .text-muted {
            color: var(--vp-text-soft) !important;
        }

        .vp-shell .invalid-feedback,
        .vp-shell .text-danger,
        .vp-inline-errors,
        .vp-field .help-block.text-danger {
            color: #ffd3d3 !important;
            font-size: .74rem;
        }

        .vp-field .form-control,
        .vp-field .form-select,
        .vp-field textarea,
        .vp-field select,
        .vp-field input {
            min-height: 40px;
            border-radius: 10px;
            border: 1px solid var(--vp-input-border);
            background: var(--vp-input-bg);
            color: var(--vp-text);
            box-shadow: none;
        }

        .vp-field textarea {
            min-height: 40px;
            resize: vertical;
        }

        .vp-field .form-control::placeholder,
        .vp-field textarea::placeholder,
        .vp-field input::placeholder {
            color: rgba(225, 233, 246, 0.65);
        }

        .vp-field input[type="checkbox"],
        .vp-field input[type="radio"] {
            accent-color: var(--vp-panel-title-bg);
        }

        .vp-field .form-control:focus,
        .vp-field .form-select:focus,
        .vp-field textarea:focus,
        .vp-field select:focus,
        .vp-field input:focus {
            border-color: var(--vp-input-focus);
            background: var(--vp-input-bg);
            color: var(--vp-text);
            box-shadow: 0 0 0 .18rem rgba(197, 210, 232, 0.18);
        }

        .vp-shell .select2-container {
            width: 100% !important;
        }

        .vp-shell .select2-container--default .select2-selection--single,
        .vp-shell .select2-container--default .select2-selection--multiple {
            min-height: 40px;
            border-radius: 10px;
            border: 1px solid var(--vp-input-border);
            background: var(--vp-input-bg);
        }

        .vp-shell .select2-container--default .select2-selection--single .select2-selection__rendered {
            color: var(--vp-text);
            line-height: 38px;
            padding-left: .75rem;
            padding-right: 2rem;
        }

        .vp-shell .select2-container--default .select2-selection--single .select2-selection__placeholder {
            color: rgba(225, 233, 246, 0.65);
        }

        .vp-shell .select2-container--default .select2-selection--single .select2-selection__arrow {
            height: 32px;
            right: .35rem;
        }

        .vp-shell .select2-container--default .select2-selection--single .select2-selection__arrow b {
            border-color: #d9e4f5 transparent transparent transparent;
        }

        .vp-shell .select2-dropdown {
            border: 1px solid var(--vp-input-border);
            background: #243257;
        }

        .vp-shell .select2-search--dropdown .select2-search__field {
            border: 1px solid var(--vp-input-border);
            background: #1e2a4a;
            color: var(--vp-text);
        }

        .vp-shell .select2-results__option {
            color: var(--vp-text);
        }

        .vp-shell .select2-container--default .select2-results__option--highlighted[aria-selected] {
            background: var(--vp-panel-title-bg);
            color: #ffffff;
        }

        .vp-field .referente-hidden-select {
            display: none;
        }

        .vp-field .referente-search-wrapper {
            position: relative;
        }

        .vp-field .referente-search-results {
            position: absolute;
            top: calc(100% + .35rem);
            left: 0;
            right: 0;
            z-index: 1200;
            border: 1px solid var(--vp-input-border);
            border-radius: 6px;
            background: rgba(24, 34, 61, 0.98);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.22);
            max-height: 220px;
            overflow-y: auto;
            padding: .35rem 0;
            scrollbar-width: thin;
            scrollbar-color: rgba(255, 255, 255, 0.35) rgba(24, 34, 61, 0.98);
        }

        .vp-field .referente-search-results[hidden] {
            display: none !important;
        }

        .vp-field .referente-search-option {
            display: block;
            width: 100%;
            border: 0;
            background: transparent;
            color: var(--vp-text);
            text-align: left;
            padding: .55rem .85rem;
        }

        .vp-field .referente-search-option:hover,
        .vp-field .referente-search-option:focus {
            background: rgba(86, 166, 157, 0.22);
            outline: none;
        }

        .vp-field .referente-search-empty {
            color: var(--vp-text-soft);
            padding: .55rem .85rem;
        }

        .vp-field .referente-search-error {
            display: block;
            margin-top: .35rem;
            color: #ffd0d0;
            font-size: .875rem;
        }

        .vp-field .referente-selected-items {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: .55rem;
        }

        .vp-field .referente-selected-chip {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            border: 1px solid rgba(208, 220, 238, 0.22);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            color: var(--vp-text);
            padding: .35rem .55rem .35rem .7rem;
            font-size: .875rem;
        }

        .vp-field .referente-chip-remove {
            border: 0;
            border-radius: 50%;
            width: 1.25rem;
            height: 1.25rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #dceafe;
            background: rgba(255, 255, 255, 0.12);
            line-height: 1;
        }

        .vp-field .referente-chip-remove:hover,
        .vp-field .referente-chip-remove:focus {
            background: rgba(255, 255, 255, 0.22);
            outline: none;
        }

        .vp-contact-item {
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 12px;
            padding: 1rem .85rem .35rem;
            background: rgba(255, 255, 255, 0.04);
        }

        .vp-contact-item .form-check-label {
            color: var(--vp-text);
            font-weight: 600;
        }

        .vp-status-card {
            margin-top: 0;
            border: 0;
            border-radius: 0;
            padding: 0;
            background: transparent;
        }

        .vp-status-card h4 {
            display: none;
        }

        .vp-status-card p {
            margin: 0 0 .75rem;
            color: var(--vp-text-soft);
            font-size: .8rem;
        }

        .vp-switch {
            min-height: auto;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            padding: 0;
            border-radius: 0;
            border: 0;
            background: transparent;
            color: var(--vp-text);
        }

        .vp-switch .form-check-label {
            color: var(--vp-text);
            font-weight: 600;
        }

        .vp-switch .form-check-input {
            margin-right: .55rem;
            margin-top: .15rem;
        }

        .vp-inline-errors {
            margin-top: .35rem;
            font-size: .74rem;
        }

        .vp-actions {
            display: flex;
            gap: .5rem;
            justify-content: flex-end;
            padding: .1rem 0 0;
            background: transparent;
            border-top: 0;
            border-radius: 0;
            flex-wrap: wrap;
        }

        .vp-actions .btn {
            border-radius: 999px;
            padding: .4rem .95rem;
            font-size: .76rem;
            font-weight: 700;
            box-shadow: none;
        }

        .vp-actions .btn-secondary {
            color: var(--vp-cancel-text);
            border-color: rgba(255, 255, 255, 0.4);
            background: var(--vp-cancel-bg);
        }

        .vp-actions .btn-secondary:hover {
            color: var(--vp-cancel-text);
            background: #e6eaef;
        }

        .vp-actions .btn-primary {
            background: var(--vp-save-bg);
            border-color: var(--vp-save-bg);
            color: #ffffff;
        }

        .vp-actions .btn-primary:hover,
        .vp-actions .btn-primary:focus {
            background: var(--vp-save-hover);
            border-color: var(--vp-save-hover);
            color: #ffffff;
        }

        .vp-actions .btn-outline-primary {
            color: #ffffff;
            border-color: rgba(255, 255, 255, 0.38);
            background: rgba(38, 53, 93, 0.4);
        }

        .vp-actions .btn-outline-primary:hover {
            background: rgba(255, 255, 255, 0.12);
            color: #fff;
            border-color: rgba(255, 255, 255, 0.65);
        }

        @media (max-width: 991px) {
            .vp-shell {
                padding: .8rem;
            }

            .vp-hero {
                padding: .85rem .95rem;
            }

            .vp-panel-header {
                align-items: flex-start;
            }

            .vp-actions {
                justify-content: stretch;
            }

            .vp-actions .btn {
                flex: 1 1 100%;
            }
        }

        @media (max-width: 767px) {
            .vp-shell {
                border-radius: 10px;
            }

            .vp-hero h1 {
                font-size: 1.08rem;
                line-height: 1.35;
            }

            .vp-panel-header {
                padding: .5rem .7rem;
            }

            .vp-section {
                padding: .8rem .7rem .25rem;
            }
        }
    `;
