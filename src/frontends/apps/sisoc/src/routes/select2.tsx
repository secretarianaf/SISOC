/* eslint-disable react-refresh/only-export-components -- shared parity module: components plus the helpers and hooks that go with them. */
import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type SelectHTMLAttributes } from "react";
import { createPortal } from "react-dom";
import type { ReactNode } from "react";

/**
 * Select2 4.1 look-alike over local choices (markup of the native widget, so `select2.min.css`
 * styles it the same). The hidden native `<select>` stays in the DOM and owns the form value.
 *
 * One component for the four local variants that used to live in `cdfSelect2`, `duplasSelect2`,
 * `pasSelect2` and `datacalleSelect2`. Each difference between them is an explicit option; the
 * defaults reproduce the `datacalle`/`pas` interaction. The remote selector of Inspecciones
 * (`InspSelect2`) keeps its own async data source; its focus rule is available here as
 * `singleFocus="selection"`.
 *
 * `remote` reproduces the `ajax` source Select2 builds from the widget's `data-ajax--*` attributes
 * (the big VAT selects of #2889): the choices are only the chosen value and the rest is searched.
 */
export type Choice = { value: string; label: string };

/** Select2 `ajax` from `data-ajax--url`, `data-ajax--delay` and `data-minimum-input-length`. */
export type RemoteSource = { url: string; delay: number; minimumInputLength: number };

type Fetched = { term: string; status: "ready" | "error"; options: Choice[] };

const isRemoteOption = (o: unknown): o is { id: string | number; text: string } =>
  typeof o === "object" && o !== null && ["string", "number"].includes(typeof (o as { id?: unknown }).id) && typeof (o as { text?: unknown }).text === "string";

/** Elemento desde el que el navegador mide un hijo `position: absolute` de `parent`. */
const baseDePosicion = (parent: HTMLElement): HTMLElement | null => {
  if (getComputedStyle(parent).position !== "static") return parent;
  return parent.offsetParent as HTMLElement | null;
};

export const plain = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { [key: `data-${string}`]: string | undefined };

export type Select2Props = {
  id: string;
  name: string;
  choices: Choice[];
  value: string[];
  onChange: (value: string[]) => void;
  multiple?: boolean;
  /** Text of the placeholder (single: the box; multiple: the search field). Undefined: none. */
  placeholder?: string;
  /** Classes of the hidden native select, without `is-invalid` and `select2-hidden-accessible`. */
  selectClassName: string;
  /** Extra attributes of the hidden native select (`required`, `data-*`, `aria-label`, `aria-describedby`). */
  selectProps?: SelectProps;
  invalid?: boolean;
  disabled?: boolean;
  /** Message of the results list when nothing matches. */
  noResults: string;
  /** `dropdownParent`: undefined = `<body>` (tracks scroll); an element = placed inside it; null = not available yet (nothing shown). */
  dropdownParent?: HTMLElement | null;
  /** Hide the choice with an empty value from the results and the chosen list (a placeholder stands for it). */
  hideEmptyChoice?: boolean;
  /** The clear cross: none, fires on click (also empties the search) or on mousedown (also closes). */
  clearTrigger?: "none" | "click" | "mousedown";
  /** Which element gets `select2-container--focus`: none, the inline search field, or anything focused inside the container. */
  focusMarker?: "none" | "search" | "container";
  /** `keep`: opening/closing leaves the typed term and Escape/Tab only close; `reset`: opening/closing clears it, Escape refocuses. */
  termHandling?: "keep" | "reset";
  /** Enter on an already chosen option of a multiple: `close` only closes (Select2 4.1), `toggle` removes it. */
  enterOnSelected?: "close" | "toggle";
  /** The remove cross of a chip clears the search and opens the results on the first chosen option. */
  removeOpensResults?: boolean;
  /** Mousedown counts as outside unless it lands on the results list (`results`) or anywhere in the dropdown (`dropdown`). */
  outsideClick?: "results" | "dropdown";
  /** Single only. `search`: opening moves focus to the search field of the dropdown. `selection`: the box keeps focus (native single select: Enter, Space and Alt+ArrowDown open; Escape, Tab and Alt+ArrowUp close without moving focus). */
  singleFocus?: "search" | "selection";
  /** Preserve the viewport when restoring focus after the dropdown closes. */
  preventFocusScroll?: boolean;
  /** Rendered between the hidden native `<select>` and the Select2 box (where a script inserts feedback `afterend` of the select). */
  afterSelect?: ReactNode;
  /** Remote source: results come from `url` (`term`, `_type`, `q`) as `{results: [{id, text}]}`, not from `choices`. */
  remote?: RemoteSource;
};

