import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { crearCliente, SinPermiso } from "@sisoc/api";
import InsumosAccessError from "./InsumosAccessError";
import { insumosListPath } from "./insumosPaths";
import { InsumosForbiddenError, rejectInsumosForbidden, validateInsumosStatus, type WebPrerequisite } from "./webAccess";

type Action = "crear" | "editar" | "eliminar";
type Values = { programa: string; nombre: string; descripcion: string; orden: string; activo: boolean };
type Metadata = { initial: Values; options: { programa: { value: string; label: string }[] } };
type Confirmation = { id: number; nombre: string };
type Errors = Record<string, string[]>;
type State = { status: "loading" } | { status: "ready"; endpoint: string; data: Metadata | Confirmation } | { status: "error"; endpoint: string; forbidden: boolean; prerequisite?: WebPrerequisite | null };
type Props = { action: Action; id?: string; onComplete: (message: string) => void; onCancel: () => void };
const client = crearCliente("/api");
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";

function isMetadata(value: unknown): value is Metadata {
  if (!record(value) || !record(value.initial) || !record(value.options)) return false;
  const initial = value.initial;
  return ["programa", "nombre", "descripcion", "orden"].every((name) => typeof initial[name] === "string") &&
    typeof initial.activo === "boolean" && Array.isArray(value.options.programa) &&
    value.options.programa.every((item) => record(item) && typeof item.value === "string" && typeof item.label === "string");
}
function isConfirmation(value: unknown): value is Confirmation {
  return record(value) && Number.isSafeInteger(value.id) && Number(value.id) > 0 && typeof value.nombre === "string";
}
function fieldErrors(error: unknown): Errors | null {
  const response = (error as { response?: { status?: number; data?: { errors?: unknown } } })?.response;
  if (response?.status !== 400 || !record(response.data?.errors)) return null;
  const parsed: Errors = {};
  for (const [name, entries] of Object.entries(response.data.errors)) {
    if (!Array.isArray(entries) || !entries.every((entry) => record(entry) && typeof entry.message === "string")) return null;
    parsed[name] = entries.map((entry) => entry.message as string);
  }
  return Object.keys(parsed).length ? parsed : null;
}

