/**
 * Second stylesheet of `centro_detail.html` (the `<style>` block after the modals, verbatim): the dark Bootstrap modals of the
 * page and of the courses panel (`#modalCurso`, `#modalComisionCurso`, `.vat-ui-modal`) and their select2 look.
 */
export const CENTRO_MODALES_CSS = `
        #modalCurso .form-control:disabled,
        #modalCurso .form-select:disabled,
        #modalCurso .modal-locked-field,
        #modalComisionCurso .form-control:disabled,
        #modalComisionCurso .form-select:disabled,
        #modalComisionCurso .modal-locked-field {
            background-color: #253446 !important;
            color: #e5e7eb !important;
            border-color: #3d4f63 !important;
            opacity: 1 !important;
            -webkit-text-fill-color: #e5e7eb !important;
            cursor: not-allowed;
        }

        #modalCurso .modal-dialog {
            max-width: 460px;
        }

        #modalCurso .modal-content {
            background: linear-gradient(180deg, #2f3d6b 0%, #28335c 100%);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            box-shadow: 0 30px 80px rgba(5, 12, 24, 0.55);
            color: #ffffff;
            overflow: hidden;
        }

        #modalCurso .modal-header,
        #modalCurso .modal-footer {
            border: 0;
        }

        .sisoc-curso-modal-header {
            position: relative;
            justify-content: center;
            padding: 1.15rem 1.25rem .85rem;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0) 100%);
        }

        .sisoc-curso-modal-header::after {
            content: '';
            position: absolute;
            left: 1.25rem;
            right: 1.25rem;
            bottom: 0;
            height: 2px;
            border-radius: 2px;
            background: linear-gradient(90deg, #3b8681 0%, #4a8ddb 100%);
        }

        .sisoc-curso-modal-header .modal-title {
            display: inline-flex;
            align-items: center;
            gap: .55rem;
            font-size: 21px;
            font-weight: 700;
            font-family: Georgia, 'Times New Roman', serif;
            color: #ffffff;
        }

        .sisoc-curso-modal-header .modal-title i {
            font-size: 17px;
            color: #7cb2f2;
        }

        .sisoc-curso-close {
            position: absolute;
            top: 1rem;
            right: 1rem;
            width: 28px;
            height: 28px;
            margin: 0;
            padding: 0;
            border-radius: 8px;
            background-color: rgba(255, 255, 255, 0.08);
            filter: brightness(0) invert(1);
            opacity: .85;
            transition: background-color .18s ease, opacity .18s ease;
        }

        .sisoc-curso-close:hover {
            background-color: rgba(255, 255, 255, 0.18);
            opacity: 1;
        }

        .sisoc-curso-modal-body {
            padding: 1.15rem 1.25rem .25rem;
            max-height: min(68vh, 560px);
            overflow-y: auto;
        }

        .sisoc-curso-modal-body::-webkit-scrollbar {
            width: 8px;
        }

        .sisoc-curso-modal-body::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.18);
            border-radius: 99px;
        }

        .sisoc-curso-modal-body::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.28);
        }

        #modalCurso #planEstudioSeleccionadoInfo {
            margin-bottom: .6rem;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.14);
            color: #f2f7ff;
            padding: .5rem .65rem;
            font-size: 12px;
        }

        .sisoc-curso-label {
            display: block;
            margin-bottom: .4rem;
            color: #ffffff;
            font-size: 12px;
            font-weight: 700;
        }

        #modalCurso .form-control,
        #modalCurso .form-select,
        .sisoc-curso-select-trigger {
            width: 100%;
            min-height: 40px;
            border-radius: 9px;
            border: 1px solid rgba(255, 255, 255, 0.28);
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
            font-size: 12.5px;
            box-shadow: none;
            transition: border-color .18s ease, background-color .18s ease, box-shadow .18s ease;
        }

        #modalCurso .form-control,
        #modalCurso .form-select {
            padding: .5rem .8rem;
        }

        #modalCurso .form-control:hover,
        #modalCurso .form-select:hover,
        .sisoc-curso-select-trigger:hover {
            border-color: rgba(255, 255, 255, 0.45);
            background: rgba(255, 255, 255, 0.07);
        }

        #modalCurso textarea.form-control {
            min-height: 72px;
            resize: vertical;
        }

        #modalCurso .form-control::placeholder {
            color: rgba(255, 255, 255, 0.55);
        }

        #modalCurso .form-control:focus,
        #modalCurso .form-select:focus,
        .sisoc-curso-select-trigger:focus {
            border-color: #4a8ddb;
            background: rgba(74, 141, 219, 0.08);
            box-shadow: 0 0 0 0.18rem rgba(74, 141, 219, 0.22);
            outline: none;
        }

        #modalCurso select.form-select option,
        #modalCurso select.form-control option {
            color: #1c2742;
            background-color: #ffffff;
        }

        .sisoc-curso-select-trigger {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: .42rem .72rem;
            text-align: left;
        }

        .sisoc-curso-summary,
        .sisoc-curso-help,
        #modalCurso .form-text {
            color: rgba(255, 255, 255, 0.78) !important;
            font-size: 11px;
            margin-top: .35rem;
            line-height: 1.3;
        }

        .sisoc-curso-check-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: .05rem .1rem .15rem;
        }

        .sisoc-curso-check {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            color: #ffffff;
            font-size: 12px;
            cursor: pointer;
        }

        .sisoc-curso-check .form-check-input {
            margin: 0;
            width: 14px;
            height: 14px;
            border-radius: 2px;
            border: 1px solid rgba(255, 255, 255, 0.82);
            background-color: transparent;
            box-shadow: none;
        }

        .sisoc-curso-check .form-check-input:checked {
            background-color: #ffffff;
            border-color: #ffffff;
        }

        .sisoc-curso-modal-footer {
            display: flex;
            justify-content: flex-end;
            gap: .6rem;
            padding: .85rem 1.25rem 1.15rem;
            background: rgba(0, 0, 0, 0.12);
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }

        .sisoc-curso-submit {
            border: 0;
            border-radius: 999px;
            min-height: 38px;
            padding: .5rem 1.35rem;
            font-size: 12.5px;
            font-weight: 700;
            line-height: 1;
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            transition: transform .18s ease, box-shadow .18s ease, filter .18s ease, opacity .18s ease;
        }

        .sisoc-curso-submit:hover {
            transform: translateY(-1px);
            filter: brightness(1.06);
        }

        .sisoc-curso-submit:disabled {
            opacity: .8;
            transform: none;
        }

        .sisoc-curso-submit--secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #e6f1ff;
            box-shadow: none;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .sisoc-curso-submit--secondary:hover {
            background: rgba(255, 255, 255, 0.16);
        }

        .sisoc-curso-submit--primary {
            background: linear-gradient(135deg, #3a9d40 0%, #2e7d33 100%);
            color: #ffffff;
            box-shadow: 0 10px 22px rgba(7, 26, 11, 0.32);
        }

        /* Vouchers — header con contador chip */
        .sisoc-curso-vouchers-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .6rem;
            margin-bottom: .4rem;
        }

        .sisoc-curso-voucher-counter {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            padding: .18rem .55rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.18);
            color: rgba(255, 255, 255, 0.78);
            font-size: 11px;
            font-weight: 600;
            letter-spacing: .02em;
            line-height: 1;
            transition: background .18s ease, border-color .18s ease, color .18s ease;
        }

        .sisoc-curso-voucher-counter i {
            font-size: 10px;
            opacity: .85;
        }

        .sisoc-curso-voucher-counter.is-active {
            background: rgba(46, 125, 51, 0.22);
            border-color: rgba(120, 220, 130, 0.55);
            color: #d6f5da;
        }

        .sisoc-curso-voucher-counter-label {
            text-transform: lowercase;
            opacity: .82;
        }

        /* Fallback nativo del <select multiple> antes de Select2 */
        #modalCurso select[name="voucher_parametrias"][multiple] {
            min-height: 38px;
            padding: .35rem .55rem;
        }

        #modalCurso select[name="tipo"][multiple] {
            min-height: 38px;
            padding: .35rem .55rem;
        }

        /* Select2 multiple dark mode para #modalOferta y #modalCurso */
        #modalOferta .select2-container--default .select2-selection--multiple,
        #modalCurso .select2-container--default .select2-selection--multiple {
            background-color: #1e2a3a !important;
            border: 1px solid #3d4f63 !important;
            border-radius: 0.25rem;
            min-height: 38px;
        }

        /* Select2 multiple — refinamiento visual para #modalCurso */
        #modalCurso .select2-container--default .select2-selection--multiple {
            border-radius: 8px !important;
            border-color: rgba(255, 255, 255, 0.32) !important;
            background-color: rgba(255, 255, 255, 0.04) !important;
            min-height: 40px;
            padding: 2px 6px;
            transition: border-color .18s ease, box-shadow .18s ease;
        }

        #modalCurso .select2-container--default.select2-container--focus .select2-selection--multiple,
        #modalCurso .select2-container--default.select2-container--open .select2-selection--multiple {
            border-color: #ffffff !important;
            background-color: rgba(255, 255, 255, 0.07) !important;
            box-shadow: 0 0 0 0.14rem rgba(255, 255, 255, 0.12) !important;
        }

        #modalCurso .select2-container--default .select2-selection--multiple .select2-selection__rendered {
            padding: 0 2px;
        }

        #modalCurso .select2-container--default .select2-selection--multiple .select2-selection__choice {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            background: linear-gradient(135deg, #3a8a40 0%, #2e7d33 100%) !important;
            color: #ffffff !important;
            border: 0 !important;
            border-radius: 999px !important;
            padding: 2px 10px 2px 4px !important;
            margin: 3px 4px 3px 0 !important;
            font-size: 11px;
            font-weight: 600;
            line-height: 1.4;
            box-shadow: 0 2px 6px rgba(7, 26, 11, 0.28);
        }

        #modalCurso .select2-container--default .select2-selection--multiple .select2-selection__choice__remove {
            order: -1;
            color: rgba(255, 255, 255, 0.85) !important;
            border: 0 !important;
            margin: 0 !important;
            padding: 0 2px 0 4px !important;
            font-size: 13px;
            line-height: 1;
            background: transparent !important;
        }

        #modalCurso .select2-container--default .select2-selection--multiple .select2-selection__choice__remove:hover {
            color: #ffffff !important;
            background: transparent !important;
            transform: scale(1.1);
        }

        #modalCurso .select2-container--default .select2-search--inline .select2-search__field {
            color: #ffffff !important;
            font-size: 12px;
            margin-top: 6px;
            margin-left: 4px;
        }

        #modalCurso .select2-container--default .select2-search--inline .select2-search__field::placeholder {
            color: rgba(255, 255, 255, 0.55) !important;
        }

        /* Select2 multiple dark mode (regla base mantenida abajo) */

        #modalOferta .select2-container--default.select2-container--focus .select2-selection--multiple {
            background-color: #253446 !important;
            border-color: #f39c12 !important;
            box-shadow: 0 0 0 0.2rem rgba(243, 156, 18, 0.15) !important;
        }
        #modalOferta .select2-container--default .select2-selection--multiple .select2-selection__choice {
            background-color: #2c3e50 !important;
            color: #f39c12 !important;
            border: 1px solid #3d4f63 !important;
            border-radius: 3px;
        }
        #modalOferta .select2-container--default .select2-selection--multiple .select2-selection__choice__remove {
            color: #9ca3af !important;
            border-right: 1px solid #3d4f63 !important;
        }
        #modalOferta .select2-container--default .select2-selection--multiple .select2-selection__choice__remove:hover {
            color: #ef4444 !important;
            background-color: transparent !important;
        }
        #modalOferta .select2-container--default .select2-search--inline .select2-search__field {
            color: #e5e7eb !important;
        }
        #modalOferta .select2-container--default .select2-selection--multiple .select2-selection__rendered {
            color: #e5e7eb !important;
        }
        /* Dropdown (se renderiza dentro de .modal-body por dropdownParent) */
        #formOferta .select2-dropdown,
        #formCurso .select2-dropdown {
            background-color: #1e2a3a !important;
            border: 1px solid #3d4f63;
        }
        #formOferta .select2-search--dropdown .select2-search__field,
        #formCurso .select2-search--dropdown .select2-search__field {
            background-color: #253446 !important;
            border: 1px solid #3d4f63 !important;
            border-radius: 0.25rem;
            color: #e5e7eb !important;
        }
        #formOferta .select2-results__option,
        #formCurso .select2-results__option {
            background-color: #1e2a3a !important;
            color: #e5e7eb !important;
            padding: 8px 12px !important;
        }
        #formOferta .select2-container--default .select2-results__option--highlighted[aria-selected],
        #formCurso .select2-container--default .select2-results__option--highlighted[aria-selected] {
            background-color: #f39c12 !important;
            color: #1e2a3a !important;
        }
        #formOferta .select2-container--default .select2-results__option[aria-selected=true],
        #formCurso .select2-container--default .select2-results__option[aria-selected=true] {
            background-color: #2c3e50 !important;
            color: #f39c12 !important;
        }
        #formOferta .select2-container--default .select2-results__option--highlighted[aria-selected=true],
        #formCurso .select2-container--default .select2-results__option--highlighted[aria-selected=true] {
            background-color: #f39c12 !important;
            color: #1e2a3a !important;
        }
`;
