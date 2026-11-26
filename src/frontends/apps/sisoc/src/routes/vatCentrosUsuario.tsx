/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators and screens are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { bool, integer, messagesValid, type Message } from "./vatShared";
import { UNCERTAIN, fieldValid, type Field } from "./vatFormShared";
import type { RouteDefinition } from "./types";

/**
 * V06.02 «Generar usuario» de un centro: `vat/centros/generar_usuario.html` (crispy fields) and
 * `vat/centros/usuario_generado.html`. `/api/web/vat/centros-usuarios/<id>/generar/` runs the native view: its GET is the form,
 * a valid POST creates the user and answers, once, what the native result page shows, the temporary password included. The
 * password lives only in this component's state: no storage, no URL, no history entry and no GET carries it; a POST is never
 * retried because the user may exist already.
 */
type Centro = { id: number; nombre: string; url: string };
export type UsuarioFormData = {
  centro: Centro; usuarios_restantes: number; fields: Field[]; non_field_errors: string[]; urls: { cancelar: string; generar: string }; messages: Message[];
};
export type UsuarioGenerado = {
  ok: true; centro: Centro; usuario: { username: string; email: string }; password: string; email_enviado: boolean; puede_generar_otro: boolean;
  urls: { generar: string }; messages: Message[];
};

const API = "web/vat/centros-usuarios/";
const NAMES = ["first_name", "last_name", "email"];
const centroValid = (v: unknown): v is Centro => record(v) && integer(v.id) && text(v.nombre) && internal(v.url);

export function usuarioFormValid(v: unknown): v is UsuarioFormData {
  return record(v) && centroValid(v.centro) && integer(v.usuarios_restantes) && Array.isArray(v.fields) && v.fields.every(fieldValid) &&
    (v.fields as Field[]).map((f) => f.name).join() === NAMES.join() &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.cancelar) && internal(v.urls.generar) &&
    messagesValid(v.messages);
}

export function usuarioGeneradoValid(v: unknown): v is UsuarioGenerado {
  return record(v) && v.ok === true && centroValid(v.centro) && record(v.usuario) && text(v.usuario.username) && text(v.usuario.email) &&
    text(v.password) && bool(v.email_enviado) && bool(v.puede_generar_otro) && record(v.urls) && internal(v.urls.generar) && messagesValid(v.messages);
}

const INPUT_CLASS: Record<string, string> = { text: "textinput", email: "emailinput" };

