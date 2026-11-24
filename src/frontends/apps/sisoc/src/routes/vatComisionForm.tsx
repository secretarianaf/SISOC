/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { bool, messagesValid, vatNavigation, type Message } from "./vatShared";
import { ConfirmDelete, Control, CsrfInput, fieldValid, Select2Links, UNCERTAIN, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import { COMISION_FORM_CSS } from "./vatComisionFormStyles";
import type { RouteDefinition } from "./types";

/**
 * V04.02 commission forms: `oferta_institucional/comision_form.html` and `comision_confirm_delete.html` (offer commission,
 * `vat_comision_{create,update,delete}`) and `curso/comision_curso_form.html` and `comision_curso_confirm_delete.html` (course
 * commission, `vat_comision_curso_{create,update,delete}`). The fields, their widget attributes and the errors come from
 * `/api/web/vat/comisiones-formularios/[cursos/]`, which runs the native ModelForm and views; the POST persists through their
 * `form_valid` / `post` (the classes are regenerated when the dates change, the message is queued and the delete is the
 * native soft delete).
 *
 * Kept native behaviors: the offer template does not draw `acepta_lista_espera`, so saving resets it; the date widgets print
 * the localized `d/m/Y`, which `<input type="date">` cannot show; the course form hides the waiting-list capacity unless the
 * waiting list is on and clears it when it is turned off (the script of the native template).
 */
export type Variante = "oferta" | "curso";
export type ComisionFormData = {
  editing: boolean; fields: (Field & { required?: boolean })[]; non_field_errors: string[]; subtitulo?: string;
  urls: { list: string; detail?: string; cancel?: string }; messages: Message[];
};
export type ComisionDeleteData = { titulo: string; subtitulo: string; urls: { detail: string } };

const API = (variante: Variante) => `web/vat/comisiones-formularios/${variante === "curso" ? "cursos/" : ""}`;
const NAMES: Record<Variante, string[]> = {
  oferta: ["oferta", "ubicacion", "codigo_comision", "nombre", "fecha_inicio", "fecha_fin", "cupo", "estado", "observaciones"],
  curso: ["curso", "ubicacion", "cupo_total", "acepta_lista_espera", "cupo_lista_espera", "fecha_inicio", "fecha_fin", "estado", "observaciones"],
};

const formValid = (variante: Variante) => (v: unknown): v is ComisionFormData => record(v) && bool(v.editing) &&
  Array.isArray(v.fields) && v.fields.every(fieldValid) && NAMES[variante].join() === (v.fields as Field[]).map((f) => f.name).join() &&
  (variante === "curso" ? (v.fields as { required?: unknown }[]).every((f) => bool(f.required)) : true) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.list) &&
  (variante === "oferta" ? text(v.subtitulo) && (v.urls.detail === "" || internal(v.urls.detail)) : v.urls.cancel === "" || internal(v.urls.cancel)) &&
  messagesValid(v.messages);
export const ofertaFormValid = formValid("oferta");
export const cursoFormValid = formValid("curso");
// Stable references: `useMainResource` refetches when its validator changes.
const VALID = { oferta: ofertaFormValid, curso: cursoFormValid };
export const comisionDeleteValid = (v: unknown): v is ComisionDeleteData => record(v) && text(v.titulo) && text(v.subtitulo) && record(v.urls) && internal(v.urls.detail);

type Valores = ReturnType<typeof useWriteForm<ComisionFormData>>;

