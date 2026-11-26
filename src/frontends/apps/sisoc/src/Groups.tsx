import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { crearCliente, leerCookie } from "@sisoc/api";
import InsumosAccessError from "./InsumosAccessError";
import { useLegacyScrollHints } from "./useLegacyScrollHints";
import { InsumosToastList } from "./InsumosToast";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "./webAccess";
import type { RequiredPasswordPresentation } from "./RequiredPasswordChange";
import "./groups.css";

type Mode = "list" | "create" | "edit";
type Choice = { id: number; label: string };
type Field = { name: "name" | "permissions"; label: string; help_text: string; required: boolean; max_length?: number; choices?: Choice[] };
type Errors = Record<string, { message: string; code: string }[]>;
type FormData = { title: string; submit_text: string; fields: Field[]; initial: { name: string; permissions: string[] }; errors: Errors; presentation: RequiredPasswordPresentation };
type ColumnKey = "name" | "permissions_count" | "id";
type Columns = { list_key: string; endpoint: string; active: ColumnKey[]; defaults: ColumnKey[]; available: { key: ColumnKey; title: string; active: boolean; required: boolean; default: boolean }[] };
type Item = { id: number; name: string; permissions_count: number };
type ListData = { items: Item[]; query: string; columns: Columns; can_export: boolean; messages: { message: string; level: "success" | "error" | "warning" | "info" }[]; presentation: RequiredPasswordPresentation };
type Props = { mode: Mode; id?: string; renderFrame?: (content: ReactNode, presentation: RequiredPasswordPresentation, title: string, breadcrumb: ReactNode) => ReactNode; navigate?: (destination: string) => void };
type State = { status: "loading" | "error" } | { status: "forbidden"; prerequisite: WebPrerequisite | null } | { status: "ready"; data: FormData | ListData };
const client = crearCliente("/api");
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v) && v > 0;
const accepted = (status: number) => status >= 200 && status < 300 || status === 403;
const keys = ["name", "permissions_count", "id"];
function frameValid(v: unknown): v is RequiredPasswordPresentation {
  if (!record(v) || !record(v.user) || typeof v.footer_version_label !== "string" || !Array.isArray(v.legacy_frame_navigation)) return false;
  const node = (n: unknown): boolean => record(n) && typeof n.id === "string" && typeof n.label === "string" && (n.href === null || safeInternalPath(n.href) !== null) && Array.isArray(n.children) && n.children.every(node);
  return ["username", "display_name", "avatar_initial", "role_label"].every(k => typeof (v.user as Record<string, unknown>)[k] === "string") && v.legacy_frame_navigation.every(node);
}
// The native widget lists bound selections in catalog order, not submission order.
function catalogOrder(ids: string[], field: Field): string[] {
  const position = new Map((field.choices ?? []).map((choice, index) => [String(choice.id), index]));
  return [...ids].sort((a, b) => (position.get(a) ?? Infinity) - (position.get(b) ?? Infinity));
}
function errorsValid(v: unknown): v is Errors {
  return record(v) && Object.entries(v).every(([k, entries]) => ["name", "permissions", "__all__"].includes(k) && Array.isArray(entries) && entries.every(e => record(e) && typeof e.message === "string"));
}
function formValid(v: unknown): v is FormData {
  if (!record(v) || !frameValid(v.presentation) || !record(v.initial) || !Array.isArray(v.fields) || !errorsValid(v.errors)) return false;
  return typeof v.title === "string" && typeof v.submit_text === "string" && typeof v.initial.name === "string" && Array.isArray(v.initial.permissions) && v.initial.permissions.every(p => typeof p === "string") && v.fields.length === 2 && v.fields.every((f, i) => record(f) && f.name === ["name", "permissions"][i] && typeof f.label === "string" && typeof f.help_text === "string" && typeof f.required === "boolean" && (i === 0 ? typeof f.max_length === "number" : Array.isArray(f.choices) && f.choices.every(c => record(c) && integer(c.id) && typeof c.label === "string")));
}
function listValid(v: unknown): v is ListData {
  if (!record(v) || !frameValid(v.presentation) || !Array.isArray(v.items) || !record(v.columns) || !Array.isArray(v.messages)) return false;
  const c = v.columns;
  return typeof v.query === "string" && typeof v.can_export === "boolean" && v.items.every(i => record(i) && integer(i.id) && typeof i.name === "string" && typeof i.permissions_count === "number") && c.endpoint === "/ajax/columnas-preferencias/" && c.list_key === "grupos_list" && Array.isArray(c.active) && c.active.length > 0 && c.active.every(k => keys.includes(k as string)) && Array.isArray(c.defaults) && c.defaults.every(k => keys.includes(k as string)) && Array.isArray(c.available) && c.available.every(a => record(a) && keys.includes(a.key as string) && typeof a.title === "string" && typeof a.active === "boolean" && typeof a.required === "boolean") && v.messages.every(m => record(m) && typeof m.message === "string" && ["success", "error", "warning", "info"].includes(m.level as string));
}

