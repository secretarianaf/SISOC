import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { crearCliente } from "@sisoc/api";
import InsumosAccessError from "./InsumosAccessError";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "./webAccess";

type NavigationNode = { id: string; label: string; href: string | null; children: NavigationNode[] };
export type RequiredPasswordPresentation = {
  user: { username: string; display_name: string; avatar_initial: string; role_label: string };
  footer_version_label: string;
  legacy_frame_navigation: NavigationNode[];
};
type PasswordName = "new_password1" | "new_password2";
type Field = { name: PasswordName; label: string; help_text: string; required: boolean };
type Metadata = {
  access: { state: "password_change_required"; required_action_url: string };
  fields: Field[];
  presentation: RequiredPasswordPresentation;
};
type Errors = Partial<Record<PasswordName | "__all__", string[]>>;
type State =
  | { status: "loading" }
  | { status: "error" }
  | { status: "redirect" }
  | { status: "forbidden"; prerequisite: WebPrerequisite | null }
  | { status: "ready"; metadata: Metadata };
type Props = {
  renderFrame?: (content: ReactNode, presentation: RequiredPasswordPresentation) => ReactNode;
};

const client = crearCliente("/api");
const endpoint = "web/password/first-change/";
const names: PasswordName[] = ["new_password1", "new_password2"];
const notice = "Contraseña actualizada correctamente.";
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";
const acceptedStatus = (status: number) => (status >= 200 && status < 300) || status === 403;

function navigationNode(value: unknown): value is NavigationNode {
  return record(value) && typeof value.id === "string" && typeof value.label === "string" &&
    (value.href === null || safeInternalPath(value.href) !== null) &&
    Array.isArray(value.children) && value.children.every(navigationNode);
}

function metadataResponse(value: unknown): value is Metadata {
  if (!record(value) || !record(value.access) || value.access.state !== "password_change_required" ||
    value.access.required_action_url !== "/password/first-change/" || !Array.isArray(value.fields) || value.fields.length !== 2 ||
    !record(value.presentation) || !record(value.presentation.user)) return false;
  const presentation = value.presentation;
  const user = presentation.user as Record<string, unknown>;
  return value.fields.every((field, index) => record(field) && field.name === names[index] &&
    typeof field.label === "string" && typeof field.help_text === "string" && typeof field.required === "boolean") &&
    ["username", "display_name", "avatar_initial", "role_label"].every((name) => typeof user[name] === "string") &&
    typeof presentation.footer_version_label === "string" && Array.isArray(presentation.legacy_frame_navigation) &&
    presentation.legacy_frame_navigation.every(navigationNode);
}

function completedResponse(value: unknown): boolean {
  return record(value) && value.ok === true && safeInternalPath(value.redirect) === "/inicio/" &&
    (value.message === undefined || value.message === notice);
}

function fieldErrors(error: unknown): Errors | null {
  const response = (error as { response?: { status?: number; data?: unknown } })?.response;
  if (response?.status !== 400 || !record(response.data) || !record(response.data.errors)) return null;
  const result: Errors = {};
  for (const [name, messages] of Object.entries(response.data.errors)) {
    if (![...names, "__all__"].includes(name) || !Array.isArray(messages) ||
      !messages.every((entry) => record(entry) && typeof entry.message === "string")) return null;
    result[name as keyof Errors] = messages.map((entry) => entry.message as string);
  }
  return Object.keys(result).length ? result : null;
}

function Help({ text, id }: { text: string; id: string }) {
  if (!text) return null;
  // The only HTML source is SetPasswordForm help. Render its list as React text,
  // never execute arbitrary markup returned by a failed or substituted response.
  const body = new DOMParser().parseFromString(text, "text/html").body;
  const list = body.children.length === 1 && body.firstElementChild?.tagName === "UL"
    ? Array.from(body.firstElementChild.children).map((item) => item.textContent ?? "") : null;
  return <div id={id} className="form-text">{list ? <ul>{list.map((item, index) => <li key={index}>{item}</li>)}</ul> : body.textContent}</div>;
}