export default function InsumosCategoriaForm({ action, id, onComplete, onCancel }: Props) {
  const listPath = insumosListPath(window.location.pathname, true);
  const endpoint = action === "crear" ? "web/insumos/categorias/crear/" : `web/insumos/categorias/${id}/${action}/`;
  const [state, setState] = useState<State>({ status: "loading" });
  const [values, setValues] = useState<Values>({ programa: "", nombre: "", descripcion: "", orden: "0", activo: true });
  const [errors, setErrors] = useState<Errors>({});
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const active = useRef(false);
  const generation = useRef(0);
  const submitting = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    generation.current += 1;
    active.current = true;
    rejectInsumosForbidden(client.get(endpoint, { signal: controller.signal, validateStatus: validateInsumosStatus }))
      .then(({ data }: { data: unknown }) => {
        if (!current) return;
        if (action === "eliminar" ? !isConfirmation(data) : !isMetadata(data)) throw new Error("Invalid category metadata");
        if (isMetadata(data)) setValues(data.initial);
        setErrors({}); setPending(false); setUncertain(false); submitting.current = false;
        setState({ status: "ready", endpoint, data: data as Metadata | Confirmation });
      }).catch((error: unknown) => {
        if (!current) return;
        setState({ status: "error", endpoint,
          forbidden: error instanceof SinPermiso || (error as { response?: { status?: number } })?.response?.status === 403,
          prerequisite: error instanceof InsumosForbiddenError ? error.prerequisite : null,
        });
      });
    return () => { current = false; active.current = false; controller.abort(); };
  }, [endpoint, action]);

  useLayoutEffect(() => {
    if (Object.keys(errors).length) window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [errors]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting.current || uncertain || state.status !== "ready" || state.endpoint !== endpoint) return;
    submitting.current = true; setPending(true); setErrors({});
    const requestGeneration = generation.current;
    const body = new URLSearchParams();
    if (action !== "eliminar") {
      for (const name of ["programa", "nombre", "descripcion", "orden"] as const) body.set(name, values[name]);
      if (values.activo) body.set("activo", "on");
    }
    try {
      const { data } = await rejectInsumosForbidden(client.post(endpoint, body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" }, validateStatus: validateInsumosStatus,
      }));
      if (!active.current || requestGeneration !== generation.current) return;
      if (!record(data) || data.ok !== true || typeof data.message !== "string" || data.redirect !== "/insumos/categorias/") throw new Error("Unconfirmed category result");
      onComplete(data.message);
    } catch (error: unknown) {
      if (!active.current || requestGeneration !== generation.current) return;
      const validation = fieldErrors(error);
      if (validation) { setErrors(validation); submitting.current = false; }
      else if (error instanceof SinPermiso || (error as { response?: { status?: number } })?.response?.status === 403) {
        setState({ status: "error", endpoint, forbidden: true, prerequisite: error instanceof InsumosForbiddenError ? error.prerequisite : null });
      } else setUncertain(true);
    } finally {
      if (active.current && requestGeneration === generation.current) setPending(false);
    }
  };
  const cancel = (event: React.MouseEvent<HTMLAnchorElement>) => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (!pending) onCancel();
  };
  const feedback = (name: string) => errors[name]?.length ? { "aria-invalid": true as const, "aria-describedby": `error_${name}` } : {};
  const renderErrors = (name: string) => errors[name]?.length ? <div id={`error_${name}`} className="invalid-feedback d-block">{errors[name].map((message, index) => <div key={index}><strong>{message}</strong></div>)}</div> : null;
  const classes = (name: string, base: string) => `${base}${errors[name]?.length ? " is-invalid" : ""}`;
  if (state.status === "loading" || state.endpoint !== endpoint) return <div className="container mt-4" role="status">Cargando formulario…</div>;
  if (state.status === "error") return state.forbidden ? <InsumosAccessError prerequisite={state.prerequisite} /> : <div className="container mt-4"><div className="alert alert-danger" role="alert">No se pudo cargar el formulario.</div><a href={listPath} onClick={cancel}>Volver al listado</a></div>;
  const disabled = pending || uncertain;
  const uncertainMessage = uncertain ? <div className="alert alert-danger" role="alert">No se pudo confirmar el resultado. Antes de volver a intentarlo, revisá el listado.</div> : null;
  if (isConfirmation(state.data)) return <div className="container mt-4"><div className="card">
    <div className="card-header bg-danger text-white"><h5 className="mb-0 fw-semibold">Confirmar eliminación</h5></div>
    <div className="card-body"><p className="mb-3">¿Seguro que desea eliminar la categoría <strong>{state.data.nombre}</strong>? Los insumos asociados quedarán como "Sin categoría".</p>
      {uncertainMessage}<form method="post" onSubmit={submit} aria-busy={pending}><button type="submit" className="btn btn-danger" disabled={disabled}>Eliminar</button>{" "}<a href={listPath} className="btn btn-secondary" aria-disabled={pending || undefined} onClick={cancel}>Cancelar</a></form>
    </div>
  </div></div>;
  return <div className="container mt-4">
    <div className="d-flex justify-content-between mb-3"><h2>{action === "crear" ? "Nueva categoría" : "Editar categoría"}</h2></div>
    <div className="card"><div className="card-body"><form method="post" noValidate onSubmit={submit} aria-busy={pending}>
      {Object.keys(errors).length > 0 && <div className="alert alert-danger" role="alert">No se pudo guardar el formulario. Revisá los campos marcados.{renderErrors("__all__")}</div>}{uncertainMessage}
      <div className="row">
        <div className="col-md-6"><div id="div_id_programa" className="mb-3"><label htmlFor="id_programa" className="form-label requiredField">Programa<span className="asteriskField">*</span></label>
          <select id="id_programa" name="programa" required className={classes("programa", "select form-select")} value={values.programa} disabled={disabled} {...feedback("programa")} onChange={(event) => setValues({ ...values, programa: event.target.value })}>{state.data.options.programa.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>{renderErrors("programa")}
        </div></div>
        <div className="col-md-6"><div id="div_id_nombre" className="mb-3"><label htmlFor="id_nombre" className="form-label requiredField">Nombre<span className="asteriskField">*</span></label><input id="id_nombre" name="nombre" type="text" maxLength={150} required className={classes("nombre", "textinput form-control")} value={values.nombre} disabled={disabled} {...feedback("nombre")} onChange={(event) => setValues({ ...values, nombre: event.target.value })} />{renderErrors("nombre")}</div></div>
      </div>
      <div id="div_id_descripcion" className="mb-3"><label htmlFor="id_descripcion" className="form-label">Descripción</label><textarea id="id_descripcion" name="descripcion" rows={3} className={classes("descripcion", "textarea form-control")} value={values.descripcion} disabled={disabled} {...feedback("descripcion")} onChange={(event) => setValues({ ...values, descripcion: event.target.value })} />{renderErrors("descripcion")}</div>
      <div className="row">
        <div className="col-md-3"><div id="div_id_orden" className="mb-3"><label htmlFor="id_orden" className="form-label requiredField">Orden<span className="asteriskField">*</span></label><input id="id_orden" name="orden" type="number" min={0} required className={classes("orden", "numberinput form-control")} value={values.orden} disabled={disabled} {...feedback("orden")} onChange={(event) => setValues({ ...values, orden: event.target.value })} />{renderErrors("orden")}</div></div>
        <div className="col-md-3"><div className="mb-3"><div id="div_id_activo" className="form-check"><input id="id_activo" name="activo" type="checkbox" role="switch" className={classes("activo", "checkboxinput form-check-input toggle-switch")} checked={values.activo} disabled={disabled} {...feedback("activo")} onChange={(event) => setValues({ ...values, activo: event.target.checked })} /><label htmlFor="id_activo" className="form-check-label">Activa</label>{renderErrors("activo")}</div></div></div>
      </div>
      <div className="d-flex justify-content-end gap-2 mt-3"><a href={listPath} className="btn btn-secondary" aria-disabled={pending || undefined} onClick={cancel}>Cancelar</a><button type="submit" className="btn btn-success" disabled={disabled}><i className="fas fa-save" aria-hidden="true" /> Guardar categoría</button></div>
    </form></div></div>
  </div>;
}
