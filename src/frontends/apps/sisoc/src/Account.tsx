import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { crearCliente } from "@sisoc/api";
import InsumosAccessError from "./InsumosAccessError";
import { InsumosToastList } from "./InsumosToast";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "./webAccess";
import type { RequiredPasswordPresentation } from "./RequiredPasswordChange";

type Mode = "account" | "confirm";
type Name = "first_name" | "last_name" | "email" | "dni" | "cuil" | "correo_institucional";
type Values = Record<Name, string>;
type Field = { name: Name; label: string; help_text: string; required: boolean; max_length: number | null; input_type: "text" | "email" };
type Notice = { message: string; level: "success" | "error" | "warning" | "info" };
type Metadata = { messages?: Notice[]; fields: Field[]; initial: Values; errors: Record<string, { message: string; code: string }[]>; presentation: RequiredPasswordPresentation };
type Errors = Partial<Record<Name | "__all__", string[]>>;
type Props = { mode?: Mode; renderFrame?: (content: ReactNode, presentation: RequiredPasswordPresentation, overlays?: ReactNode) => ReactNode; navigate?: (destination: string) => void };
type State = { status: "loading" } | { status: "error" } | { status: "redirect" } | { status: "forbidden"; prerequisite: WebPrerequisite | null } | { status: "ready"; metadata: Metadata; revision?: number };
const names: Name[] = ["first_name", "last_name", "email", "dni", "cuil", "correo_institucional"];
const client = crearCliente("/api");
const notice = "Datos personales actualizados correctamente.";
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";
const acceptedStatus = (status: number) => status >= 200 && status < 300 || status === 403;

function metadata(value: unknown): value is Metadata {
  if (!record(value) || !Array.isArray(value.fields) || value.fields.length !== names.length || !record(value.initial) || !record(value.errors) || !record(value.presentation)) return false;
  const initial = value.initial; const fields = value.fields; const frame = value.presentation;
  const node = (v: unknown): boolean => record(v) && typeof v.id === "string" && typeof v.label === "string" && (v.href === null || safeInternalPath(v.href) !== null) && Array.isArray(v.children) && v.children.every(node);
  return (value.messages === undefined || Array.isArray(value.messages) && value.messages.every(v => record(v) && typeof v.message === "string" && ["success", "error", "warning", "info"].includes(v.level as string))) && names.every((name, i) => typeof initial[name] === "string" && record(fields[i]) && fields[i].name === name && typeof fields[i].label === "string" && typeof fields[i].required === "boolean" && typeof fields[i].help_text === "string" && ["text", "email"].includes(fields[i].input_type as string)) &&
    record(frame.user) && ["username", "display_name", "avatar_initial", "role_label"].every(key => typeof (frame.user as Record<string, unknown>)[key] === "string") && typeof frame.footer_version_label === "string" && Array.isArray(frame.legacy_frame_navigation) && frame.legacy_frame_navigation.every(node);
}
function errorsFrom(value: unknown): Errors | null {
  if (!record(value)) return null;
  const result: Errors = {};
  for (const [name, entries] of Object.entries(value)) {
    if (![...names, "__all__"].includes(name) || !Array.isArray(entries) || !entries.every(entry => record(entry) && typeof entry.message === "string")) return null;
    result[name as keyof Errors] = entries.map(entry => entry.message as string);
  }
  return result;
}

