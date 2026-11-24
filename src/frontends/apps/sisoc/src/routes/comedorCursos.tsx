/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent, type RefObject } from "react";
import { sameOriginTarget } from "./cdiObservaciones";
import { UNCERTAIN, toasts, type Message } from "./comedorColaboradores";
import { Pagination } from "./listControls";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CO04.01 global app-mobile course catalog (`comedores/configuracion/cursos-app-mobile/`): list (20 per page),
 * create and edit with the image upload (`form.as_p` markup) and the soft-delete confirmation, with the native
 * templates' markup. Data and writes go through `/api/web/comedores/cursos-app-mobile/`, which runs the native
 * views (actor stamps, soft delete and its two messages). A confirmed redirect is a full-page navigation.
 */
type Page = { number: number; count: number; is_paginated: boolean; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
type Curso = {
  id: number; nombre: string; programa: string; link: string; orden: number; es_recomendado: boolean; activo: boolean; tiene_imagen: boolean;
  urls: { editar: string; eliminar: string };
};
export type ListData = { results: Curso[]; page: Page; messages: Message[]; urls: { crear: string } };
type Field = {
  name: string; label: string; type: "text" | "url" | "file" | "select" | "checkbox" | "number"; html_required: boolean; errors: string[];
  max_length: number | null; min: string | null; accept: string | null; value: string | boolean; choices?: { value: string; label: string }[];
};
export type CursoFormData = { edit_mode: boolean; fields: Field[]; non_field_errors: string[]; messages: Message[]; urls: { list: string } };
export type BajaData = { nombre: string; cancel_url: string; messages: Message[] };

const BASE = "/comedores/configuracion/cursos-app-mobile/";
const API = "web/comedores/cursos-app-mobile/";
const TYPES = ["text", "url", "file", "select", "checkbox", "number"];
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && text(m.tags));

export function listValid(v: unknown): v is ListData {
  if (!record(v) || !record(v.page) || !Array.isArray(v.results) || !record(v.urls)) return false;
  const p = v.page;
  return v.results.every((c) => record(c) && Number.isSafeInteger(c.id) && text(c.nombre) && text(c.programa) && text(c.link) && Number.isSafeInteger(c.orden) &&
    typeof c.es_recomendado === "boolean" && typeof c.activo === "boolean" && typeof c.tiene_imagen === "boolean" && record(c.urls) && internal(c.urls.editar) && internal(c.urls.eliminar)) &&
    Number.isSafeInteger(p.number) && Number.isSafeInteger(p.count) && typeof p.is_paginated === "boolean" && Array.isArray(p.range) &&
    p.range.every((n) => n === "…" || Number.isSafeInteger(n)) && text(p.query_without_page) && messagesValid(v.messages) && internal(v.urls.crear);
}

export function formValid(v: unknown): v is CursoFormData {
  if (!record(v) || !Array.isArray(v.fields) || !record(v.urls)) return false;
  return typeof v.edit_mode === "boolean" && Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && messagesValid(v.messages) && internal(v.urls.list) &&
    v.fields.length > 0 && v.fields.every((f) => record(f) && text(f.name) && text(f.label) && TYPES.includes(f.type as string) && typeof f.html_required === "boolean" &&
      Array.isArray(f.errors) && f.errors.every(text) && (f.max_length === null || Number.isSafeInteger(f.max_length)) && (f.min === null || text(f.min)) &&
      (f.accept === null || text(f.accept)) && (text(f.value) || typeof f.value === "boolean") &&
      (f.type !== "select" || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label)))));
}

