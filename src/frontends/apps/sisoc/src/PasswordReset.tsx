import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { crearCliente, leerCookie, SinPermiso } from "@sisoc/api";
import { safeInternalPath } from "./webAccess";

type Mode = "request" | "done" | "confirm" | "complete";
type Name = "username" | "email" | "new_password1" | "new_password2";
type Field = { name: Name; label: string; required: boolean; type?: string; help_text?: string; attrs: Record<string, string> };
type Errors = Partial<Record<Name, string[]>>;
type Props = {
  mode: Mode;
  /** Only the `set-password` path carries a uid; the reset token never reaches React requests. */
  uidb64?: string | null;
  navigate?: (destination: string) => void;
};
type Phase = "loading" | "ready" | "invalid" | "redirecting" | "unavailable";

const client = crearCliente("/api");
const REQUEST = "web/password/reset/";
const navigateDocument = (destination: string) => window.location.assign(destination);
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";
const TITLES: Record<Mode, string> = {
  request: "Recuperar contraseña",
  done: "Correo enviado",
  confirm: "Restablecer contraseña",
  complete: "Contraseña actualizada",
};
const FIELDS: Record<"request" | "confirm", Name[]> = {
  request: ["username", "email"],
  confirm: ["new_password1", "new_password2"],
};
// Exactly the stylesheets of user/password_reset_base.html.
const LEGACY_STYLES = [
  "https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap",
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css",
  "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
  "/static/custom/css/main.css", "/static/custom/css/login.css",
  "/static/custom/css/password_reset.css", "/static/custom/css/utils.css",
];

function fields(value: unknown, names: Name[]): value is Field[] {
  return Array.isArray(value) && value.length === names.length && value.every((field, index) =>
    record(field) && field.name === names[index] && typeof field.label === "string" && typeof field.required === "boolean" &&
    record(field.attrs) && field.attrs.id === `id_${names[index]}` &&
    Object.values(field.attrs).every((attr) => typeof attr === "string") &&
    (field.type === undefined || ["text", "email"].includes(field.type as string)) &&
    (field.help_text === undefined || typeof field.help_text === "string"));
}

function validation(error: unknown, names: Name[]): Errors | null {
  const response = (error as { response?: { status?: number; data?: unknown } })?.response;
  if (response?.status !== 400 || !record(response.data) || !record(response.data.errors)) return null;
  const errors: Errors = {};
  for (const [name, entries] of Object.entries(response.data.errors)) {
    if (!names.includes(name as Name) || !Array.isArray(entries) || !entries.length ||
      !entries.every((entry) => record(entry) && typeof entry.message === "string")) return null;
    errors[name as Name] = entries.map((entry) => entry.message as string);
  }
  return Object.keys(errors).length ? errors : null;
}

function Help({ id, text }: { id: string; text: string }) {
  // Only the source validator help is accepted; render text/list nodes, never remote HTML.
  const body = new DOMParser().parseFromString(text, "text/html").body;
  const list = body.children.length === 1 && body.firstElementChild?.tagName === "UL"
    ? [...body.firstElementChild.children].map((item) => item.textContent ?? "") : null;
  return <div id={id} className="form-text">{list ? <ul>{list.map((item, index) => <li key={index}>{item}</li>)}</ul> : body.textContent}</div>;
}

function CrispyField({ field, value, messages, disabled, onChange }: {
  field: Field; value: string; messages: string[]; disabled: boolean; onChange: (value: string) => void;
}) {
  const type = field.type ?? "password";
  const helpId = field.help_text ? `${field.attrs.id}_helptext` : "";
  const errorId = messages.length ? `${field.attrs.id}_error` : "";
  const describedBy = [helpId, errorId].filter(Boolean).join(" ") || undefined;
  return <div id={`div_${field.attrs.id}`} className="mb-3">
    <label htmlFor={field.attrs.id} className={`form-label${field.required ? " requiredField" : ""}`}>
      {field.label}{field.required && <span className="asteriskField">*</span>}
    </label>
    <input type={type} name={field.name} maxLength={field.attrs.maxlength ? Number(field.attrs.maxlength) : undefined}
      autoComplete={field.attrs.autocomplete} className={`${type}input form-control${messages.length ? " is-invalid" : ""}`}
      required={field.required} aria-invalid={messages.length ? true : undefined} aria-describedby={describedBy}
      id={field.attrs.id} value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} />
    {!!messages.length && <div id={errorId} className="invalid-feedback">
      {messages.map((message, index) => <p key={index} id={`error_${index + 1}_${field.attrs.id}`}><strong>{message}</strong></p>)}
    </div>}
    {field.help_text && <Help id={helpId} text={field.help_text} />}
  </div>;
}

export default function PasswordReset({ mode, uidb64 = null, navigate = navigateDocument }: Props) {
  return <PasswordResetPage key={`${mode}:${uidb64 ?? ""}`} mode={mode} uidb64={uidb64} navigate={navigate} />;
}

