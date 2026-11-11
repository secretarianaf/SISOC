/* eslint-disable react-refresh/only-export-components -- the list screen exports its validator and navigation seam for the unit tests. */
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { internal, record, text } from "./MainFrame";

/**
 * `lista_comedores.html`: `search_bar.html` in filters mode without the add
 * button (`advanced_filters.js`, choice fields included), `data_table.html`
 * with custom cells and actions, the server ordering header of «Nombre»,
 * column preferences (`column_config.js`) and the integrated
 * `pagination.html`. The CSV button is the native GET with the current query.
 *
 * The filters row and the column modal follow `routes/duplasList.tsx`; that
 * module does not export them, so they are repeated here (see the AC01 record).
 */
type Choice = { value: string; label: string };
type FilterField = { name: string; label: string; type: string; choices?: Choice[]; input?: { step?: string; min?: string; max?: string } };
type FiltersConfig = { fields: FilterField[]; defaultOperators?: Record<string, string>; defaultField?: string };
type Column = { key: string; title: string; active: boolean; required: boolean; default: boolean };
type Columns = { list_key: string; endpoint: string; modal_id: string; script_id: string; available: Column[]; active: string[]; defaults: string[] };
type Header = { title: string; sort_url: string | null; sort_direction: "asc" | "desc" | null };
type Cell = { content: string; data_attr: string | null; data_value: string | null };
type Action = { label: string; url: string; type: string };
type Row = { cells: Cell[]; actions: Action[] };
type Page = { is_paginated: boolean; number: number; count: number; has_rows: boolean; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type AcompanamientosListData = {
  filters_config: FiltersConfig; favorites: { section: string; url: string; detail_url_template: string };
  urls: { list: string; reset: string; export: string }; can_export: boolean; columns: Columns;
  headers: Header[]; results: Row[]; page: Page; messages: Message[];
};

const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const LEVELS = ["success", "error", "warning", "info"];

export function listValid(v: unknown): v is AcompanamientosListData {
  if (!record(v) || !record(v.filters_config) || !record(v.favorites) || !record(v.urls) || !record(v.columns) || !record(v.page)) return false;
  const f = v.filters_config, c = v.columns, p = v.page, u = v.urls;
  return Array.isArray(f.fields) && f.fields.length > 0 && f.fields.every((x) => record(x) && text(x.name) && text(x.label) && text(x.type)) &&
    text(v.favorites.section) && internal(v.favorites.url) && internal(v.favorites.detail_url_template) &&
    ["list", "reset", "export"].every((k) => internal(u[k])) && typeof v.can_export === "boolean" &&
    text(c.list_key) && internal(c.endpoint) && text(c.modal_id) && text(c.script_id) &&
    Array.isArray(c.available) && c.available.every((x) => record(x) && text(x.key) && text(x.title) && typeof x.active === "boolean" && typeof x.required === "boolean") &&
    Array.isArray(v.headers) && v.headers.every((h) => record(h) && text(h.title) && (h.sort_url === null || text(h.sort_url))) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && Array.isArray(r.cells) && r.cells.every((x) => record(x) && text(x.content)) &&
      Array.isArray(r.actions) && r.actions.every((a) => record(a) && text(a.label) && internal(a.url) && text(a.type))) &&
    typeof p.is_paginated === "boolean" && typeof p.has_rows === "boolean" && int(p.number) && int(p.count) &&
    (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || int(n)) && text(p.query_without_page) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Full-page navigation (export, reload); replaceable in tests. */
export const acompanamientosNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};

// --- Filters (`advanced_filters.js`) ---------------------------------------

type FilterRow = { key: number; field: string; value: string };

function initialRows(config: FiltersConfig, names: Set<string>): FilterRow[] {
  const blank = (key: number): FilterRow => ({ key, field: config.defaultField && names.has(config.defaultField) ? config.defaultField : "", value: "" });
  try {
    const raw = new URLSearchParams(window.location.search).get("filters");
    if (!raw) return [blank(0)];
    const parsed: unknown = JSON.parse(raw);
    if (!record(parsed) || !Array.isArray(parsed.items) || !parsed.items.length) return [blank(0)];
    return parsed.items.map((item: unknown, index: number) => (record(item) && text(item.field) && names.has(item.field)
      ? { key: index, field: item.field, value: item.value === undefined ? "" : String(item.value) }
      : blank(index)));
  } catch {
    return [blank(0)];
  }
}

