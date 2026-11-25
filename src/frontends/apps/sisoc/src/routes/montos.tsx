/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { Fragment, useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { prerequisiteFromForbidden } from "../webAccess";
import {
  Breadcrumb, breadcrumbValid, internal, postForm, record, renderMain, text, useMainResource,
  type Breadcrumbs, type MainState,
} from "./MainFrame";
import type { RouteDefinition } from "./types";
import { navigation } from "./userImport";

/**
 * CO05 amounts per program (`montoprestacion/`): list, create, edit, detail and
 * delete confirmation with the native templates' markup. Data and every write
 * go through `/api/web/comedores/montos/`, which runs the native views.
 */
type Mode = "listar" | "crear" | "editar" | "eliminar" | "detalle";
type Params = { mode: Mode; id?: string };
type Monto = {
  id: number; programa: string; desayuno_valor: string; almuerzo_valor: string; merienda_valor: string; cena_valor: string;
  usuario_creador: string; fecha_creacion: string; fecha_modificacion: string;
};
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Page = { number: number; count: number; is_paginated: boolean; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
type ListData = { results: Monto[]; page: Page; urls: { listar: string; crear: string }; messages: Message[] };
type BackButton = { url: string; text: string; type: string };
type DetailData = { breadcrumb: Breadcrumbs; back_button: BackButton; monto: Monto };
type Field = { name: string; label: string; required: boolean; value: string; choices?: { value: string; label: string }[] };
type Errors = Record<string, { message: string; code: string }[]>;
type FormPayload = { breadcrumb: Breadcrumbs; back_button: BackButton; fields: Field[]; errors: Errors };
type DeleteData = { breadcrumb: Breadcrumbs; object_name: string; delete_message: string; cancel_url: string };

const BASE = "/montoprestacion/";
const API = "web/comedores/montos/";
const VALUES = ["desayuno_valor", "almuerzo_valor", "merienda_valor", "cena_valor"] as const;
const MONTO_TEXT = ["programa", ...VALUES, "usuario_creador", "fecha_creacion", "fecha_modificacion"] as const;
const LEVELS = ["success", "error", "warning", "info"];

const montoValid = (m: unknown): m is Monto => record(m) && Number.isSafeInteger(m.id) && MONTO_TEXT.every((k) => text(m[k]));
const backValid = (b: unknown): b is BackButton => record(b) && internal(b.url) && text(b.text) && text(b.type);
function listValid(v: unknown): v is ListData {
  if (!record(v) || !record(v.page) || !record(v.urls) || !Array.isArray(v.results) || !Array.isArray(v.messages)) return false;
  const p = v.page;
  return v.results.every(montoValid) && internal(v.urls.listar) && internal(v.urls.crear) &&
    v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string)) &&
    Number.isSafeInteger(p.number) && Number.isSafeInteger(p.count) && typeof p.is_paginated === "boolean" &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || Number.isSafeInteger(n)) && text(p.query_without_page);
}
const detailValid = (v: unknown): v is DetailData => record(v) && breadcrumbValid(v.breadcrumb) && backValid(v.back_button) && montoValid(v.monto);
function formValid(v: unknown): v is FormPayload {
  return record(v) && breadcrumbValid(v.breadcrumb) && backValid(v.back_button) && record(v.errors) &&
    Object.values(v.errors).every((e) => Array.isArray(e) && e.every((x) => record(x) && text(x.message))) &&
    Array.isArray(v.fields) && v.fields.length === 5 && v.fields.every((f, i) => record(f) && f.name === ["programa", ...VALUES][i] &&
      text(f.label) && typeof f.required === "boolean" && text(f.value) &&
      (i > 0 || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label)))));
}
const deleteValid = (v: unknown): v is DeleteData => record(v) && breadcrumbValid(v.breadcrumb) &&
  text(v.object_name) && text(v.delete_message) && internal(v.cancel_url);

function ListBreadcrumb({ list }: { list: string }) {
  return <ol className="breadcrumb float-sm-right">
    <li className="breadcrumb-item"><a href={list}>Monto de Prestaciones</a></li>
    <li className="breadcrumb-item active">Listar</li>
  </ol>;
}