function PasswordResetPage({ mode, uidb64, navigate }: Required<Props>) {
  const form = mode === "request" || mode === "confirm" ? mode : null;
  const names = form ? FIELDS[form] : [];
  const confirmEndpoint = uidb64 ? `${REQUEST}${encodeURIComponent(uidb64)}/` : null;
  // A token path that reached the page is the source invalid-link state: never send it.
  const [phase, setPhase] = useState<Phase>(!form ? "ready" : form === "confirm" && !confirmEndpoint ? "invalid" : "loading");
  const [schema, setSchema] = useState<Field[]>([]);
  const [values, setValues] = useState<Partial<Record<Name, string>>>({});
  const [errors, setErrors] = useState<Errors>({});
  const [footer, setFooter] = useState("Versiones");
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [rejected, setRejected] = useState(false);
  const mounted = useRef(false);
  const submitting = useRef(false);

  useLayoutEffect(() => {
    const oldClass = document.body.className;
    const oldTheme = document.documentElement.getAttribute("data-bs-theme");
    const oldTitle = document.title;
    const otherStyles = [...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')]
      .filter((link) => !LEGACY_STYLES.includes(link.getAttribute("href") ?? ""))
      .map((link) => ({ link, disabled: link.disabled }));
    for (const { link } of otherStyles) link.disabled = true;
    const root = document.getElementById("root");
    const rootDisplay = root?.style.getPropertyValue("display") ?? "";
    const rootPriority = root?.style.getPropertyPriority("display") ?? "";
    root?.style.setProperty("display", "contents");
    document.body.className = "password-reset-page";
    document.documentElement.setAttribute("data-bs-theme", "dark");
    document.title = TITLES[mode];
    return () => {
      document.body.className = oldClass;
      if (oldTheme === null) document.documentElement.removeAttribute("data-bs-theme");
      else document.documentElement.setAttribute("data-bs-theme", oldTheme);
      document.title = oldTitle;
      for (const { link, disabled } of otherStyles) link.disabled = disabled;
      if (rootDisplay) root?.style.setProperty("display", rootDisplay, rootPriority);
      else root?.style.removeProperty("display");
    };
  }, [mode]);

  useEffect(() => {
    const controller = new AbortController();
    mounted.current = true;
    // The public request metadata also carries the footer label of every recovery page.
    const metadata = client.get(REQUEST, { signal: controller.signal }).then(({ data }: { data: unknown }) => {
      if (!record(data) || typeof data.footer_version_label !== "string") throw new Error("Invalid recovery metadata");
      if (mounted.current) setFooter(data.footer_version_label);
      return data;
    });
    metadata.catch(() => undefined);
    let load: Promise<unknown> | null = null;
    if (mode === "request") {
      load = metadata.then((data) => {
        if (!fields(data.fields, names)) throw new Error("Invalid recovery form");
        if (mounted.current) { setSchema(data.fields); setPhase("ready"); }
      });
    } else if (mode === "confirm" && confirmEndpoint) {
      load = client.get(confirmEndpoint, { signal: controller.signal }).then(({ data }: { data: unknown }) => {
        if (!mounted.current) return;
        if (record(data) && data.validlink === false) { setPhase("invalid"); return; }
        if (!record(data) || data.validlink !== true || !fields(data.fields, names)) throw new Error("Invalid confirmation");
        setSchema(data.fields); setPhase("ready");
      });
    }
    load?.catch(() => { if (mounted.current) setPhase("unavailable"); });
    return () => { mounted.current = false; controller.abort(); };
    // names derives from mode only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, confirmEndpoint]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form || phase !== "ready" || submitting.current || uncertain || rejected) return;
    const endpoint = form === "request" ? REQUEST : confirmEndpoint;
    if (!endpoint) return;
    const expected = form === "request" ? "/password_reset/done/" : "/reset/done/";
    submitting.current = true; setPending(true); setErrors({});
    const body = new URLSearchParams(names.map((name) => [name, values[name] ?? ""]));
    const clearPasswords = () => { if (form === "confirm") setValues({}); };
    try {
      const { data } = await client.post(endpoint, body, { headers: { "Content-Type": "application/x-www-form-urlencoded" } });
      if (!mounted.current) return;
      clearPasswords();
      if (form === "confirm" && record(data) && data.validlink === false) { setPhase("invalid"); return; }
      if (!record(data) || data.ok !== true || safeInternalPath(data.redirect) !== expected) throw new Error("Unconfirmed recovery result");
      setPhase("redirecting"); navigate(expected);
    } catch (error: unknown) {
      if (!mounted.current) return;
      clearPasswords();
      const invalid = validation(error, names);
      if (invalid) { setErrors(invalid); submitting.current = false; }
      else if (error instanceof SinPermiso || (error as { response?: { status?: number } })?.response?.status === 403) setRejected(true);
      else setUncertain(true);
    } finally {
      if (mounted.current) setPending(false);
    }
  };

  const disabled = pending || uncertain || rejected;
  const loginButton = <div className="password-reset-actions"><a className="btn password-reset-login-btn" href="/login/">Volver al login</a></div>;
  let content: ReactNode;
  if (mode === "done") content = <>
    <h5 className="mb-3">Solicitud recibida</h5>
    <p className="text-muted mb-3">Si los datos son correctos, recibirás un enlace de recuperación al correo registrado.</p>
    {loginButton}
  </>;
  else if (mode === "complete") content = <>
    <h5 className="mb-3">Contraseña actualizada</h5>
    <p className="text-muted mb-3">Ya puedes ingresar con tu nueva contraseña.</p>
    {loginButton}
  </>;
  else {
    const heading = <h5 className="mb-3">{mode === "request" ? "Recuperar contraseña" : "Restablecer contraseña"}</h5>;
    const intro = mode === "request" && <p className="text-muted mb-3">Ingresá tu usuario y el correo registrado. Ambos deben coincidir con los datos de tu cuenta.</p>;
    if (phase === "invalid") content = <>
      {heading}
      <p className="text-danger mb-3">El enlace no es válido o expiró. Solicita uno nuevo.</p>
      <div className="password-reset-actions"><a className="btn btn-primary" href="/password_reset/">Solicitar nuevo enlace</a></div>
    </>;
    else if (phase === "loading" || phase === "unavailable") content = <>
      {heading}{intro}
      {phase === "loading" ? <div role="status">Cargando formulario…</div>
        : <div className="alert alert-danger text-start" role="alert">No se pudo cargar el formulario. Vuelva a cargar la página para intentarlo nuevamente.</div>}
    </>;
    else content = <>
      {heading}{intro}
      <form method="post" noValidate className="password-reset-form" onSubmit={submit} aria-busy={pending}>
        <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
        {uncertain && <div className="alert alert-danger text-start" role="alert">No se pudo confirmar el resultado. Vuelva a cargar la página para comprobar el estado antes de intentarlo nuevamente.</div>}
        {rejected && <div className="alert alert-danger text-start" role="alert">La solicitud fue rechazada. Vuelva a cargar la página antes de intentarlo nuevamente.</div>}
        {schema.map((field) => <CrispyField key={field.name} field={field} value={values[field.name] ?? ""} messages={errors[field.name] ?? []}
          disabled={disabled} onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))} />)}
        <div className="password-reset-actions">
          <button className="btn btn-primary" type="submit" disabled={disabled}>{mode === "request" ? "Enviar enlace" : "Guardar contraseña"}</button>
          {mode === "request" && <a className="btn password-reset-login-btn" href="/login/">Volver al login</a>}
        </div>
      </form>
    </>;
  }

  return <>
    {LEGACY_STYLES.map((href) => href.includes("bootstrap.min.css")
      ? <link key={href} rel="stylesheet" href={href} integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossOrigin="anonymous" />
      : <link key={href} rel="stylesheet" href={href} />)}
    <header className="main-header"><nav className="navbar d-flex flex-wrap align-items-center justify-content-between gap-2"><div className="d-flex align-items-center gap-2">
      <button className="btn btn-link d-inline-flex d-lg-none p-0 text-white" type="button" data-lte-toggle="sidebar" aria-label="Abrir menu"><i className="bi bi-list fs-2" /></button>
      <a href="/inicio/" className="brand-link d-flex align-items-center"><span className="brand-text fw-light"><img src="/static/custom/img/logoBlanco.png" alt="SISOC" className="brand-image" style={{ height: 40 }} /></span></a>
    </div><ul className="nav-links mb-0 d-flex align-items-center flex-wrap"><li className="nav-item circle-btn"><form method="post" action="/logout/" className="d-inline"><input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} /><button type="submit" className="nav-link nav-link-rounded border-0 bg-transparent" aria-label="Cerrar sesión"><img src="/static/custom/img/iconos_navbar/exit.svg" alt="Salir" /></button></form></li></ul></nav></header>
    <div className="login-container"><div className="container"><div className="row password-reset-row align-items-center"><div className="col-lg-9 col-12 mx-auto"><div className="row align-items-center">
      <div className="col-md-5 col-12"><div className="card"><div className="card-body text-center">
        <img src="/static/custom/img/presidencia_logo.svg" className="mb-2 presidencia-logo" alt="" />{" "}<img src="/static/custom/img/sisoc_azul.png" alt="" className="img-fluid sisoc-logo" />
        <div className="mt-3 password-reset-content">{content}</div>
      </div></div></div>
      <div className="col-md-7 d-none d-md-block"><img src="/static/custom/img/loginPresentacion.svg" alt="logoPresentacion" className="img-fluid" /></div>
    </div></div></div></div></div>
    <footer className="app-footer"><div className="footer-content"><img src="/static/custom/img/Presidencia_footer.svg" alt="Presidencia Logo" className="footer-logo img-fluid" /><a href="/novedades/" className="footer-secondary-link" aria-label={footer}><i className="bi bi-clock-fill" /><span>{footer}</span></a></div></footer>
  </>;
}
