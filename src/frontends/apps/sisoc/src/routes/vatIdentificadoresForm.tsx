/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import type { ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { bool } from "./vatShared";
import { ConfirmDelete, Control, CsrfInput, Err, Select2Links, fieldValid, ICON, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import { UncertainNotice } from "./vatCentrosListaShared";
import type { RouteDefinition } from "./types";

/**
 * V06.01 identificador forms: `institucion/identificador_form.html` (alta y edición) and `identificador_confirm_delete.html`.
 * Fields, widget attributes and errors come from `/api/web/vat/institucion/identificadores/`, which runs the native
 * ModelForm and views; the POST persists through their `form_valid`/`post`. A `?centro=` query preselects the centro
 * and travels with the POST like the native `action=""`.
 */
export type IdentificadorFormData = { editing: boolean; fields: Field[]; non_field_errors: string[]; urls: { list: string } };
export type IdentificadorDeleteData = { valor: string; tipo: string; centro: string; urls: { detail: string } };

const API = "web/vat/institucion/identificadores/";
// Only the widgets the native template draws (the form also has `ubicacion`, which the template leaves out).
const FIELDS = ["centro", "tipo_identificador", "valor_identificador", "rol_institucional", "es_actual", "vigencia_hasta", "motivo"];

export const identificadorFormValid = (v: unknown): v is IdentificadorFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) &&
  v.fields.length === FIELDS.length && v.fields.every(fieldValid) && (v.fields as Field[]).every((f, n) => f.name === FIELDS[n]) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.list);
export const identificadorDeleteValid = (v: unknown): v is IdentificadorDeleteData => record(v) && ["valor", "tipo", "centro"].every((k) => text(v[k])) &&
  record(v.urls) && internal(v.urls.detail);

const Group = ({ icon, children }: { icon: string; children: ReactNode }) => <div className="input-group">
  <span className="input-group-text bg-light border-0"><i className={icon} style={ICON} /></span>{children}
</div>;

function IdentificadorForm({ initial, endpoint, forbidden }: { initial: IdentificadorFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: identificadorFormValid });
  const [centro, tipo, valor, rol, actual, vigencia, motivo] = data.fields;
  const label = (f: Field, required = false) => <label htmlFor={f.id} className="form-label fw-600">{f.label}{required ? <>{" "}<span className="text-danger">*</span></> : null}</label>;
  const control = (f: Field, icon: string) => <Group icon={icon}><Control f={f} state={state} set={set} /></Group>;
  return <>
    <Select2Links />
    <link rel="stylesheet" href="/static/custom/css/vat_design.css" />
    <div className="vat-ui container-fluid py-4">
      <div className="vp-hero"><h1>{data.editing ? "Editar Identificador" : "Nuevo Identificador"}</h1></div>
      <div className="row">
        <div className="col-lg-8"><div className="card border-0 shadow-sm">
          <div className="card-header"><h5 className="mb-0"><i className="bi bi-file-earmark-text me-2" />Información General</h5></div>
          <div className="card-body p-4">
            <form method="post" noValidate onSubmit={(e) => void submit(e)}>
              <CsrfInput />
              <UncertainNotice show={uncertain} />
              <div className="row mb-4"><div className="col-md-12">{label(centro, true)}{control(centro, "bi-building")}<Err f={centro} /></div></div>
              <div className="row mb-4">
                <div className="col-md-6">{label(tipo, true)}{control(tipo, "bi-tag")}<Err f={tipo} /></div>
                <div className="col-md-6">{label(valor, true)}{control(valor, "bi-hash")}<Err f={valor} /></div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{label(rol)}{control(rol, "bi-diagram-3")}<Err f={rol} /></div>
                <div className="col-md-6"><div className="form-check form-switch">
                  <Control f={actual} state={state} set={set} />{" "}<label className="form-check-label fw-600" htmlFor={actual.id}>{actual.label}</label>
                </div></div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{label(vigencia)}{control(vigencia, "bi-calendar")}<Err f={vigencia} /></div>
                <div className="col-md-6">{label(motivo)}{control(motivo, "bi-chat-left-text")}<Err f={motivo} /></div>
              </div>
              <hr className="my-4" />
              <div className="d-flex gap-2 justify-content-end">
                <a href={data.urls.list} className="btn btn-outline-secondary"><i className="bi bi-x-lg me-2" />Cancelar</a>
                <button type="submit" className="btn btn-primary"><i className="bi bi-check-lg me-2" />{" "}{data.editing ? "Actualizar" : "Crear"}</button>
              </div>
            </form>
          </div>
        </div></div>
        <div className="col-lg-4"><div className="card border-0 shadow-sm bg-light"><div className="card-body">
          <h6 className="card-title fw-600"><i className="bi bi-info-circle me-2" />Información</h6>
          <div className="small text-muted"><p>Registro histórico de identificadores (CUIE, CUE, etc).</p></div>
        </div></div></div>
      </div>
    </div>
  </>;
}

function FormPage({ id }: { id?: string }) {
  const endpoint = `${id ? `${API}${id}/editar/` : `${API}nuevo/`}${window.location.search}`;
  const [state, setState] = useMainResource(endpoint, identificadorFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: data.editing ? "Editar Identificador" : "Nueva Identificador", breadcrumb: null,
    content: <IdentificadorForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, identificadorDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar Identificador", breadcrumb: null,
    content: <ConfirmDelete title={data.valor} subtitle={`${data.tipo} • ${data.centro}`} cancel={data.urls.detail} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { mode: "nuevo" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py`.
const PATH = /^\/vat\/institucion\/identificadores\/(?:(nuevo)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatIdentificadoresFormRoute: RouteDefinition<Params> = {
  name: "vat-identificadores-form",
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
