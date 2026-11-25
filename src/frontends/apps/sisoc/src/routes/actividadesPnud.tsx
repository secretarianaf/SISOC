/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { Fragment, useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { prerequisiteFromForbidden } from "../webAccess";
import { internal, postForm, record, renderMain, text, useMainResource, type MainState } from "./MainFrame";
import type { RouteDefinition } from "./types";
import { navigation } from "./userImport";

/**
 * CO04.02 global PNUD activity catalog (`comedores/configuracion/actividades-pnud/`):
 * list with search and estado filter, create/edit with the existing/new category
 * mode and the deactivation confirmation (`activo=False`, never a delete), with
 * the native templates' markup. Data and writes go through
 * `/api/web/comedores/actividades-pnud/`, which runs the native views.
 */
type Mode = "list" | "crear" | "editar" | "baja";
type Params = { mode: Mode; id?: string };
type Actividad = { id: number; categoria: string; actividad: string; activo: boolean };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Page = { number: number; count: number; is_paginated: boolean; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
type ListData = { results: Actividad[]; estado: string; q: string; can_manage: boolean; page: Page; messages: Message[] };
type Values = { categoria: string; categoria_modo: string; categoria_existente: string; categoria_nueva: string; actividad: string; activo: boolean };
type Errors = Record<string, { message: string; code: string }[]>;
type FormPayload = { editar: boolean; values: Values; categorias: { value: string; label: string }[]; actividad_max_length: number; errors: Errors; list_url: string };
type BajaData = { categoria: string; actividad: string; cancel_url: string };

const BASE = "/comedores/configuracion/actividades-pnud/";
const API = "web/comedores/actividades-pnud/";
const LEVELS = ["success", "error", "warning", "info"];

function listValid(v: unknown): v is ListData {
  if (!record(v) || !record(v.page) || !Array.isArray(v.results) || !Array.isArray(v.messages)) return false;
  const p = v.page;
  return v.results.every((a) => record(a) && Number.isSafeInteger(a.id) && text(a.categoria) && text(a.actividad) && typeof a.activo === "boolean") &&
    text(v.estado) && text(v.q) && typeof v.can_manage === "boolean" &&
    v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string)) &&
    Number.isSafeInteger(p.number) && Number.isSafeInteger(p.count) && typeof p.is_paginated === "boolean" &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || Number.isSafeInteger(n)) && text(p.query_without_page);
}
function formValid(v: unknown): v is FormPayload {
  if (!record(v) || !record(v.values) || !record(v.errors) || !Array.isArray(v.categorias)) return false;
  const x = v.values;
  return typeof v.editar === "boolean" && ["categoria", "categoria_modo", "categoria_existente", "categoria_nueva", "actividad"].every((k) => text(x[k])) &&
    typeof x.activo === "boolean" && v.categorias.every((c) => record(c) && text(c.value) && text(c.label)) &&
    Number.isSafeInteger(v.actividad_max_length) && internal(v.list_url) &&
    Object.values(v.errors).every((e) => Array.isArray(e) && e.every((m) => record(m) && text(m.message)));
}
const bajaValid = (v: unknown): v is BajaData => record(v) && text(v.categoria) && text(v.actividad) && internal(v.cancel_url);

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
    {/* `{% if page_obj %}`: an empty page is falsy, so no count line without rows. */}
    {page.count > 0 && <p className="text-center text-muted mb-0 mt-1">Se encontraron {page.count} resultados</p>}
  </div>;
}

