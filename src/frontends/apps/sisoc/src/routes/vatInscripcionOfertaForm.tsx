/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { Control, CsrfInput, Err, fieldValid, Select2Links, UNCERTAIN, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import { bool, messagesValid, vatNavigation, type Message } from "./vatShared";
import { TourHelp } from "./vatTour";
import type { RouteDefinition } from "./types";

/**
 * V03.01 inscripción de oferta forms: `vat/inscripcion_oferta/form.html` (alta y edición) and `confirm_delete.html`.
 * Fields, widget attributes, errors and queued messages come from `/api/web/vat/inscripciones-oferta/`, which runs
 * the native form and views; the POST persists through their `form_valid` / `post`.
 */
export type InscripcionFormData = { editing: boolean; fields: Field[]; non_field_errors: string[]; urls: { list: string }; messages: Message[] };
export type InscripcionDeleteData = { ciudadano: string; oferta: string; estado_label: string; urls: { detail: string } };

const API = "web/vat/inscripciones-oferta/";

export const inscripcionFormValid = (v: unknown): v is InscripcionFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) && v.fields.length === 3 && v.fields.every(fieldValid) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.list) && messagesValid(v.messages);
export const inscripcionDeleteValid = (v: unknown): v is InscripcionDeleteData => record(v) && text(v.ciudadano) && text(v.oferta) && text(v.estado_label) && record(v.urls) && internal(v.urls.detail);

function InscripcionForm({ initial, endpoint, forbidden }: { initial: InscripcionFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: inscripcionFormValid });
  const { oferta, ciudadano, estado } = Object.fromEntries(data.fields.map((f) => [f.name, f])) as Record<string, Field>;
  const block = (f: Field) => <div className="col-md-6 mb-3">
    <label htmlFor={f.id} className="form-label">{f.label}{" "}<span className="text-danger">*</span></label>
    <Control f={f} state={state} set={set} />
    <Err f={f} />
  </div>;
  return <>
    <NativeToasts messages={data.messages} />
    <Select2Links />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-md-8"><h1 className="h3 text-dark">{data.editing ? "Editar Inscripción" : "Nueva Inscripción"}</h1></div></div>
      <div className="card"><div className="card-body">
        <form method="post" noValidate onSubmit={(e) => void submit(e)}>
          <CsrfInput />
          {uncertain && <p role="alert">{UNCERTAIN}</p>}
          {data.non_field_errors.length > 0 && <div className="alert alert-danger" role="alert">{data.non_field_errors.map((e, n) => <span key={n}>{e}<br /></span>)}</div>}
          <div className="row">{block(oferta)}{block(ciudadano)}</div>
          <div className="row">{block(estado)}</div>
          <div className="d-flex gap-2">
            <button type="submit" className="btn btn-primary"><i className="fas fa-save" />{" "}Guardar</button>
            <a href={data.urls.list} className="btn btn-secondary">Cancelar</a>
          </div>
        </form>
      </div></div>
    </div>
    <TourHelp section="inscripcion_oferta_form" />
  </>;
}

function FormPage({ id }: { id?: string }) {
  const endpoint = id ? `${API}${id}/editar/` : `${API}nueva/`;
  const [state, setState] = useMainResource(endpoint, inscripcionFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: `${data.editing ? "Editar" : "Nueva"} Inscripción - VAT`, breadcrumb: null,
    content: <InscripcionForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function DeleteContent({ data, endpoint, forbidden }: { data: InscripcionDeleteData; endpoint: string; forbidden: (d: unknown) => void }) {
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
  return <div className="container-fluid py-4">
    <div className="row mb-4"><div className="col-md-8"><h1 className="h3 text-dark">Eliminar Inscripción</h1></div></div>
    <div className="card border-danger"><div className="card-body p-5">
      <div className="text-center mb-4"><i className="fas fa-exclamation-triangle fa-3x text-danger" /></div>
      <h4 className="text-center mb-3">¿Está seguro que desea eliminar esta inscripción?</h4>
      <div className="alert alert-warning" role="alert">
        <strong>Esta acción no se puede deshacer.</strong>
        <br />
        <p className="mb-0 mt-2">Se eliminará:</p>
        <ul className="mb-0">
          <li>Ciudadano: <strong>{data.ciudadano}</strong></li>
          <li>Oferta: <strong>{data.oferta}</strong></li>
          <li>Estado actual: <strong>{data.estado_label}</strong></li>
        </ul>
      </div>
      <div className="mt-4">
        <form method="post" className="d-inline" onSubmit={(e) => void submit(e)}>
          <CsrfInput />
          {uncertain && <p role="alert">{UNCERTAIN}</p>}
          <button type="submit" className="btn btn-danger me-2"><i className="fas fa-trash" />{" "}Eliminar</button>{" "}
          <a href={data.urls.detail} className="btn btn-secondary">Cancelar</a>
        </form>
      </div>
    </div></div>
  </div>;
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, inscripcionDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar Inscripción - VAT", breadcrumb: null, content: <DeleteContent data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { mode: "nueva" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py`.
const PATH = /^\/vat\/inscripciones-oferta\/(?:(nueva)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatInscripcionOfertaFormRoute: RouteDefinition<Params> = {
  name: "vat-inscripcion-oferta-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[1] ? { mode: "nueva" } : { mode: m[3] as "editar" | "eliminar", id: m[2] };
  },
  render({ mode, id }) {
    if (mode === "eliminar") return <DeletePage key={id} id={id!} />;
    return <FormPage key={`${mode}:${id ?? ""}`} id={id} />;
  },
};