/** `{{ form.x|as_crispy_field }}`: label with its asterisk, the control and the `invalid-feedback` block. */
function CrispyField({ f, value, onChange }: { f: Field; value: string; onChange: (v: string) => void }) {
  const id = f.id;
  const required = f.attrs.required !== undefined;
  const { class: widgetClass, type } = f.attrs;
  const rest = { ...f.attrs };
  for (const key of ["class", "required", "type"]) delete rest[key];
  const described = [f.help_text && `${id}_helptext`, f.errors.length && `${id}_error`].filter(Boolean).join(" ");
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${required ? " requiredField" : ""}`}>
        {f.label}{required && <span className="asteriskField">*</span>}
      </label>
      <input name={f.name} id={id} type={type} {...rest} required={required || undefined}
        className={`${INPUT_CLASS[type] ?? "textinput"} ${widgetClass ?? "form-control"}${f.errors.length ? " is-invalid" : ""}`}
        aria-invalid={f.errors.length ? "true" : undefined} aria-describedby={described || undefined} value={value} onChange={(e) => onChange(e.target.value)} />
      {f.errors.length > 0 && (
        <div id={`${id}_error`} className="invalid-feedback">
          {f.errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e}</strong></p>)}
        </div>
      )}
      {f.help_text && <div id={`${id}_helptext`} className="form-text">{f.help_text}</div>}
    </div>
  );
}

export function UsuarioFormContent({ data, onCreated }: { data: UsuarioFormData; onCreated: (r: UsuarioGenerado) => void }) {
  const [form, setForm] = useState(data);
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(data.fields.map((f) => [f.name, String(f.value)])));
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const busy = useRef(false);
  const { centro } = form;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    // Only the fields the native template renders, plus the CSRF token.
    const body = new URLSearchParams({ csrfmiddlewaretoken: leerCookie("csrftoken") ?? "" });
    form.fields.forEach((f) => body.set(f.name, values[f.name] ?? ""));
    try {
      const { data: reply, status } = await webClient.post(`${API}${centro.id}/generar/`, body, { validateStatus: (s: number) => s === 201 || s === 400 || s === 403 });
      if (status === 403) setForbidden({ prerequisite: prerequisiteFromForbidden(reply) });
      else if (status === 201 && usuarioGeneradoValid(reply)) onCreated(reply);
      else if (status === 400 && usuarioFormValid(reply)) {
        setForm(reply);
        setValues(Object.fromEntries(reply.fields.map((f) => [f.name, String(f.value)])));
        resetAfterRejectedPost();
      } else setUncertain(true);
    } catch {
      // The outcome is unknown: the user may exist already, so it is never resubmitted.
      setUncertain(true);
    } finally {
      busy.current = false; setPending(false);
    }
  }

  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;
  return (
    <div className="row"><div className="col-12 col-lg-8 mx-auto"><div className="card card-primary card-outline">
      <div className="card-header mb-3">
        <h3 className="card-title">Generar usuario referente para:{" "}<a href={centro.url}>{centro.nombre}</a></h3>
      </div>
      <div className="card-body">
        <p className="text-muted">
          Se creará un usuario con el rol <strong>CFP</strong> (no editable) asociado a este centro.{" "}
          Cupo restante: <strong>{form.usuarios_restantes}</strong>.
        </p>
        <form method="post" className="w-100" onSubmit={(e) => void submit(e)}>
          {form.non_field_errors.length > 0 && <ul className="errorlist nonfield">{form.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul>}
          {form.fields.map((f) => <CrispyField key={f.name} f={f} value={values[f.name] ?? ""} onChange={(v) => setValues((s) => ({ ...s, [f.name]: v }))} />)}
          <button className="btn btn-primary mx-1" type="submit" disabled={pending || uncertain}>Generar usuario</button>{" "}
          <a href={form.urls.cancelar} className="btn btn-secondary">Cancelar</a>
          {uncertain && <p role="alert" className="mb-0">{UNCERTAIN}</p>}
        </form>
      </div>
    </div></div></div>
  );
}

function Credencial({ id, label, value, extra }: { id: string; label: string; value: string; extra?: string }) {
  return (
    <div className="mb-3">
      <label className="form-label" htmlFor={id}>{label}</label>
      <input className={`form-control${extra ? ` ${extra}` : ""}`} id={id} type="text" value={value} readOnly />
      {id === "cred-password" && <small className="text-muted">Seleccione el texto del campo y cópielo (Ctrl+C) antes de salir.</small>}
    </div>
  );
}

export function UsuarioGeneradoContent({ result }: { result: UsuarioGenerado }) {
  return (
    <>
      <NativeToasts messages={result.messages} />
      <div className="row"><div className="col-12 col-lg-8 mx-auto"><div className="card card-primary card-outline">
        <div className="card-header mb-3">
          <h3 className="card-title">Usuario generado para:{" "}<a href={result.centro.url}>{result.centro.nombre}</a></h3>
        </div>
        <div className="card-body">
          {result.email_enviado
            ? <p className="text-success">Se envió un correo con las credenciales a{" "}<strong>{result.usuario.email}</strong>.</p>
            : <p className="text-warning">No se pudo enviar el correo de credenciales. Entregue estos datos al referente de forma segura.</p>}
          <p className="text-muted">Esta contraseña temporal también queda visible en la edición del usuario hasta su primer cambio. Cópiela ahora.</p>
          <Credencial id="cred-usuario" label="Usuario" value={result.usuario.username} />
          <Credencial id="cred-email" label="Email" value={result.usuario.email} />
          <Credencial id="cred-password" label="Contraseña temporal" value={result.password} extra="fs-5" />
          <div className="mt-3">
            {result.puede_generar_otro && <a href={result.urls.generar} className="btn btn-secondary">Generar otro</a>}
          </div>
        </div>
      </div></div></div>
    </>
  );
}

function UsuarioPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/generar/`, usuarioFormValid);
  const [result, setResult] = useState<UsuarioGenerado | null>(null);
  return renderMain(state, "Cargando formulario…", (data) => (result
    ? { title: "Usuario generado - Centro VAT", heading: "Usuario referente generado", breadcrumb: null, content: <UsuarioGeneradoContent result={result} /> }
    : {
      title: "Generar usuario - Centro VAT", heading: "Generar usuario referente del Centro", breadcrumb: null,
      content: <><NativeToasts messages={data.messages} /><UsuarioFormContent data={data} onCreated={setResult} /></>,
    }));
}

// Native URL of `VAT/urls.py`.
export const vatCentrosUsuarioRoute: RouteDefinition<{ id: string }> = {
  name: "vat-centros-usuario",
  match(pathname) {
    const m = pathname.match(/^\/vat\/centros\/([0-9]+)\/generar-usuario\/$/);
    return m ? { id: m[1] } : null;
  },
  render: ({ id }) => <UsuarioPage key={id} id={id} />,
};