/** `components/search_bar.html`, simple mode with `search_name='q'`. */
function SearchBar({ data }: { data: ListData }) {
  return <>
    <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
    <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
    <h2 className="text-center mb-4 poncho-titulo">Buscar Actividades PNUD</h2>
    <form method="GET" action="" id="simple-search-form">
      <div className="poncho-search poncho-search--solo"><div className="poncho-search__box">
        <input type="search" id="ajax-search-input" name="q" className="poncho-search__input" placeholder="Buscar por categoria o actividad"
          title="Buscar por categoria o actividad." autoComplete="off" aria-label="Buscar por categoria o actividad." defaultValue={data.q} />
        <button type="submit" className="poncho-search__go" aria-label="Buscar"><i className="fas fa-search" aria-hidden="true" /></button>
      </div></div>
      <div className="poncho-search__meta"><span id="ajax-results-count" /></div>
      <div id="ajax-loading-indicator" className="text-center py-3" style={{ display: "none" }}>
        <div className="spinner-border" role="status"><span className="sr-only">Cargando...</span></div>
      </div>
    </form>
    <div className="row mt-3"><div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
      <a href={BASE} className="poncho-btn poncho-btn--neutro">Resetear</a>
      {data.can_manage && <>{" "}<a href={`${BASE}crear/`} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar</a></>}
    </div></div>
  </>;
}

function ActividadesList({ data }: { data: ListData }) {
  const { cardRef, tableRef, classes } = useLegacyScrollHints(String(data.results.length));
  const query = data.q ? `&q=${encodeURIComponent(data.q)}` : "";
  const filter = (estado: string, label: string) =>
    <a href={`${BASE}?estado=${estado}${query}`} className={`btn ${data.estado === estado ? "btn-primary" : "btn-outline-primary"}`}>{label}</a>;
  return <>
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <link rel="stylesheet" href="/static/custom/css/actividadesPnud.css" />
    <InsumosToastList messages={data.messages} />
    <SearchBar data={data} />
    <input type="hidden" name="estado" form="simple-search-form" value={data.estado} />
    <div className="actividades-pnud-filter poncho-filtros-modulo" aria-label="Filtro por estado">
      {filter("todas", "Todas")}{" "}{filter("activa", "Activas")}{" "}{filter("inactiva", "Inactivas")}
    </div>
    <div className="row mt-3 max-width-100"><div className="col-12"><div className="card"><div ref={cardRef} className={`card-body ${classes.card}`}>
      <div ref={tableRef} className={`table-responsive ${classes.table}`}>
        <table className="table table-bordered table-striped projects mb-0">
          <thead><tr><th>Categoría</th><th>Actividad</th><th>Estado</th><th style={{ width: "220px" }}>Acciones</th></tr></thead>
          <tbody>
            {data.results.length ? data.results.map((a) => <tr key={a.id}>
              <td>{a.categoria}</td><td>{a.actividad}</td>
              <td>{a.activo
                ? <span className="actividades-pnud-status actividades-pnud-status--active">Activo</span>
                : <span className="actividades-pnud-status actividades-pnud-status--inactive">Inactivo</span>}</td>
              <td>{data.can_manage
                ? <div className="actividades-pnud-actions">
                  <a href={`${BASE}${a.id}/editar/`} className="btn btn-sm btn-warning">Editar</a>
                  {a.activo && <>{" "}<a href={`${BASE}${a.id}/baja/`} className="btn btn-sm btn-danger">Dar de baja</a></>}
                </div>
                : "-"}</td>
            </tr>) : <tr><td colSpan={4} className="text-center">No hay actividades cargadas.</td></tr>}
          </tbody>
        </table>
      </div>
    </div></div></div></div>
    <div id="pagination-container"><Pagination page={data.page} /></div>
  </>;
}

function CsrfInput() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

function Uncertain({ list }: { list: string }) {
  return <p role="alert">No se pudo confirmar el resultado. <a href={list}>Volver al listado</a></p>;
}

/** Django's `aria-invalid`/`aria-describedby` on a widget that has errors. */
const ariaFor = (errors: Errors, name: string) => errors[name]?.length ? { "aria-invalid": true, "aria-describedby": `id_${name}_error` } : {};

function FieldErrors({ errors, name }: { errors: Errors; name: string }) {
  if (!errors[name]?.length) return null;
  return <div className="field-errors"><ul className="errorlist" id={`id_${name}_error`}>{errors[name].map((e, i) => <li key={i}>{e.message}</li>)}</ul></div>;
}

/** The inline script's `setMode` runs on load: the hidden mode's field starts empty. */
function initialValues(values: Values): Values {
  const nueva = values.categoria_modo === "nueva";
  return { ...values, categoria_modo: nueva ? "nueva" : "existente", categoria_nueva: nueva ? values.categoria_nueva : "", categoria_existente: nueva ? "" : values.categoria_existente };
}

