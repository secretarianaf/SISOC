/* eslint-disable react-refresh/only-export-components -- shared list pieces export their config validator with the components. */
import { useCallback, useRef, useState } from "react";
import { leerCookie } from "@sisoc/api";
import { useModalTabTrap } from "./nativeParity";

/**
 * Shared pieces of the native listados (`components/search_bar.html`,
 * `column_config_modal.html`, `data_table.html`, `pagination.html`) used by the
 * Duplas, AC01 and CDF lists:
 *
 * - `Filters`: filters mode with `advanced_filters.js`. One full bar per filter,
 *   the operator taken from the field type; `choice`/`boolean` fields show a
 *   value select (`options`, then `booleanOptions` or "Sí"/"No", then
 *   `choices`) that starts on its first option; `number`/`date` fields use
 *   that input type (`step` 1 by default). The form stays a native GET.
 * - `ColumnModal`: column preferences (`column_config.js`), saved through the
 *   native AJAX endpoint; the page reloads after saving.
 * - `ServerSortHeader`: the header cell that links to the server ordering.
 * - `Pagination`: the `pagination.html` list with optional result count.
 */
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
const text = (v: unknown): v is string => typeof v === "string";

type Option = { value: string; label: string };
export type FilterField = { name: string; label: string; type: string; input?: { step?: string; min?: string; max?: string }; options?: Option[]; choices?: Option[] };
export type FiltersConfig = { fields: FilterField[]; defaultOperators?: Record<string, string>; defaultField?: string; booleanOptions?: Option[] };
export type Favorites = { section: string; url: string; detail_url_template: string };

export const filtersConfigValid = (v: unknown): v is FiltersConfig => record(v) && Array.isArray(v.fields) && v.fields.length > 0 &&
  v.fields.every((f) => record(f) && text(f.name) && text(f.label) && text(f.type));

// --- Filters (`advanced_filters.js`) ---------------------------------------

type Row = { key: number; field: string; value: string };
type Prefill = { field?: unknown; value?: unknown };

function choiceOptions(field: FilterField, config: FiltersConfig): Option[] {
  if (field.options?.length) return field.options;
  if (field.type === "boolean") return config.booleanOptions ?? [{ value: "true", label: "Sí" }, { value: "false", label: "No" }];
  return field.choices ?? [];
}
const isChoice = (field: FilterField) => field.type === "choice" || field.type === "boolean";
// `applyInputAttributes`: the value input follows the field type.
const inputType = (field: FilterField) => (field.type === "number" ? "number" : field.type === "date" ? "date" : "text");

function initialRows(config: FiltersConfig, byName: Map<string, FilterField>): Row[] {
  const fallback = config.defaultField && byName.has(config.defaultField) ? config.defaultField : "";
  const valueFor = (field: string, value = "") => {
    const definition = byName.get(field) ?? config.fields[0];
    return isChoice(definition) && value === "" ? choiceOptions(definition, config)[0]?.value ?? "" : value;
  };
  const blank = (key: number): Row => ({ key, field: fallback, value: valueFor(fallback) });
  try {
    const raw = new URLSearchParams(window.location.search).get("filters");
    if (!raw) return [blank(0)];
    const parsed: unknown = JSON.parse(raw);
    if (!record(parsed) || !Array.isArray(parsed.items) || !parsed.items.length) return [blank(0)];
    return parsed.items.map((item: Prefill, index: number) => (record(item) && text(item.field) && byName.has(item.field)
      ? { key: index, field: item.field, value: valueFor(item.field, item.value === undefined ? "" : String(item.value)) }
      : blank(index)));
  } catch {
    return [blank(0)];
  }
}