export default function Account({ mode = "account", ...props }: Props) {
  return <AccountPage key={mode} mode={mode} {...props} />;
}
function AccountPage({ mode = "account", renderFrame, navigate }: Props) {
  const [state, setState] = useState<State>({ status: "loading" });
  const active = useRef(false); const generation = useRef(0);
  const endpoint = mode === "confirm" ? "web/account/confirm/" : "web/account/";
  const destination = mode === "confirm" ? "/inicio/" : "/mi-cuenta/";
  const revision = state.status === "ready" ? state.revision ?? 0 : 0;
  useLayoutEffect(() => {
    // Native successful POST reloads this canonical page at the document top.
    if (revision > 0) window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [revision]);
  useEffect(() => {
    const previous = document.title; const title = mode === "confirm" ? "SISOC - Confirma tus datos personales" : "SISOC - Mi cuenta";
    document.title = title; return () => { if (document.title === title) document.title = previous; };
  }, [mode]);
  useEffect(() => {
    const controller = new AbortController(); active.current = true; const current = ++generation.current;
    client.get(endpoint, { signal: controller.signal, validateStatus: acceptedStatus }).then(({ data, status }: { data: unknown; status?: number }) => {
      if (!active.current || current !== generation.current) return;
      if (status === 403) setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) });
      else if (record(data) && data.ok === true && safeInternalPath(data.redirect) === destination) { setState({ status: "redirect" }); (navigate ?? window.location.assign.bind(window.location))(destination); }
      else if (metadata(data)) setState({ status: "ready", metadata: data });
      else setState({ status: "error" });
    }).catch(() => { if (active.current && current === generation.current) setState({ status: "error" }); });
    return () => { active.current = false; generation.current += 1; controller.abort(); };
  }, [endpoint, destination, navigate]);
  async function completed() {
    if (navigate || mode === "confirm") { (navigate ?? window.location.assign.bind(window.location))(destination); return; }
    const current = generation.current;
    const { data } = await client.get(endpoint);
    if (active.current && current === generation.current) {
      if (!metadata(data)) throw new Error("Invalid own-account refresh");
      window.history.replaceState(null, "", destination);
      setState(previous => ({ status: "ready", metadata: data, revision: previous.status === "ready" ? (previous.revision ?? 0) + 1 : 1 }));
    }
  }
  if (state.status === "loading" || state.status === "redirect") return <main role="status">{state.status === "loading" ? "Cargando formulario…" : "Continuando en SISOC…"}</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar el formulario.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  const accountForm = (
    <AccountForm
      key={state.revision ?? 0} mode={mode} metadata={state.metadata}
      endpoint={endpoint} destination={destination} completed={completed}
      invalid={metadata => setState(previous => previous.status === "ready" ? { ...previous, metadata } : previous)}
      forbidden={data => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) })}
    />
  );
  const notices = <InsumosToastList key={state.revision ?? 0} messages={state.metadata.messages ?? []} />;
  const content = mode === "confirm" ? (
    <div className="row poncho-form"><div className="col-12">
      <p className="text-muted">Para continuar usando SISOC necesitamos que confirmes o corrijas tus datos personales.</p>
    </div></div>
  ) : <>
    {notices}
    <div className="row justify-content-center poncho-form"><div className="col-lg-8">
      <div className="card shadow-sm"><div className="card-body">{accountForm}</div></div>
    </div></div>
  </>;
  const overlays = mode === "confirm" ? <>
    {notices}
    <div className="modal-backdrop show" />
    <div className="modal show d-block" id="modal-confirmar-datos" tabIndex={-1}
      role="dialog" aria-modal="true" aria-labelledby="modal-confirmar-datos-titulo">
      <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable modal-lg" role="document">
        <div className="modal-content poncho-form">
          <div className="modal-header"><h4 className="modal-title" id="modal-confirmar-datos-titulo">Confirma tus datos personales</h4></div>
          {accountForm}
        </div>
      </div>
    </div>
  </> : undefined;
  return <>
    <link rel="stylesheet" href="/static/custom/css/poncho_formularios.css" />
    {renderFrame ? renderFrame(content, state.metadata.presentation, overlays) : (
      <main><h3>{mode === "confirm" ? "Confirma tus datos personales" : "Mi cuenta"}</h3>{content}{overlays}</main>
    )}
  </>;
}