export default function Groups(props: Props) {
  return <GroupPage key={`${props.mode}:${props.id ?? ""}`} {...props} />;
}
function GroupPage({ mode, id, renderFrame, navigate }: Props) {
  const [state, setState] = useState<State>({ status: "loading" });
  const endpoint = mode === "list" ? `web/groups/${window.location.search}` : mode === "create" ? "web/groups/create/" : `web/groups/${id}/edit/`;
  useEffect(() => {
    let active = true; const controller = new AbortController();
    client.get(endpoint, { signal: controller.signal, validateStatus: accepted }).then(({ data, status }: { data: unknown; status?: number }) => {
      if (!active) return;
      if (status === 403) setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) });
      else setState((mode === "list" ? listValid(data) : formValid(data)) ? { status: "ready", data: data as FormData | ListData } : { status: "error" });
    }).catch(() => { if (active) setState({ status: "error" }); });
    return () => { active = false; controller.abort(); };
  }, [endpoint, mode]);
  useEffect(() => { const before = document.title; document.title = mode === "list" ? "SISOC - Grupos de usuarios" : "SISOC - Grupos"; return () => { document.title = before; }; }, [mode]);
  if (state.status === "loading") return <main role="status">Cargando grupos…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar el grupo.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  if (state.status !== "ready") return null;
  const title = mode === "list" ? "Grupos de usuarios" : (state.data as FormData).title;
  const breadcrumb = <ol className="breadcrumb float-sm-right"><li className="breadcrumb-item">Administración</li><li className="breadcrumb-item"><a href="/grupos/">Grupos</a></li>{mode !== "list" && <li className="breadcrumb-item active">{title}</li>}</ol>;
  const content = mode === "list" ? <GroupList data={state.data as ListData} navigate={navigate} /> : <GroupForm data={state.data as FormData} endpoint={endpoint} navigate={navigate} forbidden={data => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) })} />;
  return renderFrame ? renderFrame(content, state.data.presentation, title, breadcrumb) : <main>{content}</main>;
}

