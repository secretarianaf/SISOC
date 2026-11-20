/* eslint-disable react-refresh/only-export-components -- route module: the screen and its route definition live together. */
import { useEffect, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { prerequisiteFromForbidden } from "../webAccess";
import { Breadcrumb, accepted, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { resetAfterRejectedPost } from "./nativeParity";
import PasPanelRoute from "./pasCambioEstado";
import { PAS_API, PAS_STYLESHEET, list, shape, stylesheetsReady } from "./pasFrame";
import PasSelect2 from "./pasSelect2";
import type { RouteDefinition } from "./types";

/**
 * `pas/persona_form.html` (`pas/crear` and `pas/<pk>/editar`, crispy fields, `pas.js` selects). The options and
 * the save go to `/api/web/pas/personas/...`, which runs the native forms and services. Like the native view,
 * a save ends on `pas/panel-control/<pk>` with the success message as a toast; a rejection is the same form
 * again with the errors under the fields. A POST is never retried.
 */
type Choice = { value: string; label: string };
type FieldError = { message: string; code: string };
type Options = {
  provincias: Choice[]; municipios: Choice[]; estados: Choice[]; generos: Choice[];
  avisos_por_estado: Record<string, { id: number; text: string }[]>;
};
type EditData = Options & { id: number; initial: Record<string, string> };
type Mode = { kind: "crear" } | { kind: "editar"; id: string };
type Outcome = { kind: "saved"; id: number; message: string } | { kind: "rejected"; errors: Record<string, FieldError[]> } | { kind: "uncertain" } | { kind: "forbidden"; data: unknown };

const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const SELECT2_CSS = "https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css";
const TEXT_FIELDS = ["id_persona", "apellidos", "nombres", "dni", "cuit", "genero", "domicilio", "correo_electronico", "telefono_celular"] as const;
const EMPTY = (label: string): Choice => ({ value: "", label });

const choiceValid = (v: unknown): v is Choice => shape(v, { value: text, label: text });
const optionsValid = (v: unknown): v is Options => shape(v, {
  provincias: list(choiceValid), municipios: list(choiceValid), estados: list(choiceValid), generos: list(choiceValid),
  avisos_por_estado: (m) => record(m) && Object.values(m).every(list((a: unknown): a is object => shape(a, { id: (n) => Number.isSafeInteger(n), text }))),
});
const editValid = (v: unknown): v is EditData => optionsValid(v) && shape(v, { id: (n) => Number.isSafeInteger(n), initial: record });
const errorsValid = (v: unknown): v is Record<string, FieldError[]> => record(v) &&
  Object.values(v).every(list((e: unknown): e is FieldError => shape(e, { message: text, code: text })));

async function save(mode: Mode, body: URLSearchParams): Promise<Outcome> {
  const url = mode.kind === "crear" ? `${PAS_API}personas/crear/` : `${PAS_API}personas/${mode.id}/editar/`;
  try {
    const { data, status } = await webClient.post(url, body, { validateStatus: (s: number) => accepted(s) || s === 400 });
    if (status === 403) return { kind: "forbidden", data };
    if ((status === 200 || status === 201) && record(data) && Number.isSafeInteger(data.id) && text(data.message)) {
      return { kind: "saved", id: data.id as number, message: data.message };
    }
    if (status === 400 && record(data) && errorsValid(data.errors)) return { kind: "rejected", errors: data.errors };
  } catch {
    // Reported as unconfirmed below.
  }
  return { kind: "uncertain" };
}

async function loadMunicipios(provincia: string): Promise<Choice[] | null> {
  try {
    const { data, status } = await webClient.get(`${PAS_API}personas/opciones/?provincia=${encodeURIComponent(provincia)}`, { validateStatus: accepted });
    return status === 200 && optionsValid(data) ? data.municipios : null;
  } catch {
    return null;
  }
}

/** `{{ form.<field>|as_crispy_field }}`: label with asterisk, the control and the inline errors. */
function Field({ name, label, required, errors, children }: { name: string; label: string; required: boolean; errors: FieldError[]; children: ReactNode }) {
  const id = `id_${name}`;
  return <div id={`div_${id}`} className="mb-3">
    <label htmlFor={id} className={`form-label${required ? " requiredField" : ""}`}>
      {label}{required && <span className="asteriskField">*</span>}
    </label>{" "}
    {children}
    {errors.length > 0 && <div id={`${id}_error`} className="invalid-feedback">
      {errors.map((e, i) => <span key={i} id={`error_${i + 1}_${id}`}><strong>{e.message}</strong></span>)}
    </div>}
  </div>;
}

function Form({ mode, options, initial, onDone }: { mode: Mode; options: Options; initial: Record<string, string>; onDone: (o: Outcome) => void }) {
  const crear = mode.kind === "crear";
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(TEXT_FIELDS.map((k) => [k, initial[k] ?? ""])));
  const [provincia, setProvincia] = useState(initial.provincia ?? "");
  const [municipio, setMunicipio] = useState(initial.municipio ?? "");
  const [municipios, setMunicipios] = useState(options.municipios);
  const [estado, setEstado] = useState("");
  const [avisos, setAvisos] = useState<string[]>([]);
  const [errors, setErrors] = useState<Record<string, FieldError[]>>({});
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [generation, setGeneration] = useState(0);
  const busy = useRef(false);
  const answers = useRef(0);
  useEffect(() => {
    if (generation === answers.current) return;
    answers.current = generation;
    resetAfterRejectedPost();
  }, [generation]);

  const err = (name: string) => errors[name] ?? [];
  const input = (name: (typeof TEXT_FIELDS)[number], type: string, extra: object) => <input type={type} name={name} id={`id_${name}`}
    className={`form-control ${type === "number" ? "numberinput" : type === "email" ? "emailinput" : "textinput"}${err(name).length ? " is-invalid" : ""}`}
    value={values[name]} onChange={(e) => setValues({ ...values, [name]: e.target.value })} {...extra} />;

  function changeProvincia(next: string[]) {
    // `pas.js`: the municipio list restarts at «---------» and is filled from the server.
    const value = next[0] ?? "";
    setProvincia(value);
    setMunicipio("");
    setMunicipios([]);
    if (value) void loadMunicipios(value).then((rows) => { if (rows) setMunicipios(rows); });
  }
  function changeEstado(next: string[]) {
    const value = next[0] ?? "";
    setEstado(value);
    const offered = new Set((options.avisos_por_estado[value] ?? []).map((a) => String(a.id)));
    setAvisos((current) => current.filter((a) => offered.has(a)));
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true;
    const body = new URLSearchParams();
    for (const name of TEXT_FIELDS) body.append(name, values[name]);
    body.append("provincia", provincia);
    body.append("municipio", municipio);
    if (crear) {
      body.append("estado", estado);
      for (const aviso of avisos) body.append("avisos", aviso);
    }
    const result = await save(mode, body);
    busy.current = false;
    if (result.kind === "rejected") setErrors(result.errors);
    else setErrors({});
    if (result.kind === "saved" || result.kind === "forbidden") { onDone(result); return; }
    setOutcome(result);
    setGeneration((n) => n + 1);
  }
  const back = (event: MouseEvent) => { event.preventDefault(); window.history.back(); };
  const volver = crear ? "/pas/listar" : `/pas/panel-control/${mode.kind === "editar" ? mode.id : ""}`;
  const nonField = err("__all__");
  const select = (name: string, label: string, choices: Choice[], value: string, onChange: (v: string[]) => void, multiple = false) => (
    <Field name={name} label={label} required errors={err(name)}>
      <PasSelect2 id={`id_${name}`} name={name} multiple={multiple} parent={null} value={multiple ? avisos : value ? [value] : []} onChange={onChange}
        invalid={err(name).length > 0} choices={choices} />
    </Field>);

  return <>
    <div className="d-flex justify-content-between mb-3">
      <a href="#" data-history-back="true" className="btn btn-secondary" onClick={back}>Cancelar</a>
    </div>
    <div className="row comedor-form">
      <div className="col-12">
        {outcome?.kind === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
        <form method="post" id="pasForm" className="w-100" onSubmit={(e) => void submit(e)}>
          <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
          <div className="section-card" data-section="persona">
            <div className="section-header">
              <div className="section-header-left">
                <div className="section-icon"><i className="fas fa-user" /></div>
                <div className="section-title-group">
                  <h3 className="section-title">{crear ? "Crear registro PAS" : "Editar registro PAS"}</h3>
                  <p className="section-subtitle">Datos principales de la persona titular</p>
                </div>
              </div>
            </div>
            <div className="section-body collapse show">
              {nonField.length > 0 && <div className="alert alert-danger">{nonField.map((e) => e.message).join(" ")}</div>}
              <div className="form-group row">
                <div className="col-md-3"><Field name="id_persona" label="IdPersona" required errors={err("id_persona")}>{input("id_persona", "number", { min: 0, required: true })}</Field></div>
                <div className="col-md-3"><Field name="apellidos" label="Apellidos" required errors={err("apellidos")}>{input("apellidos", "text", { maxLength: 150, required: true })}</Field></div>
                <div className="col-md-3"><Field name="nombres" label="Nombres" required errors={err("nombres")}>{input("nombres", "text", { maxLength: 150, required: true })}</Field></div>
                <div className="col-md-3"><Field name="dni" label="DNI" required errors={err("dni")}>{input("dni", "number", { min: 0, required: true })}</Field></div>
              </div>
              <div className="form-group row">
                <div className="col-md-3"><Field name="cuit" label="CUIT" required={false} errors={err("cuit")}>{input("cuit", "text", { maxLength: 20 })}</Field></div>
                <div className="col-md-3"><Field name="genero" label="Género (RENAPER)" required={false} errors={err("genero")}>
                  <select name="genero" id="id_genero" className={`form-select${err("genero").length ? " is-invalid" : ""}`} value={values.genero}
                    onChange={(e) => setValues({ ...values, genero: e.target.value })}>
                    {[EMPTY("---------"), ...options.generos].map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </Field></div>
                <div className="col-md-3">{select("provincia", "Provincia", [EMPTY("---------"), ...options.provincias], provincia, changeProvincia)}</div>
                <div className="col-md-3">{select("municipio", "Municipio", [EMPTY("---------"), ...municipios], municipio, (v) => setMunicipio(v[0] ?? ""))}</div>
              </div>
              <div className="form-group row">
                <div className="col-md-4"><Field name="domicilio" label="Calle, número, piso y departamento" required={false} errors={err("domicilio")}>{input("domicilio", "text", { maxLength: 255 })}</Field></div>
                <div className="col-md-4"><Field name="correo_electronico" label="Correo electrónico" required={false} errors={err("correo_electronico")}>{input("correo_electronico", "email", { maxLength: 254 })}</Field></div>
                <div className="col-md-4"><Field name="telefono_celular" label="Teléfono celular" required={false} errors={err("telefono_celular")}>{input("telefono_celular", "text", { maxLength: 30 })}</Field></div>
              </div>
            </div>
          </div>
          {crear && <div className="section-card" data-section="estado">
            <div className="section-header">
              <div className="section-header-left">
                <div className="section-icon"><i className="fas fa-tasks" /></div>
                <div className="section-title-group">
                  <h3 className="section-title">Estado del titular</h3>
                  <p className="section-subtitle">Estado vigente y motivos asociados</p>
                </div>
              </div>
            </div>
            <div className="section-body collapse show">
              <div className="form-group row">
                <div className="col-md-4">{select("estado", "Estado", [EMPTY("Seleccione un estado"), ...options.estados], estado, changeEstado)}</div>
                <div className="col-md-8">{select("avisos", "Avisos", (options.avisos_por_estado[estado] ?? []).map((a) => ({ value: String(a.id), label: a.text })), "", setAvisos, true)}</div>
              </div>
            </div>
          </div>}
          <div className="sticky-actions">
            <a href={volver} className="btn btn-secondary"><i className="fas fa-arrow-left mr-1" /> Volver</a>{" "}
            <button className="btn btn-success" type="submit"><i className="fas fa-save mr-1" /> Guardar registro</button>
          </div>
        </form>
      </div>
    </div>
  </>;
}

/** The native page has its stylesheets in `<head>`, so the form first paints styled: draw it once the body links applied. */
function WhenStyled({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let active = true;
    void stylesheetsReady().then(() => { if (active) setReady(true); });
    return () => { active = false; };
  }, []);
  return ready ? <>{children}</> : null;
}

function PersonaFormPage({ mode }: { mode: Mode }) {
  const endpoint = mode.kind === "crear" ? `${PAS_API}personas/opciones/` : `${PAS_API}personas/${mode.id}/`;
  const [state, setState] = useMainResource<Options | EditData>(endpoint, mode.kind === "crear" ? optionsValid : editValid);
  const [saved, setSaved] = useState<{ id: number; message: string } | null>(null);
  if (saved) return <PasPanelRoute id={String(saved.id)} notices={[{ message: saved.message, level: "success" }]} />;
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: "PAS",
    breadcrumb: <Breadcrumb items={[{ text: "PAS", url: "/pas/listar" }, { text: mode.kind === "crear" ? "Crear" : "Editar", url: null }]} />,
    content: <>
      <link rel="stylesheet" href={SELECT2_CSS} />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      {PAS_STYLESHEET}
      <WhenStyled><Form mode={mode} options={data} initial={"initial" in data ? data.initial : {}}
        onDone={(o) => {
          if (o.kind === "forbidden") setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(o.data) });
          else if (o.kind === "saved") {
            window.history.pushState({}, "", `/pas/panel-control/${o.id}`);
            setSaved({ id: o.id, message: o.message });
          }
        }} /></WhenStyled>
    </>,
  }));
}

type Params = { kind: "crear" } | { kind: "editar"; id: string };
const PATH = /^\/pas\/(?:(crear)|([0-9]+)\/editar)$/;

export const pasPersonaFormRoute: RouteDefinition<Params> = {
  name: "pas-persona-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[1] ? { kind: "crear" } : { kind: "editar", id: m[2] };
  },
  render: (params) => <PersonaFormPage key={params.kind === "editar" ? params.id : "crear"} mode={params} />,
};
