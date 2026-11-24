/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { type ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { bool } from "./vatShared";
import { ConfirmDelete, Control, CsrfInput, Err, FORM_CSS, fieldValid, ICON, Select2Links, UNCERTAIN, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import type { RouteDefinition } from "./types";

/**
 * V08.02 resultado forms: `resultado_form.html` (alta y edición) and `resultado_confirm_delete.html`.
 * The fields, their widget attributes and the errors come from `/api/web/vat/resultados-evaluacion/`,
 * which runs the native ModelForm and views; the POST persists through their `form_valid`.
 */
export type ResultadoFormData = { editing: boolean; fields: Field[]; urls: { list: string } };
export type ResultadoDeleteData = { persona: string; evaluacion: string; calificacion: string; urls: { detail: string } };

const API = "web/vat/resultados-evaluacion/";

export const resultadoFormValid = (v: unknown): v is ResultadoFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) && v.fields.length === 5 &&
  v.fields.every(fieldValid) && record(v.urls) && internal(v.urls.list);
export const resultadoDeleteValid = (v: unknown): v is ResultadoDeleteData => record(v) && text(v.persona) && text(v.evaluacion) && text(v.calificacion) &&
  record(v.urls) && internal(v.urls.detail);

function ResultadoForm({ initial, endpoint, forbidden }: { initial: ResultadoFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: resultadoFormValid });
  const label = (f: Field, required: boolean): ReactNode => <label htmlFor={f.id} className="form-label fw-600">{f.label}{required && <>{" "}<span className="text-danger">*</span></>}</label>;
  const group = (f: Field, icon: string) => <div className="input-group"><span className="input-group-text bg-light border-0"><i className={icon} style={ICON} /></span><Control f={f} state={state} set={set} /></div>;
  const { evaluacion, inscripcion, calificacion, aprobo, observaciones } = Object.fromEntries(data.fields.map((f) => [f.name, f])) as Record<string, Field>;
  return <>
    <Select2Links />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-12"><div className="d-flex align-items-center gap-2 mb-4">
        <a href={data.urls.list} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
        <div><h1 className="h2 mb-0" style={ICON}>
          {data.editing ? <><i className="bi bi-pencil-square me-2" />Editar Resultado</> : <><i className="bi bi-plus-circle me-2" />Nuevo Resultado</>}
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
                <div className="col-md-6">{label(evaluacion, true)}{group(evaluacion, "bi-clipboard2-data")}<Err f={evaluacion} /></div>
                <div className="col-md-6">{label(inscripcion, true)}{group(inscripcion, "bi-person-check")}<Err f={inscripcion} /></div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{label(calificacion, false)}{group(calificacion, "bi-123")}<Err f={calificacion} /></div>
                <div className="col-md-6">{label(aprobo, false)}{group(aprobo, "bi-check2-circle")}<Err f={aprobo} /></div>
              </div>
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
          <div className="small text-muted"><p>Calificación y resultado de un inscripto en una evaluación.</p></div>
        </div></div></div>
      </div>
    </div>
    <style>{FORM_CSS}</style>
  </>;
}

function FormPage({ id }: { id?: string }) {
  const endpoint = id ? `${API}${id}/editar/` : `${API}nuevo/`;
  const [state, setState] = useMainResource(endpoint, resultadoFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: data.editing ? "Editar Resultado" : "Nueva Resultado", breadcrumb: null,
    content: <ResultadoForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, resultadoDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar Resultado", breadcrumb: null,
    content: <ConfirmDelete title={data.persona} subtitle={`${data.evaluacion} • Calif: ${data.calificacion}`} cancel={data.urls.detail} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { mode: "nuevo" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py`.
const PATH = /^\/vat\/resultados-evaluacion\/(?:(nuevo)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatResultadosFormRoute: RouteDefinition<Params> = {
  name: "vat-resultados-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[1] ? { mode: "nuevo" } : { mode: m[3] as "editar" | "eliminar", id: m[2] };
  },
  render({ mode, id }) {
    if (mode === "eliminar") return <DeletePage key={id} id={id!} />;
    return <FormPage key={`${mode}:${id ?? ""}`} id={id} />;
  },
};
