/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { type ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { bool, messagesValid, type Message } from "./vatShared";
import { ConfirmDelete, Control, CsrfInput, Err, FORM_CSS, fieldValid, ICON, Select2Links, UNCERTAIN, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import type { RouteDefinition } from "./types";

/**
 * V04.02 schedule forms: `oferta_institucional/horario_form.html` and `horario_confirm_delete.html`, shared by the offer
 * (`vat_comision_horario_*`) and the course (`vat_comision_curso_horario_*`) commissions. The fields, their widget
 * attributes and the errors come from `/api/web/vat/comisiones-horarios/[cursos/]`, which runs the native ModelForm and
 * views; the POST persists through their `form_valid` / `post` (the classes are regenerated and the message queued).
 *
 * Kept native defect: the template draws `form.comision`, which the course form does not have, so on the course variant the
 * first group is empty (label with only the asterisk, icon without control). The page cannot submit the commission there;
 * React posts it as a hidden input so the link from the commission detail works.
 */
export type Variante = "oferta" | "curso";
export type HorarioFormData = { editing: boolean; campo: "comision" | "comision_curso"; fields: Field[]; non_field_errors: string[]; urls: { list: string }; messages: Message[] };
export type HorarioDeleteData = { titulo: string; subtitulo: string; urls: { detail: string } };

const API = (variante: Variante) => `web/vat/comisiones-horarios/${variante === "curso" ? "cursos/" : ""}`;
const NAMES = (campo: string) => [campo, "dia_semana", "hora_desde", "hora_hasta", "aula_espacio", "vigente"];

export const horarioFormValid = (v: unknown): v is HorarioFormData => record(v) && bool(v.editing) && (v.campo === "comision" || v.campo === "comision_curso") &&
  Array.isArray(v.fields) && v.fields.every(fieldValid) && NAMES(v.campo).join() === (v.fields as Field[]).map((f) => f.name).join() &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.list) && messagesValid(v.messages);
export const horarioDeleteValid = (v: unknown): v is HorarioDeleteData => record(v) && text(v.titulo) && text(v.subtitulo) && record(v.urls) && internal(v.urls.detail);

function HorarioForm({ initial, endpoint, forbidden }: { initial: HorarioFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: horarioFormValid });
  const label = (f: Field | null, required: boolean): ReactNode => <label htmlFor={f?.id ?? ""} className="form-label fw-600">{f?.label}{required && <>{" "}<span className="text-danger">*</span></>}</label>;
  const group = (f: Field | null, icon: string) => <div className="input-group"><span className="input-group-text bg-light border-0"><i className={icon} style={ICON} /></span>{f && <Control f={f} state={state} set={set} />}</div>;
  const byName = Object.fromEntries(data.fields.map((f) => [f.name, f])) as Record<string, Field>;
  const { dia_semana: dia, hora_desde: desde, hora_hasta: hasta, aula_espacio: aula, vigente } = byName;
  // The course form has no `comision` field: the native template prints an empty group.
  const comision = data.campo === "comision" ? byName.comision : null;
  return <>
    <NativeToasts messages={data.messages} />
    <Select2Links />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-12"><div className="d-flex align-items-center gap-2 mb-4">
        <a href={data.urls.list} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
        <div><h1 className="h2 mb-0" style={ICON}>
          {data.editing ? <><i className="bi bi-pencil-square me-2" />Editar Horario</> : <><i className="bi bi-plus-circle me-2" />Nueva Horario</>}
        </h1></div>
      </div></div></div>
      <div className="row">
        <div className="col-lg-8"><div className="card border-0 shadow-sm">
          <div className="card-header bg-light border-bottom"><h5 className="mb-0"><i className="bi bi-file-earmark-text me-2" style={ICON} />Información General</h5></div>
          <div className="card-body p-4">
            <form method="post" noValidate onSubmit={(e) => void submit(e)}>
              <CsrfInput />
              {data.campo === "comision_curso" && <input type="hidden" name="comision_curso" value={String(state.comision_curso ?? "")} />}
              {uncertain && <p role="alert">{UNCERTAIN}</p>}
              <div className="row mb-4"><div className="col-md-12">
                {label(comision, true)}{group(comision, "bi-people")}{comision && <Err f={comision} />}
              </div></div>
              <div className="row mb-4">
                <div className="col-md-6">{label(dia, true)}{group(dia, "bi-calendar-day")}<Err f={dia} /></div>
                <div className="col-md-6">{label(aula, false)}{group(aula, "bi-door-open")}<Err f={aula} /></div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{label(desde, true)}{group(desde, "bi-clock")}<Err f={desde} /></div>
                <div className="col-md-6">{label(hasta, true)}{group(hasta, "bi-clock-fill")}<Err f={hasta} /></div>
              </div>
              <div className="row mb-4"><div className="col-md-6"><div className="form-check form-switch">
                <Control f={vigente} state={state} set={set} />{" "}
                <label className="form-check-label fw-600" htmlFor={vigente.id}>{vigente.label}</label>
              </div></div></div>
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
          <div className="small text-muted"><p>Horario de clases para una comisión.</p></div>
        </div></div></div>
      </div>
    </div>
    <style>{FORM_CSS}</style>
  </>;
}

function FormPage({ variante, id }: { variante: Variante; id?: string }) {
  const endpoint = `${API(variante)}${id ? `${id}/editar/` : "nuevo/"}`;
  const [state, setState] = useMainResource(id ? endpoint : `${endpoint}${window.location.search}`, horarioFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: `${data.editing ? "Editar" : "Nueva"} Horario`, breadcrumb: null,
    content: <HorarioForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function DeletePage({ variante, id }: { variante: Variante; id: string }) {
  const endpoint = `${API(variante)}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, horarioDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar Horario", breadcrumb: null,
    content: <ConfirmDelete title={data.titulo} subtitle={data.subtitulo} cancel={data.urls.detail} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { variante: Variante; mode: "nuevo" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py` (`vat_comision_horario_*` and `vat_comision_curso_horario_*`); the list and the detail stay native.
const PATH = /^\/vat\/(cursos\/)?comisiones\/horarios\/(?:(nuevo)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatComisionHorarioFormRoute: RouteDefinition<Params> = {
  name: "vat-comision-horario-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    const variante: Variante = m[1] ? "curso" : "oferta";
    return m[2] ? { variante, mode: "nuevo" } : { variante, mode: m[4] as "editar" | "eliminar", id: m[3] };
  },
  render({ variante, mode, id }) {
    if (mode === "eliminar") return <DeletePage key={`${variante}:${id}`} variante={variante} id={id!} />;
    return <FormPage key={`${variante}:${mode}:${id ?? ""}`} variante={variante} id={id} />;
  },
};
