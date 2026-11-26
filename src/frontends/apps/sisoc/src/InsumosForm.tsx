import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { crearCliente, SinPermiso } from "@sisoc/api";
import InsumosAccessError from "./InsumosAccessError";
import { insumosListPath } from "./insumosPaths";
import {
  InsumosForbiddenError,
  rejectInsumosForbidden,
  validateInsumosStatus,
  type WebPrerequisite,
} from "./webAccess";

type Action = "crear" | "editar" | "eliminar";
type Values = { programa: string; categoria: string; titulo: string; descripcion: string; activo: boolean };
type Option = { value: string; label: string; programa_id?: string };
type Metadata = {
  initial: Values;
  options: { programa: Option[]; categoria: Option[] };
  current_file: { name: string; download_url: string | null } | null;
};
type Errors = Record<string, string[]>;
type Confirmation = { id: number; titulo: string };
type State = { status: "loading" } | { status: "error"; endpoint: string; message: string; forbidden: boolean; prerequisite?: WebPrerequisite | null } | { status: "ready"; endpoint: string; metadata: Metadata | Confirmation };
type Props = { action: Action; id?: string; onComplete: (message: string) => void; onCancel: () => void };
const client = crearCliente("/api");
const ACCEPT = ".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.csv";
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";

function internalDownload(value: unknown): value is string {
  return typeof value === "string" && /^\/insumos\/[0-9]+\/descargar\/?$/.test(value);
}

function isMetadata(value: unknown): value is Metadata {
  if (!record(value) || !record(value.initial) || !record(value.options)) return false;
  const initial = value.initial;
  if (!["programa", "categoria", "titulo", "descripcion"].every((field) => typeof initial[field] === "string") || typeof initial.activo !== "boolean") return false;
  for (const name of ["programa", "categoria"]) {
    const options = value.options[name];
    if (!Array.isArray(options) || !options.every((option) => record(option) && typeof option.value === "string" && typeof option.label === "string" && (option.programa_id === undefined || typeof option.programa_id === "string"))) return false;
  }
  const file = value.current_file;
  return file === null || (record(file) && typeof file.name === "string" && (file.download_url === null || internalDownload(file.download_url)));
}

function isConfirmation(value: unknown): value is Confirmation {
  return record(value) && typeof value.id === "number" && Number.isSafeInteger(value.id) && value.id > 0 && typeof value.titulo === "string";
}

function validationErrors(error: unknown): Errors | null {
  const response = (error as { response?: { status?: number; data?: { errors?: unknown } } })?.response;
  if (response?.status !== 400 || !record(response.data?.errors)) return null;
  const result: Errors = {};
  for (const [name, messages] of Object.entries(response.data.errors)) {
    if (!Array.isArray(messages) || !messages.every((entry) => record(entry) && typeof entry.message === "string")) return null;
    result[name] = messages.map((entry) => entry.message as string);
  }
  return Object.keys(result).length ? result : null;
}

