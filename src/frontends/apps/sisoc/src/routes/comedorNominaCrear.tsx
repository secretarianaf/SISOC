/* eslint-disable react-refresh/only-export-components -- route module: the validator and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { sameOriginTarget } from "./cdiObservaciones";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeModal, NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CO01 `comedor/nomina_form.html` ("Agregar a Nómina", `nomina_directa_crear` and `nomina_crear`): the DNI
 * search (a plain GET form like the native one), the matches with their «Agregar» modal, and the two
 * creation forms (with and without DNI) with the nómina state and observations. Data and POSTs go through
 * `/api/web/comedores/nomina-crear/`, which runs the native views; a confirmed redirect is a full-page
 * navigation like the native 302 and a rejected POST replaces the page like the native reload.
 */
type Choice = { value: string; label: string; checked?: boolean };
type Field = {
  name: string; id: string; label: string; required: boolean; kind: "input" | "select" | "textarea" | "checkbox" | "checkboxmultiple";
  attrs: Record<string, string>; help_text: string; errors: string[]; value: string | boolean | string[]; choices?: Choice[];
};
type FormData_ = { fields: Field[]; non_field_errors: string[] };
type Ciudadano = {
  id: number; apellido: string; nombre: string; documento: string; tipo_registro: string; revision: boolean;
  comunidad_indigena: string; situacion_calle: string; celiaquia: string;
};
type Message = { message: string; tags: string };
export type NominaCrearData = {
  comedor: { id: number; nombre: string; url: string }; query: string;
  cupo: { completo: boolean; ocupados: number; tope: number } | null; has_activities: boolean;
  ciudadanos: Ciudadano[]; show_form: boolean; renaper: boolean; mode: string;
  form_ciudadano: FormData_; form_sin_dni: FormData_; form_extra: FormData_; modal_fields: Field[];
  estados: { value: string; label: string }[]; pnud: boolean; actividades: { id: number; label: string }[]; messages: Message[];
};

const KINDS = ["input", "select", "textarea", "checkbox", "checkboxmultiple"];
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);

function fieldValid(f: unknown): f is Field {
  return record(f) && text(f.name) && text(f.id) && text(f.label) && typeof f.required === "boolean" && KINDS.includes(f.kind as string) &&
    record(f.attrs) && Object.values(f.attrs).every(text) && text(f.help_text) && strings(f.errors) &&
    (text(f.value) || typeof f.value === "boolean" || strings(f.value)) &&
    (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));
}
const formValid = (f: unknown): f is FormData_ => record(f) && Array.isArray(f.fields) && f.fields.every(fieldValid) && strings(f.non_field_errors);

export function nominaCrearValid(v: unknown): v is NominaCrearData {
  if (!record(v) || !record(v.comedor)) return false;
  return integer(v.comedor.id) && text(v.comedor.nombre) && internal(v.comedor.url) && text(v.query) &&
    (v.cupo === null || (record(v.cupo) && typeof v.cupo.completo === "boolean" && integer(v.cupo.ocupados) && integer(v.cupo.tope))) &&
    typeof v.has_activities === "boolean" && typeof v.show_form === "boolean" && typeof v.renaper === "boolean" && text(v.mode) && typeof v.pnud === "boolean" &&
    Array.isArray(v.ciudadanos) && v.ciudadanos.every((c) => record(c) && integer(c.id) && text(c.apellido) && text(c.nombre) && text(c.documento) &&
      text(c.tipo_registro) && typeof c.revision === "boolean" && text(c.comunidad_indigena) && text(c.situacion_calle) && text(c.celiaquia)) &&
    formValid(v.form_ciudadano) && formValid(v.form_sin_dni) && formValid(v.form_extra) &&
    Array.isArray(v.modal_fields) && v.modal_fields.every(fieldValid) &&
    Array.isArray(v.estados) && v.estados.every((e) => record(e) && text(e.value) && text(e.label)) &&
    Array.isArray(v.actividades) && v.actividades.every((a) => record(a) && integer(a.id) && text(a.label)) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && text(m.tags));
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const nominaCrearNavigation = { assign: (to: string) => window.location.assign(to) };

const TOAST_LEVEL: Record<string, "success" | "error" | "warning" | "info"> = { success: "success", error: "error", warning: "warning", info: "info", debug: "info" };
const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";
const ATTRIBUTES: Record<string, string> = { class: "className", maxlength: "maxLength", readonly: "readOnly", cols: "cols", rows: "rows" };