function ActividadForm({ data: initial, endpoint, forbidden }: { data: FormPayload; endpoint: string; forbidden: (d: unknown) => void }) {
  const [data, setData] = useState(initial);
  const [values, setValues] = useState(() => initialValues(initial.values));
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const set = (patch: Partial<Values>) => setValues((v) => ({ ...v, ...patch }));
  const setMode = (mode: "existente" | "nueva") => set(mode === "existente" ? { categoria_modo: mode, categoria_nueva: "" } : { categoria_modo: mode, categoria_existente: "" });
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const body = new URLSearchParams({
      categoria: values.categoria, categoria_modo: values.categoria_modo, categoria_existente: values.categoria_existente,
      categoria_nueva: values.categoria_nueva, actividad: values.actividad,
    });
    if (values.activo) body.append("activo", "on");
    const result = await postForm(endpoint, body);
    busy.current = false;
    if (result.kind === "redirect") navigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else if (result.kind === "invalid" && formValid(result.data)) {
      setData(result.data); setValues(initialValues(result.data.values)); window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    } else setUncertain(true);
  }
  const { errors } = data;
  const nueva = values.categoria_modo === "nueva";
  const general = errors.__all__ ?? [];
  return <>
    <link rel="stylesheet" href="/static/custom/css/actividadesPnud.css" />
    <div className="row"><div className="col-md-8"><div className="card card-primary">
      <div className="card-header"><h3 className="card-title">{data.editar ? "Editar actividad" : "Crear actividad"}</h3></div>
      <form method="post" className="actividades-pnud-form" onSubmit={(e) => void submit(e)}>
        <div className="card-body">
          <CsrfInput />
          {uncertain && <Uncertain list={data.list_url} />}
          {general.length > 0 && <div className="alert alert-danger"><ul className="errorlist nonfield">{general.map((e, i) => <li key={i}>{e.message}</li>)}</ul></div>}
          <input type="hidden" name="categoria" value={values.categoria} id="id_categoria" {...ariaFor(errors, "categoria")} />
          <input type="hidden" name="categoria_modo" value={values.categoria_modo} id="id_categoria_modo" {...ariaFor(errors, "categoria_modo")} />
          <div className="categoria-mode-buttons" role="group" aria-label="Modo de categoria">
            <button type="button" className={`btn btn-sm ${nueva ? "btn-outline-primary" : "btn-primary"}`} data-categoria-mode-button="existente" onClick={() => setMode("existente")}>Usar existente</button>{" "}
            <button type="button" className={`btn btn-sm ${nueva ? "btn-primary" : "btn-outline-primary"}`} data-categoria-mode-button="nueva" onClick={() => setMode("nueva")}>Crear nueva</button>
          </div>
          <div className="form-group categoria-field" data-categoria-mode-field="existente" hidden={nueva}>
            <label htmlFor="id_categoria_existente">Categoria existente</label>{" "}
            <select name="categoria_existente" className="form-control" id="id_categoria_existente" value={values.categoria_existente} onChange={(e) => set({ categoria_existente: e.target.value })} {...ariaFor(errors, "categoria_existente")}>
              {data.categorias.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>{" "}
            <small className="form-text">Selecciona una categoria ya cargada.</small>
          </div>
          <div className="form-group categoria-field" data-categoria-mode-field="nueva" hidden={!nueva}>
            <label htmlFor="id_categoria_nueva">Nueva categoria</label>{" "}
            <input type="text" name="categoria_nueva" className="form-control" placeholder="Escribi una categoria nueva" id="id_categoria_nueva" value={values.categoria_nueva} onChange={(e) => set({ categoria_nueva: e.target.value })} {...ariaFor(errors, "categoria_nueva")} />{" "}
            <small className="form-text">Completa este campo solo si queres crear una categoria nueva.</small>
            {/* The template shows `form.categoria.errors`; the form adds its category error to the mode field. */}
            <FieldErrors errors={errors} name="categoria" />
          </div>
          <div className="form-group">
            <label htmlFor="id_actividad">Actividad</label>{" "}
            <input type="text" name="actividad" className="form-control" maxLength={data.actividad_max_length} required id="id_actividad" value={values.actividad} onChange={(e) => set({ actividad: e.target.value })} {...ariaFor(errors, "actividad")} />
            <FieldErrors errors={errors} name="actividad" />
          </div>
          <div className="form-group form-check">
            <input type="checkbox" name="activo" className="form-check-input" id="id_activo" checked={values.activo} onChange={(e) => set({ activo: e.target.checked })} {...ariaFor(errors, "activo")} />{" "}
            <label className="form-check-label" htmlFor="id_activo">Activo</label>
            <FieldErrors errors={errors} name="activo" />
          </div>
        </div>
        <div className="card-footer d-flex justify-content-between">
          <a href={data.list_url} className="btn btn-outline-secondary">Volver</a>{" "}
          <button type="submit" className="btn btn-primary">Guardar</button>
        </div>
      </form>
    </div></div></div>
  </>;
}