export default function InsumosForm({ action, id, onComplete, onCancel }: Props) {
  const listPath = insumosListPath(window.location.pathname);
  const endpoint = action === "crear" ? "web/insumos/crear/" : `web/insumos/${id}/${action}/`;
  const [state, setState] = useState<State>({ status: "loading" });
  const [values, setValues] = useState<Values>({ programa: "", categoria: "", titulo: "", descripcion: "", activo: true });
  const [file, setFile] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
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
    rejectInsumosForbidden(client.get(endpoint, {
      signal: controller.signal,
      validateStatus: validateInsumosStatus,
    })).then(({ data }: { data: unknown }) => {
      if (!current) return;
      if (action === "eliminar" ? !isConfirmation(data) : !isMetadata(data)) throw new Error("Invalid form metadata");
      if (isMetadata(data)) setValues(data.initial);
      setFile(null);
      setErrors({});
      setPending(false);
      setUncertain(false);
      submitting.current = false;
      setState({ status: "ready", endpoint, metadata: data as Metadata | Confirmation });
    }).catch((error: unknown) => {
      if (!current) return;
      const forbidden = error instanceof SinPermiso ||
        (error as { response?: { status?: number } })?.response?.status === 403;
      setState({
        status: "error",
        endpoint,
        message: error instanceof SinPermiso ? error.message : "No se pudo cargar el formulario.",
        forbidden,
        prerequisite: error instanceof InsumosForbiddenError ? error.prerequisite : null,
      });
    });
    return () => { current = false; active.current = false; generation.current += 1; controller.abort(); };
  }, [endpoint, action]);

  useLayoutEffect(() => {
    if (state.status === "ready" && state.endpoint === endpoint && action !== "eliminar" && Object.keys(errors).length > 0) {
      // Match the legacy invalid-POST navigation after field errors are rendered.
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    }
  }, [errors, state, endpoint, action]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting.current || uncertain || state.status !== "ready" || state.endpoint !== endpoint) return;
    const requestGeneration = generation.current;
    submitting.current = true;
    setPending(true);
    setErrors({});
    const body = new FormData();
    for (const field of ["programa", "categoria", "titulo", "descripcion"] as const) body.append(field, values[field]);
    if (values.activo) body.append("activo", "on");
    if (file) body.append("archivo", file);
    try {
      const { data } = await rejectInsumosForbidden(client.post(
        endpoint,
        action === "eliminar" ? undefined : body,
        { validateStatus: validateInsumosStatus },
      ));
      if (!active.current || generation.current !== requestGeneration) return;
      if (!record(data) || data.ok !== true || typeof data.message !== "string" || data.redirect !== "/insumos/") throw new Error("Unconfirmed mutation response");
      onComplete(data.message);
    } catch (error: unknown) {
      if (!active.current || generation.current !== requestGeneration) return;
      const fields = validationErrors(error);
      if (fields) {
        setFile(null);
        if (fileInput.current) fileInput.current.value = "";
        setErrors(fields);
        submitting.current = false;
      } else if (error instanceof SinPermiso ||
        (error as { response?: { status?: number } })?.response?.status === 403) {
        setState({
          status: "error",
          endpoint,
          message: error instanceof SinPermiso ? error.message : "No se pudo completar la operación.",
          forbidden: true,
          prerequisite: error instanceof InsumosForbiddenError ? error.prerequisite : null,
        });
      } else {
        setUncertain(true);
      }
    } finally {
      if (active.current && generation.current === requestGeneration) setPending(false);
    }
  };

  const cancel = (event: React.MouseEvent<HTMLAnchorElement>) => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (pending) return;
    onCancel();
  };
  const feedback = (field: string) => errors[field]?.length ? { "aria-invalid": true as const, "aria-describedby": `error_${field}` } : {};
  const fieldErrors = (field: string) => errors[field]?.length ? <div id={`error_${field}`} className="invalid-feedback d-block">{errors[field].map((message, index) => <div key={index}>{field === "__all__" ? message : <strong>{message}</strong>}</div>)}</div> : null;
  const inputClass = (field: string, base: string) => `${base}${errors[field]?.length ? " is-invalid" : ""}`;

  if (state.status === "loading" || state.endpoint !== endpoint) return <div className="container mt-4" role="status">Cargando formulario…</div>;
  if (state.status === "error") return state.forbidden
    ? <InsumosAccessError prerequisite={state.prerequisite} />
    : <div className="container mt-4"><div className="alert alert-danger" role="alert">{state.message}</div><a href={listPath} onClick={cancel}>Volver al listado</a></div>;
  const disabled = pending || uncertain;
  if (isConfirmation(state.metadata)) return (
    <div className="container mt-4"><div className="card">
      <div className="card-header bg-danger text-white"><h5 className="mb-0 fw-semibold">Confirmar eliminación</h5></div>
      <div className="card-body"><p className="mb-3">¿Seguro que desea eliminar el insumo <strong>{state.metadata.titulo}</strong>?</p>
        {uncertain && <div className="alert alert-danger" role="alert">No se pudo confirmar el resultado. Antes de volver a intentarlo, revisá el listado.</div>}
        <form method="post" onSubmit={submit} aria-busy={pending}>
          <button type="submit" className="btn btn-danger" disabled={disabled}>Eliminar</button>{" "}
          <a href={listPath} className="btn btn-secondary" aria-disabled={pending || undefined} onClick={cancel}>Cancelar</a>
        </form>
      </div>
    </div></div>
  );
  const metadata = state.metadata;
  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between mb-3"><h2>{action === "crear" ? "Nuevo insumo" : "Editar insumo"}</h2></div>
      <div className="card"><div className="card-body">
        <form key={endpoint} method="post" encType="multipart/form-data" noValidate onSubmit={submit} aria-busy={pending}>
          {Object.keys(errors).length > 0 && <div className="alert alert-danger" role="alert">No se pudo guardar el formulario. Revisá los campos marcados.{fieldErrors("__all__")}</div>}
          {uncertain && <div className="alert alert-danger" role="alert">No se pudo confirmar el resultado. Antes de volver a intentarlo, revisá el listado.</div>}
          <div className="row">
            <div className="col-md-6"><div id="div_id_programa" className="mb-3">
              <label htmlFor="id_programa" className="form-label requiredField">Programa<span className="asteriskField">*</span></label>
              <select id="id_programa" name="programa" required className={inputClass("programa", "select form-select")} value={values.programa} disabled={disabled} {...feedback("programa")} onChange={(event) => {
                const programa = event.target.value;
                setValues((current) => ({ ...current, programa, categoria: metadata.options.categoria.some((option) => option.value === current.categoria && option.programa_id === programa) ? current.categoria : "" }));
              }}>{metadata.options.programa.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>{fieldErrors("programa")}
            </div></div>
            <div className="col-md-6"><div id="div_id_categoria" className="mb-3">
              <label htmlFor="id_categoria" className="form-label">Categoría</label>
              <select id="id_categoria" name="categoria" className={inputClass("categoria", "categoriaselect form-select")} value={values.categoria} disabled={disabled} {...feedback("categoria")} onChange={(event) => setValues({ ...values, categoria: event.target.value })}>
                {metadata.options.categoria.filter((option) => !option.value || (!!values.programa && option.programa_id === values.programa)).map((option) => <option key={option.value} value={option.value} data-programa={option.programa_id}>{option.label}</option>)}
              </select>{fieldErrors("categoria")}
            </div><small className="text-muted d-block mb-3">Se muestran solo las categorías del programa seleccionado.</small></div>
          </div>
          <div id="div_id_titulo" className="mb-3"><label htmlFor="id_titulo" className="form-label requiredField">Título<span className="asteriskField">*</span></label>
            <input id="id_titulo" name="titulo" type="text" maxLength={200} required className={inputClass("titulo", "textinput form-control")} value={values.titulo} disabled={disabled} {...feedback("titulo")} onChange={(event) => setValues({ ...values, titulo: event.target.value })} />{fieldErrors("titulo")}
          </div>
          <div id="div_id_descripcion" className="mb-3"><label htmlFor="id_descripcion" className="form-label">Descripción</label>
            <textarea id="id_descripcion" name="descripcion" rows={3} className={inputClass("descripcion", "textarea form-control")} value={values.descripcion} disabled={disabled} {...feedback("descripcion")} onChange={(event) => setValues({ ...values, descripcion: event.target.value })} />{fieldErrors("descripcion")}
          </div>
          {metadata.current_file && <p className="mb-1"><i className="fas fa-paperclip" aria-hidden="true" /> Archivo actual: {metadata.current_file.download_url ? <a href={metadata.current_file.download_url}>{metadata.current_file.name}</a> : metadata.current_file.name}</p>}
          <div id="div_id_archivo" className="mb-3"><label htmlFor="id_archivo" className="form-label requiredField">Archivo<span className="asteriskField">*</span></label>
            {metadata.current_file && (
              <div className="input-group mb-2">
                <span className="input-group-text">Actualmente</span>
                <div className="form-control d-flex h-auto">
                  <span className="text-break flex-grow-1">
                    {metadata.current_file.download_url
                      ? <a href={metadata.current_file.download_url}>{metadata.current_file.name}</a>
                      : metadata.current_file.name}
                  </span>
                </div>
              </div>
            )}
            <div>
              <input id="id_archivo" name="archivo" ref={fileInput} type="file" accept={ACCEPT} required={action === "crear"} className={inputClass("archivo", "form-control")} disabled={disabled} {...feedback("archivo")} onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </div>{fieldErrors("archivo")}
          </div>
          <small className="text-muted d-block mb-3">PDF, imágenes, Word, Excel o CSV — máx. 10 MB</small>
          <div className="mb-3"><div id="div_id_activo" className="form-check"><input id="id_activo" name="activo" type="checkbox" role="switch" className={inputClass("activo", "checkboxinput form-check-input toggle-switch")} checked={values.activo} disabled={disabled} {...feedback("activo")} onChange={(event) => setValues({ ...values, activo: event.target.checked })} /><label htmlFor="id_activo" className="form-check-label">Activo</label>{fieldErrors("activo")}</div></div>
          <div className="d-flex justify-content-end gap-2 mt-3"><a href={listPath} className="btn btn-secondary" aria-disabled={pending || undefined} onClick={cancel}>Cancelar</a><button type="submit" className="btn btn-success" disabled={disabled}><i className="fas fa-save" aria-hidden="true" /> Guardar insumo</button></div>
        </form>
      </div></div>
    </div>
  );
}