/** The attributes crispy rendered on the control, as React props. */
function controlProps(attrs: Record<string, string>): Record<string, unknown> {
  const props: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "required" || key === "readonly" || key === "disabled" || key === "multiple") props[ATTRIBUTES[key] ?? key] = true;
    else props[ATTRIBUTES[key] ?? key] = value;
  }
  return props;
}

function Errors({ id, errors }: { id: string; errors: string[] }) {
  if (!errors.length) return null;
  return <div id={`${id}_error`} className="invalid-feedback">{errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e}</strong></p>)}</div>;
}

function NominaField({ field, disabled }: { field: Field; disabled: boolean }) {
  const { id } = field;
  if (field.kind === "checkbox") {
    return (
      <div className="mb-3">
        <div id={`div_${id}`} className="form-check">
          <input type="checkbox" name={field.name} id={id} {...controlProps(field.attrs)} defaultChecked={field.value === true} disabled={disabled} />{" "}
          <label htmlFor={id} className="form-check-label">{field.label}</label>
          <Errors id={id} errors={field.errors} />
        </div>
      </div>
    );
  }
  if (field.kind === "checkboxmultiple") {
    return (
      <div id={`div_${id}`} className="mb-3">
        <fieldset>
          <legend className="form-label fs-6">{field.label}</legend>
          <div>
            {(field.choices ?? []).map((c, i) => (
              <div key={c.value} className="form-check">
                <input type="checkbox" className="form-check-input" name={field.name} value={c.value} id={`${id}_${i + 1}`} defaultChecked={c.checked} disabled={disabled} />{" "}
                <label htmlFor={`${id}_${i + 1}`} className="form-check-label">{c.label}</label>
              </div>
            ))}
          </div>
          <Errors id={id} errors={field.errors} />
        </fieldset>
      </div>
    );
  }
  const props = controlProps(field.attrs);
  let control: ReactNode;
  if (field.kind === "select") {
    control = <select name={field.name} id={id} {...props} defaultValue={String(field.value)} disabled={disabled}>{(field.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select>;
  } else if (field.kind === "textarea") {
    control = <textarea name={field.name} id={id} {...props} defaultValue={String(field.value)} disabled={disabled} />;
  } else {
    control = <input name={field.name} id={id} {...props} defaultValue={String(field.value)} disabled={disabled} />;
  }
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>{field.label}{field.required && <span className="asteriskField">*</span>}</label>{" "}
      {control}{" "}
      <Errors id={id} errors={field.errors} />
    </div>
  );
}

/** crispy's `errors.html`: the non-field errors drawn at the top of a form. */
function FormErrors({ errors }: { errors: string[] }) {
  if (!errors.length) return null;
  return <div className="alert alert-block alert-danger"><ul className="m-0">{errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>;
}

function Alert({ message }: { message: Message }) {
  const [open, setOpen] = useState(true);
  if (!open) return null;
  const tone = message.tags === "error" ? "danger" : message.tags;
  return (
    <div className={`alert alert-${tone} alert-dismissible fade show`} role="alert">
      {message.message}
      <button type="button" className="btn-close" data-bs-dismiss="alert" aria-label="Cerrar" onClick={() => setOpen(false)} />
    </div>
  );
}

type Submit = (event: FormEvent<HTMLFormElement>) => void;

function IdentityBadges({ c }: { c: Ciudadano }) {
  return (
    <>
      {c.tipo_registro === "SIN_DNI" ? <span className="badge bg-warning text-dark">Sin DNI</span>
        : c.tipo_registro === "DNI_NO_VALIDADO_RENAPER" ? <span className="badge bg-danger">RENAPER no validado</span>
          : <span className="badge bg-success">Estándar</span>}
      {c.revision && <>{" "}<span className="badge bg-secondary ms-1"><i className="fas fa-exclamation-triangle" /> Revisión</span></>}
    </>
  );
}

function AddModal({ data, target, close, post }: { data: NominaCrearData; target: Ciudadano; close: () => void; post: (body: URLSearchParams) => void }) {
  const [invalid, setInvalid] = useState(false);
  const optionFor = (field: Field, value: string) => ((field.choices ?? []).some((c) => c.value === value) ? value : "");
  const initial = [target.comunidad_indigena, target.situacion_calle, target.celiaquia];
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const estado = form.elements.namedItem("estado") as HTMLSelectElement;
    if (!estado.value) { setInvalid(true); return; }
    setInvalid(false);
    post(new URLSearchParams(new FormData(form) as unknown as Record<string, string>));
  }
  return (
    <NativeModal id="modalNomina" title="Agregar a Nómina" close={close}>
      <div className="modal-content">
        <form method="post" id="form-nomina" className={invalid ? "was-validated" : undefined} onSubmit={submit}>
          <div className="modal-header">
            <h5 className="modal-title" id="modalNominaLabel">Agregar a Nómina</h5>
            <button type="button" className="btn-close" aria-label="Cerrar" onClick={close} />
          </div>
          <div className="modal-body">
            <input type="hidden" name="ciudadano_id" id="ciudadano_id" value={target.id} />
            <div className="fs-6 fw-bold py-2 mb-3" id="ciudadano_nombre_display">Ciudadano seleccionado: {target.apellido || "-"}, {target.nombre || "-"}</div>
            <div className="row">
              <div className="col-md-6">
                <label htmlFor="estado" className="form-label">Estado</label>{" "}
                <select name="estado" id="estado" className={`form-control${invalid ? " is-invalid" : ""}`} required defaultValue="">
                  <option value="">Seleccione un estado</option>
                  {data.estados.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
                </select>
                <div className="invalid-feedback">Seleccione un estado.</div>
              </div>
              <div className="col-md-12 mt-3">
                <label htmlFor="observaciones" className="form-label">Observaciones</label>{" "}
                <textarea name="observaciones" id="observaciones" className="form-control" rows={3} />
              </div>
              {data.modal_fields.map((f, i) => (
                <div key={f.id} className="col-md-4 mt-3"><NominaField field={{ ...f, value: optionFor(f, initial[i]) }} disabled={false} /></div>
              ))}
              {data.pnud && (
                <div className="col-md-12 mt-4">
                  <div className="border rounded p-3">
                    <div className="fw-bold mb-2">Asistencia</div>
                    <div className="form-check">
                      <input type="checkbox" className="form-check-input" id="modal_asistencia_alimentaria" name="asistencia_alimentaria" defaultChecked />{" "}
                      <label className="form-check-label" htmlFor="modal_asistencia_alimentaria">Prestacion alimentaria</label>
                    </div>
                    <div className="form-check mt-2">
                      <input type="checkbox" className="form-check-input" id="modal_asistencia_actividades" name="asistencia_actividades" />{" "}
                      <label className="form-check-label" htmlFor="modal_asistencia_actividades">Actividades</label>
                    </div>
                    <div className="mt-3">
                      <div className="form-label mb-2">Actividades asociadas</div>
                      {data.actividades.length > 0 ? data.actividades.map((a) => (
                        <div key={a.id} className="form-check">
                          <input type="checkbox" className="form-check-input modal-actividad-pnud" id={`modal_actividad_${a.id}`} name="actividad_ids" value={a.id} />{" "}
                          <label className="form-check-label" htmlFor={`modal_actividad_${a.id}`}>{a.label}</label>
                        </div>
                      )) : <div className="text-muted small">No hay actividades activas para asociar.</div>}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
          <div className="modal-footer">
            <button type="submit" className="btn btn-success">Agregar</button>
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

function NominaCrearContent({ data, endpoint, replace }: { data: NominaCrearData; endpoint: string; replace: (next: NominaCrearData) => void }) {
  const [sinDni, setSinDni] = useState(data.mode === "sin_dni");
  const [revealed, setRevealed] = useState(data.show_form || data.mode === "sin_dni");
  const [target, setTarget] = useState<Ciudadano | null>(null);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  const card = useRef<HTMLDivElement>(null);
  const reveal = (toSinDni: boolean) => {
    setSinDni(toSinDni); setRevealed(true);
    window.requestAnimationFrame(() => card.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };
  async function post(body: URLSearchParams) {
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    let message = UNCERTAIN;
    try {
      const { data: response, status } = await webClient.post(endpoint, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
      if (status === 400 && nominaCrearValid(response)) {
        replace(response); busy.current = false; setPending(false); resetAfterRejectedPost();
        return;
      }
      const to = status < 300 && record(response) && response.ok === true ? sameOriginTarget(response.redirect) : null;
      if (to) { nominaCrearNavigation.assign(to); return; }
      if (status === 403 && record(response) && text(response.detail)) message = response.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown, nothing is retried.
    }
    busy.current = false; setPending(false); setUncertain(message); setTarget(null);
  }
  const submit: Submit = (event) => {
    event.preventDefault();
    post(new URLSearchParams(new FormData(event.currentTarget) as unknown as Record<string, string>));
  };
  const cupo = data.cupo;
  return (
    <>
      <div className="container">
        <h2 className="text-center display-4 mb-4">Agregar a Nómina</h2>
        {data.messages.map((m, i) => <Alert key={i} message={m} />)}
        {/* The native base template also raises each flash message as a toast at the end of <body>. */}
        <NativeToasts messages={data.messages.map((m) => ({ message: m.message, level: TOAST_LEVEL[m.tags] ?? "info" }))} />
        {uncertain && <div className="alert alert-danger" role="alert">{uncertain}</div>}
        {cupo && (cupo.completo ? (
          <div className="alert alert-warning" role="status">
            <strong>Cupo de Prestación alimentaria completo</strong>{" "}
            ({cupo.ocupados} de {cupo.tope} personas conveniadas).
            <br />
            No se pueden sumar más personas con Prestación alimentaria.{" "}
            {data.has_activities
              ? "Puede agregarlas solo en Actividades, o dar de baja a alguien de la nómina para liberar un lugar."
              : "Para sumar a alguien, dé de baja a otra persona de la nómina para liberar un lugar."}
          </div>
        ) : (
          <div className="alert alert-info" role="status">Cupo de Prestación alimentaria: {cupo.ocupados} de {cupo.tope} personas conveniadas.</div>
        ))}

        <div className="card mb-3">
          <div className="card-header font-weight-bold">Buscar Ciudadano</div>
          <div className="card-body">
            <form method="get" className="form-inline">
              <div className="form-group mr-2">
                <label htmlFor="busqueda-dni" className="sr-only">DNI</label>
                <input type="text" className="form-control" name="query" id="busqueda-dni" placeholder="Ingrese DNI (mín 4 dígitos)" defaultValue={data.query} />
              </div>
              <button className="btn btn-secondary mt-3" type="submit">Buscar</button>{" "}
              <button className="btn btn-outline-primary mt-3 ml-2" type="button" id="btn-sin-dni" onClick={() => reveal(true)}>Sin DNI</button>
            </form>
          </div>
        </div>

        {data.ciudadanos.length > 0 && (
          <div className="card mb-3">
            <div className="card-header font-weight-bold">Resultados de Búsqueda</div>
            <div className="card-body table-responsive">
              <table className="table table-bordered table-hover">
                <thead><tr><th>Apellido</th><th>Nombre</th><th>DNI</th><th>Estado identidad</th><th>Acción</th></tr></thead>
                <tbody>
                  {data.ciudadanos.map((c) => (
                    <tr key={c.id}>
                      <td>{c.apellido || "-"}</td>
                      <td>{c.nombre || "-"}</td>
                      <td>{c.documento || "-"}</td>
                      <td><IdentityBadges c={c} /></td>
                      <td>
                        {c.revision
                          ? <button type="button" className="btn btn-sm btn-secondary" disabled title="Debe validarse la identidad antes de ingresar a nómina">Revisión pendiente</button>
                          : <button type="button" className="btn btn-sm btn-success btn-agregar" onClick={() => setTarget(c)}>Agregar</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {data.show_form && (
          <div className="alert alert-info mb-3">
            <i className="bi bi-exclamation-triangle-fill fs-4" />{" "}
            {data.renaper && data.ciudadanos.length > 0
              ? "Se encontraron coincidencias pendientes de revisión. Se precargaron datos desde RENAPER; confirme para crear y agregar a la nómina."
              : data.renaper
                ? "No se encontraron coincidencias en el sistema. Se precargaron datos desde RENAPER; confirme para crear y agregar a la nómina."
                : "No se encontraron coincidencias."}
          </div>
        )}
        <div ref={card} className={`card mb-3${revealed ? "" : " d-none"}`} id="card-creacion-ciudadano">
          <div className="card-header d-flex justify-content-between align-items-center">
            <span className="font-weight-bold" id="titulo-creacion-ciudadano">{sinDni ? "Crear Ciudadano sin DNI" : "Crear Nuevo Ciudadano"}</span>
            <button type="button" className={`btn btn-sm btn-outline-secondary${sinDni ? " d-none" : ""}`} id="btn-cambiar-modo" onClick={() => reveal(!sinDni)}>{sinDni ? "Con DNI" : "Sin DNI"}</button>
          </div>
          <div className="card-body">
            <ModeForms data={data} sinDni={sinDni} onSubmit={submit} pending={pending} />
          </div>
        </div>
      </div>
      {target && <AddModal data={data} target={target} close={() => setTarget(null)} post={(body) => void post(body)} />}
    </>
  );
}

/** Both forms stay in the DOM like the native page; only the one of the current mode is enabled and visible. */
function ModeForms({ data, sinDni, onSubmit, pending }: { data: NominaCrearData; sinDni: boolean; onSubmit: Submit; pending: boolean }) {
  return (
    <>
      <div id="formulario-con-dni" className={sinDni ? "d-none" : undefined}>
        <CreateInner data={data} sinDni={false} disabled={sinDni} onSubmit={onSubmit} pending={pending} />
      </div>
      <div id="formulario-sin-dni" className={sinDni ? undefined : "d-none"}>
        <CreateInner data={data} sinDni disabled={!sinDni} onSubmit={onSubmit} pending={pending} />
      </div>
    </>
  );
}

function CreateInner({ data, sinDni, disabled, onSubmit, pending }: { data: NominaCrearData; sinDni: boolean; disabled: boolean; onSubmit: Submit; pending: boolean }) {
  const form = sinDni ? data.form_sin_dni : data.form_ciudadano;
  return (
    <>
      {sinDni && <div className="alert alert-warning">Esta alta excepcional se guardará sin revisión manual y se agregará directamente a la nómina.</div>}
      {form.non_field_errors.length > 0 && <div className="alert alert-danger">{form.non_field_errors.join(" ")}</div>}
      <form method="post" onSubmit={onSubmit}>
        <input type="hidden" name="modo_creacion" value={sinDni ? "sin_dni" : "con_dni"} disabled={disabled} />
        {!sinDni && data.renaper && <input type="hidden" name="origen_dato" value="renaper" disabled={disabled} />}
        {form.fields.map((f) => <NominaField key={f.id} field={f} disabled={disabled} />)}
        <div className="mt-4 alert alert-light">
          <h5 className="mb-3"><i className="bi bi-info-circle-fill" /> Estado y observaciones en la Nómina</h5>
          <FormErrors errors={data.form_extra.non_field_errors} />
          {data.form_extra.fields.map((f) => <NominaField key={f.id} field={f} disabled={disabled} />)}
        </div>
        <button type="submit" className="btn btn-primary" disabled={pending || disabled}>
          {pending ? <><span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" /> Procesando…</> : sinDni ? "Crear ciudadano sin DNI" : "Crear y Agregar"}
        </button>
      </form>
    </>
  );
}

function NominaCrearPage({ endpoint }: { endpoint: string }) {
  const [state, setState] = useMainResource(endpoint, nominaCrearValid);
  const [revision, setRevision] = useState(0);
  return renderMain(state, "Cargando nómina…", (data) => ({
    title: "Agregar a Nómina",
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <li className="breadcrumb-item"><a href={data.comedor.url}>Comedor</a></li>
        <li className="breadcrumb-item active">Agregar a Nómina</li>
      </ol>
    ),
    content: <NominaCrearContent key={revision} data={data} endpoint={endpoint} replace={(next) => {
      setState((s) => (s.status === "ready" ? { ...s, data: next } : s));
      setRevision((n) => n + 1);
    }} />,
  }));
}

// Native URLs `nomina_directa_crear` and `nomina_crear` (trailing slash like the Django routes).
const ADMISION = /^\/comedores\/([1-9]\d*)\/admision\/([1-9]\d*)\/nomina\/crear\/$/;
const DIRECTA = /^\/comedores\/([1-9]\d*)\/nomina\/crear\/$/;

export const comedorNominaCrearRoute: RouteDefinition<{ endpoint: string }> = {
  name: "comedor-nomina-crear",
  match(pathname) {
    const base = "web/comedores/nomina-crear/";
    const admision = ADMISION.exec(pathname);
    if (admision) return { endpoint: `${base}${admision[1]}/admision/${admision[2]}/` };
    const directa = DIRECTA.exec(pathname);
    return directa ? { endpoint: `${base}${directa[1]}/` } : null;
  },
  // The native form posts to its own URL, so the search (`?query=`) travels with the endpoint.
  render: ({ endpoint }) => <NominaCrearPage key={endpoint} endpoint={`${endpoint}${window.location.search}`} />,
};