function OfertaForm({ w }: { w: Valores }) {
  const { data, state, set, uncertain, submit } = w;
  const byName = Object.fromEntries(data.fields.map((f) => [f.name, f])) as Record<string, Field>;
  const block = (name: string, required: boolean, col = "col-md-6") => {
    const f = byName[name];
    return <div className={col}>
      <label htmlFor={f.id} className="form-label">{f.label}{required && <>{" "}<span className="text-danger">*</span></>}</label>
      <Control f={f} state={state} set={set} />
      {f.errors.length > 0 && <div className="text-danger mt-1">{f.errors[0]}</div>}
    </div>;
  };
  return <>
    <div className="ci-hero">
      <div className="d-flex align-items-center gap-3">
        <a href={data.urls.list} className="ci-back"><i className="bi bi-arrow-left" /></a>
        <div>
          <div className="ci-hero-title" style={{ marginTop: 0 }}>
            {data.editing ? <><i className="bi bi-pencil-square me-2" />Editar Comisión</> : <><i className="bi bi-plus-circle me-2" />Nueva Comisión</>}
          </div>
          {data.editing
            ? <div className="ci-hero-sub" style={{ opacity: 0.75, fontSize: ".88rem" }}>{data.subtitulo}</div>
            : <div className="ci-hero-sub">Completá los datos para crear una nueva comisión</div>}
        </div>
      </div>
    </div>
    <div className="row g-3 align-items-start">
      <div className="col-xl-8">
        <form method="post" noValidate onSubmit={(e) => void submit(e)}>
          <CsrfInput />
          {uncertain && <p role="alert">{UNCERTAIN}</p>}
          <div className="ci-panel">
            <div className="ci-sec-head"><span className="ci-sec-title"><i className="bi bi-file-earmark-text me-2" />Información General</span></div>
            <div className="ci-form"><div className="row g-3">
              {block("oferta", true)}{block("ubicacion", false)}{block("codigo_comision", true)}{block("nombre", true)}
              {block("fecha_inicio", true)}{block("fecha_fin", true)}{block("cupo", true)}{block("estado", true)}{block("observaciones", false, "col-12")}
            </div></div>
            <div className="ci-footer">
              <a href={data.urls.list} className="btn btn-sm btn-outline-secondary rounded-3"><i className="bi bi-x-lg me-1" />Cancelar</a>
              <button type="submit" className="btn btn-sm btn-primary rounded-3"><i className="bi bi-check-lg me-1" />{" "}{data.editing ? "Actualizar" : "Crear"}</button>
            </div>
          </div>
        </form>
      </div>
      <div className="col-xl-4"><div style={{ position: "sticky", top: "1rem" }}>
        <div className="ci-scard">
          <p className="ci-sc-title">Información</p>
          <p className="mb-0" style={{ fontSize: ".82rem", color: "var(--bs-secondary-color)" }}>Una comisión es un grupo de estudiantes inscriptos a una oferta educativa, con horarios y sesiones de clase asociadas.</p>
        </div>
        {data.editing && <div className="ci-scard">
          <p className="ci-sc-title">Acciones</p>
          <div className="d-grid gap-2"><a href={data.urls.detail} className="btn btn-outline-secondary btn-sm rounded-3"><i className="bi bi-eye me-2" />Ver detalle</a></div>
        </div>}
      </div></div>
    </div>
    <style>{COMISION_FORM_CSS}</style>
  </>;
}

function CursoForm({ w }: { w: Valores }) {
  const { data, state, set, uncertain, submit } = w;
  const acepta = state.acepta_lista_espera === true;
  const cupoEspera = String(state.cupo_lista_espera ?? "");
  // The native script clears the waiting-list capacity as soon as the waiting list is off (also on load).
  useEffect(() => { if (!acepta && cupoEspera !== "") set("cupo_lista_espera", ""); }, [acepta, cupoEspera, set]);
  const err = (f: Field): ReactNode => f.errors.length > 0 && <div className="text-danger small mt-1">{f.errors[0]}</div>;
  const help = (f: Field): ReactNode => !!f.help_text && <div className="form-text">{f.help_text}</div>;
  const label = (f: Field & { required?: boolean }): ReactNode => <label htmlFor={f.id} className="form-label fw-bold">{f.label}{f.required && <>{" "}<span className="text-danger">*</span></>}</label>;
  return <div className="container-fluid py-4">
    <div className="card border-0 shadow-sm"><div className="card-body p-4">
      <h1 className="h4 mb-3">{data.editing ? "Editar Comisión de Curso" : "Nueva Comisión de Curso"}</h1>
      <form method="post" noValidate onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        {uncertain && <p role="alert">{UNCERTAIN}</p>}
        <div className="row g-3">
          {data.fields.map((f) => {
            if (f.name === "acepta_lista_espera") {
              return <div className="col-md-6" key={f.name}>
                <div className="form-check mt-4 pt-2">
                  <Control f={f} state={state} set={set} />{" "}
                  <label htmlFor={f.id} className="form-check-label fw-bold">{f.label}</label>
                </div>
                {err(f)}{help(f)}
              </div>;
            }
            if (f.name === "cupo_lista_espera") {
              const control = { ...f, attrs: acepta ? { ...f.attrs, required: "required" } : f.attrs };
              return <div className={`col-md-6${acepta ? "" : " d-none"}`} data-waitlist-capacity-wrapper="" key={f.name}>
                {label(f)}
                <Control f={control} state={state} set={set} />
                {err(f)}{help(f)}
              </div>;
            }
            return <div className="col-md-6" key={f.name}>{label(f)}<Control f={f} state={state} set={set} />{err(f)}</div>;
          })}
        </div>
        <div className="d-flex justify-content-end gap-2 mt-4">
          {data.editing
            ? <a href={data.urls.cancel} className="btn btn-outline-secondary">Cancelar</a>
            : <button type="button" onClick={() => window.history.back()} className="btn btn-outline-secondary">Cancelar</button>}
          <button type="submit" className="btn btn-primary">{data.editing ? "Actualizar" : "Crear"}</button>
        </div>
      </form>
    </div></div>
  </div>;
}

