/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useState, type FormEvent } from "react";
import { InsumosToastList } from "../InsumosToast";
import { client, csrfToken, integer, messagesValid, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import type { RouteDefinition } from "./types";

/**
 * CDF04.03: `centros/generar_usuario_cdf.html` (crispy fields) and
 * `centros/usuario_cdf_generado.html`. The API runs the native view (404, then
 * delegation, territory and quota 403). The 201 is the CR1 projection: the
 * temporary password lives only in this component's memory and is lost on
 * leaving or reloading; a POST is never retried.
 */
const API = "web/cdf/centros/";
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

type FieldError = { message: string; code: string };
type Field = { name: string; label: string; required: boolean; widget: string; help_text: string; value: string; attrs: Record<string, string> };
export type UsuarioFormData = {
  centro: { id: number; nombre: string }; grupo: string; usuarios_restantes: number;
  fields: Field[]; errors: Record<string, FieldError[]>; non_field_errors: string[]; messages: CdfMessage[];
};
export type UsuarioGenerado = {
  usuario: { username: string; email: string }; password: string; email_enviado: boolean; puede_generar_otro: boolean; message: string;
};

const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && text(f.label) && typeof f.required === "boolean" &&
  text(f.widget) && text(f.help_text) && text(f.value) && record(f.attrs) && Object.values(f.attrs).every(text);

export function usuarioFormValid(v: unknown): v is UsuarioFormData {
  return record(v) && record(v.centro) && integer(v.centro.id) && text(v.centro.nombre) && text(v.grupo) && integer(v.usuarios_restantes) &&
    Array.isArray(v.fields) && v.fields.every(fieldValid) && record(v.errors) &&
    Object.values(v.errors).every((list) => Array.isArray(list) && list.every((e) => record(e) && text(e.message) && text(e.code))) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && messagesValid(v.messages);
}

export function usuarioGeneradoValid(v: unknown): v is UsuarioGenerado {
  return record(v) && record(v.usuario) && text(v.usuario.username) && text(v.usuario.email) && text(v.password) &&
    typeof v.email_enviado === "boolean" && typeof v.puede_generar_otro === "boolean" && text(v.message);
}

const INPUT_CLASS: Record<string, string> = { text: "textinput", email: "emailinput" };
const detailUrl = (id: number) => `/centrodefamilia/centros/${id}/`;
const generarUrl = (id: number) => `/centrodefamilia/centros/${id}/generar-usuario/`;

function CrispyField({ field, errors }: { field: Field; errors: FieldError[] }) {
  const id = `id_${field.name}`;
  const described = [field.help_text && `${id}_helptext`, errors.length && `${id}_error`].filter(Boolean).join(" ");
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>
        {field.label}{field.required && <span className="asteriskField">*</span>}
      </label>
      <input type={field.widget} name={field.name} defaultValue={field.value} {...field.attrs}
        className={`form-control ${INPUT_CLASS[field.widget] ?? "textinput"}${errors.length ? " is-invalid" : ""}`}
        required={field.required || undefined} aria-invalid={errors.length ? "true" : undefined}
        aria-describedby={described || undefined} id={id} />
      {errors.length > 0 && (
        <div id={`${id}_error`} className="invalid-feedback">
          {errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e.message}</strong></p>)}
        </div>
      )}
      {field.help_text && <div id={`${id}_helptext`} className="form-text">{field.help_text}</div>}
    </div>
  );
}

