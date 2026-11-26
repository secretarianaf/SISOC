/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { Breadcrumb, internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import type { Catalogo } from "./vatCatalogos";
import { MODALIDAD_FORM_CSS } from "./vatCatalogosStyles";
import { Control, CsrfInput, fieldValid, Select2Links, UNCERTAIN, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import { bool, messagesValid, vatNavigation, type Message } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V07.02 catalogo forms: `vat/catalogo/{sector,subsector,modalidadcursada,titulorreferencia}_form.html` and
 * `*_confirm_delete.html`. Fields, widget attributes, errors and queued messages come from
 * `/api/web/vat/catalogos/<slug>/`, which runs the native forms and views; the POST persists through their
 * `form_valid` / `post`.
 */
export type CatalogoFormData = {
  editing: boolean; fields: Field[]; non_field_errors: string[]; urls: { list: string; vat: string; cancel?: string };
  page?: { page_title: string; page_description: string; submit_text: string }; messages: Message[];
};
export type CatalogoDeleteData = { nombre: string; sector: string; urls: { detail: string } };

const API = (catalogo: Catalogo) => `web/vat/catalogos/${catalogo}/`;
const FIELDS: Record<Catalogo, number> = { sectores: 2, subsectores: 3, "modalidades-cursado": 3, "titulos-referencia": 5 };

export const catalogoFormValid = (catalogo: Catalogo) => (v: unknown): v is CatalogoFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) &&
  v.fields.length === FIELDS[catalogo] && v.fields.every(fieldValid) && Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) &&
  record(v.urls) && internal(v.urls.list) && internal(v.urls.vat) && (v.urls.cancel === undefined || internal(v.urls.cancel)) &&
  (catalogo !== "modalidades-cursado" || (record(v.page) && text(v.page.page_title) && text(v.page.page_description) && text(v.page.submit_text) && internal(v.urls.cancel))) &&
  messagesValid(v.messages);
export const catalogoDeleteValid = (v: unknown): v is CatalogoDeleteData => record(v) && text(v.nombre) && text(v.sector) && record(v.urls) && internal(v.urls.detail);

// `useMainResource` refetches when the validator changes: keep one per catalogo.
const FORM_VALID = Object.fromEntries((Object.keys(FIELDS) as Catalogo[]).map((c) => [c, catalogoFormValid(c)])) as Record<Catalogo, ReturnType<typeof catalogoFormValid>>;

const NOUN: Record<Catalogo, string> = { sectores: "Sector", subsectores: "Subsector", "modalidades-cursado": "Modalidad de Cursado", "titulos-referencia": "Título" };
const CRUMB: Record<Catalogo, string> = { sectores: "Sectores", subsectores: "Subsectores", "modalidades-cursado": "Modalidades de Cursado", "titulos-referencia": "Títulos" };

/** `{{ field.errors }}` / `{{ form.non_field_errors }}`: Django's `<ul class="errorlist">`. */
const ErrorList = ({ errors, nonfield = false }: { errors: string[]; nonfield?: boolean }) => <ul className={nonfield ? "errorlist nonfield" : "errorlist"}>{errors.map((e, n) => <li key={n}>{e}</li>)}</ul>;

/** The generic `for field in form` card of the sector, subsector and title forms. */
function GenericForm({ catalogo, initial, endpoint, forbidden }: { catalogo: Catalogo; initial: CatalogoFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: catalogoFormValid(catalogo) });
  const noun = catalogo === "titulos-referencia" ? "Título" : NOUN[catalogo];
  const verb = data.editing ? "Editar" : "Nuevo";
  return <>
    <NativeToasts messages={data.messages} />
    <Select2Links />
    <div className="row"><div className="col-md-8"><div className="card">
      <div className="card-header bg-primary text-white"><h3 className="card-title">{verb} {noun}</h3></div>
      <form method="post" className={catalogo === "titulos-referencia" ? undefined : "form-horizontal"} onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        {uncertain && <p role="alert">{UNCERTAIN}</p>}
        <div className="card-body">
          {data.fields.map((f) => <div key={f.name} className="form-group">
            <label htmlFor={f.id}>{f.label}</label>{" "}
            <Control f={f} state={state} set={set} />
            {f.errors.length > 0 && <>{" "}<small className="text-danger"><ErrorList errors={f.errors} /></small></>}
          </div>)}
        </div>
        <div className="card-footer">
          <button type="submit" className="btn btn-primary">{data.editing ? "Actualizar" : "Crear"}</button>{" "}
          <a href={data.urls.list} className="btn btn-secondary">Cancelar</a>
        </div>
      </form>
    </div></div></div>
  </>;
}

