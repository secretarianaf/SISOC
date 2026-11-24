/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { type ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { bool } from "./vatShared";
import { ConfirmDelete, Control, CsrfInput, Err, FORM_CSS, fieldValid, ICON, Select2Links, UNCERTAIN, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import type { RouteDefinition } from "./types";

/**
 * V08.02 evaluación forms: `evaluacion_form.html` (alta y edición) and `evaluacion_confirm_delete.html`.
 * The fields, their widget attributes and the errors come from `/api/web/vat/evaluaciones/`, which
 * runs the native ModelForm and views; the POST persists through their `form_valid`.
 */
export type FormData_ = { editing: boolean; fields: Field[]; urls: { list: string } };
export type DeleteData = { nombre: string; tipo_label: string; comision: string; urls: { detail: string } };

const API = "web/vat/evaluaciones/";

export const formValid = (v: unknown): v is FormData_ => record(v) && bool(v.editing) && Array.isArray(v.fields) && v.fields.length === 8 && v.fields.every(fieldValid) &&
  record(v.urls) && internal(v.urls.list);
export const deleteValid = (v: unknown): v is DeleteData => record(v) && text(v.nombre) && text(v.tipo_label) && text(v.comision) && record(v.urls) && internal(v.urls.detail);

function EvaluacionForm({ initial, endpoint, forbidden }: { initial: FormData_; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: formValid });
  const label = (f: Field, required: boolean): ReactNode => <label htmlFor={f.id} className="form-label fw-600">{f.label}{required && <>{" "}<span className="text-danger">*</span></>}</label>;
  const group = (f: Field, icon: string) => <div className="input-group"><span className="input-group-text bg-light border-0"><i className={icon} style={ICON} /></span><Control f={f} state={state} set={set} /></div>;
  const { comision, tipo, nombre, fecha, ponderacion, es_final: esFinal, descripcion, observaciones } = Object.fromEntries(data.fields.map((f) => [f.name, f])) as Record<string, Field>;
  return <>
    <Select2Links />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-12"><div className="d-flex align-items-center gap-2 mb-4">
        <a href={data.urls.list} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
        <div><h1 className="h2 mb-0" style={ICON}>
          {data.editing ? <><i className="bi bi-pencil-square me-2" />Editar Evaluación</> : <><i className="bi bi-plus-circle me-2" />Nueva Evaluación</>}
        </h1></div>
      </div></div></div>
      <div className="row">
        <div className="col-lg-8"><div className="card border-0 shadow-sm">
          <div className="card-header bg-light border-bottom"><h5 className="mb-0"><i className="bi bi-file-earmark-text me-2" style={ICON} />Información General</h5></div>
          <div className="card-body p-4">
            <form method="post" noValidate onSubmit={(e) => void submit(e)}>
              <CsrfInput />
              {uncertain && <p role="alert">{UNCERTAIN}</p>}
              <div className="row mb-4">
                <div className="col-md-6">{label(comision, true)}{group(comision, "bi-people")}<Err f={comision} /></div>
                <div className="col-md-6">{label(tipo, true)}{group(tipo, "bi-tag")}<Err f={tipo} /></div>
              </div>
              <div className="row mb-4"><div className="col-md-12">{label(nombre, true)}{group(nombre, "bi-type")}<Err f={nombre} /></div></div>
              <div className="row mb-4">
                <div className="col-md-6">{label(fecha, true)}{group(fecha, "bi-calendar-event")}<Err f={fecha} /></div>
                <div className="col-md-6">{label(ponderacion, true)}{group(ponderacion, "bi-percent")}<Err f={ponderacion} /></div>
              </div>
              <div className="row mb-4"><div className="col-md-6"><div className="form-check form-switch">
                <Control f={esFinal} state={state} set={set} />{" "}<label className="form-check-label fw-600" htmlFor={esFinal.id}>{esFinal.label}</label>
              </div></div></div>
              <div className="row mb-4"><div className="col-md-12">{label(descripcion, false)}<Control f={descripcion} state={state} set={set} /><Err f={descripcion} /></div></div>
              <div className="row mb-4"><div className="col-md-12">{label(observaciones, false)}<Control f={observaciones} state={state} set={set} /><Err f={observaciones} /></div></div>
              <hr className="my-4" />
              <div className="d-flex gap-2 justify-content-end">
                <a href={data.urls.list} className="btn btn-outline-secondary"><i className="bi bi-x-lg me-2" />Cancelar</a>
                <button type="submit" className="btn btn-primary"><i className="bi bi-check-lg me-2" />{" "}{data.editing ? "Actualizar" : "Crear"}</button>
              </div>
            </form>
          </div>
        </div></div>
        <div className="col-lg-4"><div className="card border-0 shadow-sm bg-light"><div className="card-body">
          <h6 className="card-title fw-600" style={ICON}><i className="bi bi-info-circle me-2" />Información</h6>
          <div className="small text-muted"><p>Evaluación para una comisión (Parcial, Final, Integradora, Recuperatorio).</p></div>
        </div></div></div>
      </div>
    </div>
    <style>{FORM_CSS}</style>
  </>;
}

function FormPage({ id }: { id?: string }) {
  const endpoint = id ? `${API}${id}/editar/` : `${API}nueva/`;
  const [state, setState] = useMainResource(endpoint, formValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: data.editing ? "Editar Evaluación" : "Nueva Evaluación", breadcrumb: null,
    content: <EvaluacionForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, deleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar Evaluación", breadcrumb: null,
    content: <ConfirmDelete title={data.nombre} subtitle={`${data.tipo_label} • ${data.comision}`} cancel={data.urls.detail} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { mode: "nueva" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py`.
const PATH = /^\/vat\/evaluaciones\/(?:(nueva)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatEvaluacionesFormRoute: RouteDefinition<Params> = {
  name: "vat-evaluaciones-form",
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
