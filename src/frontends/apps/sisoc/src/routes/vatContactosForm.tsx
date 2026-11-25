/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import type { ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { bool } from "./vatShared";
import { Control, CsrfInput, Err, Select2Links, fieldValid, ICON, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import { UncertainNotice, usePostDelete } from "./vatCentrosListaShared";
import type { RouteDefinition } from "./types";

/**
 * V06.01 contacto forms: `institucion/contacto_form.html` (alta y edición) and `contacto_confirm_delete.html`.
 * Fields, widget attributes and errors come from `/api/web/vat/institucion/contactos/`, which runs the native
 * ModelForm and views; the POST persists through their `form_valid`/`post`. A `?centro=` query locks the centro
 * (the native `lock_centro`) and travels with the POST like the native `action=""`.
 */
export type ContactoFormData = { editing: boolean; fields: Field[]; non_field_errors: string[]; urls: { list: string } };
export type ContactoDeleteData = { valor: string; tipo: string; centro: string; urls: { detail: string } };

const API = "web/vat/institucion/contactos/";
const FIELDS = ["centro", "nombre_contacto", "rol_area", "documento", "telefono_contacto", "email_contacto", "es_principal"];

export const contactoFormValid = (v: unknown): v is ContactoFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) &&
  v.fields.length === FIELDS.length && v.fields.every(fieldValid) && (v.fields as Field[]).every((f, n) => f.name === FIELDS[n]) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.list);
export const contactoDeleteValid = (v: unknown): v is ContactoDeleteData => record(v) && ["valor", "tipo", "centro"].every((k) => text(v[k])) &&
  record(v.urls) && internal(v.urls.detail);

/** The widget `oninput` strips non-digits in the native page; React gets it as the `set` filter instead of an inert attribute. */
const withoutInline = (f: Field): Field => ({ ...f, attrs: Object.fromEntries(Object.entries(f.attrs).filter(([k]) => k !== "oninput")) });

const Group = ({ icon, children }: { icon: string; children: ReactNode }) => <div className="input-group">
  <span className="input-group-text bg-light border-0"><i className={`bi ${icon}`} style={ICON} /></span>{children}
</div>;

function ContactoForm({ initial, endpoint, forbidden }: { initial: ContactoFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: contactoFormValid });
  const [centro, nombre, rol, documento, telefono, email, principal] = data.fields.map(withoutInline);
  const setDigits = (name: string, value: string | boolean) => set(name, name === "documento" && typeof value === "string" ? value.replace(/\D/g, "") : value);
  const label = (f: Field, required = false) => <label htmlFor={f.id} className="form-label fw-600">{f.label}{required && <>{" "}<span className="text-danger">*</span></>}</label>;
  const control = (f: Field, icon: string) => <Group icon={icon}><Control f={f} state={state} set={setDigits} /></Group>;
  return <>
    <Select2Links />
    <link rel="stylesheet" href="/static/custom/css/vat_design.css" />
    <div className="vat-ui container-fluid py-4">
      <div className="vp-hero"><h1>{data.editing ? "Editar Contacto" : "Nuevo Contacto"}</h1></div>
      <div className="row">
        <div className="col-lg-8"><div className="card border-0 shadow-sm">
          <div className="card-header"><h5 className="mb-0"><i className="bi bi-file-earmark-text me-2" />Información General</h5></div>
          <div className="card-body p-4">
            <form method="post" noValidate onSubmit={(e) => void submit(e)}>
              <CsrfInput />
              <UncertainNotice show={uncertain} />
              <div className="row mb-4"><div className="col-md-12">{label(centro, true)}{control(centro, "bi-building")}<Err f={centro} /></div></div>
              <div className="row mb-4">
                <div className="col-md-6">{label(nombre)}{control(nombre, "bi-person")}<Err f={nombre} /></div>
                <div className="col-md-6">{label(rol)}{control(rol, "bi-briefcase")}<Err f={rol} /></div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{label(documento)}{control(documento, "bi-person-vcard")}<Err f={documento} /></div>
                <div className="col-md-6">{label(telefono, true)}{control(telefono, "bi-telephone")}<Err f={telefono} /></div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{label(email, true)}{control(email, "bi-envelope")}<Err f={email} /></div>
                <div className="col-md-6 d-flex align-items-end"><div className="form-check form-switch">
                  <Control f={principal} state={state} set={setDigits} />{" "}<label className="form-check-label fw-600" htmlFor={principal.id}>{principal.label}</label>
                </div></div>
              </div>
              {data.non_field_errors.length > 0 && <div className="alert alert-danger"><ul className="errorlist nonfield">{data.non_field_errors.map((e) => <li key={e}>{e}</li>)}</ul></div>}
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
          <div className="small text-muted">
            <p><strong>Canal obligatorio:</strong><br />Cada contacto debe tener al menos un teléfono o correo electrónico.</p>
            <hr />
            <p><strong>Responsable principal:</strong><br />Si marcás este contacto como principal, reemplaza al principal anterior del centro.</p>
          </div>
        </div></div></div>
      </div>
    </div>
  </>;
}