/** `modalidadcursada_form.html`: hero, panel and switch with the title, text and cancel URL of the native view. */
function ModalidadForm({ initial, endpoint, forbidden }: { initial: CatalogoFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: catalogoFormValid("modalidades-cursado") });
  const { nombre, descripcion, activo } = Object.fromEntries(data.fields.map((f) => [f.name, f])) as Record<string, Field>;
  const page = data.page!;
  const field = (f: Field, extra = "") => <div className={`col-md-6 vp-field${extra}`}>
    <label htmlFor={f.id}>{f.label}</label>
    <Control f={f} state={state} set={set} />
    {f.errors.length > 0 && <div className="vp-inline-errors">{f.errors[0]}</div>}
  </div>;
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/cardsDetail.css" />
    <style>{MODALIDAD_FORM_CSS}</style>
    <div className="vp-shell">
      <div className="vp-hero"><div><h1><i className="fas fa-layer-group" />{page.page_title}</h1><p>{page.page_description}</p></div></div>
      <form method="post" noValidate onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        {uncertain && <p role="alert">{UNCERTAIN}</p>}
        {data.non_field_errors.length > 0 && <div className="alert alert-danger"><ErrorList errors={data.non_field_errors} nonfield /></div>}
        <div className="card vp-panel">
          <div className="vp-panel-header"><div>
            <h3 className="card-title"><i className="fas fa-pen" />Datos de la Modalidad</h3>
            <div className="small">Completá  la información base con el mismo estilo visual del catálogo curricular.</div>
          </div></div>
          <div className="vp-section">
            <div className="row">
              {field(nombre)}
              {field(descripcion)}
              <div className="col-md-4 vp-field mt-2">
                <div className="vp-switch form-check form-switch">
                  <Control f={activo} state={state} set={set} />{" "}
                  <label className="form-check-label" htmlFor={activo.id}>{activo.label}</label>
                </div>
                {activo.errors.length > 0 && <div className="vp-inline-errors">{activo.errors[0]}</div>}
              </div>
            </div>
            <div className="vp-actions">
              <a href={data.urls.cancel} className="btn btn-secondary"><i className="fas fa-arrow-left" />Cancelar</a>{" "}
              <button type="submit" className="btn btn-primary"><i className="fas fa-save" />{page.submit_text}</button>
            </div>
          </div>
        </div>
      </form>
    </div>
  </>;
}

function FormPage({ catalogo, id }: { catalogo: Catalogo; id?: string }) {
  const endpoint = id ? `${API(catalogo)}${id}/editar/` : `${API(catalogo)}${catalogo === "modalidades-cursado" ? "nueva" : "nuevo"}/`;
  const [state, setState] = useMainResource(endpoint, FORM_VALID[catalogo]);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => {
    const verb = data.editing ? "Editar" : "Nuevo";
    if (catalogo === "modalidades-cursado") {
      return { title: data.page!.page_title, heading: data.page!.page_title, breadcrumb: null, content: <ModalidadForm initial={data} endpoint={endpoint} forbidden={forbidden} /> };
    }
    return {
      title: `${verb} ${NOUN[catalogo]}`,
      breadcrumb: <Breadcrumb items={[
        { text: "VAT", url: data.urls.vat }, { text: CRUMB[catalogo], url: data.urls.list }, { text: verb, url: null },
      ]} />,
      content: <GenericForm catalogo={catalogo} initial={data} endpoint={endpoint} forbidden={forbidden} />,
    };
  });
}

function DeleteContent({ catalogo, data, endpoint, forbidden }: { catalogo: Catalogo; data: CatalogoDeleteData; endpoint: string; forbidden: (d: unknown) => void }) {
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const result = await postForm(endpoint, new URLSearchParams());
    busy.current = false;
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else setUncertain(true);
  }
  const name: ReactNode = catalogo === "subsectores" ? <><strong>{data.nombre}</strong> ({data.sector})</> : <strong>{data.nombre}</strong>;
  return <div className="row"><div className="col-md-6"><div className="card card-danger">
    <div className="card-header bg-danger text-white"><h3 className="card-title">Confirmar eliminación</h3></div>
    <div className="card-body"><p>¿Eliminar {name}?</p></div>
    <div className="card-footer">
      <form method="post" onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        {uncertain && <p role="alert">{UNCERTAIN}</p>}
        <button type="submit" className="btn btn-danger"><i className="fas fa-trash" />{" "}Eliminar</button>{" "}
        <a href={data.urls.detail} className="btn btn-secondary">Cancelar</a>
      </form>
    </div>
  </div></div></div>;
}

function DeletePage({ catalogo, id }: { catalogo: Catalogo; id: string }) {
  const endpoint = `${API(catalogo)}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, catalogoDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Confirmar eliminación",
    breadcrumb: <Breadcrumb items={[{ text: CRUMB[catalogo], url: `/vat/catalogos/${catalogo}/` }, { text: "Eliminar", url: null }]} />,
    content: <DeleteContent catalogo={catalogo} data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { catalogo: Catalogo; mode: "nuevo" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py` (`nueva/` for the modalidades de cursado).
const PATH = /^\/vat\/catalogos\/(sectores|subsectores|modalidades-cursado|titulos-referencia)\/(?:(nuevo|nueva)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatCatalogosFormRoute: RouteDefinition<Params> = {
  name: "vat-catalogos-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    const catalogo = m[1] as Catalogo;
    if (m[2]) return (m[2] === "nueva") === (catalogo === "modalidades-cursado") ? { catalogo, mode: "nuevo" } : null;
    return { catalogo, mode: m[4] as "editar" | "eliminar", id: m[3] };
  },
  render({ catalogo, mode, id }) {
    if (mode === "eliminar") return <DeletePage key={`${catalogo}:${id}`} catalogo={catalogo} id={id!} />;
    return <FormPage key={`${catalogo}:${mode}:${id ?? ""}`} catalogo={catalogo} id={id} />;
  },
};
