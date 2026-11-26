/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { fieldValid, messagesValid, urlsValid, type CoreField, type CoreMessage } from "./coreCommon";
import type { RouteDefinition } from "./types";

/**
 * T05.02: `programa_form.html`. GET `/api/web/core/programas/crear/` and `/<pk>/editar/` project the native
 * `ProgramaForm`; the POST runs `form_valid` (message + redirect to the detail, a full-page navigation) and a
 * rejected form answers 400 with the bound form, nothing written. Access: any authenticated user.
 */
export type FormData = { mode: "create" | "edit"; fields: CoreField[]; urls: { list: string }; messages: CoreMessage[] };

export const programaFormValid = (v: unknown): v is FormData =>
  record(v) && (v.mode === "create" || v.mode === "edit") && messagesValid(v.messages) && urlsValid(v.urls, ["list"]) &&
  Array.isArray(v.fields) && v.fields.every(fieldValid);

const UNCERTAIN = "No se pudo confirmar el resultado. Revise el listado de programas antes de volver a intentar.";

/** Replaceable in tests: the success redirect is a full-page navigation. */
export const coreProgramaFormNavigation = { assign: (to: string) => window.location.assign(to) };

type Values = Record<string, string | boolean>;
const initial = (fields: CoreField[]): Values => Object.fromEntries(fields.map((f) => [f.name, f.value]));

/** `{{ field }}` as the Django widget prints it; the attributes come from the native widget. */
function Widget({ field, value, onChange }: { field: CoreField; value: string | boolean; onChange: (v: string | boolean) => void }) {
  const a = field.attrs;
  const common = {
    id: field.id, name: field.name, className: a.class, required: field.required || undefined,
    "aria-invalid": a["aria-invalid"] as "true" | undefined, "aria-describedby": a["aria-describedby"],
  };
  if (field.widget === "checkbox") return <input type="checkbox" {...common} checked={value === true} onChange={(e) => onChange(e.target.checked)} />;
  if (field.widget === "select") {
    return (
      <select {...common} value={String(value)} onChange={(e) => onChange(e.target.value)}>
        {(field.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
    );
  }
  if (field.widget === "textarea") {
    return <textarea {...common} cols={Number(a.cols) || undefined} rows={Number(a.rows) || undefined} value={String(value)} onChange={(e) => onChange(e.target.value)} />;
  }
  return <input type={a.type ?? field.widget} {...common} maxLength={a.maxlength ? Number(a.maxlength) : undefined} value={String(value)} onChange={(e) => onChange(e.target.value)} />;
}

export function ProgramaFormContent({ data: first, id }: { data: FormData; id?: string }) {
  const [data, setData] = useState(first);
  const [values, setValues] = useState<Values>(() => initial(first.fields));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  const edit = data.mode === "edit";
  const endpoint = edit ? `web/core/programas/${id}/editar/` : "web/core/programas/crear/";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true); setError("");
    // Only what the native template renders; an unchecked checkbox is simply absent.
    const body = new URLSearchParams();
    for (const f of data.fields) {
      const v = values[f.name];
      if (f.widget === "checkbox") { if (v === true) body.append(f.name, "on"); } else body.append(f.name, String(v));
    }
    const outcome = await postForm(endpoint, body);
    if (outcome.kind === "redirect" && internal(outcome.url)) { coreProgramaFormNavigation.assign(outcome.url); return; }
    if (outcome.kind === "invalid" && programaFormValid(outcome.data)) {
      // The native page reloaded with the bound form: values kept, errors shown, view at the top.
      setData(outcome.data); setValues(initial(outcome.data.fields)); resetAfterRejectedPost();
    } else setError(outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN);
    busy.current = false; setPending(false);
  }

  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row">
        <div className="col-md-8">
          <div className="card">
            <div className="card-header bg-primary text-white">
              <h3 className="card-title">{edit ? "Editar Programa" : "Nuevo Programa"}</h3>
            </div>
            <form method="post" action="" onSubmit={submit}>
              <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
              <div className="card-body">
                {data.fields.map((f) => (
                  <div className="form-group" key={f.name}>
                    <label htmlFor={f.id}>{f.label}</label>{" "}
                    <Widget field={f} value={values[f.name]} onChange={(v) => setValues({ ...values, [f.name]: v })} />
                    {f.errors.length > 0 && (
                      <small className="text-danger">
                        <ul className="errorlist" id={f.attrs["aria-describedby"]}>{f.errors.map((e) => <li key={e}>{e}</li>)}</ul>
                      </small>
                    )}
                  </div>
                ))}
                {error && <p role="alert" className="text-danger">{error}</p>}
              </div>
              <div className="card-footer">
                <button type="submit" className="btn btn-primary" disabled={pending}>{edit ? "Actualizar" : "Crear"}</button>{" "}
                <a href={data.urls.list} className="btn btn-secondary">Cancelar</a>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

function FormPage({ id }: { id?: string }) {
  const [state] = useMainResource(id ? `web/core/programas/${id}/editar/` : "web/core/programas/crear/", programaFormValid);
  return renderMain(state, "Cargando formulario…", (data) => ({
    // `{% if form.instance.pk %}Editar{% else %}Nuevo{% endif %} Programa`.
    title: data.mode === "edit" ? "Editar Programa" : "Nuevo Programa",
    activePath: data.mode === "edit" ? "programas/<int:pk>/editar/" : "programas/crear/",
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <li className="breadcrumb-item"><a href={data.urls.list}>Programas</a></li>
        <li className="breadcrumb-item active">{data.mode === "edit" ? "Editar" : "Nuevo"}</li>
      </ol>
    ),
    content: <ProgramaFormContent key={id ?? "crear"} data={data} id={id} />,
  }));
}

export const coreProgramaFormRoute: RouteDefinition<{ id?: string }> = {
  name: "core-programa-form",
  match(pathname) {
    if (pathname === "/programas/crear/") return {};
    const found = /^\/programas\/([0-9]+)\/editar\/$/.exec(pathname);
    return found ? { id: found[1] } : null;
  },
  render: ({ id }) => <FormPage id={id} />,
};