export default function RequiredPasswordChange({ renderFrame }: Props) {
  const [state, setState] = useState<State>({ status: "loading" });
  const [values, setValues] = useState({ new_password1: "", new_password2: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const active = useRef(false);
  const generation = useRef(0);
  const submitting = useRef(false);
  const clearPasswords = () => setValues({ new_password1: "", new_password2: "" });

  useEffect(() => {
    const previous = document.title;
    document.title = "SISOC - Cambio obligatorio de contraseña";
    return () => { if (document.title === "SISOC - Cambio obligatorio de contraseña") document.title = previous; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    active.current = true;
    const current = ++generation.current;
    client.get(endpoint, { signal: controller.signal, validateStatus: acceptedStatus }).then(({ data, status }: { data: unknown; status?: number }) => {
      if (!active.current || current !== generation.current) return;
      if (status === 403) {
        setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) });
      } else if (completedResponse(data)) {
        setState({ status: "redirect" });
        window.location.assign("/inicio/");
      } else if (metadataResponse(data)) {
        setState({ status: "ready", metadata: data });
      } else {
        setState({ status: "error" });
      }
    }).catch(() => {
      if (active.current && current === generation.current) setState({ status: "error" });
    });
    return () => { active.current = false; generation.current += 1; controller.abort(); };
  }, []);

  useLayoutEffect(() => {
    if (Object.keys(errors).length) window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [errors]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state.status !== "ready" || submitting.current || uncertain) return;
    const current = generation.current;
    submitting.current = true;
    setPending(true);
    setErrors({});
    try {
      const { data, status } = await client.post(endpoint, new URLSearchParams(values), { validateStatus: acceptedStatus });
      if (!active.current || current !== generation.current) return;
      clearPasswords();
      if (status === 403) {
        setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) });
      } else if (completedResponse(data)) {
        setState({ status: "redirect" });
        window.location.assign("/inicio/");
      } else {
        setUncertain(true);
      }
    } catch (error: unknown) {
      if (!active.current || current !== generation.current) return;
      clearPasswords();
      const validation = fieldErrors(error);
      if (validation) {
        setErrors(validation);
        submitting.current = false;
      } else {
        setUncertain(true);
      }
    } finally {
      if (active.current && current === generation.current) setPending(false);
    }
  }

  if (state.status === "loading" || state.status === "redirect") return <main role="status">{state.status === "loading" ? "Cargando formulario…" : "Continuando en SISOC…"}</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  if (state.status === "error") return <main role="alert">No se pudo cargar el formulario.</main>;

  const disabled = pending || uncertain;
  const content = <div className="row justify-content-center"><div className="col-md-6"><div className="card shadow-sm">
    <div className="card-header"><h5 className="mb-0">Debes actualizar tu contraseña</h5></div>
    <div className="card-body">
      <p className="text-muted">Por seguridad, este usuario tiene configurado cambio obligatorio de contraseña.</p>
      {uncertain && <div className="alert alert-danger" role="alert">No se pudo confirmar el resultado. Revise el estado antes de volver a intentarlo. <a href="/inicio/">Revisar el estado</a></div>}
      {errors.__all__ && <div className="alert alert-danger" role="alert">{errors.__all__.map((message, index) => <p key={index}>{message}</p>)}</div>}
      <form method="post" noValidate onSubmit={submit}>
        {state.metadata.fields.map((field) => {
          const messages = errors[field.name] ?? [];
          const helpId = `hint_id_${field.name}`;
          return <div id={`div_id_${field.name}`} className="mb-3" key={field.name}>
            <label htmlFor={`id_${field.name}`} className="form-label requiredField">{field.label}{field.required && <span className="asteriskField">*</span>}</label>
            <input id={`id_${field.name}`} name={field.name} type="password" autoComplete="new-password" required={field.required}
              className={`passwordinput form-control${messages.length ? " is-invalid" : ""}`} disabled={disabled}
              aria-invalid={messages.length ? true : undefined} aria-describedby={field.help_text ? helpId : undefined}
              value={values[field.name]} onChange={(event) => setValues({ ...values, [field.name]: event.target.value })} />
            {messages.map((message, index) => <p id={`error_${index + 1}_id_${field.name}`} className="invalid-feedback" key={index}><strong>{message}</strong></p>)}
            <Help text={field.help_text} id={helpId} />
          </div>;
        })}
        <button className="btn btn-primary" type="submit" disabled={disabled}>Guardar contraseña</button>
      </form>
    </div>
  </div></div></div>;
  return renderFrame ? renderFrame(content, state.metadata.presentation) : <main><h3>Actualizar contraseña</h3>{content}</main>;
}
