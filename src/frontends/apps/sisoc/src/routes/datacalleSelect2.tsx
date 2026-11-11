import { useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";

/**
 * The `select.select2` of `relevamiento_form.html` as `custom.js`
 * (`initSelect2Elements`) builds them with Select2 4.1.0-beta.1: `width: 100%`,
 * the empty option's text as placeholder with `allowClear` on single selects,
 * no placeholder on multiple ones, default English texts and the dropdown on
 * `<body>`. The native `<select>` stays in the DOM, hidden like Select2 hides it,
 * and owns the form value; options always come from the server.
 */
export type Choice = { value: string; label: string };

const plain = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();

export default function DatacalleSelect2({ id, name, className, multiple = false, choices, value, onChange, disabled = false, required = false, invalid = false, describedBy }: {
  id: string;
  name: string;
  /** Classes of the hidden native select (crispy: `select2 form-select`, `select2 selectmultiple form-select`). */
  className: string;
  multiple?: boolean;
  /** Single: the first choice with an empty value gives the placeholder (`buildSelect2Options`). */
  choices: Choice[];
  value: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
}) {
  const empty = multiple ? undefined : choices.find((c) => c.value === "");
  const placeholder = empty?.label;
  const [open, setOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const [term, setTerm] = useState("");
  const [highlight, setHighlight] = useState(0);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const container = useRef<HTMLSpanElement>(null);
  const selection = useRef<HTMLSpanElement>(null);
  const search = useRef<HTMLInputElement>(null);
  // With a placeholder Select2 hides its empty option from the results.
  const options = placeholder === undefined ? choices : choices.filter((c) => c.value !== "");
  const chosen = options.filter((c) => value.includes(c.value));
  const results = options.filter((c) => plain(c.label).includes(plain(term)));
  const containerId = `select2-${id}-container`;
  const resultsId = `select2-${id}-results`;

  useLayoutEffect(() => {
    if (!open || !container.current) return undefined;
    const place = () => {
      const r = container.current!.getBoundingClientRect();
      setPosition({ top: r.bottom + window.scrollY, left: r.left + window.scrollX, width: r.width });
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    const close = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!container.current?.contains(target) && !document.getElementById(resultsId)?.closest(".select2-container")?.contains(target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
      document.removeEventListener("mousedown", close);
    };
  }, [open, resultsId, value.length]);

  useLayoutEffect(() => {
    if (open && !multiple) search.current?.focus();
  }, [open, multiple]);

  function show() {
    if (disabled) return;
    setOpen(true);
    setTerm("");
    setHighlight(Math.max(0, options.findIndex((c) => value.includes(c.value))));
  }
  function hide(refocus = true) {
    setOpen(false);
    setTerm("");
    if (refocus) (multiple ? search : selection).current?.focus();
  }
  function pick(choice: Choice) {
    if (multiple) onChange(value.includes(choice.value) ? value.filter((v) => v !== choice.value) : [...value, choice.value]);
    else onChange([choice.value]);
    hide();
  }
  function navigate(event: KeyboardEvent<HTMLElement>) {
    if (disabled) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) { show(); return; }
      setHighlight((h) => Math.min(Math.max(h + (event.key === "ArrowDown" ? 1 : -1), 0), Math.max(results.length - 1, 0)));
    } else if (event.key === "Enter" || (event.key === " " && !multiple && !open)) {
      event.preventDefault();
      if (!open) show();
      else if (results[highlight]) pick(results[highlight]);
    } else if (event.key === "Escape") {
      if (open) { event.preventDefault(); event.stopPropagation(); hide(); }
    } else if (event.key === "Tab") {
      if (open) hide(false);
    } else if (multiple && event.key === "Backspace" && term === "" && chosen.length) {
      event.preventDefault();
      const last = chosen[chosen.length - 1];
      onChange(value.filter((v) => v !== last.value));
      setTerm(last.label);
      setOpen(true);
    }
  }
  const toggle = (event: { target: EventTarget; preventDefault(): void }) => {
    if (disabled || (event.target as HTMLElement).closest(".select2-selection__clear, .select2-selection__choice__remove")) return;
    event.preventDefault();
    if (open) hide(); else { show(); if (multiple) search.current?.focus(); }
  };
  const clearButton = !multiple && placeholder !== undefined && chosen.length > 0 && (
    <button type="button" className="select2-selection__clear" tabIndex={-1} title="Remove all items" aria-label="Remove all items"
      aria-describedby={containerId} onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); if (!disabled) { onChange([]); setOpen(false); } }}>
      <span aria-hidden="true">×</span>
    </button>
  );
  const searchWidth = chosen.length === 0 && placeholder !== undefined ? "100%" : `${(term.length + 1) * 0.75}em`;
  const containerClass = ["select2 select2-container select2-container--default", open && "select2-container--below select2-container--open",
    focused && "select2-container--focus", disabled && "select2-container--disabled"].filter(Boolean).join(" ");
  return <>
    <select name={name} className={`${className}${invalid ? " is-invalid" : ""} select2-hidden-accessible`} id={id} multiple={multiple}
      required={required || undefined} disabled={disabled || undefined} aria-invalid={invalid ? "true" : undefined} aria-describedby={describedBy}
      tabIndex={-1} aria-hidden="true" value={multiple ? value : value[0] ?? ""} onChange={() => undefined}>
      {choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>
    <span ref={container} className={containerClass} dir="ltr" style={{ width: "100%" }} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}>
      <span className="selection">
        {multiple
          ? <span className="select2-selection select2-selection--multiple" role="combobox" aria-haspopup="true" aria-expanded={open} tabIndex={-1}
            aria-disabled={disabled ? "true" : "false"} aria-owns={open ? resultsId : undefined} onMouseDown={toggle}>
            <ul className="select2-selection__rendered" id={containerId}>
              {chosen.map((c) => <li key={c.value} className="select2-selection__choice" title={c.label}>
                <button type="button" className="select2-selection__choice__remove" tabIndex={-1} title="Remove item" aria-label="Remove item"
                  aria-describedby={`${containerId}-choice-${c.value}`} onClick={() => { if (!disabled) onChange(value.filter((v) => v !== c.value)); }}>
                  <span aria-hidden="true">×</span>
                </button>
                <span className="select2-selection__choice__display" id={`${containerId}-choice-${c.value}`}>{c.label}</span>
              </li>)}
            </ul>
            <span className="select2-search select2-search--inline">
              <input ref={search} className="select2-search__field" type="search" tabIndex={disabled ? -1 : 0} autoCorrect="off" autoCapitalize="none" spellCheck={false}
                role="searchbox" aria-autocomplete="list" autoComplete="off" aria-describedby={containerId} aria-controls={open ? resultsId : undefined}
                disabled={disabled || undefined} placeholder="" style={{ width: searchWidth }} value={term}
                onChange={(e) => { setTerm(e.target.value); setOpen(true); setHighlight(0); }} onKeyDown={navigate} />
            </span>
          </span>
          : <span ref={selection} className="select2-selection select2-selection--single" role="combobox" aria-haspopup="true" aria-expanded={open}
            tabIndex={disabled ? -1 : 0} aria-disabled={disabled ? "true" : "false"} aria-labelledby={containerId} aria-owns={open ? resultsId : undefined}
            onMouseDown={toggle} onKeyDown={navigate}>
            {clearButton}
            <span className="select2-selection__rendered" id={containerId} role="textbox" aria-readonly="true" title={chosen[0]?.label}>
              {chosen[0] ? chosen[0].label : placeholder !== undefined && <span className="select2-selection__placeholder">{placeholder}</span>}
            </span>
            <span className="select2-selection__arrow" role="presentation"><b role="presentation" /></span>
          </span>}
      </span>
      <span className="dropdown-wrapper" aria-hidden="true" />
    </span>
    {open && createPortal(
      <span className="select2-container select2-container--default select2-container--open" style={{ position: "absolute", top: `${position.top}px`, left: `${position.left}px` }}>
        <span className="select2-dropdown select2-dropdown--below" dir="ltr" style={{ width: `${position.width}px` }}>
          {!multiple && <span className="select2-search select2-search--dropdown">
            <input ref={search} className="select2-search__field" type="search" tabIndex={0} autoCorrect="off" autoCapitalize="none" spellCheck={false}
              role="searchbox" aria-autocomplete="list" autoComplete="off" aria-controls={resultsId} value={term}
              onChange={(e) => { setTerm(e.target.value); setHighlight(0); }} onKeyDown={navigate} />
          </span>}
          <span className="select2-results">
            <ul className="select2-results__options" role="listbox" aria-multiselectable={multiple ? "true" : undefined} id={resultsId} aria-expanded="true" aria-hidden="false">
              {results.length ? results.map((c, index) => <li key={c.value} id={`select2-${id}-result-${c.value}`} role="option" aria-selected={value.includes(c.value)}
                className={`select2-results__option select2-results__option--selectable${value.includes(c.value) ? " select2-results__option--selected" : ""}${index === highlight ? " select2-results__option--highlighted" : ""}`}
                onMouseEnter={() => setHighlight(index)} onMouseDown={(e) => e.preventDefault()} onClick={() => pick(c)}>{c.label}</li>)
                : <li className="select2-results__option select2-results__message" role="alert" aria-live="assertive">No results found</li>}
            </ul>
          </span>
        </span>
      </span>,
      document.body,
    )}
  </>;
}
