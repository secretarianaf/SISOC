import { useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";

/**
 * The two selects of the state-change modal as `pas.js` builds them with
 * Select2 4.1.0-beta.1: `width: "100%"`, `allowClear`, `minimumResultsForSearch: 0`,
 * placeholder «Seleccione una opcion» (single) or «Seleccione avisos» (multiple)
 * and `dropdownParent` = the modal. The native `<select>` stays in the DOM,
 * hidden like Select2 hides it, and owns the form value.
 */
export type Choice = { value: string; label: string };

const plain = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();

export default function PasSelect2({ id, name, multiple = false, choices, value, onChange, parent }: {
  id: string;
  name: string;
  multiple?: boolean;
  /** Single: the first choice is the empty option (Select2 shows the placeholder for it). */
  choices: Choice[];
  value: string[];
  onChange: (value: string[]) => void;
  /** `dropdownParent`: the dropdown is placed inside this element. */
  parent: HTMLElement | null;
}) {
  const placeholder = multiple ? "Seleccione avisos" : "Seleccione una opcion";
  const [open, setOpen] = useState(false);
  // Select2 marks the container `select2-container--focus` while its selection or search has focus.
  const [focused, setFocused] = useState(false);
  const [term, setTerm] = useState("");
  const [highlight, setHighlight] = useState(0);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const container = useRef<HTMLSpanElement>(null);
  const selection = useRef<HTMLSpanElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const options = choices.filter((c) => c.value !== "");
  const chosen = options.filter((c) => value.includes(c.value));
  const results = options.filter((c) => plain(c.label).includes(plain(term)));
  const containerId = `select2-${id}-container`;
  const resultsId = `select2-${id}-results`;

  useLayoutEffect(() => {
    if (!open || !container.current || !parent) return undefined;
    const place = () => {
      const r = container.current!.getBoundingClientRect();
      const p = parent.getBoundingClientRect();
      setPosition({ top: r.bottom - p.top + parent.scrollTop, left: r.left - p.left + parent.scrollLeft, width: r.width });
    };
    place();
    window.addEventListener("resize", place);
    const close = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!container.current?.contains(target) && !document.getElementById(resultsId)?.closest(".select2-container")?.contains(target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => {
      window.removeEventListener("resize", place);
      document.removeEventListener("mousedown", close);
    };
  }, [open, parent, resultsId, value.length]);

  useLayoutEffect(() => {
    if (open && !multiple) search.current?.focus();
  }, [open, multiple]);

  function show() {
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
  function clear() {
    onChange([]);
    setOpen(false);
  }
  function navigate(event: KeyboardEvent<HTMLElement>) {
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

  const clearButton = chosen.length > 0 && <button type="button" className="select2-selection__clear" tabIndex={-1} title="Remove all items"
    aria-label="Remove all items" aria-describedby={containerId} onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); clear(); }}>
    <span aria-hidden="true">×</span>
  </button>;
  const toggle = (event: { target: EventTarget; preventDefault(): void }) => {
    if ((event.target as HTMLElement).closest(".select2-selection__clear, .select2-selection__choice__remove")) return;
    event.preventDefault();
    if (open) hide(); else { show(); if (multiple) search.current?.focus(); }
  };
  return <>
    <select name={name} className={`form-select pas-select2${multiple ? " selectmultiple" : ""} select2-hidden-accessible`} required id={id}
      multiple={multiple} tabIndex={-1} aria-hidden="true" value={multiple ? value : value[0] ?? ""} onChange={() => undefined}>
      {(multiple ? options : choices).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>
    <span ref={container} className={`select2 select2-container select2-container--default${open ? " select2-container--below select2-container--open" : ""}${focused ? " select2-container--focus" : ""}`}
      dir="ltr" style={{ width: "100%" }} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}>
      <span className="selection">
        {multiple
          ? <span className="select2-selection select2-selection--multiple" role="combobox" aria-haspopup="true" aria-expanded={open} tabIndex={-1}
            aria-disabled="false" aria-owns={open ? resultsId : undefined} onMouseDown={toggle}>
            {clearButton}
            <ul className="select2-selection__rendered" id={containerId}>
              {chosen.map((c) => <li key={c.value} className="select2-selection__choice" title={c.label}>
                <button type="button" className="select2-selection__choice__remove" tabIndex={-1} title="Remove item" aria-label="Remove item"
                  aria-describedby={`${containerId}-choice-${c.value}`} onClick={() => onChange(value.filter((v) => v !== c.value))}>
                  <span aria-hidden="true">×</span>
                </button>
                <span className="select2-selection__choice__display" id={`${containerId}-choice-${c.value}`}>{c.label}</span>
              </li>)}
            </ul>
            <span className="select2-search select2-search--inline">
              <input ref={search} className="select2-search__field" type="search" tabIndex={0} autoCorrect="off" autoCapitalize="none" spellCheck={false}
                role="searchbox" aria-autocomplete="list" autoComplete="off" aria-describedby={containerId} aria-controls={open ? resultsId : undefined}
                placeholder={chosen.length ? "" : placeholder} style={{ width: chosen.length ? `${(term.length + 1) * 0.75}em` : "100%" }} value={term}
                onChange={(e) => { setTerm(e.target.value); setOpen(true); setHighlight(0); }} onKeyDown={navigate} />
            </span>
          </span>
          : <span ref={selection} className="select2-selection select2-selection--single" role="combobox" aria-haspopup="true" aria-expanded={open}
            tabIndex={0} aria-disabled="false" aria-labelledby={containerId} aria-owns={open ? resultsId : undefined}
            onMouseDown={toggle} onKeyDown={navigate}>
            {clearButton}
            <span className="select2-selection__rendered" id={containerId} role="textbox" aria-readonly="true" title={chosen[0]?.label}>
              {chosen[0] ? chosen[0].label : <span className="select2-selection__placeholder">{placeholder}</span>}
            </span>
            <span className="select2-selection__arrow" role="presentation"><b role="presentation" /></span>
          </span>}
      </span>
      <span className="dropdown-wrapper" aria-hidden="true" />
    </span>
    {open && parent && createPortal(
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
      parent,
    )}
  </>;
}