export function bajaValid(v: unknown): v is BajaData {
  return record(v) && text(v.nombre) && internal(v.cancel_url) && messagesValid(v.messages);
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const cursosNavigation = { assign: (to: string) => window.location.assign(to) };
const STATUSES = (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403;
const yesNo = (v: boolean, yes: string, no: string) => (v ? yes : no);

function ListContent({ data }: { data: ListData }) {
  const { page } = data;
  return <>
    <NativeToasts messages={toasts(data.messages)} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <div className="action-bar mb-3">
      <a href={data.urls.crear} className="btn btn-primary"><i className="fas fa-plus" /> Agregar</a>
    </div>
    <div className="row mt-3 max-width-100"><div className="col-12"><div className="card"><div className="card-body">
      <table className="table table-bordered table-striped projects">
        <thead><tr>
          <th>Nombre</th><th>Programa objetivo</th><th>Link</th><th>Orden</th><th>Recomendado</th><th>Estado</th><th>Imagen</th><th style={{ width: "18%" }}>Acciones</th>
        </tr></thead>
        <tbody>
          {data.results.length ? data.results.map((c) => <tr key={c.id}>
            <td>{c.nombre}</td>
            <td>{c.programa}</td>
            <td><a href={c.link} target="_blank" rel="noreferrer">{c.link}</a></td>
            <td>{c.orden}</td>
            <td>{yesNo(c.es_recomendado, "Sí", "No")}</td>
            <td>{yesNo(c.activo, "Activo", "Inactivo")}</td>
            <td>{yesNo(c.tiene_imagen, "Sí", "No")}</td>
            <td>
              <a href={c.urls.editar} className="btn btn-sm btn-warning">Editar</a>{" "}
              <a href={c.urls.eliminar} className="btn btn-sm btn-danger">Eliminar</a>
            </td>
          </tr>) : <tr><td colSpan={8} className="text-center">No hay cursos cargados.</td></tr>}
        </tbody>
      </table>
    </div></div></div></div>
    <div id="pagination-container">
      <Pagination paginated={page.is_paginated} number={page.number} previous={page.previous} next={page.next} range={page.range}
        href={(n) => `?${page.query_without_page}page=${n}`} count={page.count > 0 ? page.count : null} />
    </div>
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando cursos…", (data) => ({
    title: "Cursos App Mobile", activePath: BASE,
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={BASE}>Cursos App Mobile</a></li>
      <li className="breadcrumb-item active">Listar</li>
    </ol>,
    content: <ListContent data={data} />,
  }));
}

/** `form.as_p`: the errors list comes before its paragraph, the label carries the colon suffix. */
function AsP({ field, value, onChange, fileRef }: { field: Field; value: string | boolean; onChange: (v: string | boolean) => void; fileRef: RefObject<HTMLInputElement | null> }) {
  const id = `id_${field.name}`;
  const invalid = field.errors.length > 0;
  const aria = invalid ? { "aria-invalid": "true" as const, "aria-describedby": `${id}_error` } : {};
  const required = field.html_required || undefined;
  let control;
  if (field.type === "select") {
    control = <select name={field.name} className="form-control" required={required} id={id} value={String(value)} onChange={(e) => onChange(e.target.value)} {...aria}>
      {field.choices!.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>;
  } else if (field.type === "checkbox") {
    control = <input type="checkbox" name={field.name} className="form-check-input" id={id} checked={value === true} onChange={(e) => onChange(e.target.checked)} {...aria} />;
  } else if (field.type === "file") {
    control = <input ref={fileRef} type="file" name={field.name} className="form-control" accept={field.accept ?? undefined} id={id} {...aria} />;
  } else {
    control = <input type={field.type} name={field.name} className="form-control" maxLength={field.max_length ?? undefined} min={field.min ?? undefined} required={required} id={id}
      value={String(value)} onChange={(e) => onChange(e.target.value)} {...aria} />;
  }
  return <>
    {invalid && <ul className="errorlist" id={`${id}_error`}>{field.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>}
    <p><label htmlFor={id}>{field.label}:</label>{" "}{control}</p>
  </>;
}

function CursoForm({ data, endpoint, rejected }: { data: CursoFormData; endpoint: string; rejected: (d: CursoFormData) => void }) {
  const [values, setValues] = useState<Record<string, string | boolean>>(() => Object.fromEntries(data.fields.map((f) => [f.name, f.value])));
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  const file = useRef<HTMLInputElement | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new window.FormData();
    for (const f of data.fields) {
      if (f.type === "file") { const chosen = file.current?.files?.[0]; if (chosen) body.append(f.name, chosen); }
      else if (f.type === "checkbox") { if (values[f.name] === true) body.append(f.name, "on"); }
      else body.append(f.name, String(values[f.name]));
    }
    let message = UNCERTAIN;
    try {
      const { data: response, status } = await webClient.post(endpoint, body, { validateStatus: STATUSES });
      if (status === 400 && formValid(response)) { rejected(response); resetAfterRejectedPost(); return; }
      const to = status < 300 && record(response) && response.ok === true ? sameOriginTarget(response.redirect) : null;
      if (to) { cursosNavigation.assign(to); return; }
      if (status === 403 && record(response) && text(response.detail)) message = response.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    busy.current = false; setPending(false); setUncertain(message);
  }
  return <div className="row"><div className="col-md-8"><div className="card card-primary">
    <div className="card-header"><h3 className="card-title">{data.edit_mode ? "Editar curso" : "Crear curso"}</h3></div>
    <form method="post" encType="multipart/form-data" onSubmit={(event) => void submit(event)}>
      <div className="card-body">
        {data.non_field_errors.length > 0 && <ul className="errorlist nonfield">{data.non_field_errors.map((e, i) => <li key={i}>{e}</li>)}</ul>}
        {data.fields.map((f) => <AsP key={f.name} field={f} value={values[f.name]} fileRef={file} onChange={(v) => setValues((all) => ({ ...all, [f.name]: v }))} />)}
        {uncertain && <p role="alert" className="mb-0">{uncertain}</p>}
      </div>
      <div className="card-footer d-flex justify-content-between">
        <a href={data.urls.list} className="btn btn-outline-secondary">Volver</a>{" "}
        <button type="submit" className="btn btn-primary" disabled={pending || !!uncertain}>Guardar</button>
      </div>
    </form>
  </div></div></div>;
}

function FormContent({ initial, endpoint }: { initial: CursoFormData; endpoint: string }) {
  const [state, setState] = useState({ data: initial, revision: 0 });
  return <>
    <NativeToasts key={`t${state.revision}`} messages={toasts(state.data.messages)} />
    <CursoForm key={state.revision} data={state.data} endpoint={endpoint} rejected={(response) => setState((s) => ({ data: response, revision: s.revision + 1 }))} />
  </>;
}

function FormPage({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(endpoint, formValid);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: "Cursos App Mobile", activePath: BASE,
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={data.urls.list}>Cursos App Mobile</a></li>
      <li className="breadcrumb-item active">{data.edit_mode ? "Editar" : "Crear"}</li>
    </ol>,
    content: <FormContent initial={data} endpoint={endpoint} />,
  }));
}

