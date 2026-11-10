import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";

/**
 * J2 remote selector of Inspecciones: the closed/open markup of the native
 * Select2 4.1 (`panel.js`) so `select2.min.css` and `panel.css` style it the same,
 * with its texts («Escribí al menos N letras», «Buscando…», «Sin resultados»),
 * 250 ms delay, allowClear and the two-line option. A hidden native `<select>`
 * keeps the form field, so the filter form submits exactly as before. Response
 * text is rendered as text, never as HTML.
 */
export type InspOption = { id: number; text: string; detalle?: string };

type Results = { status: "short" | "searching" | "empty" | "ready" | "error"; options: InspOption[] };
type Fetched = { term: string; status: "empty" | "ready" | "error"; options: InspOption[] };

function isOption(value: unknown): value is InspOption {
  if (!value || typeof value !== "object") return false;
  const option = value as Record<string, unknown>;
  return Number.isSafeInteger(option.id) && typeof option.text === "string" &&
    (option.detalle === undefined || typeof option.detalle === "string");
}

export default function InspSelect2({ id, name, placeholder, minimum, initial, search }: {
  id: string;
  name: string;
  placeholder: string;
  minimum: number;
  initial: InspOption | null;
  /** Remote search; resolves `{results}` of the J2 endpoint. */
  search: (term: string, signal: AbortSignal) => Promise<unknown>;
}) {
  const [selected, setSelected] = useState<InspOption | null>(initial);
  const [open, setOpen] = useState(false);
  const [term, setTerm] = useState("");
  const [fetched, setFetched] = useState<Fetched | null>(null);
  const [highlight, setHighlight] = useState(0);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const container = useRef<HTMLSpanElement>(null);
  const selection = useRef<HTMLSpanElement>(null);
  const field = useRef<HTMLInputElement>(null);
  const hidden = useRef<HTMLSelectElement>(null);
  const changed = useRef(false);

  useLayoutEffect(() => {
    if (!open || !container.current) return;
    const box = container.current.getBoundingClientRect();
    setPosition({ top: box.bottom + window.scrollY, left: box.left + window.scrollX, width: box.width });
    field.current?.focus();
  }, [open]);

  // Results are stored per term; the shown state derives from the current term.
  const results: Results = term.length < minimum ? { status: "short", options: [] }
    : fetched?.term === term ? fetched : { status: "searching", options: [] };
  useEffect(() => {
    if (!open || term.length < minimum) return undefined;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      search(term.trim(), controller.signal).then((data) => {
        const list = (data as { results?: unknown })?.results;
        setHighlight(0);
        if (!Array.isArray(list) || !list.every(isOption)) setFetched({ term, status: "error", options: [] });
        else setFetched({ term, status: list.length ? "ready" : "empty", options: list });
      }).catch(() => { if (!controller.signal.aborted) setFetched({ term, status: "error", options: [] }); });
    }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [open, term, minimum, search]);

  useEffect(() => {
    if (!open) return undefined;
    const outside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (container.current?.contains(target) || document.getElementById(`${id}-dropdown`)?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", outside);
    return () => document.removeEventListener("mousedown", outside);
  }, [open, id]);

  // The hidden select carries the value; fire the native change after React committed it,
  // so the form's auto-submit listener reacts as it does to Select2.
  useEffect(() => {
    if (!changed.current) return;
    changed.current = false;
    hidden.current?.dispatchEvent(new Event("change", { bubbles: true }));
  }, [selected]);

  const close = () => { setOpen(false); setTerm(""); selection.current?.focus(); };
  const choose = (option: InspOption | null) => { changed.current = true; setSelected(option); close(); };
  const keyOnSelection = (event: KeyboardEvent) => {
    if (["Enter", " ", "ArrowDown", "ArrowUp"].includes(event.key)) { event.preventDefault(); setOpen(true); }
  };
  const keyOnSearch = (event: KeyboardEvent) => {
    const options = results.status === "ready" ? results.options : [];
    if (event.key === "Escape" || event.key === "Tab") { if (event.key === "Escape") event.preventDefault(); close(); return; }
    if (event.key === "ArrowDown") { event.preventDefault(); setHighlight((h) => Math.min(h + 1, Math.max(options.length - 1, 0))); }
    if (event.key === "ArrowUp") { event.preventDefault(); setHighlight((h) => Math.max(h - 1, 0)); }
    if (event.key === "Enter") { event.preventDefault(); if (options[highlight]) choose(options[highlight]); }
  };
  const resultsId = `select2-${id}-results`;
  const renderedId = `select2-${id}-container`;
  const message = results.status === "short" ? `Escribí al menos ${minimum} letras`
    : results.status === "searching" ? "Buscando…"
      : results.status === "empty" ? "Sin resultados"
        : results.status === "error" ? "No se pudieron cargar los resultados" : "";
  return (
    <>
      <select ref={hidden} id={id} name={name} tabIndex={-1} className="select2-hidden-accessible" aria-hidden="true" data-insp-auto-submit="" value={selected ? String(selected.id) : ""} onChange={() => undefined}>
        <option value="" />
        {selected && <option value={selected.id}>{selected.text}</option>}
      </select>
      <span ref={container} className={`select2 select2-container select2-container--default${open ? " select2-container--below select2-container--open select2-container--focus" : ""}`} dir="ltr">
        <span className="selection">
          <span ref={selection} className="select2-selection select2-selection--single" role="combobox" aria-haspopup="true" aria-expanded={open} tabIndex={0} aria-disabled="false" aria-labelledby={renderedId} aria-owns={open ? resultsId : undefined}
            onMouseDown={(event) => { if ((event.target as HTMLElement).closest(".select2-selection__clear")) return; event.preventDefault(); if (open) close(); else setOpen(true); }}
            onKeyDown={keyOnSelection}>
            {selected && (
              <button type="button" className="select2-selection__clear" tabIndex={-1} title="Remove all items" aria-label="Remove all items" aria-describedby={renderedId}
                onMouseDown={(event) => { event.preventDefault(); event.stopPropagation(); choose(null); }}>
                <span aria-hidden="true">×</span>
              </button>
            )}
            <span className="select2-selection__rendered" id={renderedId} role="textbox" aria-readonly="true" title={selected?.text}>
              {selected ? selected.text : <span className="select2-selection__placeholder">{placeholder}</span>}
            </span>
            <span className="select2-selection__arrow" role="presentation"><b role="presentation" /></span>
          </span>
        </span>
        <span className="dropdown-wrapper" aria-hidden="true" />
      </span>
      {open && createPortal(
        <span id={`${id}-dropdown`} className="select2-container select2-container--default select2-container--open" style={{ position: "absolute", top: `${position.top}px`, left: `${position.left}px` }}>
          <span className="select2-dropdown select2-dropdown--below" dir="ltr" style={{ width: `${position.width}px` }}>
            <span className="select2-search select2-search--dropdown">
              <input ref={field} className="select2-search__field" type="search" tabIndex={0} autoCorrect="off" autoCapitalize="none" spellCheck={false} role="searchbox" aria-autocomplete="list" autoComplete="off" aria-controls={resultsId}
                value={term} onChange={(event) => setTerm(event.target.value)} onKeyDown={keyOnSearch} />
            </span>
            <span className="select2-results">
              <ul className="select2-results__options" role="listbox" id={resultsId} aria-expanded="true" aria-hidden="false">
                {results.status === "ready" ? results.options.map((option, index) => (
                  <li key={option.id} className={`select2-results__option select2-results__option--selectable${index === highlight ? " select2-results__option--highlighted" : ""}`} role="option" aria-selected={selected?.id === option.id}
                    onMouseEnter={() => setHighlight(index)} onMouseUp={() => choose(option)}>
                    {option.detalle ? <span>{option.text}<span className="insp-detalle">{option.detalle}</span></span> : option.text}
                  </li>
                )) : (
                  <li role="alert" aria-live="assertive" className={`select2-results__option ${results.status === "searching" ? "loading-results" : "select2-results__message"}`}>{message}</li>
                )}
              </ul>
            </span>
          </span>
        </span>,
        document.body,
      )}
    </>
  );
}