function GroupForm({ data, endpoint, navigate, forbidden }: { data: FormData; endpoint: string; navigate?: (path: string) => void; forbidden: (data: unknown) => void }) {
  const [name, setName] = useState(data.initial.name); const [chosen, setChosen] = useState(() => catalogOrder(data.initial.permissions, data.fields[1]));
  const [errors, setErrors] = useState(data.errors); const [pending, setPending] = useState(false); const [uncertain, setUncertain] = useState(false);
  // An invalid response re-renders the native page, so the widget starts fresh.
  const [revision, setRevision] = useState(0);
  const active = useRef(false); const submitting = useRef(false);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (submitting.current || uncertain) return;
    submitting.current = true; setPending(true);
    const body = new URLSearchParams({ name }); chosen.forEach(id => body.append("permissions", id));
    try {
      const { data: result, status } = await client.post(endpoint, body, { validateStatus: accepted });
      if (!active.current) return;
      if (status === 403) forbidden(result);
      else if (record(result) && result.ok === true && result.redirect === "/grupos/") (navigate ?? window.location.assign.bind(window.location))("/grupos/");
      else setUncertain(true);
    } catch (error: unknown) {
      if (!active.current) return;
      const response = (error as { response?: { status?: number; data?: unknown } }).response;
      if (response?.status === 400 && formValid(response.data) && Object.keys(response.data.errors).length) {
        setErrors(response.data.errors); setName(response.data.initial.name); setChosen(catalogOrder(response.data.initial.permissions, data.fields[1])); setRevision(current => current + 1); submitting.current = false;
        window.scrollTo({ top: 0, left: 0, behavior: "instant" });
      } else setUncertain(true);
    } finally { if (active.current) setPending(false); }
  }
  const disabled = pending || uncertain;
  return <>
    <link rel="stylesheet" href="/static/admin/css/widgets.css" /><link rel="stylesheet" href="/static/custom/css/group_dual_listbox.css" />
    <div className="row justify-content-center"><div className="col-lg-10"><div className="card shadow-sm">
      <div className="card-header"><h5 className="mb-0">{data.title}</h5></div><div className="card-body">
        <form method="post" noValidate autoComplete="off" onSubmit={submit}>
          <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
          {uncertain && <p role="alert">No se pudo confirmar el resultado. <a href="/grupos/">Volver a grupos</a></p>}
          {errors.__all__?.map((e, i) => <p role="alert" key={i}>{e.message}</p>)}
          <div className="row"><div className="col-md-6"><div id="div_id_name" className="mb-3">
            <label htmlFor="id_name" className="form-label requiredField">{data.fields[0].label}<span className="asteriskField">*</span></label>
            <input name="name" id="id_name" type="text" className={`textinput form-control${errors.name?.length ? " is-invalid" : ""}`} maxLength={data.fields[0].max_length} required value={name} disabled={disabled} onChange={e => setName(e.target.value)} />
            {errors.name?.map((e, i) => <p id={`error_${i + 1}_id_name`} className="invalid-feedback" key={i}><strong>{e.message}</strong></p>)}
          </div></div></div>
          <div className="row"><PermissionSelector key={revision} field={data.fields[1]} chosen={chosen} onChange={setChosen} disabled={disabled} errors={errors.permissions ?? []} /></div>
          <div className="row"><div className="col-md-12"><div className="form-group mb-0 mt-3 d-flex justify-content-between">
            <a href="/grupos/" className="btn btn-secondary mb-3">Cancelar</a><div><button type="submit" className="btn btn-primary mb-3" disabled={disabled}><i className="fas fa-save me-1" /> {data.submit_text}</button></div>
          </div></div></div>
        </form>
      </div>
    </div></div></div>
  </>;
}

