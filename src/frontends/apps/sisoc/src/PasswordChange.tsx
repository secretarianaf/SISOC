import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { crearCliente, leerCookie } from "@sisoc/api";
import { safeInternalPath } from "./webAccess";

type Name = "old_password" | "new_password1" | "new_password2";
type Field = { name: Name; label: string; help_text: string; required: boolean; attrs: { id: string; autocomplete?: string; autofocus?: boolean; "aria-describedby"?: string } };
type Metadata = { title: string; done_title: string; done_text: string; intro_text: string; submit_label: string; fields: Field[] };
type Errors = Partial<Record<Name | "__all__", string[]>>;
type State = { phase: "loading" } | { phase: "unavailable" } | { phase: "blocked" } | { phase: "redirecting" } | { phase: "ready"; metadata: Metadata };
type Props = { mode?: "form" | "done"; navigate?: (destination: string) => void };
const client = crearCliente("/api");
const endpoint = "web/password/change/";
const names: Name[] = ["old_password", "new_password1", "new_password2"];
const empty = (): Record<Name, string> => ({ old_password: "", new_password1: "", new_password2: "" });
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";
const navigateDocument = (path: string) => window.location.assign(path);
const accepted = (status: number) => (status >= 200 && status < 300) || status === 403;
const styles = ["/static/unfold/fonts/inter/styles.css", "/static/unfold/fonts/material-symbols/styles.css", "/static/unfold/css/styles.css", "/static/unfold/css/simplebar/simplebar.css"];

function metadata(value: unknown): value is Metadata {
  if (!record(value) || !Array.isArray(value.fields) || value.fields.length !== 3 ||
    !["title", "done_title", "done_text", "intro_text", "submit_label"].every((key) => typeof value[key] === "string" && !!value[key])) return false;
  return value.fields.every((field, index) => {
    if (!record(field) || field.name !== names[index] || typeof field.label !== "string" || typeof field.help_text !== "string" ||
      typeof field.required !== "boolean" || !record(field.attrs)) return false;
    const attrs = field.attrs;
    return attrs.id === `id_${field.name}` && Object.keys(attrs).every((key) => ["id", "autocomplete", "autofocus", "aria-describedby"].includes(key)) &&
      (attrs.autocomplete === undefined || attrs.autocomplete === (index === 0 ? "current-password" : "new-password")) &&
      (attrs.autofocus === undefined || typeof attrs.autofocus === "boolean") &&
      (attrs["aria-describedby"] === undefined || attrs["aria-describedby"] === `id_${field.name}_helptext`);
  });
}

function errorsFrom(error: unknown): { errors: Errors; note: string } | null {
  const response = (error as { response?: { status?: number; data?: unknown } })?.response;
  if (response?.status !== 400 || !record(response.data) || !record(response.data.errors)) return null;
  const errors: Errors = {};
  for (const [name, entries] of Object.entries(response.data.errors)) {
    if (![...names, "__all__"].includes(name) || !Array.isArray(entries) || !entries.length ||
      !entries.every((entry) => record(entry) && typeof entry.message === "string")) return null;
    errors[name as keyof Errors] = entries.map((entry) => entry.message as string);
  }
  if (!Object.keys(errors).length) return null;
  return { errors, note: typeof response.data.error_note === "string" ? response.data.error_note : "Por favor, corrija el siguiente error." };
}

function Help({ text }: { text: string }) {
  if (!text) return null;
  // Only source Form help is accepted; render text/list nodes, never remote HTML.
  const body = new DOMParser().parseFromString(text, "text/html").body;
  const list = body.children.length === 1 && body.firstElementChild?.tagName === "UL"
    ? [...body.firstElementChild.children].map((item) => item.textContent ?? "") : null;
  return <div className="leading-relaxed mt-2 text-xs">{list ? <ul>{list.map((text, index) => <li key={index}>{text}</li>)}</ul> : body.textContent}</div>;
}

export default function PasswordChange({ mode = "form", navigate = navigateDocument }: Props) {
  return <PasswordChangePage key={mode} mode={mode} navigate={navigate} />;
}