export function UsuarioFormContent({ data, onCreated }: { data: UsuarioFormData; onCreated: (r: UsuarioGenerado) => void }) {
  const [form, setForm] = useState(data);
  const [state, setState] = useState<"idle" | "sending" | "uncertain">("idle");
  const { centro } = form;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state !== "idle") return;
    setState("sending");
    try {
      const { data: body, status } = await client.post(`${API}${centro.id}/generar-usuario/`, new FormData(event.currentTarget),
        { validateStatus: (s: number) => s === 201 || s === 400 });
      if (status === 201 && usuarioGeneradoValid(body)) { onCreated(body); return; }
      if (status === 400 && usuarioFormValid(body)) { setForm(body); setState("idle"); return; }
      setState("uncertain");
    } catch {
      setState("uncertain");
    }
  }

  return (
    <div className="row">
      <div className="col-12 col-lg-8 mx-auto">
        <div className="card card-primary card-outline">
          <div className="card-header mb-3">
            <h3 className="card-title">Generar usuario referente para:{" "}<a href={detailUrl(centro.id)}>{centro.nombre}</a></h3>
          </div>
          <div className="card-body">
            <p className="text-muted">
              Se creará un usuario con el rol <strong>{form.grupo}</strong> (no editable) asociado a este centro.
              {" "}Cupo restante: <strong>{form.usuarios_restantes}</strong>.
            </p>
            {state === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
            <form method="post" className="w-100" onSubmit={submit} key={JSON.stringify(form.errors) + form.non_field_errors.join()}>
              <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
              {form.non_field_errors.length > 0 && <ul className="errorlist nonfield">{form.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul>}
              {form.fields.map((field) => <CrispyField key={field.name} field={field} errors={form.errors[field.name] ?? []} />)}
              <button className="btn btn-primary mx-1" type="submit" disabled={state !== "idle" || undefined}>Generar usuario</button>{" "}
              <a href={detailUrl(centro.id)} className="btn btn-secondary">Cancelar</a>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

function Credencial({ id, label, value, extra }: { id: string; label: string; value: string; extra?: string }) {
  return (
    <div className="mb-3">
      <label className="form-label" htmlFor={id}>{label}</label>
      <input className={`form-control${extra ? ` ${extra}` : ""}`} id={id} type="text" value={value} readOnly />
      {id === "cred-password" && <>{" "}<small className="text-muted">Seleccione el texto del campo y cópielo (Ctrl+C) antes de salir.</small></>}
    </div>
  );
}

export function UsuarioGeneradoContent({ centro, result }: { centro: { id: number; nombre: string }; result: UsuarioGenerado }) {
  return (
    <div className="row">
      <div className="col-12 col-lg-8 mx-auto">
        <div className="card card-primary card-outline">
          <div className="card-header mb-3">
            <h3 className="card-title">Usuario generado para:{" "}<a href={detailUrl(centro.id)}>{centro.nombre}</a></h3>
          </div>
          <div className="card-body">
            {result.email_enviado
              ? <p className="text-success">Se envió un correo con las credenciales a{" "}<strong>{result.usuario.email}</strong>.</p>
              : <p className="text-warning">No se pudo enviar el correo de credenciales. Entregue estos datos al referente de forma segura.</p>}
            <p className="text-muted">
              Esta contraseña temporal también queda visible en la edición del usuario hasta su primer cambio. Cópiela ahora.
            </p>
            <Credencial id="cred-usuario" label="Usuario" value={result.usuario.username} />
            <Credencial id="cred-email" label="Email" value={result.usuario.email} />
            <Credencial id="cred-password" label="Contraseña temporal" value={result.password} extra="fs-5" />
            <div className="mt-3">
              {result.puede_generar_otro && <a href={generarUrl(centro.id)} className="btn btn-secondary">Generar otro</a>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function CentroUsuario({ id }: { id: string }) {
  const state = useCdfPage(`${API}${id}/generar-usuario/`, usuarioFormValid);
  const [result, setResult] = useState<UsuarioGenerado | null>(null);
  return renderCdf(state, (data) => (result
    ? {
      title: "Usuario generado - Centro de Familia",
      heading: "Usuario referente generado",
      breadcrumb: null,
      content: <><InsumosToastList messages={[{ message: result.message, level: "success" }]} /><UsuarioGeneradoContent centro={data.centro} result={result} /></>,
    }
    : {
      title: "Generar usuario - Centro de Familia",
      heading: "Generar usuario referente del CDF",
      breadcrumb: null,
      content: <UsuarioFormContent data={data} onCreated={setResult} />,
    }));
}

// Native URL of the CDF referente user generation (CDF04.03).
export const cdfCentroUsuarioRoute: RouteDefinition<{ id: string }> = {
  name: "cdf-centro-usuario",
  match: (pathname) => {
    const m = /^\/centrodefamilia\/centros\/([1-9]\d*)\/generar-usuario\/$/.exec(pathname);
    return m ? { id: m[1] } : null;
  },
  render: ({ id }) => <CentroUsuario id={id} />,
};