function ComisionFormBody({ variante, initial, endpoint, forbidden }: { variante: Variante; initial: ComisionFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const w = useWriteForm({ initial, endpoint, forbidden, valid: VALID[variante] });
  return <>
    <NativeToasts messages={w.data.messages} />
    <Select2Links />
    {variante === "oferta" ? <OfertaForm w={w} /> : <CursoForm w={w} />}
  </>;
}

const TITLE = (variante: Variante, editing: boolean) => `${editing ? "Editar" : "Nueva"} Comisión${variante === "curso" ? " de Curso" : ""}`;

function FormPage({ variante, id }: { variante: Variante; id?: string }) {
  const endpoint = `${API(variante)}${id ? `${id}/editar/` : "nueva/"}`;
  const [state, setState] = useMainResource(id ? endpoint : `${endpoint}${window.location.search}`, VALID[variante]);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: TITLE(variante, data.editing), breadcrumb: null,
    content: <ComisionFormBody variante={variante} initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

/** `curso/comision_curso_confirm_delete.html`: the plain card (the offer commission uses the shared confirmation card). */
function CursoDelete({ data, endpoint, forbidden }: { data: ComisionDeleteData; endpoint: string; forbidden: (d: unknown) => void }) {
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
  return <div className="container-fluid py-4"><div className="card border-0 shadow-sm"><div className="card-body p-4">
    <h1 className="h4 mb-3">Eliminar comisión de curso</h1>
    <p>¿Seguro que querés eliminar la comisión{" "}<strong>{data.titulo}</strong>?</p>
    <form method="post" onSubmit={(e) => void submit(e)}>
      <CsrfInput />
      {uncertain && <p role="alert">{UNCERTAIN}</p>}
      <div className="d-flex gap-2 justify-content-end">
        <a href={data.urls.detail} className="btn btn-outline-secondary">Cancelar</a>
        <button type="submit" className="btn btn-danger">Eliminar</button>
      </div>
    </form>
  </div></div></div>;
}

function DeletePage({ variante, id }: { variante: Variante; id: string }) {
  const endpoint = `${API(variante)}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, comisionDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: variante === "curso" ? "Eliminar Comisión de Curso" : "Eliminar Comisión", breadcrumb: null,
    content: variante === "curso"
      ? <CursoDelete data={data} endpoint={endpoint} forbidden={forbidden} />
      : <ConfirmDelete title={data.titulo} subtitle={data.subtitulo} cancel={data.urls.detail} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { variante: Variante; mode: "nueva" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py` (`vat_comision_{create,update,delete}` and `vat_comision_curso_{create,update,delete}`); the list,
// the detail and the course wizard stay native in this module.
const PATH = /^\/vat\/(cursos\/)?comisiones\/(?:(nueva)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatComisionFormRoute: RouteDefinition<Params> = {
  name: "vat-comision-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    const variante: Variante = m[1] ? "curso" : "oferta";
    return m[2] ? { variante, mode: "nueva" } : { variante, mode: m[4] as "editar" | "eliminar", id: m[3] };
  },
  render({ variante, mode, id }) {
    if (mode === "eliminar") return <DeletePage key={`${variante}:${id}`} variante={variante} id={id!} />;
    return <FormPage key={`${variante}:${mode}:${id ?? ""}`} variante={variante} id={id} />;
  },
};