function PermissionSelector({ field, chosen, onChange, disabled, errors }: { field: Field; chosen: string[]; onChange: (ids: string[]) => void; disabled: boolean; errors: Errors[string] }) {
  const [filter, setFilter] = useState(""); const [fromSelection, setFromSelection] = useState<string[]>([]); const [toSelection, setToSelection] = useState<string[]>([]);
  const from = useRef<HTMLSelectElement>(null); const filterNode = useRef<HTMLParagraphElement>(null); const to = useRef<HTMLSelectElement>(null);
  const choices = field.choices ?? [];
  const [availableOrder, setAvailableOrder] = useState(() => choices.filter(c => !chosen.includes(String(c.id))).map(c => String(c.id)));
  const byId = new Map(choices.map(c => [String(c.id), c]));
  const available = availableOrder.map(id => byId.get(id)).filter((c): c is Choice => !!c && !chosen.includes(String(c.id)) && filter.toLowerCase().split(/\s+/).every(part => c.label.toLowerCase().includes(part)));
  const selected = chosen.map(id => byId.get(id)).filter((c): c is Choice => !!c);
  // Source refresh_icons runs on init, select change and link/double-click moves, never on filter keys.
  const [icons, setIcons] = useState(() => ({ add: false, remove: false, addAll: availableOrder.length > 0, removeAll: chosen.length > 0 }));
  useLayoutEffect(() => {
    const resize = () => {
      if (!to.current || !from.current || !filterNode.current) return;
      const style = window.getComputedStyle(to.current);
      const extra = style.boxSizing === "border-box" ? [style.paddingTop, style.paddingBottom, style.borderTopWidth, style.borderBottomWidth].reduce((sum, value) => sum + (parseInt(value, 10) || 0), 0) : 0;
      to.current.style.height = `${from.current.offsetHeight + filterNode.current.offsetHeight + extra}px`;
    };
    resize(); const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize); if (from.current) observer?.observe(from.current); if (filterNode.current) observer?.observe(filterNode.current);
    return () => observer?.disconnect();
  }, []);
  function move(ids: string[], add: boolean, refresh = true) {
    if (disabled) return;
    const nextChosen = add ? [...chosen, ...ids.filter(id => !chosen.includes(id))] : chosen.filter(id => !ids.includes(id));
    onChange(nextChosen);
    setAvailableOrder(current => add ? current.filter(id => !ids.includes(id)) : [...current, ...ids.filter(id => !current.includes(id))]);
    setFromSelection([]); setToSelection([]);
    if (refresh) {
      const nextAvailable = add ? available.filter(c => !ids.includes(String(c.id))) : [...available, ...ids.map(id => byId.get(id)).filter((c): c is Choice => !!c)];
      setIcons({ add: false, remove: false, addAll: nextAvailable.length > 0, removeAll: nextChosen.length > 0 });
    }
  }
  const link = (id: string, label: string, title: string, className: string, enabled: boolean, action: () => void) => <a href="#" id={id} title={title} className={`${className}${enabled && !disabled ? " active" : ""}`} aria-disabled={disabled || !enabled} onClick={e => { e.preventDefault(); if (enabled && !disabled) action(); }}>{label}</a>;
  return <div className="col-12 group-dual-listbox"><div id="div_id_permissions" className="mb-3">
    <label htmlFor="id_permissions_from" className="form-label">{field.label}</label>
    <div id="id_permissions_helptext" className="form-text">{field.help_text}</div>
    {errors.map((e, i) => <p className="invalid-feedback d-block" key={i}><strong>{e.message}</strong></p>)}
    <div className="selector"><div className="selector-available">
      <h2>Permisos disponibles <span className="help help-tooltip help-icon" title={'This is the list of available Permisos. You may choose some by selecting them in the box below and then clicking the "Choose" arrow between the two boxes.'} /></h2>
      <p id="id_permissions_filter" className="selector-filter" ref={filterNode}><label htmlFor="id_permissions_input"><span className="help-tooltip search-label-icon" title="Escriba en esta caja para filtrar la lista de Permisos disponibles." /></label>{" "}<input id="id_permissions_input" type="text" placeholder="Filtro" value={filter} disabled={disabled} onChange={e => { setFilter(e.target.value); setFromSelection([]); }} onKeyDown={e => {
        if (e.key === "Enter") { e.preventDefault(); if (available[0]) { move([String(available[0].id)], true, false); setFromSelection(available[1] ? [String(available[1].id)] : []); } }
        else if (e.key === "ArrowRight") { const oldIndex = available.findIndex(c => String(c.id) === fromSelection[0]); const remaining = available.filter(c => !fromSelection.includes(String(c.id))); move(fromSelection, true, false); const next = remaining[oldIndex === remaining.length ? remaining.length - 1 : oldIndex]; setFromSelection(next ? [String(next.id)] : []); }
        else if (e.key === "ArrowDown" || e.key === "ArrowUp") { const index = available.findIndex(c => String(c.id) === fromSelection[0]); const next = e.key === "ArrowDown" ? (index + 1) % available.length : index <= 0 ? available.length - 1 : index - 1; if (available[next]) setFromSelection([String(available[next].id)]); }
      }} /></p>
      <select ref={from} id="id_permissions_from" name="permissions_old" className="filtered" multiple aria-describedby="id_permissions_helptext" value={fromSelection} disabled={disabled} onChange={e => { const ids = Array.from(e.target.selectedOptions, o => o.value); setFromSelection(ids); setIcons({ add: ids.length > 0, remove: toSelection.length > 0, addAll: available.length > 0, removeAll: selected.length > 0 }); }} onDoubleClick={() => move(fromSelection, true)}>
        {available.map(c => <option key={c.id} value={String(c.id)} title={c.label}>{c.label}</option>)}
      </select>
      {link("id_permissions_add_all_link", "Choose all", "Click to choose all Permisos at once.", "selector-chooseall", icons.addAll, () => move(available.map(c => String(c.id)), true))}
    </div><ul className="selector-chooser"><li>{link("id_permissions_add_link", "Choose", "Choose", "selector-add", icons.add, () => move(fromSelection, true))}</li><li>{link("id_permissions_remove_link", "Remove", "Remove", "selector-remove", icons.remove, () => move(toSelection, false))}</li></ul>
      <div className="selector-chosen"><h2>Permisos seleccionados/as <span className="help help-tooltip help-icon" title={'This is the list of chosen Permisos. You may remove some by selecting them in the box below and then clicking the "Remove" arrow between the two boxes.'} /></h2>
        <select ref={to} id="id_permissions_to" multiple size={0} name="permissions" className="filtered" value={toSelection} disabled={disabled} onChange={e => { const ids = Array.from(e.target.selectedOptions, o => o.value); setToSelection(ids); setIcons({ add: fromSelection.length > 0, remove: ids.length > 0, addAll: available.length > 0, removeAll: selected.length > 0 }); }} onDoubleClick={() => move(toSelection, false)}>{selected.map(c => <option key={c.id} value={String(c.id)} title={c.label}>{c.label}</option>)}</select>
        {link("id_permissions_remove_all_link", "Remove all", "Click to remove all chosen Permisos at once.", "selector-clearall", icons.removeAll, () => move(chosen, false))}
      </div>
    </div>
  </div></div>;
}