function focusControl(control: HTMLElement | null, preventScroll: boolean) {
  if (preventScroll) control?.focus({ preventScroll: true });
  else control?.focus();
}

export default function Select2({
  id, name, choices, value, onChange, multiple = false, placeholder, selectClassName, selectProps, invalid = false, disabled = false,
  noResults, dropdownParent, hideEmptyChoice = false, clearTrigger = "none", focusMarker = "container", termHandling = "reset",
  enterOnSelected = "toggle", removeOpensResults = false, outsideClick = "dropdown", singleFocus = "search", preventFocusScroll = false,
  afterSelect, remote,
}: Select2Props) {
  const [open, setOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const [term, setTerm] = useState("");
  const [highlight, setHighlight] = useState(0);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  // Remote options picked here: the hidden select keeps their `<option>` like Select2 appends it.
  const [remembered, setRemembered] = useState<Choice[]>([]);
  const [fetched, setFetched] = useState<Fetched | null>(null);
  const container = useRef<HTMLSpanElement>(null);
  const selection = useRef<HTMLSpanElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const known = [...choices, ...remembered.filter((r) => !choices.some((c) => c.value === r.value))];
  // Select2 lists choices in option order, not in selection order.
  const options = hideEmptyChoice ? known.filter((c) => c.value !== "") : known;
  const chosen = options.filter((c) => value.includes(c.value));
  const remoteUrl = remote?.url;
  const remoteDelay = remote?.delay ?? 0;
  const minimumInput = remote?.minimumInputLength ?? 0;
  const remoteStatus = !remote ? null : term.length < minimumInput ? "short" : fetched?.term === term ? fetched.status : "searching";
  const results = !remote ? options.filter((c) => plain(c.label).includes(plain(term)))
    : remoteStatus === "ready" ? fetched!.options : [];
  // Select2 4.1 English messages (the native VAT pages load Select2 without a language).
  const message = remoteStatus === "short" ? `Please enter ${minimumInput - term.length} or more characters`
    : remoteStatus === "searching" ? "Searching…" : remoteStatus === "error" ? "The results could not be loaded." : noResults;
  const containerId = `select2-${id}-container`;
  const resultsId = `select2-${id}-results`;
  const keepTerm = termHandling === "keep";
  const selectionFocus = !multiple && singleFocus === "selection";
  const target = dropdownParent === undefined ? document.body : dropdownParent;

  useLayoutEffect(() => {
    if (!open || !container.current || dropdownParent === null) return undefined;
    const place = () => {
      const r = container.current!.getBoundingClientRect();
      // Como el AttachBody de Select2: el desplegable cuelga de dropdownParent, pero su
      // `position: absolute` se mide desde el primer ancestro posicionado. Con un padre
      // estático (#municipio-field en comedorForm) se medía desde el padre y el navegador
      // lo dibujaba arriba de todo (#2954).
      const base = dropdownParent ? baseDePosicion(dropdownParent) : null;
      if (base && base !== document.body) {
        const p = base.getBoundingClientRect();
        setPosition({ top: r.bottom - p.top - base.clientTop + base.scrollTop, left: r.left - p.left - base.clientLeft + base.scrollLeft, width: r.width });
      } else setPosition({ top: r.bottom + window.scrollY, left: r.left + window.scrollX, width: r.width });
    };
    place();
    window.addEventListener("resize", place);
    if (!dropdownParent) window.addEventListener("scroll", place, true);
    const close = (event: MouseEvent) => {
      const node = event.target as Node;
      const list = document.getElementById(resultsId);
      const inside = outsideClick === "results" ? list : list?.closest(".select2-container");
      if (!container.current?.contains(node) && !inside?.contains(node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => {
      window.removeEventListener("resize", place);
      if (!dropdownParent) window.removeEventListener("scroll", place, true);
      document.removeEventListener("mousedown", close);
    };
  }, [open, dropdownParent, resultsId, outsideClick, value.length]);

  useLayoutEffect(() => {
    // Sin scroll: este efecto corre antes del render con la posición calculada, con el
    // desplegable todavía en {0, 0}; enfocar con scroll subía la página entera (#2954).
    if (open && !multiple && !selectionFocus) search.current?.focus({ preventScroll: true });
  }, [open, multiple, selectionFocus]);

  // Select2 AjaxAdapter: waits `delay` after the last keystroke, cancels the previous request.
  useEffect(() => {
    if (!remoteUrl || !open || term.length < minimumInput) return undefined;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ term, _type: "query", q: term });
      fetch(`${remoteUrl}?${params}`, {
        credentials: "same-origin", headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" }, signal: controller.signal,
      })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((data: unknown) => {
          const list = (data as { results?: unknown } | null)?.results;
          setHighlight(0);
          if (!Array.isArray(list) || !list.every(isRemoteOption)) setFetched({ term, status: "error", options: [] });
          else setFetched({ term, status: "ready", options: list.map((o) => ({ value: String(o.id), label: o.text })) });
        })
        .catch(() => { if (!controller.signal.aborted) setFetched({ term, status: "error", options: [] }); });
    }, remoteDelay);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [remoteUrl, remoteDelay, minimumInput, open, term]);

  function show() {
    if (disabled) return;
    setOpen(true);
    if (!keepTerm) setTerm("");
    // `keep` looks into the filtered results; `reset` clears the term in the same batch, so it uses all options.
    setHighlight(Math.max(0, (keepTerm ? results : options).findIndex((c) => value.includes(c.value))));
  }
  function hide(refocus = true) {
    setOpen(false);
    setTerm("");
    if (refocus) focusControl((multiple ? search : selection).current, preventFocusScroll);
  }
  function pick(choice: Choice, fromKeyboard = false) {
    if (remote && !known.some((c) => c.value === choice.value)) setRemembered((r) => [...r, choice]);
    if (multiple) {
      if (!(fromKeyboard && enterOnSelected === "close" && value.includes(choice.value))) {
        onChange(value.includes(choice.value) ? value.filter((v) => v !== choice.value) : [...value, choice.value]);
      }
    } else onChange([choice.value]);
    hide();
  }
  function removeChoice(choice: Choice) {
    if (disabled) return;
    const next = value.filter((v) => v !== choice.value);
    onChange(next);
    if (removeOpensResults) {
      setTerm("");
      setOpen(true);
      setHighlight(Math.max(0, choices.findIndex((c) => next.includes(c.value))));
    }
  }
  function navigate(event: KeyboardEvent<HTMLElement>) {
    if (disabled) return;
    if (selectionFocus) { navigateSelection(event); return; }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) { show(); return; }
      setHighlight((h) => Math.min(Math.max(h + (event.key === "ArrowDown" ? 1 : -1), 0), Math.max(results.length - 1, 0)));
    } else if (event.key === "Enter" || (event.key === " " && !multiple && !open)) {
      event.preventDefault();
      if (!open) show();
      else if (results[highlight]) pick(results[highlight], true);
    } else if (event.key === "Escape") {
      if (keepTerm) setOpen(false);
      else if (open) { event.preventDefault(); event.stopPropagation(); hide(); }
    } else if (event.key === "Tab") {
      if (keepTerm) setOpen(false);
      else if (open) hide(false);
    } else if (multiple && event.key === "Backspace" && term === "" && chosen.length) {
      // Select2 removes the last choice and leaves its text in the search box.
      event.preventDefault();
      const last = chosen[chosen.length - 1];
      onChange(value.filter((v) => v !== last.value));
      setTerm(last.label);
      setOpen(true);
    }
  }
  // Native single select: the box keeps focus; shared by the box and the dropdown search field.
  function navigateSelection(event: KeyboardEvent<HTMLElement>) {
    if (!open) {
      if (event.key === "Enter" || event.key === " " || (event.key === "ArrowDown" && event.altKey)) { event.preventDefault(); show(); }
      return;
    }
    if (event.key === "Escape" || event.key === "Tab" || (event.key === "ArrowUp" && event.altKey)) { event.preventDefault(); hide(); return; }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((h) => Math.min(Math.max(h + (event.key === "ArrowDown" ? 1 : -1), 0), Math.max(results.length - 1, 0)));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (results[highlight]) pick(results[highlight], true);
    }
  }
  const boxMouseDown = (event: { target: EventTarget; preventDefault(): void }) => {
    if (disabled || (event.target as HTMLElement).closest(".select2-selection__clear, .select2-selection__choice__remove")) return;
    // The native single select takes focus on press; the others focus their search field themselves.
    if (!selectionFocus) event.preventDefault();
    if (keepTerm) {
      search.current?.focus();
      if (open) setOpen(false); else show();
    } else if (open) hide();
    else { show(); if (multiple) search.current?.focus(); }
  };
  const clearButton = clearTrigger !== "none" && chosen.length > 0 && (
    <button type="button" className="select2-selection__clear" tabIndex={-1} title="Remove all items" aria-label="Remove all items" aria-describedby={containerId}
      {...(clearTrigger === "click"
        ? { onClick: () => { onChange([]); setTerm(""); } }
        : { onMouseDown: (e: { preventDefault(): void; stopPropagation(): void }) => { e.preventDefault(); e.stopPropagation(); if (!disabled) { onChange([]); setOpen(false); } } })}>
      <span aria-hidden="true">×</span>
    </button>
  );
  const searchWidth = chosen.length === 0 && placeholder !== undefined ? "100%" : `${(term.length + 1) * 0.75}em`;
  const containerClass = ["select2 select2-container select2-container--default", open && "select2-container--below select2-container--open",
    focused && "select2-container--focus", disabled && "select2-container--disabled"].filter(Boolean).join(" ");
  const searchFocus = focusMarker === "search" ? { onFocus: () => setFocused(true), onBlur: () => setFocused(false) } : {};
  const containerFocus = focusMarker === "container" ? { onFocus: () => setFocused(true), onBlur: () => setFocused(false) } : {};
  return <>
    <select name={name} className={`${selectClassName}${invalid ? " is-invalid" : ""} select2-hidden-accessible`} id={id} multiple={multiple}
      disabled={disabled || undefined} aria-invalid={invalid ? "true" : undefined} tabIndex={-1} aria-hidden="true"
      {...selectProps} value={multiple ? value : value[0] ?? ""} onChange={() => undefined}>
      {known.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>
    {afterSelect}
    <span ref={container} className={containerClass} dir="ltr" style={{ width: "100%" }} {...containerFocus}>
      <span className="selection">
        {multiple
          ? <span className="select2-selection select2-selection--multiple" role="combobox" aria-haspopup="true" aria-expanded={open} tabIndex={-1}
            aria-disabled={disabled ? "true" : "false"} aria-owns={open ? resultsId : undefined} onMouseDown={boxMouseDown}>
            {clearButton}
            <ul className="select2-selection__rendered" id={containerId}>
              {chosen.map((c) => <li key={c.value} className="select2-selection__choice" title={c.label}>
                <button type="button" className="select2-selection__choice__remove" tabIndex={-1} title="Remove item" aria-label="Remove item"
                  aria-describedby={`${containerId}-choice-${c.value}`} onClick={() => removeChoice(c)}>
                  <span aria-hidden="true">×</span>
                </button>
                <span className="select2-selection__choice__display" id={`${containerId}-choice-${c.value}`}>{c.label}</span>
              </li>)}
            </ul>
            <span className="select2-search select2-search--inline">
              <input ref={search} className="select2-search__field" type="search" tabIndex={disabled ? -1 : 0} autoCorrect="off" autoCapitalize="none" spellCheck={false}
                role="searchbox" aria-autocomplete="list" autoComplete="off" aria-describedby={containerId} aria-controls={open ? resultsId : undefined}
                disabled={disabled || undefined} placeholder={chosen.length ? "" : placeholder ?? ""} style={{ width: searchWidth }} value={term}
                onChange={(e) => { setTerm(e.target.value); setOpen(true); setHighlight(0); }} onKeyDown={navigate} {...searchFocus} />
            </span>
          </span>
          : <span ref={selection} className="select2-selection select2-selection--single" role="combobox" aria-haspopup="true" aria-expanded={open}
            tabIndex={disabled ? -1 : 0} aria-disabled={disabled ? "true" : "false"} aria-labelledby={containerId} aria-owns={open ? resultsId : undefined}
            onMouseDown={boxMouseDown} onKeyDown={navigate}>
            {clearButton}
            <span className="select2-selection__rendered" id={containerId} role="textbox" aria-readonly="true" title={chosen[0]?.label}>
              {chosen[0] ? chosen[0].label : placeholder !== undefined && <span className="select2-selection__placeholder">{placeholder}</span>}
            </span>
            <span className="select2-selection__arrow" role="presentation"><b role="presentation" /></span>
          </span>}
      </span>
      <span className="dropdown-wrapper" aria-hidden="true" />
    </span>
    {open && target && createPortal(
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
                : <li className={`select2-results__option ${remoteStatus === "searching" ? "loading-results" : "select2-results__message"}`} role="alert" aria-live="assertive">{message}</li>}
            </ul>
          </span>
        </span>
      </span>,
      target,
    )}
  </>;
}
