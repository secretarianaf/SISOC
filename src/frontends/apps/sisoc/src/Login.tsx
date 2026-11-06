import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { crearCliente, leerCookie, SinPermiso } from "@sisoc/api";

type Errors = Record<string, string[]>;
type Field = { name: string; label: string; required: boolean; max_length: number | null };
type Metadata = { fields: Field[]; initial: { username: string }; errors: Record<string, unknown>; footer_version_label: string };
type Phase = "loading" | "ready" | "redirecting" | "unavailable";
type Props = { navigate?: (destination: string) => void };
const client = crearCliente("/api");
const navigateDocument = (destination: string) => window.location.assign(destination);
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";

function metadata(value: unknown): value is Metadata {
  if (!record(value) || !record(value.initial) || !record(value.errors) || !Array.isArray(value.fields)) return false;
  const fields = value.fields;
  return typeof value.initial.username === "string" && typeof value.footer_version_label === "string" &&
    fields.length === 2 && ["username", "password"].every((name) => fields.some((field: unknown) =>
      record(field) && field.name === name && typeof field.label === "string" && typeof field.required === "boolean" &&
      (field.max_length === null || (Number.isSafeInteger(field.max_length) && Number(field.max_length) > 0))));
}

function approvedRedirect(value: unknown): value is { ok: true; redirect: string } {
  if (!record(value) || value.ok !== true || typeof value.redirect !== "string" || !value.redirect) return false;
  try {
    const destination = new URL(value.redirect, window.location.href);
    return ["http:", "https:"].includes(destination.protocol) && destination.host === window.location.host &&
      !destination.username && !destination.password &&
      (window.location.protocol !== "https:" || destination.protocol === "https:");
  } catch { return false; }
}

function validation(error: unknown): { errors: Errors; username: string } | null {
  const response = (error as { response?: { status?: number; data?: unknown } })?.response;
  if (response?.status !== 400 || !record(response.data) || !record(response.data.errors) ||
    !record(response.data.initial) || typeof response.data.initial.username !== "string") return null;
  const errors: Errors = {};
  for (const [name, entries] of Object.entries(response.data.errors)) {
    if (!Array.isArray(entries) || !entries.length || !entries.every((entry) => record(entry) && typeof entry.message === "string")) return null;
    errors[name] = entries.map((entry) => entry.message as string);
  }
  return Object.keys(errors).length ? { errors, username: response.data.initial.username } : null;
}

export default function Login({ navigate = navigateDocument }: Props) {
  return <LoginPage key={window.location.pathname + window.location.search} navigate={navigate} />;
}

