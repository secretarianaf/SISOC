/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validator and navigation seam are exported for the tests. */
import { useCallback, useRef, useState } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { safeInternalPath } from "../webAccess";
import { Breadcrumb, breadcrumbValid, internal, record, renderMain, text, useMainResource, type Breadcrumbs } from "./MainFrame";
import type { RouteDefinition } from "./types";
import { useModalTabTrap } from "./nativeParity";

/**
 * RM01.01 global list of monthly rendiciones
 * (`rendicioncuentasmensual_global_list.html`): `search_bar.html` in filters
 * mode (`advanced_filters.js`), the column preferences modal
 * (`column_config.js`), the native cells, `pagination.html` («Volver» /
 * «Continuar») and the CSV button (`export_helper.js`, native GET
 * `listado/?export=csv`). Data comes from
 * `/api/web/comedores/rendicioncuentasmensual/listado/`, which runs the native
 * view; every cell is the text the native include renders.
 */
type Option = { value: string; label: string };
type FilterField = { name: string; label: string; type: string; input?: { step?: string; min?: string; max?: string }; options?: Option[]; choices?: Option[] };
type FiltersConfig = { fields: FilterField[]; defaultOperators?: Record<string, string>; defaultField?: string; booleanOptions?: Option[] };
type Column = { key: string; title: string; active: boolean; required: boolean; default: boolean };
type Columns = { list_key: string; endpoint: string; modal_id: string; script_id: string; available: Column[]; active: string[]; defaults: string[] };
type Cell = { text: string; badge: string | null };
type Row = { id: number; cells: Cell[]; detail_url: string };
type Page = { is_paginated: boolean; number: number; count: number; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type RendicionListData = {
  breadcrumb: Breadcrumbs;
  filters_config: FiltersConfig;
  favorites: { section: string; url: string; detail_url_template: string };
  urls: { list: string; reset: string; export: string; nueva_auditoria: string };
  can_export: boolean;
  can_nueva_auditoria: boolean;
  columns: Columns;
  headers: string[];
  results: Row[];
  page: Page;
  messages: Message[];
};

const API = "web/comedores/rendicioncuentasmensual/listado/";
const LEVELS = ["success", "error", "warning", "info"];
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);

export function listValid(v: unknown): v is RendicionListData {
  if (!record(v) || !record(v.filters_config) || !record(v.favorites) || !record(v.urls) || !record(v.columns) || !record(v.page)) return false;
  const f = v.filters_config, c = v.columns, p = v.page, u = v.urls;
  return breadcrumbValid(v.breadcrumb) &&
    Array.isArray(f.fields) && f.fields.length > 0 && f.fields.every((x) => record(x) && text(x.name) && text(x.label) && text(x.type)) &&
    text(v.favorites.section) && internal(v.favorites.url) && internal(v.favorites.detail_url_template) &&
    ["list", "reset", "export", "nueva_auditoria"].every((k) => internal(u[k])) &&
    typeof v.can_export === "boolean" && typeof v.can_nueva_auditoria === "boolean" &&
    text(c.list_key) && internal(c.endpoint) && text(c.modal_id) && text(c.script_id) &&
    Array.isArray(c.available) && c.available.every((x) => record(x) && text(x.key) && text(x.title) && typeof x.active === "boolean" && typeof x.required === "boolean") &&
    Array.isArray(v.headers) && v.headers.every(text) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && integer(r.id) && internal(r.detail_url) && Array.isArray(r.cells) &&
      r.cells.every((x) => record(x) && text(x.text) && (x.badge === null || text(x.badge)))) &&
    typeof p.is_paginated === "boolean" && integer(p.number) && integer(p.count) &&
    (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || integer(n)) && text(p.query_without_page) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Full-page navigation (CSV download, reload after saving columns); replaceable in tests. */
export const rendicionNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};

// --- Filters (`advanced_filters.js`) ---------------------------------------

type FilterRow = { key: number; field: string; value: string };
type Prefill = { field?: unknown; value?: unknown };
const isChoice = (field: FilterField) => field.type === "choice" || field.type === "boolean";