function FormPage({ id }: { id?: string }) {
  const endpoint = `${id ? `${API}${id}/editar/` : `${API}nuevo/`}${window.location.search}`;
  const [state, setState] = useMainResource(endpoint, contactoFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: data.editing ? "Editar Contacto" : "Nuevo Contacto", breadcrumb: null,
    content: <ContactoForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function DeleteCard({ data, endpoint, forbidden }: { data: ContactoDeleteData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { uncertain, submit } = usePostDelete(endpoint, forbidden);
  return <>
    <link rel="stylesheet" href="/static/custom/css/vat_design.css" />
    <div className="vat-ui container-fluid py-4"><div className="row"><div className="col-lg-6 offset-lg-3 col-md-8 offset-md-2">
      <div className="card border-danger border-2 shadow-sm"><div className="card-body p-5 text-center">
        <div className="mb-4"><i className="bi bi-exclamation-triangle" style={{ fontSize: "4rem", color: "#dc3545" }} /></div>
        <h2 className="h4 mb-2 fw-bold">¿Estás seguro?</h2>
        <p className="text-muted mb-4">Esta acción no se puede deshacer</p>
        <div className="alert alert-light border mb-4"><div className="mb-2">
          <strong className="d-block mb-1">{data.valor}</strong>
          <small className="text-muted d-block">{data.tipo} • {data.centro}</small>
        </div></div>
        <div className="alert alert-warning mb-4" role="alert">
          <i className="bi bi-exclamation-circle me-2" />{" "}<strong>Advertencia:</strong> Al eliminar este contacto, se perderá todo el registro de su información.
        </div>
        <form method="post" className="mt-4" onSubmit={submit}>
          <CsrfInput />
          <UncertainNotice show={uncertain} />
          <div className="d-grid gap-2">
            <button type="submit" className="btn btn-danger btn-lg"><i className="bi bi-trash me-2" />Sí, eliminar definitivamente</button>
            <a href={data.urls.detail} className="btn btn-outline-secondary btn-lg"><i className="bi bi-x-lg me-2" />Cancelar</a>
          </div>
        </form>
        <p className="small text-muted mt-4 mb-0">Si cometiste un error, puedes cancelar y volver al detalle del contacto.</p>
      </div></div>
    </div></div></div>
    <style>{".fw-bold { font-weight: 700 !important; } .border-danger { border-color: #dc3545 !important; } .text-danger { color: #dc3545 !important; }"}</style>
  </>;
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, contactoDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar Contacto", breadcrumb: null, content: <DeleteCard data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { mode: "nuevo" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py`.
const PATH = /^\/vat\/institucion\/contactos\/(?:(nuevo)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatContactosFormRoute: RouteDefinition<Params> = {
  name: "vat-contactos-form",
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