function Filters({ data }: { data: AcompanamientosListData }) {
  const config = data.filters_config;
  const fields = config.fields.filter((f) => f.name && f.label);
  const byName = new Map(fields.map((f) => [f.name, f]));
  const defaults: Record<string, string> = { text: "contains", number: "eq", date: "eq", boolean: "eq", choice: "eq", ...config.defaultOperators };
  const [rows, setRows] = useState(() => initialRows(config, new Set(byName.keys())));
  const next = useRef(rows.length);
  const hidden = useRef<HTMLInputElement>(null);
  const update = (key: number, change: Partial<FilterRow>) => setRows((current) => current.map((r) => (r.key === key ? { ...r, ...change } : r)));
  function submit() {
    const items = rows.flatMap((row) => {
      const field = row.field || fields[0].name;
      const definition = byName.get(field);
      const value = row.value.trim();
      return definition && value !== "" ? [{ field, op: defaults[definition.type] ?? "contains", value }] : [];
    });
    if (hidden.current) hidden.current.value = JSON.stringify({ logic: "AND", items });
  }
  return (
    <form method="GET" action={data.urls.list} id="filters-form" className="ms-0 ms-lg-5" data-config-id="filters-config-json"
      data-seccion-filtros-favoritos={data.favorites.section} data-url-filtros-favoritos={data.favorites.url}
      data-plantilla-url-filtro-favorito={data.favorites.detail_url_template} onSubmit={submit}>
      <div id="poncho-filters-rows" className="poncho-rows">
        {rows.map((row, index) => {
          const definition = byName.get(row.field) ?? fields[0];
          const choice = definition.type === "choice";
          return (
            <div key={row.key} className="poncho-search poncho-search--row">
              <select className="poncho-search__field" data-rol="campo" aria-label="Buscar por" value={row.field}
                onChange={(e) => update(row.key, { field: e.target.value, value: "" })}>
                <option value="">Buscar por</option>
                {fields.map((f) => <option key={f.name} value={f.name}>{f.label}</option>)}
              </select>
              <div className="poncho-search__box">
                <input type={definition.type === "number" ? "number" : definition.type === "date" ? "date" : "text"} className="poncho-search__input" data-rol="valor"
                  autoComplete="off" aria-label="Valor a buscar" placeholder={`Buscar por filtro ${index + 1}`} value={choice ? "" : row.value}
                  step={definition.type === "number" ? definition.input?.step ?? "1" : undefined} min={definition.input?.min} max={definition.input?.max}
                  hidden={choice} style={choice ? { display: "none" } : undefined} onChange={(e) => update(row.key, { value: e.target.value })} />
                <select className="poncho-search__input poncho-search__input--select" data-rol="valor-select" aria-label="Valor a buscar"
                  hidden={!choice} style={choice ? undefined : { display: "none" }} value={choice ? row.value : ""} onChange={(e) => update(row.key, { value: e.target.value })}>
                  {choice && <><option value="">Seleccionar</option>{(definition.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</>}
                </select>
                <button type="submit" className="poncho-search__go" aria-label="Buscar"><i className="fas fa-search" aria-hidden="true" /></button>
              </div>
              <div className="poncho-row-actions">
                <button type="button" className="poncho-addfilter" data-rol="agregar"
                  onClick={() => setRows((current) => [...current, { key: next.current++, field: config.defaultField && byName.has(config.defaultField) ? config.defaultField : "", value: "" }])}>
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

function ColumnModal({ columns, close }: { columns: Columns; close: () => void }) {
  const [order, setOrder] = useState(columns.available.map((c) => c.key));
  const [selected, setSelected] = useState(() => columns.available.filter((c) => c.active).map((c) => c.key));
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const modal = useRef<HTMLDivElement>(null);
  const busy = useRef(false);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const before = document.body.style.overflow;
    document.body.classList.add("modal-open");
    document.body.style.overflow = "hidden";
    modal.current?.focus();
    const key = (e: KeyboardEvent) => { if (e.key === "Escape" && !busy.current) close(); };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      document.body.classList.remove("modal-open");
      document.body.style.overflow = before;
      previous?.focus();
    };
  }, [close]);
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
      acompanamientosNavigation.reload();
    } catch (e: unknown) {
      setError(e instanceof Error && e.message ? e.message : fallback);
      setPending(false); busy.current = false;
    }
  }, [columns, order, selected]);
  const move = (key: string, offset: number) => setOrder((current) => {
    const i = current.indexOf(key), j = i + offset;
    if (j < 0 || j >= current.length) return current;
    const copy = [...current]; [copy[i], copy[j]] = [copy[j], copy[i]];
    return copy;
  });
  const titleId = `${columns.modal_id}-title`;
  return (
    <>
      <div className="modal-backdrop fade show" />
      <div ref={modal} className="modal fade show d-block" id={columns.modal_id} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby={titleId}
        data-column-config="true" data-config-id={columns.script_id} onClick={(e) => { if (e.target === e.currentTarget && !pending) close(); }}>
        <div className="modal-dialog modal-dialog-centered modal-lg"><div className="modal-content">
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
        </div></div>
      </div>
    </>
  );
}

// --- Table (`data_table.html` with custom cells) and `pagination.html` -------

function Pagination({ page }: { page: Page }) {
  const href = (n: number) => `?${page.query_without_page}page=${n}`;
  const item = (label: string, target: number | null, extra = "") => target === null
    ? <li className={`page-item disabled${extra}`}><a href="#" className="page-link">{label}</a></li>
    : <li className={`page-item${extra}`}><a href={href(target)} className="page-link">{label}</a></li>;
  return <div className="mt-2">
    {page.is_paginated && <ul className="pagination">
      {item("Volver", page.previous)}
      {page.range.map((n, i) => <Fragment key={i}>{n === "…" ? item("...", null) : item(String(n), n, page.number === n ? " active" : " ")}</Fragment>)}
      {item("Continuar", page.next)}
    </ul>}
    {page.has_rows && <p className="text-center text-muted mb-0 mt-1">Se encontraron {page.count} resultados</p>}
  </div>;
}

const SORT_ICON = { asc: "fa-sort-up", desc: "fa-sort-down" } as const;

function Table({ data }: { data: AcompanamientosListData }) {
  const [configOpen, setConfigOpen] = useState(false);
  return (
    <div className="row mt-5 max-width-100"><div className="col-12"><div className="card"><div className="card-body">
      <div className="d-flex justify-content-start mb-2">
        <button type="button" className="btn btn-outline-warning btn-sm" data-bs-toggle="modal" data-bs-target={`#${data.columns.modal_id}`}
          onClick={() => setConfigOpen(true)}>Configurar columnas</button>
      </div>
      {configOpen && <ColumnModal columns={data.columns} close={() => setConfigOpen(false)} />}
      <div className="table-responsive-lg">
        <table className="table table-bordered table-striped projects ">
          <thead><tr>
            {data.headers.map((h, i) => <th key={i}>{h.sort_url
              ? <a href={h.sort_url} className="d-flex align-items-center justify-content-between gap-2 text-reset text-decoration-none">
                {h.title} <i className={`fas ${h.sort_direction ? SORT_ICON[h.sort_direction] : "fa-sort"}`} />
              </a>
              : h.title}</th>)}
            <th style={{ width: "15%" }} className="notexport">Acciones</th>
          </tr></thead>
          <tbody>
            {data.results.length ? data.results.map((row, r) => <tr key={r}>
              {row.cells.map((cell, i) => <td key={i} {...(cell.data_attr ? { [`data-${cell.data_attr}`]: cell.data_value || cell.content } : {})}>{cell.content}</td>)}
              <td className="project-actions text-right">
                {row.actions.length > 0 && <div className="action-buttons flex-wrap flex-lg-nowrap" role="group">
                  {row.actions.map((a) => <a key={a.label} href={a.url} className={`btn btn-${a.type} `} title={a.label}>{a.label}</a>)}
                </div>}
              </td>
            </tr>) : <tr><td colSpan={data.headers.length + 1} className="text-center text-muted py-4">No se encontraron comedores.</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination page={data.page} />
    </div></div></div></div>
  );
}

function exportCsv(base: string) {
  // `export_helper.js`: the native GET with the current query.
  const url = new URL(base, window.location.href);
  if (url.origin !== window.location.origin) return;
  new URLSearchParams(window.location.search).forEach((value, key) => url.searchParams.set(key, value));
  acompanamientosNavigation.assign(`${url.pathname}${url.search}`);
}

export function AcompanamientosListContent({ data }: { data: AcompanamientosListData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <InsumosToastList messages={data.messages} />
      <div className="poncho-topbar">
        {data.can_export && (
          <button type="button" className="poncho-export btn-export-csv" data-url={data.urls.export} title="Descargar listado actual en CSV"
            onClick={() => exportCsv(data.urls.export)}>
            <i className="fas fa-file-excel" aria-hidden="true" />Exportar búsqueda
          </button>
        )}
      </div>
      <h2 className="text-center mb-4 poncho-titulo">Comedores en Acompañamiento</h2>
      <Filters data={data} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.reset} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
        </div>
      </div>
      <Table data={data} />
    </>
  );
}