function choiceOptions(field: FilterField, config: FiltersConfig): Option[] {
  if (field.options?.length) return field.options;
  if (field.type === "boolean") return config.booleanOptions ?? [{ value: "true", label: "Sí" }, { value: "false", label: "No" }];
  return field.choices ?? [];
}

/** `applyInputAttributes`: number keeps a step, date its picker, the rest is text. */
function inputType(field: FilterField) {
  return field.type === "number" ? "number" : field.type === "date" ? "date" : "text";
}

function Filters({ data }: { data: RendicionListData }) {
  const config = data.filters_config;
  const fields = config.fields.filter((f) => f.name && f.label);
  const byName = new Map(fields.map((f) => [f.name, f]));
  const defaults: Record<string, string> = { text: "contains", number: "eq", date: "eq", boolean: "eq", choice: "eq", ...config.defaultOperators };
  const fallback = config.defaultField && byName.has(config.defaultField) ? config.defaultField : "";
  // A choice row without a value shows (and sends) its first option, as the native select does.
  const firstValue = (name: string) => {
    const definition = byName.get(name) ?? fields[0];
    return isChoice(definition) ? choiceOptions(definition, config)[0]?.value ?? "" : "";
  };
  const [rows, setRows] = useState<FilterRow[]>(() => {
    const blank = (key: number): FilterRow => ({ key, field: fallback, value: firstValue(fallback) });
    try {
      const raw = new URLSearchParams(window.location.search).get("filters");
      if (!raw) return [blank(0)];
      const parsed: unknown = JSON.parse(raw);
      if (!record(parsed) || !Array.isArray(parsed.items) || !parsed.items.length) return [blank(0)];
      return parsed.items.map((item: Prefill, index: number) => {
        if (!record(item) || !text(item.field) || !byName.has(item.field)) return blank(index);
        const value = item.value === undefined ? undefined : String(item.value);
        return { key: index, field: item.field, value: value ?? firstValue(item.field) };
      });
    } catch {
      return [blank(0)];
    }
  });
  const next = useRef(rows.length);
  const hidden = useRef<HTMLInputElement>(null);
  const update = (key: number, change: Partial<FilterRow>) => setRows((current) => current.map((r) => (r.key === key ? { ...r, ...change } : r)));
  function submit() {
    // The native submit handler only serializes; the browser then sends the GET form.
    const items = rows.flatMap((row) => {
      const field = row.field || fields[0].name;
      const definition = byName.get(field);
      if (!definition) return [];
      const value = isChoice(definition) ? row.value : row.value.trim();
      return value !== "" ? [{ field, op: defaults[definition.type] ?? "contains", value }] : [];
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
                  step={!choice && definition.type === "number" ? definition.input?.step ?? "1" : undefined}
                  min={choice ? undefined : definition.input?.min} max={choice ? undefined : definition.input?.max}
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
                  onClick={() => setRows((current) => [...current, { key: next.current++, field: fallback, value: firstValue(fallback) }])}>
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
      rendicionNavigation.reload();
    } catch (e: unknown) {
      setError(e instanceof Error && e.message ? e.message : fallback);
      setPending(false); busy.current = false;
    }
  }, [columns, order, selected]);
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

// --- Table (`rendicioncuentasmensual_global_list.html`) ---------------------

function Table({ data }: { data: RendicionListData }) {
  const [configOpen, setConfigOpen] = useState(false);
  const close = useCallback(() => setConfigOpen(false), []);
  const { cardRef, tableRef, classes } = useLegacyScrollHints(JSON.stringify(data.columns.active));
  return (
    <div className="row mt-5 max-width-100">
      <div className="col-12">
        <div className="card comedor-table-card">
          <div ref={cardRef} className={`card-body ${classes.card}`}>
            <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
              <div>
                <div className="d-flex justify-content-start mb-2">
                  <button type="button" className="btn btn-outline-warning btn-sm" data-bs-toggle="modal" data-bs-target={`#${data.columns.modal_id}`}
                    onClick={() => setConfigOpen(true)}>Configurar columnas</button>
                </div>
                {configOpen && <ColumnModal columns={data.columns} close={close} />}
              </div>
              {data.can_nueva_auditoria && (
                <a href={data.urls.nueva_auditoria} className="btn btn-primary"><i className="fas fa-clipboard-check" aria-hidden="true" />{" "}Nueva Auditoría</a>
              )}
            </div>
            <div ref={tableRef} className={`table-responsive-lg ${classes.table}`}>
              <table className="table table-comedor-moderno">
                <thead>
                  <tr>
                    {data.headers.map((header, index) => <th key={`${index}:${header}`}>{header}</th>)}
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.length ? data.results.map((row) => (
                    <tr key={row.id}>
                      {row.cells.map((cell, index) => <td key={index}>{cell.badge !== null ? <span className={cell.badge}>{cell.text}</span> : cell.text}</td>)}
                      <td>
                        <div className="comedor-actions">
                          <a href={safeInternalPath(row.detail_url) ?? "/"} className="btn btn-ver" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
                        </div>
                      </td>
                    </tr>
                  )) : (
                    <tr><td colSpan={data.headers.length + 1}>No hay rendiciones registradas.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Pagination (`pagination.html` with «Volver» / «Continuar») -------------

function Pagination({ page }: { page: Page }) {
  const href = (n: number) => `?${page.query_without_page}page=${n}`;
  return (
    <div className="mt-2">
      {page.is_paginated && (
        <ul className="pagination">
          <li className={`page-item${page.previous === null ? " disabled" : ""}`}>
            <a href={page.previous === null ? "#" : href(page.previous)} className="page-link">Volver</a>
          </li>
          {page.range.map((n, index) => (n === "…" ? (
            <li key={`gap-${index}`} className="page-item disabled"><a href="#" className="page-link">...</a></li>
          ) : (
            <li key={n} className={`page-item ${page.number === n ? "active" : ""}`}><a href={href(n)} className="page-link">{n}</a></li>
          )))}
          <li className={`page-item${page.next === null ? " disabled" : ""}`}>
            <a href={page.next === null ? "#" : href(page.next)} className="page-link">Continuar</a>
          </li>
        </ul>
      )}
      {/* An empty `page_obj` is falsy in the template: no count line. */}
      {page.count > 0 && <p className="text-center text-muted mb-0 mt-1">Se encontraron {page.count} resultados</p>}
    </div>
  );
}

/** `export_helper.js`: the native CSV URL with the current query (no sortable headers here). */
function exportCsv(base: string) {
  const url = new URL(base, window.location.href);
  if (url.origin !== window.location.origin) return;
  new URLSearchParams(window.location.search).forEach((value, key) => url.searchParams.set(key, value));
  rendicionNavigation.assign(`${url.pathname}${url.search}`);
}

export function RendicionListContent({ data }: { data: RendicionListData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <InsumosToastList messages={data.messages} />
      <div className="comedor-list-container">
        <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
        <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
        <div className="poncho-topbar">
          {data.can_export && (
            <button type="button" className="poncho-export btn-export-csv" data-url={data.urls.export} title="Descargar listado actual en CSV"
              onClick={() => exportCsv(data.urls.export)}>
              <i className="fas fa-file-excel" aria-hidden="true" />Exportar búsqueda
            </button>
          )}
        </div>
        <h2 className="text-center mb-4 poncho-titulo">Buscar Rendiciones</h2>
        <Filters data={data} />
        <div className="row mt-3">
          <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
            <a href={data.urls.reset} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
          </div>
        </div>
        <Table data={data} />
        <Pagination page={data.page} />
      </div>
    </>
  );
}

function ListadoPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando rendiciones…", (data) => ({
    title: "Rendiciones",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <RendicionListContent data={data} />,
  }));
}

// Native URL of `rendicioncuentasmensual/urls.py` under the runtime's
// `rendicioncuentasmensual/` include (the prefix is repeated on purpose).
const LISTADO = "/rendicioncuentasmensual/rendicioncuentasmensual/listado/";

export const rendicionMensualRoute: RouteDefinition<Record<string, never>> = {
  name: "comedores-rendicion-mensual",
  match(pathname) {
    return pathname === LISTADO ? {} : null;
  },
  render() {
    return <ListadoPage />;
  },
};