function AccountForm({ mode, metadata: data, endpoint, destination, completed, forbidden, invalid }: { mode: Mode; metadata: Metadata; endpoint: string; destination: string; completed: () => Promise<void>; invalid: (metadata: Metadata) => void; forbidden: (data: unknown) => void }) {
  const [values, setValues] = useState(data.initial); const [errors, setErrors] = useState<Errors>({});
  const [pending, setPending] = useState(false); const [uncertain, setUncertain] = useState(false); const [complete, setComplete] = useState(false);
  const form = useRef<HTMLFormElement>(null); const active = useRef(false); const submitting = useRef(false); const generation = useRef(0);
  useLayoutEffect(() => { active.current = true; generation.current += 1; const id = requestAnimationFrame(() => setComplete(form.current?.checkValidity() ?? false)); return () => { active.current = false; generation.current += 1; cancelAnimationFrame(id); }; }, []);
  useLayoutEffect(() => {
    if (!Object.keys(errors).length) return;
    // Reset after error markup commits, as a fresh native modal document does.
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    const modalBody = form.current?.querySelector<HTMLElement>(".modal-body");
    if (modalBody) { modalBody.scrollTop = 0; modalBody.scrollLeft = 0; }
  }, [errors]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (submitting.current || uncertain) return;
    submitting.current = true; setPending(true); setErrors({}); const current = generation.current;
    try {
      const { data: result, status } = await client.post(endpoint, new URLSearchParams(values), { validateStatus: acceptedStatus });
      if (!active.current || current !== generation.current) return;
      if (status === 403) forbidden(result);
      else if (record(result) && result.ok === true && safeInternalPath(result.redirect) === destination && result.message === notice) await completed();
      else setUncertain(true);
    } catch (error: unknown) {
      if (!active.current || current !== generation.current) return;
      const response = (error as { response?: { status?: number; data?: unknown } })?.response;
      const result = response?.data; const validation = record(result) ? errorsFrom(result.errors) : null;
      if (response?.status === 400 && validation && Object.keys(validation).length && metadata(result)) { setErrors(validation); setValues(result.initial); invalid(result); submitting.current = false; }
      else setUncertain(true);
    } finally { if (active.current && current === generation.current) setPending(false); }
  }
  function field(name: Name) {
    const descriptor = data.fields.find(item => item.name === name)!;
    const messages = errors[name] ?? [];
    const helpId = `hint_id_${name}`;
    return (
      <div className="col-md-6" key={name}>
        <div id={`div_id_${name}`} className="mb-3">
          <label htmlFor={`id_${name}`} className={`form-label${descriptor.required ? " requiredField" : ""}`}>
            {descriptor.label}{descriptor.required && <span className="asteriskField">*</span>}
          </label>
          <input
            id={`id_${name}`} name={name} type={descriptor.input_type}
            required={descriptor.required} maxLength={descriptor.max_length ?? undefined}
            className={`${descriptor.input_type === "email" ? "emailinput" : "textinput"} form-control${messages.length ? " is-invalid" : ""}`}
            value={values[name]} disabled={pending || uncertain}
            aria-describedby={descriptor.help_text ? helpId : undefined}
            onChange={event => setValues({ ...values, [name]: event.target.value })}
          />
          {messages.map((message, index) => (
            <p id={`error_${index + 1}_id_${name}`} className="invalid-feedback" key={index}>
              <strong>{message}</strong>
            </p>
          ))}
          {descriptor.help_text && <div id={helpId} className="form-text">{descriptor.help_text}</div>}
        </div>
      </div>
    );
  }
  const fields = (
    <div data-mi-cuenta-form>
      {errors.__all__ && <div className="alert alert-danger" role="alert">
        {errors.__all__.map((message, index) => <div key={index}>{message}</div>)}
      </div>}
      <h6 className="text-uppercase text-muted mb-3">Datos personales</h6>
      <div className="row">{field("first_name")}{field("last_name")}</div>
      <div className="row">{field("dni")}{field("cuil")}</div>
      <hr />
      <h6 className="text-uppercase text-muted mb-3">Contacto</h6>
      <div className="row">{field("email")}{field("correo_institucional")}</div>
    </div>
  );
  const button = (
    <button className="poncho-btn poncho-btn--cta" type="submit" data-mi-cuenta-submit disabled={pending || uncertain || !complete}>
      Guardar datos
    </button>
  );
  return (
    <form
      method="post" action={mode === "confirm" ? "/mi-cuenta/confirmar/" : undefined} noValidate
      ref={form} onSubmit={submit}
      onInput={event => setComplete(event.currentTarget.checkValidity())}
      onChange={event => setComplete(event.currentTarget.checkValidity())}
    >
      {uncertain && <div className="alert alert-danger" role="alert">
        No se pudo confirmar el resultado. Revise el estado antes de volver a intentarlo.{" "}
        <a href={mode === "confirm" ? "/mi-cuenta/confirmar/" : "/mi-cuenta/"}>Revisar el estado</a>
      </div>}
      {mode === "confirm" ? <>
        <div className="modal-body">
          <p className="text-muted">Como parte del proceso de actualización de datos, te solicitamos que revises tu información personal y completes los campos pendientes o desactualizados.</p>
          <p className="text-muted small">Vas a poder modificar estos datos luego desde <strong>Mi cuenta</strong>.</p>
          {fields}
        </div>
        <div className="modal-footer justify-content-end">{button}</div>
      </> : <>{fields}{button}</>}
    </form>
  );
}