function BajaConfirm({ data, endpoint, forbidden }: { data: BajaData; endpoint: string; forbidden: (d: unknown) => void }) {
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const result = await postForm(endpoint, new URLSearchParams());
    busy.current = false;
    if (result.kind === "redirect") navigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else setUncertain(true);
  }
  return <div className="row"><div className="col-md-6"><div className="card card-danger">
    <div className="card-header"><h3 className="card-title">Dar de baja actividad PNUD</h3></div>
    <form method="post" onSubmit={(e) => void submit(e)}>
      <CsrfInput />
      <div className="card-body">
        {uncertain && <Uncertain list={data.cancel_url} />}
        <p>Se marcará como inactiva la actividad <strong>{data.categoria} - {data.actividad}</strong>.</p>
      </div>
      <div className="card-footer d-flex justify-content-between">
        <a href={data.cancel_url} className="btn btn-outline-secondary">Cancelar</a>{" "}
        <button type="submit" className="btn btn-danger">Dar de baja</button>
      </div>
    </form>
  </div></div></div>;
}

const TITLE = "Actividades PNUD";
// The native sidebar marks «Actividades PNUD» on every page whose path contains `actividades-pnud`.
const ACTIVE = BASE;

function useForbidden<T>(setState: (s: MainState<T>) => void) {
  return (d: unknown) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) });
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando actividades…", (data) => ({
    title: TITLE, activePath: ACTIVE,
    breadcrumb: <ol className="breadcrumb float-sm-right"><li className="breadcrumb-item active">Actividades PNUD</li></ol>,
    content: <ActividadesList data={data} />,
  }));
}

function FormPage({ mode, id }: { mode: "crear" | "editar"; id?: string }) {
  const endpoint = mode === "crear" ? `${API}crear/` : `${API}${id}/editar/`;
  const [state, setState] = useMainResource(endpoint, formValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: TITLE, activePath: ACTIVE,
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={data.list_url}>Actividades PNUD</a></li>
      <li className="breadcrumb-item active">{data.editar ? "Editar" : "Crear"}</li>
    </ol>,
    content: <ActividadForm data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function BajaPage({ id }: { id: string }) {
  const endpoint = `${API}${id}/baja/`;
  const [state, setState] = useMainResource(endpoint, bajaValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Dar de baja actividad PNUD", activePath: ACTIVE, breadcrumb: null,
    content: <BajaConfirm data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

// Native URLs of `comedores/urls.py`, with their trailing slashes.
const PATH = /^\/comedores\/configuracion\/actividades-pnud\/(?:(crear)\/|([0-9]+)\/(editar|baja)\/)?$/;

export const actividadesPnudRoute: RouteDefinition<Params> = {
  name: "comedores-actividades-pnud",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    if (m[1]) return { mode: "crear" };
    if (m[2]) return { mode: m[3] as Mode, id: m[2] };
    return { mode: "list" };
  },
  render({ mode, id }) {
    if (mode === "list") return <ListPage />;
    if (mode === "crear" || mode === "editar") return <FormPage key={`${mode}:${id ?? ""}`} mode={mode} id={id} />;
    return <BajaPage id={id!} />;
  },
};
