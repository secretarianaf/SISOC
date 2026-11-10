import { useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";

/**
 * Técnicos selector of `dupla_form.html`: the markup of the native Select2 4.1
 * multiple (`duplas.js`: width 100%, placeholder, «Sin resultados») so
 * `select2.min.css` and `duplasSelect2.min.css` style it the same. The native
 * `<select multiple>` stays in the DOM (hidden like Select2 hides it) and owns
 * the form value; options come from the server, never typed ids.
 */
export type Choice = { value: string; label: string };

const plain = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();

export default function DuplasSelect2({ id, name, placeholder, choices, value, onChange, invalid, describedBy }: {
  id: string;
  name: string;
  placeholder: string;
  choices: Choice[];
  value: string[];
  onChange: (value: string[]) => void;
  invalid: boolean;
  describedBy: string;
}) {
  const [open, setOpen] = useState(false);
  const [term, setTerm] = useState("");
  const [highlight, setHighlight] = useState(0);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const container = useRef<HTMLSpanElement>(null);
  const search = useRef<HTMLInputElement>(null);
  // Select2 lists choices in option order, not in selection order.
  const chosen = choices.filter((c) => value.includes(c.value));
  const results = choices.filter((c) => plain(c.label).includes(plain(term)));
  const containerId = `select2-${id}-container`;

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
      if (!container.current?.contains(target) && !document.getElementById(`select2-${id}-results`)?.contains(target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
      document.removeEventListener("mousedown", close);
    };
  }, [open, id, value.length]);

  function show() {
    setOpen(true);
    setHighlight(Math.max(0, results.findIndex((c) => value.includes(c.value))));
  }
  // A click on a chosen option removes it; Enter on it only closes (Select2 4.1).
  function toggle(choice: Choice, fromKeyboard = false) {
    if (!(fromKeyboard && value.includes(choice.value))) {
      onChange(value.includes(choice.value) ? value.filter((v) => v !== choice.value) : [...value, choice.value]);
    }
    // closeOnSelect: the dropdown closes and the search is cleared.
    setOpen(false);
    setTerm("");
    search.current?.focus();
  }
  // The remove cross unselects, clears the search and opens the results on the first chosen one.
  function removeChoice(choice: Choice) {
    const next = value.filter((v) => v !== choice.value);
    onChange(next);
    setTerm("");
    setOpen(true);
    setHighlight(Math.max(0, choices.findIndex((c) => next.includes(c.value))));
  }
  function keyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) { show(); return; }
      setHighlight((h) => Math.min(Math.max(h + (event.key === "ArrowDown" ? 1 : -1), 0), Math.max(results.length - 1, 0)));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (!open) show();
      else if (results[highlight]) toggle(results[highlight], true);
    } else if (event.key === "Escape" || event.key === "Tab") {
      setOpen(false);
    } else if (event.key === "Backspace" && term === "" && chosen.length) {
      // Select2 removes the last choice and leaves its text in the search box.
      event.preventDefault();
      const last = chosen[chosen.length - 1];
      onChange(value.filter((v) => v !== last.value));
      setTerm(last.label);
      setOpen(true);
    }
  }
  const searchWidth = chosen.length === 0 ? "100%" : `${(term.length + 1) * 0.75}em`;
  return (
    <>
      <select name={name} className={`form-control js-tecnico selectmultiple form-select${invalid ? " is-invalid" : ""} select2-hidden-accessible`}
        data-role="select2" data-placeholder={placeholder} aria-label={placeholder} required aria-invalid={invalid ? "true" : undefined}
        aria-describedby={describedBy} id={id} multiple tabIndex={-1} aria-hidden="true" value={value} onChange={() => undefined}>
        {choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      <span ref={container} className={`select2 select2-container select2-container--default${open ? " select2-container--below select2-container--open" : ""}`}
        dir="ltr" style={{ width: "100%" }}>
        <span className="selection">
          <span className="select2-selection select2-selection--multiple" role="combobox" aria-haspopup="true" aria-expanded={open} tabIndex={-1}
            aria-disabled="false" aria-owns={open ? `select2-${id}-results` : undefined}
            onMouseDown={(event) => { if ((event.target as HTMLElement).closest(".select2-selection__choice__remove")) return; event.preventDefault(); search.current?.focus(); if (open) setOpen(false); else show(); }}>
            <ul className="select2-selection__rendered" id={containerId}>
              {chosen.map((c) => (
                <li key={c.value} className="select2-selection__choice" title={c.label}>
                  <button type="button" className="select2-selection__choice__remove" tabIndex={-1} title="Remove item" aria-label="Remove item"
                    aria-describedby={`${containerId}-choice-${c.value}`} onClick={() => removeChoice(c)}>
                    <span aria-hidden="true">×</span>
                  </button>
                  <span className="select2-selection__choice__display" id={`${containerId}-choice-${c.value}`}>{c.label}</span>
                </li>
              ))}
            </ul>
            <span className="select2-search select2-search--inline">
              <input ref={search} className="select2-search__field" type="search" tabIndex={0} autoCorrect="off" autoCapitalize="none" spellCheck={false}
                role="searchbox" aria-autocomplete="list" autoComplete="off" aria-describedby={containerId}
                aria-controls={open ? `select2-${id}-results` : undefined}
                placeholder={chosen.length ? "" : placeholder} style={{ width: searchWidth }} value={term}
                onChange={(event) => { setTerm(event.target.value); setOpen(true); setHighlight(0); }} onKeyDown={keyDown} />
            </span>
          </span>
        </span>
        <span className="dropdown-wrapper" aria-hidden="true" />
      </span>
      {open && createPortal(
        <span className="select2-container select2-container--default select2-container--open" style={{ position: "absolute", top: `${position.top}px`, left: `${position.left}px` }}>
          <span className="select2-dropdown select2-dropdown--below" dir="ltr" style={{ width: `${position.width}px` }}>
            <span className="select2-results">
              <ul className="select2-results__options" role="listbox" aria-multiselectable="true" id={`select2-${id}-results`} aria-expanded="true" aria-hidden="false">
                {results.length ? results.map((c, index) => (
                  <li key={c.value} id={`select2-${id}-result-${c.value}`} role="option" aria-selected={value.includes(c.value)}
                    className={`select2-results__option select2-results__option--selectable${value.includes(c.value) ? " select2-results__option--selected" : ""}${index === highlight ? " select2-results__option--highlighted" : ""}`}
                    onMouseEnter={() => setHighlight(index)} onMouseDown={(event) => event.preventDefault()} onClick={() => toggle(c)}>
                    {c.label}
                  </li>
                )) : <li className="select2-results__option select2-results__message" role="alert" aria-live="assertive">Sin resultados</li>}
              </ul>
            </span>
          </span>
        </span>,
        document.body,
      )}
    </>
  );
}