export function Filters({ config, action, favorites }: { config: FiltersConfig; action: string; favorites: Favorites }) {
  const fields = config.fields.filter((f) => f.name && f.label);
  const byName = new Map(fields.map((f) => [f.name, f]));
  const defaults: Record<string, string> = { text: "contains", number: "eq", date: "eq", boolean: "eq", choice: "eq", ...config.defaultOperators };
  const [rows, setRows] = useState(() => initialRows(config, byName));
  const next = useRef(rows.length);
  const hidden = useRef<HTMLInputElement>(null);
  const update = (key: number, change: Partial<Row>) => setRows((current) => current.map((r) => (r.key === key ? { ...r, ...change } : r)));
  const firstValue = (name: string) => {
    const definition = byName.get(name) ?? fields[0];
    return isChoice(definition) ? choiceOptions(definition, config)[0]?.value ?? "" : "";
  };
  function submit() {
    // The native submit handler only serializes; the browser then sends the GET form.
    const items = rows.flatMap((row) => {
      const field = row.field || fields[0].name;
      const definition = byName.get(field);
      const value = definition && isChoice(definition) ? row.value : row.value.trim();
      return definition && value !== "" ? [{ field, op: defaults[definition.type] ?? "contains", value }] : [];
    });
    if (hidden.current) hidden.current.value = JSON.stringify({ logic: "AND", items });
  }
  return (
    <form method="GET" action={action} id="filters-form" className="ms-0 ms-lg-5" data-config-id="filters-config-json"
      data-seccion-filtros-favoritos={favorites.section} data-url-filtros-favoritos={favorites.url}
      data-plantilla-url-filtro-favorito={favorites.detail_url_template} onSubmit={submit}>
      <div id="poncho-filters-rows" className="poncho-rows">
        {rows.map((row, index) => {
          const definition = byName.get(row.field) ?? fields[0];
          const choice = isChoice(definition);
          const options = choice ? [...choiceOptions(definition, config)] : [];
          if (choice && row.value !== "" && !options.some((o) => o.value === row.value)) options.push({ value: row.value, label: row.value });
          return (
            <div key={row.key} className="poncho-search poncho-search--row">
              <select className="poncho-search__field" data-rol="campo" aria-label="Buscar por" value={row.field}
                onChange={(e) => update(row.key, { field: e.target.value, value: firstValue(e.target.value) })}>
                <option value="">Buscar por</option>
                {fields.map((f) => <option key={f.name} value={f.name}>{f.label}</option>)}
              </select>
              <div className="poncho-search__box">
                <input type={inputType(definition)} className="poncho-search__input" data-rol="valor" autoComplete="off" aria-label="Valor a buscar"
                  placeholder={`Buscar por filtro ${index + 1}`} value={choice ? "" : row.value} hidden={choice} style={{ display: choice ? "none" : "" }}
                  step={definition.type === "number" ? definition.input?.step ?? "1" : undefined} min={definition.input?.min} max={definition.input?.max}
                  onChange={(e) => update(row.key, { value: e.target.value })} />
                <select className="poncho-search__input poncho-search__input--select" data-rol="valor-select" aria-label="Valor a buscar"
                  hidden={!choice} style={{ display: choice ? "" : "none" }} value={choice ? row.value : ""}
                  onChange={(e) => update(row.key, { value: e.target.value })}>
                  {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <button type="submit" className="poncho-search__go" aria-label="Buscar"><i className="fas fa-search" aria-hidden="true" /></button>
              </div>
              <div className="poncho-row-actions">
                <button type="button" className="poncho-addfilter" data-rol="agregar"
                  onClick={() => setRows((current) => {
                    const field = config.defaultField && byName.has(config.defaultField) ? config.defaultField : "";
                    return [...current, { key: next.current++, field, value: firstValue(field) }];
                  })}>
                  <i className="fas fa-plus" aria-hidden="true" /><span>Filtro</span>
                </button>
                <button type="button" className="poncho-removefilter" data-rol="quitar" hidden={index === 0} style={{ display: index > 0 ? "" : "none" }}
                  onClick={() => setRows((current) => current.filter((r) => r.key !== row.key))}>
                  <i className="fas fa-minus" aria-hidden="true" /><span>Filtro</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
      <input ref={hidden} type="hidden" name="filters" id="filters-input" />
    </form>
  );
}

// --- Column preferences (`column_config_modal.html` + `column_config.js`) ---

type Column = { key: string; title: string; active: boolean; required: boolean; default: boolean };
export type Columns = { list_key: string; endpoint: string; modal_id: string; script_id: string; available: Column[]; active: string[]; defaults: string[] };

/** `reload`: the page's full-page reload seam, called once the preference is saved. */
export function ColumnModal({ columns, close, reload }: { columns: Columns; close: () => void; reload: () => void }) {
  const [order, setOrder] = useState(columns.available.map((c) => c.key));
  const [selected, setSelected] = useState(() => columns.available.filter((c) => c.active).map((c) => c.key));
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const modal = useRef<HTMLDivElement>(null);
  const busy = useRef(false);
  useModalTabTrap(modal, close, { busy });
  const save = useCallback(async (reset: boolean) => {
    if (busy.current) return;
    const values = order.filter((k) => selected.includes(k));
    setError("");
    if (!reset && !values.length) { setError("Debe haber al menos una columna visible."); return; }
    const fallback = reset ? "No se pudo restablecer la configuracion." : "No se pudo guardar la configuracion.";
    busy.current = true; setPending(true);
    try {
      const response = await fetch(columns.endpoint, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": leerCookie("csrftoken") ?? "", "X-Requested-With": "XMLHttpRequest" },
        body: JSON.stringify(reset ? { list_key: columns.list_key, reset: true } : { list_key: columns.list_key, columns: values }),
      });
      const result: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(record(result) && text(result.error) ? result.error : fallback);
      reload();
    } catch (e: unknown) {
      setError(e instanceof Error && e.message ? e.message : fallback);
      setPending(false); busy.current = false;
    }
  }, [columns, order, selected, reload]);
  const move = (key: string, offset: number) => setOrder((current) => {
    const i = current.indexOf(key), j = i + offset;
    if (j < 0 || j >= current.length) return current;
    const nextOrder = [...current]; [nextOrder[i], nextOrder[j]] = [nextOrder[j], nextOrder[i]];
    return nextOrder;
  });
  const titleId = `${columns.modal_id}-title`;
  return (
    <>
      <div className="modal-backdrop fade show" />
      <div ref={modal} className="modal fade show d-block" id={columns.modal_id} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby={titleId}
        data-column-config="true" data-config-id={columns.script_id} onClick={(e) => { if (e.target === e.currentTarget && !pending) close(); }}>
        <div className="modal-dialog modal-dialog-centered modal-lg">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id={titleId}>Columnas visibles</h5>
              <button type="button" className="btn-close" aria-label="Cerrar" disabled={pending} onClick={close} />
            </div>
            <div className="modal-body">
              <p className="text-muted mb-3">Seleccioná qué columnas mostrar y ordenalas con las flechas.</p>
              <div className="list-group column-config-list">
                {order.map((key) => {
                  const column = columns.available.find((c) => c.key === key);
                  if (!column) return null;
                  const id = `${columns.modal_id}-${key}`;
                  return (
                    <div key={key} className="list-group-item d-flex flex-wrap align-items-center justify-content-between gap-2" data-column-key={key}>
                      <div className="form-check">
                        <input className="form-check-input column-config-checkbox" type="checkbox" id={id} checked={selected.includes(key)} disabled={pending || column.required}
                          onChange={(e) => setSelected((current) => (e.target.checked ? [...current, key] : current.filter((k) => k !== key)))} />
                        {" "}<label className="form-check-label" htmlFor={id}>{column.title}</label>
                        {column.required && <>{" "}<span className="badge bg-secondary ms-2">Obligatoria</span></>}
                      </div>
                      <div className="btn-group btn-group-sm" role="group">
                        <button type="button" className="btn btn-light column-move-up" title="Mover arriba" disabled={pending} onClick={() => move(key, -1)}><i className="fas fa-arrow-up" /></button>
                        <button type="button" className="btn btn-light column-move-down" title="Mover abajo" disabled={pending} onClick={() => move(key, 1)}><i className="fas fa-arrow-down" /></button>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className={`alert alert-danger mt-3 column-config-error${error ? "" : " d-none"}`}>{error}</div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary column-config-reset" disabled={pending} onClick={() => void save(true)}>Restablecer</button>
              <button type="button" className="btn btn-primary column-config-save" disabled={pending} onClick={() => void save(false)}>Guardar</button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// --- Server ordering header (`data_table.html` with `sort_url`) -------------

const SORT_ICON = { asc: "fa-sort-up", desc: "fa-sort-down" } as const;

export function ServerSortHeader({ title, url, direction }: { title: string; url: string; direction: "asc" | "desc" | null }) {
  return (
    <a href={url} className="d-flex align-items-center justify-content-between gap-2 text-reset text-decoration-none">
      {title} <i className={`fas ${direction ? SORT_ICON[direction] : "fa-sort"}`} />
    </a>
  );
}

// --- Pagination (`pagination.html`) -----------------------------------------

/**
 * `range` marks gaps with "…" or "..."; `count` is the result total line
 * (`null` hides it, as an empty page or a NoCount paginator does).
 */
export function Pagination({ paginated, number, previous, next, range, href, count, prevText = "Volver", nextText = "Continuar" }: {
  paginated: boolean; number: number; previous: number | null; next: number | null; range: (number | string)[];
  href: (page: number) => string; count: number | null; prevText?: string; nextText?: string;
}) {
  const end = (label: string, target: number | null) => (
    <li className={`page-item${target === null ? " disabled" : ""}`}>
      <a href={target === null ? "#" : href(target)} className="page-link">{label}</a>
    </li>
  );
  return (
    <div className="mt-2">
      {paginated && (
        <ul className="pagination">
          {end(prevText, previous)}
          {range.map((n, index) => (typeof n !== "number" ? (
            <li key={`gap-${index}`} className="page-item disabled"><a href="#" className="page-link">...</a></li>
          ) : (
            <li key={n} className={`page-item ${number === n ? "active" : ""}`}><a href={href(n)} className="page-link">{n}</a></li>
          )))}
          {end(nextText, next)}
        </ul>
      )}
      {count !== null && <p className="text-center text-muted mb-0 mt-1">Se encontraron {count} resultados</p>}
    </div>
  );
}