function BackLink({ button }: { button: BackButton }) {
  // components/action_buttons.html with an empty button list.
  return <div className="d-flex justify-content-between mb-4"><a href={button.url} className={`btn btn-${button.type}`}>{button.text}</a></div>;
}

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

function MontosList({ data }: { data: ListData }) {
  return <>
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <InsumosToastList messages={data.messages} />
    <div className="action-bar mb-3"><a href={data.urls.crear} className="btn btn-primary"><i className="fas fa-plus" /> Agregar</a></div>
    <div className="row mt-3 max-width-100"><div className="col-12"><div className="card"><div className="card-body">
      <table className="table table-bordered table-striped projects">
        <thead><tr>
          <th>Programa</th><th>Valor desayuno</th><th>Valor almuerzo</th><th>Valor merienda</th><th>Valor cena</th>
          <th>Usuario creador</th><th>Fecha creación</th><th>Fecha modificación</th><th style={{ width: "18%" }} className="notexport">Acciones</th>
        </tr></thead>
        <tbody id="prestaciones-tbody">
          {data.results.length ? data.results.map((m) => <tr key={m.id}>
            {MONTO_TEXT.map((k) => <td key={k}>{m[k]}</td>)}
            <td>
              <a href={`${BASE}${m.id}/detalle`} className="btn btn-sm btn-info">Ver</a>{" "}
              <a href={`${BASE}${m.id}/editar`} className="btn btn-sm btn-warning">Editar</a>{" "}
              <a href={`${BASE}${m.id}/eliminar`} className="btn btn-sm btn-danger">Eliminar</a>
            </td>
          </tr>) : <tr><td colSpan={9} className="text-center">No hay montos de prestaciones cargados.</td></tr>}
        </tbody>
      </table>
    </div></div></div></div>
    <div id="pagination-container"><Pagination page={data.page} /></div>
  </>;
}

const DETAIL_ROWS: [keyof Monto, string][] = [
  ["programa", "Programa"], ["desayuno_valor", "Valor desayuno"], ["almuerzo_valor", "Valor almuerzo"], ["merienda_valor", "Valor merienda"],
  ["cena_valor", "Valor cena"], ["usuario_creador", "Usuario creador"], ["fecha_creacion", "Fecha creación"], ["fecha_modificacion", "Fecha modificación"],
];

function MontoDetail({ data }: { data: DetailData }) {
  return <>
    <link rel="stylesheet" href="/static/custom/css/detailModerno.css" />
    <div className="card">
      <div className="card-header"><h3 className="card-title">Detalle de Monto de Prestación</h3></div>
      <div className="card-body">
        <BackLink button={data.back_button} />
        <table className="table table-bordered table-striped"><tbody>
          {DETAIL_ROWS.map(([k, label]) => <tr key={k}><th>{label}</th><td>{data.monto[k]}</td></tr>)}
        </tbody></table>
      </div>
    </div>
  </>;
}

function CsrfInput() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

function Uncertain({ list }: { list: string }) {
  return <p role="alert">No se pudo confirmar el resultado. <a href={list}>Volver al listado</a></p>;
}

/** One crispy-forms (Bootstrap 5) field: label, control and its error block. */
function FormField({ field, errors }: { field: Field; errors: Errors[string] }) {
  const id = `id_${field.name}`;
  const invalid = errors.length > 0;
  const aria = invalid ? { "aria-invalid": true, "aria-describedby": `${id}_error` } : {};
  return <div id={`div_${id}`} className="mb-3">
    <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>{field.label}{field.required && <span className="asteriskField">*</span>}</label>{" "}
    {field.choices
      ? <select name={field.name} className={`form-control select form-select${invalid ? " is-invalid" : ""}`} required {...aria} id={id} defaultValue={field.value}>
        {field.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      : <input type="number" name={field.name} defaultValue={field.value} className={`form-control numberinput${invalid ? " is-invalid" : ""}`} step="0.01" {...aria} id={id} />}
    {invalid && <>{" "}<div id={`${id}_error`} className="invalid-feedback">{errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e.message}</strong></p>)}</div></>}
  </div>;
}