function GroupList({ data, navigate }: { data: ListData; navigate?: (path: string) => void }) {
  const [items, setItems] = useState(data.items); const [sort, setSort] = useState<{ key: ColumnKey | null; direction: "asc" | "desc" | null }>({ key: null, direction: null });
  const [configOpen, setConfigOpen] = useState(false);
  const { cardRef, tableRef, classes: scrollClasses } = useLegacyScrollHints(JSON.stringify(data.columns.active));
  function sortBy(key: ColumnKey) {
    const direction = sort.key === key ? sort.direction === "asc" ? "desc" : sort.direction === "desc" ? null : "asc" : "asc";
    setSort({ key: direction ? key : null, direction });
    // The original third click removes the indicator but keeps the last row order.
    if (!direction) return;
    setItems(current => [...current].sort((a, b) => {
      const av = String(a[key]), bv = String(b[key]); const an = parseFloat(av), bn = parseFloat(bv);
      const value = !Number.isNaN(an) && !Number.isNaN(bn) ? an - bn : av.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").localeCompare(bv.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, ""), "es", { sensitivity: "base" });
      return direction === "asc" ? value : -value;
    }));
  }
  function exportCsv() {
    const query = new URLSearchParams(window.location.search); if (sort.key && sort.direction) { query.set("sort", sort.key); query.set("direction", sort.direction); }
    (navigate ?? window.location.assign.bind(window.location))(`/grupos/exportar/${query.size ? `?${query}` : ""}`);
  }
  return <>
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" /><link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" /><link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
    <InsumosToastList messages={data.messages} />
    <div className="poncho-topbar">{data.can_export && <button type="button" className="poncho-export btn-export-csv" data-url="/grupos/exportar/" title="Descargar listado actual en CSV" onClick={exportCsv}><i className="fas fa-file-excel" aria-hidden="true" />Exportar búsqueda</button>}</div>
    <h2 className="text-center mb-4 poncho-titulo">Grupos de usuarios</h2>
    <form method="get" action="/grupos/" id="simple-search-form"><div className="poncho-search poncho-search--solo"><div className="poncho-search__box"><input type="search" id="ajax-search-input" name="busqueda" className="poncho-search__input" placeholder="Buscar" title="Ingrese términos de búsqueda" aria-label="Ingrese términos de búsqueda" autoComplete="off" defaultValue={data.query} /><button type="submit" className="poncho-search__go" aria-label="Buscar"><i className="fas fa-search" aria-hidden="true" /></button></div></div><div className="poncho-search__meta"><span id="ajax-results-count" /></div></form>
    <div className="row mt-3"><div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions"><a href="/grupos/" className="poncho-btn poncho-btn--neutro">Resetear</a><a href="/grupos/crear/" className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar</a></div></div>
    <div className="row mt-5 max-width-100"><div className="col-12"><div className="card"><div ref={cardRef} className={`card-body ${scrollClasses.card}`}>
      <div className="d-flex justify-content-start mb-2"><button type="button" className="btn btn-outline-warning btn-sm" onClick={() => setConfigOpen(true)}>Configurar columnas</button></div>
      <div ref={tableRef} className={`table-responsive-lg ${scrollClasses.table}`}><table className="table table-bordered table-striped projects"><thead><tr>{data.columns.active.map(key => <th key={key} className={`sortable${sort.key === key ? ` sort-${sort.direction}` : ""}`} data-column={key} onClick={() => sortBy(key)}>{data.columns.available.find(c => c.key === key)?.title}<i className={`fas ${sort.key === key ? sort.direction === "asc" ? "fa-sort-up" : "fa-sort-down" : "fa-sort"} sort-icon`} /></th>)}<th className="notexport" style={{ width: "15%" }}>Acciones</th></tr></thead><tbody>{items.length ? items.map(item => <tr key={item.id}>{data.columns.active.map(key => <td key={key}>{item[key]}</td>)}<td className="project-actions text-right"><div className="action-buttons flex-wrap flex-lg-nowrap" role="group"><a href={`/grupos/editar/${item.id}/`} className="btn btn-editar" title="Editar"><i className="fas fa-edit" /> Editar</a></div></td></tr>) : <tr><td colSpan={data.columns.active.length + 1} className="text-center text-muted py-4">No hay grupos disponibles.</td></tr>}</tbody></table></div>
    </div></div></div></div>
    {configOpen && <ColumnModal columns={data.columns} close={() => setConfigOpen(false)} />}
  </>;
}