function PasswordChangePage({ mode, navigate }: Required<Props>) {
  const [state, setState] = useState<State>({ phase: "loading" });
  const [values, setValues] = useState(empty);
  const [errors, setErrors] = useState<Errors>({});
  const [errorNote, setErrorNote] = useState("");
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const active = useRef(false);
  const generation = useRef(0);
  const submitting = useRef(false);

  useLayoutEffect(() => {
    const html = document.documentElement;
    const oldBody = document.body.className, oldClass = html.className, oldTheme = html.getAttribute("data-bs-theme"), oldTitle = document.title;
    const others = [...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')]
      .filter((link) => !styles.includes(link.getAttribute("href") ?? ""))
      .map((link) => ({ link, disabled: link.disabled }));
    for (const { link } of others) link.disabled = true;
    const root = document.getElementById("root");
    const display = root?.style.getPropertyValue("display"), priority = root?.style.getPropertyPriority("display");
    root?.style.setProperty("display", "contents");
    html.className = "";
    html.removeAttribute("data-bs-theme");
    document.body.className = "antialiased bg-base-50 font-sans text-font-default-light text-sm dark:bg-base-900 dark:text-font-default-dark";
    return () => {
      document.body.className = oldBody; html.className = oldClass; document.title = oldTitle;
      if (oldTheme === null) html.removeAttribute("data-bs-theme"); else html.setAttribute("data-bs-theme", oldTheme);
      for (const { link, disabled } of others) link.disabled = disabled;
      if (display) root?.style.setProperty("display", display, priority); else root?.style.removeProperty("display");
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    active.current = true;
    const current = ++generation.current;
    client.get(endpoint, { signal: controller.signal, validateStatus: accepted }).then(({ data, status }: { data: unknown; status?: number }) => {
      if (!active.current || current !== generation.current) return;
      if (status === 403) setState({ phase: "blocked" });
      else if (metadata(data)) setState({ phase: "ready", metadata: data });
      else setState({ phase: "unavailable" });
    }).catch(() => { if (active.current && current === generation.current) setState({ phase: "unavailable" }); });
    return () => { active.current = false; generation.current += 1; controller.abort(); };
  }, []);

  useEffect(() => {
    if (state.phase === "ready") document.title = `${mode === "done" ? state.metadata.done_title : state.metadata.title} | Administración de sitio Django`;
  }, [state, mode]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode !== "form" || state.phase !== "ready" || submitting.current || uncertain) return;
    submitting.current = true; setPending(true); setErrors({}); setErrorNote("");
    const current = generation.current;
    try {
      const { data, status } = await client.post(endpoint, new URLSearchParams(values), { validateStatus: accepted });
      if (!active.current || current !== generation.current) return;
      setValues(empty());
      if (status === 403) setState({ phase: "blocked" });
      else if (record(data) && data.ok === true && safeInternalPath(data.redirect) === "/password_change/done/") {
        setState({ phase: "redirecting" }); navigate("/password_change/done/");
      } else setUncertain(true);
    } catch (error: unknown) {
      if (!active.current || current !== generation.current) return;
      setValues(empty());
      const invalid = errorsFrom(error);
      if (invalid) { setErrors(invalid.errors); setErrorNote(invalid.note); submitting.current = false; }
      else if ((error as { response?: { status?: number } })?.response?.status === 403) setState({ phase: "blocked" });
      else setUncertain(true);
    } finally {
      if (active.current && current === generation.current) setPending(false);
    }
  }

  let content;
  if (state.phase === "loading" || state.phase === "redirecting") content = <div role="status">{state.phase === "loading" ? "Cargando formulario…" : "Continuando…"}</div>;
  else if (state.phase === "blocked") content = <div role="alert">La solicitud fue rechazada. <a href="/inicio/">Revisar el acceso</a></div>;
  else if (state.phase === "unavailable") content = <div role="alert">No se pudo cargar el cambio de contraseña.</div>;
  else if (mode === "done") content = <div className="mb-3 px-3 py-2.5 leading-[18px] rounded-default bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400">{state.metadata.done_text}</div>;
  else {
    const disabled = pending || uncertain;
    content = <form method="post" noValidate id="_form" onSubmit={submit}>
      <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
      <input type="text" name="username" value="" readOnly className="hidden" />
      <div>
        {errorNote && <p className="errornote bg-red-100 mb-4 text-red-700 px-3 py-2.5 leading-[18px] rounded-default dark:bg-red-500/20 dark:border-red-500/20 dark:text-red-400">{errorNote}</p>}
        {errors.__all__ && <div role="alert">{errors.__all__.map((text, index) => <p key={index}>{text}</p>)}</div>}
        {uncertain && <div role="alert">No se pudo confirmar si la contraseña cambió. <a href="/password_change/">Volver al formulario</a> sin repetir el envío automáticamente.</div>}
        <div className="mb-3 px-3 py-2.5 leading-[18px] rounded-default bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400">{state.metadata.intro_text}</div>
        <fieldset className="fieldset group border border-base-200 mb-6 rounded-default shadow-xs p-3 dark:border-base-800 *:last:mb-0">
          {state.metadata.fields.map((field) => {
            const messages = errors[field.name] ?? [];
            return <div key={field.name} className={`${messages.length ? "errors " : ""}flex flex-col group mb-4`}>
              <div className="flex flex-col gap-2">
                <label htmlFor={field.attrs.id} className="block font-semibold text-important">{field.label}{field.required && <span className="text-red-600 dark:text-red-500">*</span>}</label>
                <input id={field.attrs.id} name={field.name} type="password" autoComplete={field.attrs.autocomplete} autoFocus={field.attrs.autofocus}
                  required={field.required} disabled={disabled} aria-describedby={field.attrs["aria-describedby"]} aria-invalid={messages.length ? true : undefined}
                  value={values[field.name]} onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))} />
              </div>
              {!!messages.length && <div className="mt-2 text-red-600 text-xs dark:text-red-500"><ul>{messages.map((text, index) => <li key={index}>{text}</li>)}</ul></div>}
              <Help text={field.help_text} />
            </div>;
          })}
          <div className="border-t border-base-200 flex justify-end -mx-3 pt-3 px-3 dark:border-base-800">
            <button type="submit" disabled={disabled} className="font-medium inline-flex group items-center gap-1 relative rounded-default justify-center whitespace-nowrap cursor-pointer px-3 py-2 border border-base-200 bg-primary-600 border-transparent text-white hover:bg-primary-600/80">{state.metadata.submit_label}</button>
          </div>
        </fieldset>
      </div>
    </form>;
  }

  return <>
    {styles.map((href) => <link key={href} rel="stylesheet" href={href} />)}
    <div id="page" className="flex max-w-full min-h-screen"><div id="main" className="bg-white flex flex-col grow min-w-0 dark:bg-base-900">
      <div className="bg-white border-b border-base-200 mb-6 px-4 z-40 dark:bg-base-900 dark:border-base-800 dark:text-font-default-dark"><div className="container flex items-center h-16 mx-auto py-4"><div id="header-inner" className="flex items-center relative w-full"><div className="flex items-center w-full" /></div></div></div>
      <div className="px-4"><div className="container mx-auto" /></div>
      <div className="@container px-4 pb-4 grow"><div id="content" className="container mx-auto colM"><div id="content-main">{content}</div></div></div>
    </div></div>
  </>;
}
