/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { bool } from "./vatShared";
import { Control, CsrfInput, fieldValid, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import { FieldErrors, UncertainNotice, usePostDelete } from "./vatCentrosListaShared";
import { modalidadBreadcrumb } from "./vatModalidadInstitucional";
import type { RouteDefinition } from "./types";

/**
 * V06.01 modalidad forms: `modalidad_institucional/form.html` (alta y edición) and `confirm_delete.html`.
 * Fields, widget attributes and errors come from `/api/web/vat/modalidades-institucionales/`, which runs the
 * native ModelForm and views; the POST persists through their `form_valid`/`post`.
 */
export type ModalidadFormData = { editing: boolean; fields: Field[]; non_field_errors: string[]; urls: { list: string } };
export type ModalidadDeleteData = { nombre: string; urls: { detail: string } };

const API = "web/vat/modalidades-institucionales/";

export const modalidadFormValid = (v: unknown): v is ModalidadFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) && v.fields.length === 3 &&
  v.fields.every(fieldValid) && Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.list);
export const modalidadDeleteValid = (v: unknown): v is ModalidadDeleteData => record(v) && text(v.nombre) && record(v.urls) && internal(v.urls.detail);

function ModalidadForm({ initial, endpoint, forbidden }: { initial: ModalidadFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: modalidadFormValid });
  const [nombre, descripcion, activo] = data.fields;
  return <div className="row"><div className="col-md-8"><div className="card">
    <div className="card-header bg-primary text-white"><h3 className="card-title">{data.editing ? "Editar Modalidad Institucional" : "Nueva Modalidad Institucional"}</h3></div>
    <form method="post" className="form-horizontal" noValidate onSubmit={(e) => void submit(e)}>
      <CsrfInput />
      <div className="card-body">
        <UncertainNotice show={uncertain} />
        {data.non_field_errors.length > 0 && <div className="alert alert-danger">{data.non_field_errors.map((e) => <p key={e}>{e}</p>)}</div>}
        <div className="form-group"><label htmlFor={nombre.id}>{nombre.label}</label>{" "}<Control f={nombre} state={state} set={set} /><FieldErrors f={nombre} /></div>
        <div className="form-group"><label htmlFor={descripcion.id}>{descripcion.label}</label>{" "}<Control f={descripcion} state={state} set={set} /><FieldErrors f={descripcion} /></div>
        <div className="form-group"><div className="form-check"><Control f={activo} state={state} set={set} />{" "}<label className="form-check-label" htmlFor={activo.id}>{activo.label}</label></div><FieldErrors f={activo} /></div>
      </div>
      <div className="card-footer">
        <button type="submit" className="btn btn-primary">{data.editing ? "Actualizar" : "Crear"}</button>{" "}
        <a href={data.urls.list} className="btn btn-secondary">Cancelar</a>
      </div>
    </form>
  </div></div></div>;
}

function FormPage({ id }: { id?: string }) {
  const endpoint = id ? `${API}${id}/editar/` : `${API}nueva/`;
  const [state, setState] = useMainResource(endpoint, modalidadFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: data.editing ? "VAT - Editar Modalidad Institucional" : "VAT - Nueva Modalidad Institucional",
    breadcrumb: modalidadBreadcrumb(data.editing ? "Editar" : "Nueva"),
    content: <ModalidadForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function DeleteCard({ data, endpoint, forbidden }: { data: ModalidadDeleteData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { uncertain, submit } = usePostDelete(endpoint, forbidden);
  return <div className="row"><div className="col-md-6"><div className="card card-danger">
    <div className="card-header bg-danger text-white"><h3 className="card-title">Confirmar eliminación</h3></div>
    <div className="card-body">
      <p>¿Está seguro de que desea eliminar la modalidad institucional <strong>{data.nombre}</strong>?</p>
      <p className="text-muted">Esta acción no se puede deshacer.</p>
    </div>
    <div className="card-footer">
      <form method="post" onSubmit={submit}>
        <CsrfInput />
        <UncertainNotice show={uncertain} />
        <button type="submit" className="btn btn-danger"><i className="fas fa-trash" />{" "}Eliminar</button>{" "}
        <a href={data.urls.detail} className="btn btn-secondary"><i className="fas fa-arrow-left" />{" "}Cancelar</a>
      </form>
    </div>
  </div></div></div>;
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, modalidadDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "VAT - Confirmar eliminación de Modalidad Institucional", breadcrumb: modalidadBreadcrumb("Confirmar eliminación"),
    content: <DeleteCard data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { mode: "nueva" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py`.
const PATH = /^\/vat\/modalidades-institucionales\/(?:(nueva)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatModalidadInstitucionalFormRoute: RouteDefinition<Params> = {
  name: "vat-modalidad-institucional-form",
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