function LoginPage({ navigate }: { navigate: (destination: string) => void }) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [footer, setFooter] = useState("Versiones");
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [rejected, setRejected] = useState(false);
  const mounted = useRef(false);
  const generation = useRef(0);
  const submitting = useRef(false);
  const usernameInput = useRef<HTMLInputElement>(null);

  useLayoutEffect(() => {
    if (!pending && Object.keys(errors).length > 0) usernameInput.current?.focus();
  }, [errors, pending]);

  useLayoutEffect(() => {
    const oldClass = document.body.className;
    const oldTheme = document.documentElement.getAttribute("data-bs-theme");
    const oldTitle = document.title;
    // The isolated shared entry also loads business styles absent from legacy login.
    const legacyStyles = new Set([
      "https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap",
      "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css",
      "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
      "/static/custom/css/main.css", "/static/custom/css/login.css", "/static/custom/css/utils.css",
    ]);
    const otherStyles = [...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')]
      .filter((link) => !legacyStyles.has(link.getAttribute("href") ?? ""))
      .map((link) => ({ link, disabled: link.disabled }));
    for (const { link } of otherStyles) link.disabled = true;
    const root = document.getElementById("root");
    const rootDisplay = root?.style.getPropertyValue("display") ?? "";
    const rootPriority = root?.style.getPropertyPriority("display") ?? "";
    root?.style.setProperty("display", "contents");
    document.body.className = "login-page";
    document.documentElement.setAttribute("data-bs-theme", "dark");
    document.title = "Login";
    return () => {
      document.body.className = oldClass;
      if (oldTheme === null) document.documentElement.removeAttribute("data-bs-theme");
      else document.documentElement.setAttribute("data-bs-theme", oldTheme);
      document.title = oldTitle;
      for (const { link, disabled } of otherStyles) link.disabled = disabled;
      if (rootDisplay) root?.style.setProperty("display", rootDisplay, rootPriority);
      else root?.style.removeProperty("display");
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    mounted.current = true; generation.current += 1; submitting.current = false;
    client.get("web/login/", { signal: controller.signal }).then(({ data }: { data: unknown }) => {
      if (!current) return;
      if (approvedRedirect(data)) { setPhase("redirecting"); navigate(data.redirect); return; }
      if (!metadata(data)) throw new Error("Invalid public login metadata");
      setUsername(data.initial.username); setFooter(data.footer_version_label); setPhase("ready");
    }).catch(() => { if (current) setPhase("unavailable"); });
    return () => { current = false; mounted.current = false; generation.current += 1; controller.abort(); };
  }, [navigate]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (phase !== "ready" || submitting.current || uncertain || rejected) return;
    const requestGeneration = generation.current;
    submitting.current = true; setPending(true); setErrors({});
    const normalizedUsername = username.trim(); setUsername(normalizedUsername);
    const body = new URLSearchParams({ username: normalizedUsername, password });
    const next = new URLSearchParams(window.location.search).get("next");
    if (next !== null) body.set("next", next);
    try {
      const { data } = await client.post("web/login/", body, { headers: { "Content-Type": "application/x-www-form-urlencoded" } });
      if (!mounted.current || requestGeneration !== generation.current) return;
      setPassword("");
      if (!approvedRedirect(data)) throw new Error("Unconfirmed login destination");
      setPhase("redirecting"); navigate(data.redirect);
    } catch (error: unknown) {
      if (!mounted.current || requestGeneration !== generation.current) return;
      setPassword("");
      const invalid = validation(error);
      if (invalid) { setErrors(invalid.errors); setUsername(invalid.username); submitting.current = false; }
      else if (error instanceof SinPermiso || (error as { response?: { status?: number } })?.response?.status === 403) setRejected(true);
      else setUncertain(true);
    } finally {
      if (mounted.current && requestGeneration === generation.current) setPending(false);
    }
  };
  const disabled = pending || uncertain || rejected;
  const generalErrors = errors.__all__ ?? [];
  const fieldErrors = (name: string) => errors[name]?.length ? <div className="invalid-feedback d-block text-start" id={`login-${name}-errors`}>{errors[name].map((message, index) => <div key={index}>{message}</div>)}</div> : null;
  const describedBy = (name: string) => [generalErrors.length ? "login-error" : "", errors[name]?.length ? `login-${name}-errors` : ""].filter(Boolean).join(" ") || undefined;

  return <>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossOrigin="anonymous" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" />
    <link rel="stylesheet" href="/static/custom/css/main.css" /><link rel="stylesheet" href="/static/custom/css/login.css" /><link rel="stylesheet" href="/static/custom/css/utils.css" />
    <header className="main-header"><nav className="navbar d-flex flex-wrap align-items-center justify-content-between gap-2"><div className="d-flex align-items-center gap-2">
      <button className="btn btn-link d-inline-flex d-lg-none p-0 text-white" type="button" data-lte-toggle="sidebar" aria-label="Abrir menu"><i className="bi bi-list fs-2" /></button>
      <a href="/inicio/" className="brand-link d-flex align-items-center"><span className="brand-text fw-light"><img src="/static/custom/img/logoBlanco.png" alt="SISOC" className="brand-image" style={{ height: 40 }} /></span></a>
    </div><ul className="nav-links mb-0 d-flex align-items-center flex-wrap"><li className="nav-item circle-btn"><form method="post" action="/logout/" className="d-inline"><input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} /><button type="submit" className="nav-link nav-link-rounded border-0 bg-transparent" aria-label="Cerrar sesión"><img src="/static/custom/img/iconos_navbar/exit.svg" alt="Salir" /></button></form></li></ul></nav></header>
    <div className="login-container"><div className="container"><div className="row login-row align-items-center"><div className="col-lg-9 col-12 mx-auto"><div className="row align-items-center">
      <div className="col-md-5 col-12"><div className="card"><div className="card-body text-center">
        <img src="/static/custom/img/presidencia_logo.svg" className="mb-2 presidencia-logo" alt="" />{" "}<img src="/static/custom/img/sisoc_azul.png" alt="" className="img-fluid sisoc-logo" />
        <p className="mt-3 mb-3">Ingresa al Sistema con Usuario y Contraseña</p>
        {phase === "loading" && <div role="status">Cargando acceso…</div>}
        {phase === "unavailable" && <div className="alert alert-danger text-start" role="alert">No se pudo cargar el inicio de sesión. Vuelva a cargar la página para intentarlo nuevamente.</div>}
        {phase === "ready" && <form method="post" id="form-login" className="mb-3" onSubmit={submit} aria-busy={pending}>
          {generalErrors.length > 0 && <div id="login-error" className="alert alert-danger text-start" role="alert">{generalErrors.map((message, index) => <div key={index}>{message}</div>)}</div>}
          {uncertain && <div className="alert alert-danger text-start" role="alert">No se pudo confirmar el inicio de sesión. Vuelva a cargar la página para comprobar el estado antes de intentarlo nuevamente.</div>}
          {rejected && <div className="alert alert-danger text-start" role="alert">La solicitud fue rechazada. Vuelva a cargar la página para comprobar el acceso antes de intentarlo nuevamente.</div>}
          <div className="mb-3"><div className="input-group"><span className="input-group-text"><div className="icon-box"><i className="bi bi-person" /></div></span>
            <input ref={usernameInput} id="id_username" name="username" type="text" className={`form-control${errors.username?.length ? " is-invalid" : ""}`} placeholder="Usuario" autoFocus aria-label="Username" aria-describedby={describedBy("username")} value={username} required disabled={disabled} onChange={(event) => setUsername(event.target.value)} />
          </div>{fieldErrors("username")}</div>
          <div className="mb-3"><div className="input-group"><span className="input-group-text"><div className="icon-box"><i className="bi bi-key" /></div></span>
            <input id="id_password" name="password" type="password" className={`form-control${errors.password?.length ? " is-invalid" : ""}`} placeholder="Contraseña" aria-label="Password" aria-describedby={describedBy("password")} value={password} required disabled={disabled} onChange={(event) => setPassword(event.target.value)} />
          </div>{fieldErrors("password")}</div>
          <button id="login-submit-button" className="btn btn-primary btn-block fw-bold" type="submit" disabled={disabled}><span id="login-submit-spinner" className={`spinner-border spinner-border-sm me-2${pending ? "" : " d-none"}`} role="status" aria-hidden="true" /><span id="login-submit-text">{pending ? "Ingresando" : "Ingresar"}</span></button>
          <div className="mt-3"><a href="/password_reset/">¿Olvidaste tu contraseña? Restablecela aquí.</a></div>
        </form>}
      </div></div></div>
      <div className="col-md-7 d-none d-md-block"><img src="/static/custom/img/loginPresentacion.svg" alt="logoPresentacion" className="img-fluid" /></div>
    </div></div></div></div></div>
    <footer className="app-footer"><div className="footer-content"><img src="/static/custom/img/Presidencia_footer.svg" alt="Presidencia Logo" className="footer-logo img-fluid" /><a href="/novedades/" className="footer-secondary-link" aria-label={footer}><i className="bi bi-clock-fill" /><span>{footer}</span></a></div></footer>
  </>;
}