function BajaContent({ data, endpoint }: { data: BajaData; endpoint: string }) {
  const [uncertain, setUncertain] = useState("");
  const [pending, setPending] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    let message = UNCERTAIN;
    try {
      const { data: response, status } = await webClient.post(endpoint, new URLSearchParams(), { validateStatus: STATUSES });
      const to = status < 300 && record(response) && response.ok === true ? sameOriginTarget(response.redirect) : null;
      if (to) { cursosNavigation.assign(to); return; }
      if (status === 403 && record(response) && text(response.detail)) message = response.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    busy.current = false; setPending(false); setUncertain(message);
  }
  return <>
    <NativeToasts messages={toasts(data.messages)} />
    <div className="row"><div className="col-md-6"><div className="card card-danger">
      <div className="card-header"><h3 className="card-title">Eliminar curso</h3></div>
      <form method="post" onSubmit={(event) => void submit(event)}>
        <div className="card-body">
          <p>¿Desea eliminar el curso <strong>{data.nombre}</strong>?</p>
          {uncertain && <p role="alert" className="mb-0">{uncertain}</p>}
        </div>
        <div className="card-footer d-flex justify-content-between">
          <a href={data.cancel_url} className="btn btn-outline-secondary">Cancelar</a>{" "}
          <button type="submit" className="btn btn-danger" disabled={pending || !!uncertain}>Eliminar</button>
        </div>
      </form>
    </div></div></div>
  </>;
}

function BajaPage({ pk }: { pk: string }) {
  const endpoint = `${API}${pk}/eliminar/`;
  const [state] = useMainResource(endpoint, bajaValid);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar curso", activePath: BASE, breadcrumb: null,
    content: <BajaContent data={data} endpoint={endpoint} />,
  }));
}

type Params = { page: "list" } | { page: "create" } | { page: "edit" | "delete"; pk: string };

// Native URLs of `comedores/urls.py`, with their trailing slashes.
const PATH = /^\/comedores\/configuracion\/cursos-app-mobile\/(?:(crear)\/|([0-9]+)\/(editar|eliminar)\/)?$/;

export const comedorCursosRoute: RouteDefinition<Params> = {
  name: "comedores-cursos-app-mobile",
  match(pathname) {
    const m = PATH.exec(pathname);
    if (!m) return null;
    if (m[1]) return { page: "create" };
    if (m[2]) return { page: m[3] === "editar" ? "edit" : "delete", pk: m[2] };
    return { page: "list" };
  },
  render(params) {
    if (params.page === "list") return <ListPage key={window.location.search} />;
    if (params.page === "create") return <FormPage key="create" endpoint={`${API}crear/`} />;
    if (params.page === "edit") return <FormPage key={`e${params.pk}`} endpoint={`${API}${params.pk}/editar/`} />;
    return <BajaPage key={`d${params.pk}`} pk={params.pk} />;
  },
};