function ColumnModal({ columns, close }: { columns: Columns; close: () => void }) {
  const [order, setOrder] = useState(columns.available.map(c => c.key)); const [selected, setSelected] = useState(columns.active); const [error, setError] = useState(""); const [pending, setPending] = useState(false);
  const modal = useRef<HTMLDivElement>(null); const active = useRef(true); const busy = useRef(false);
  useEffect(() => {
    active.current = true;
    const previous = document.activeElement as HTMLElement | null; const before = document.body.style.overflow; document.body.classList.add("modal-open"); document.body.style.overflow = "hidden"; modal.current?.focus();
    const key = (e: KeyboardEvent) => { if (e.key === "Escape" && !busy.current) close(); if (e.key === "Tab") { const controls = Array.from(modal.current?.querySelectorAll<HTMLElement>('button:not([disabled]),input:not([disabled]),[tabindex="0"]') ?? []); const first = controls[0], last = controls.at(-1); if (e.shiftKey && (document.activeElement === first || document.activeElement === modal.current)) { e.preventDefault(); last?.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); } } };
    document.addEventListener("keydown", key); return () => { active.current = false; document.removeEventListener("keydown", key); document.body.classList.remove("modal-open"); document.body.style.overflow = before; previous?.focus(); };
  }, [close]);
  async function save(reset: boolean) {
    if (busy.current) return; const values = order.filter(k => selected.includes(k)); if (!reset && !values.length) { setError("Debe haber al menos una columna visible."); return; }
    busy.current = true; setPending(true); setError("");
    try {
      const response = await fetch(columns.endpoint, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": leerCookie("csrftoken") ?? "", "X-Requested-With": "XMLHttpRequest" }, body: JSON.stringify(reset ? { list_key: columns.list_key, reset: true } : { list_key: columns.list_key, columns: values }) });
      const result: unknown = await response.json(); if (!response.ok) throw new Error(record(result) && typeof result.error === "string" ? result.error : "No se pudo guardar la configuracion.");
      if (active.current) window.location.reload();
    } catch (e: unknown) { if (active.current) { setError(e instanceof Error ? e.message : "No se pudo guardar la configuracion."); setPending(false); busy.current = false; } }
  }
  function move(key: ColumnKey, offset: number) { setOrder(current => { const i = current.indexOf(key), j = i + offset; if (j < 0 || j >= current.length) return current; const next = [...current]; [next[i], next[j]] = [next[j], next[i]]; return next; }); }
  return <><div className="modal-backdrop fade show" /><div ref={modal} className="modal fade show d-block" id="column-config-modal-grupos_list" tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="groups-columns-title" onClick={e => { if (e.target === e.currentTarget && !pending) close(); }}><div className="modal-dialog modal-dialog-centered modal-lg"><div className="modal-content"><div className="modal-header"><h5 className="modal-title" id="groups-columns-title">Columnas visibles</h5><button type="button" className="btn-close" aria-label="Cerrar" disabled={pending} onClick={close} /></div><div className="modal-body"><p className="text-muted mb-3">Seleccioná qué columnas mostrar y ordenalas con las flechas.</p><div className="list-group column-config-list">{order.map(key => { const column = columns.available.find(c => c.key === key)!; return <div key={key} className="list-group-item d-flex flex-wrap align-items-center justify-content-between gap-2" data-column-key={key}><div className="form-check"><input type="checkbox" className="form-check-input column-config-checkbox" id={`groups-column-${key}`} checked={selected.includes(key)} disabled={pending || column.required} onChange={e => setSelected(current => e.target.checked ? [...current, key] : current.filter(k => k !== key))} /><label className="form-check-label" htmlFor={`groups-column-${key}`}>{column.title}</label></div><div className="btn-group btn-group-sm" role="group"><button type="button" className="btn btn-light column-move-up" title="Mover arriba" disabled={pending} onClick={() => move(key, -1)}><i className="fas fa-arrow-up" /></button><button type="button" className="btn btn-light column-move-down" title="Mover abajo" disabled={pending} onClick={() => move(key, 1)}><i className="fas fa-arrow-down" /></button></div></div>; })}</div>{error && <div className="alert alert-danger mt-3" role="alert">{error}</div>}</div><div className="modal-footer"><button type="button" className="btn btn-outline-secondary column-config-reset" disabled={pending} onClick={() => void save(true)}>Restablecer</button><button type="button" className="btn btn-primary column-config-save" disabled={pending} onClick={() => void save(false)}>Guardar</button></div></div></div></div></>;
}