function MontoForm({ data: initial, endpoint, list, forbidden }: { data: FormPayload; endpoint: string; list: string; forbidden: (d: unknown) => void }) {
  const [data, setData] = useState(initial);
  const [revision, setRevision] = useState(0);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const values = new FormData(event.currentTarget);
    const body = new URLSearchParams();
    for (const name of ["programa", ...VALUES]) body.append(name, String(values.get(name) ?? ""));
    const result = await postForm(endpoint, body);
    busy.current = false;
    if (result.kind === "redirect") navigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else if (result.kind === "invalid" && formValid(result.data)) {
      // The native view re-renders the page with the bound form.
      setData(result.data); setRevision((n) => n + 1); window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    } else setUncertain(true);
  }
  const general = data.errors.__all__ ?? [];
  return <>
    <BackLink button={data.back_button} />
    <div className="card card-body shadow">
      <h2 className="text-center display-4 mb-4">Datos de Monto de Prestación</h2>
      <form key={revision} method="post" action="" encType="multipart/form-data" onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        {uncertain && <Uncertain list={list} />}
        {general.length > 0 && <div className="alert alert-block alert-danger"><ul className="m-0">{general.map((e, i) => <li key={i}>{e.message}</li>)}</ul></div>}
        {data.fields.map((f) => <FormField key={f.name} field={f} errors={data.errors[f.name] ?? []} />)}
        <div className="text-center mt-4"><button type="submit" className="btn btn-primary">Guardar</button></div>
      </form>
    </div>
  </>;
}

function MontoDelete({ data, endpoint, forbidden }: { data: DeleteData; endpoint: string; forbidden: (d: unknown) => void }) {
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
  // components/delete_confirm.html with the view's message and the default texts.
  return <div className="error-page mt-5 px-3"><div className="error-content">
    <h3><i className="fas fa-exclamation-triangle text-danger px-2" /> Atención!</h3>
    <p>{data.delete_message} <span className="font-weight-bold">{data.object_name}</span>?</p>
    <div className="text-left">
      <form method="post" action="" onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        {uncertain && <Uncertain list={data.cancel_url} />}
        <button type="submit" className="btn btn-danger btn-sm">Dar de baja</button>{" "}
        <a href={data.cancel_url} className="btn btn-secondary btn-sm">Cancelar</a>
      </form>
    </div>
  </div></div>;
}

const LIST = `${BASE}listar`;
// The native sidebar marks «Monto de Prestaciones» on every page whose path contains `montoprestacion`.
const ACTIVE = LIST;
const TITLES: Record<Mode, string> = { listar: "Prestaciones", crear: "Monto Prestación", editar: "Monto Prestación", detalle: "Monto de Prestación", eliminar: "Confirmar Eliminación" };

function useForbidden<T>(setState: (s: MainState<T>) => void) {
  return (d: unknown) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) });
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando montos…", (data) => ({ title: TITLES.listar, activePath: ACTIVE, breadcrumb: <ListBreadcrumb list={data.urls.listar} />, content: <MontosList data={data} /> }));
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, detailValid);
  return renderMain(state, "Cargando monto…", (data) => ({ title: TITLES.detalle, activePath: ACTIVE, breadcrumb: <Breadcrumb items={data.breadcrumb} />, content: <MontoDetail data={data} /> }));
}

function FormPage({ mode, id }: { mode: "crear" | "editar"; id?: string }) {
  const endpoint = mode === "crear" ? `${API}crear/` : `${API}${id}/editar/`;
  const [state, setState] = useMainResource(endpoint, formValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: TITLES[mode], activePath: ACTIVE, heading: "Monto de Prestación", breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <MontoForm data={data} endpoint={endpoint} list={LIST} forbidden={forbidden} />,
  }));
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, deleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: TITLES.eliminar, activePath: ACTIVE, breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <MontoDelete data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

// Native URLs of `comedores/montos_urls.py`, same (absent) trailing slashes.
const PATH = /^\/montoprestacion\/(?:(listar|crear)|([0-9]+)\/(editar|eliminar|detalle))$/;

export const montosRoute: RouteDefinition<Params> = {
  name: "comedores-montos",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[1] ? { mode: m[1] as Mode } : { mode: m[3] as Mode, id: m[2] };
  },
  render({ mode, id }) {
    if (mode === "listar") return <ListPage />;
    if (mode === "crear" || mode === "editar") return <FormPage key={`${mode}:${id ?? ""}`} mode={mode} id={id} />;
    if (mode === "detalle") return <DetailPage id={id!} />;
    return <DeletePage id={id!} />;
  },
};
