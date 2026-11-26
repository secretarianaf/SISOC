/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Fragment, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { InsumosToastList } from "../InsumosToast";
import CdfSelect2 from "./cdfSelect2";
import { client, csrfToken, integer, internal, messagesValid, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";

/**
 * CDF03.02: `beneficiarios/beneficiarios_form.html` with the behaviour of
 * `centro_familia_beneficiarios.js`: CUIL and responsable searches (RENAPER
 * through the native service), dependent geography, client checks and one
 * combined POST to `/api/web/cdf/`, which runs the shared native processing
 * without queuing a Django message. A POST is never retried.
 */
const API = "web/cdf/beneficiarios/";
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const REQUIRED = "Este campo es requerido";
const BENEFICIARIO_REQUIRED = ["nombre", "apellido", "cuil", "dni", "genero", "fecha_nacimiento", "domicilio", "provincia", "maximo_nivel_educativo", "actividad_preferida"];
const RESPONSABLE_REQUIRED = ["nombre", "apellido", "dni", "cuil", "genero", "fecha_nacimiento", "vinculo_parental", "provincia"];
const HIDDEN = ["responsable", "provincia_tabla", "municipio_tabla", "localidad_tabla"];
const SEXO: Record<string, string> = { femenino: "F", masculino: "M" };

type Choice = { value: string; label: string };
type Field = { name: string; label: string; required: boolean; kind: string; column: string; attrs: Record<string, string>; choices?: Choice[] };
export type PreinscripcionData = {
  beneficiario: Field[]; responsable: Field[]; urls: { municipios: string; localidades: string }; messages: CdfMessage[];
};

const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && text(f.label) && typeof f.required === "boolean" && text(f.kind) &&
  text(f.column) && record(f.attrs) && Object.values(f.attrs).every(text) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));

export function preinscripcionValid(v: unknown): v is PreinscripcionData {
  return record(v) && Array.isArray(v.beneficiario) && v.beneficiario.every(fieldValid) && Array.isArray(v.responsable) &&
    v.responsable.every(fieldValid) && record(v.urls) && internal(v.urls.municipios) && internal(v.urls.localidades) && messagesValid(v.messages);
}

/** Browser seams (alerts, reload, geography); replaceable in tests. */
export const preinscripcionBrowser = {
  alert: (message: string) => window.alert(message),
  reload: () => window.location.reload(),
  load: (url: string): Promise<unknown> => fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } }).then((r) => r.json()),
};

type Value = string | string[] | boolean;
type Values = Record<string, Value>;
type Errors = Record<string, string[]>;
type Alert = { className: string; message: string } | null;
const geoValid = (v: unknown): v is { id: number; nombre: string }[] => Array.isArray(v) && v.every((g) => record(g) && integer(g.id) && text(g.nombre));
const BLANK: Choice[] = [{ value: "", label: "---------" }];

function initialValues(fields: Field[]): Values {
  const values: Values = {};
  for (const f of fields) values[f.name] = f.kind === "checkbox" ? false : f.kind === "selectmultiple" || f.kind === "checkboxmultiple" ? [] : "";
  return values;
}

/** Server attributes of the crispy control as React props. */
function controlProps(attrs: Record<string, string>) {
  const props: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") props.className = value;
    else if (key === "readonly") props.readOnly = true;
    else if (key === "required") props.required = true;
    else if (key === "disabled") props.disabled = true;
    else if (key === "maxlength") props.maxLength = Number(value);
    else if (key !== "multiple" && key !== "value" && key !== "checked") props[key] = value;
  }
  return props;
}

type FormProps = {
  fields: Field[]; values: Values; errors: Errors; set: (name: string, value: Value) => void;
  geo: { municipio: Choice[]; localidad: Choice[] }; onGeo: (name: string, value: string) => void;
  hidden?: Record<string, boolean>;
};

function Feedback({ messages }: { messages: string[] }) {
  return <>{messages.map((m, i) => <div key={i} className="invalid-feedback">{m}</div>)}</>;
}

function FormFields({ fields, values, errors, set, geo, onGeo, hidden = {} }: FormProps) {
  return (
    <>
      {fields.map((field) => {
        const id = `id_${field.name}`;
        const props = controlProps(field.attrs);
        const fieldErrors = errors[field.name] ?? [];
        const invalid = fieldErrors.length ? " is-invalid" : "";
        const className = `${String(props.className ?? "")}${invalid}`;
        const label = (
          <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>
            {field.label}{field.required && <span className="asteriskField">*</span>}
          </label>
        );
        let body: ReactNode;
        if (field.kind === "checkbox") {
          body = (
            <div className="mb-3">
              <div id={`div_${id}`} className="form-check">
                <input type="checkbox" name={field.name} {...props} className={className} id={id} checked={values[field.name] === true}
                  onChange={(e) => set(field.name, e.target.checked)} />
                <label htmlFor={id} className="form-check-label">{field.label}</label>
                <Feedback messages={fieldErrors} />
              </div>
            </div>
          );
        } else if (field.kind === "checkboxmultiple") {
          const chosen = (values[field.name] as string[]) ?? [];
          body = (
            <div id={`div_${id}`} className="mb-3">
              <div>
                {(field.choices ?? []).map((c, i) => (
                  <div key={c.value} className="form-check">
                    <input type="checkbox" className="form-check-input" name={field.name} value={c.value} id={`${id}_${i}`} checked={chosen.includes(c.value)}
                      onChange={(e) => set(field.name, e.target.checked ? [...chosen, c.value] : chosen.filter((v) => v !== c.value))} />
                    <label htmlFor={`${id}_${i}`} className="form-check-label">{c.label}</label>
                  </div>
                ))}
              </div>
            </div>
          );
        } else if (field.kind === "selectmultiple") {
          body = (
            <div id={`div_${id}`} className="mb-3">
              {label}
              <CdfSelect2 id={id} name={field.name} placeholder={field.attrs["data-placeholder"] ?? ""} className={String(props.className ?? "")}
                choices={field.choices ?? []}
                value={(values[field.name] as string[]) ?? []} onChange={(v) => set(field.name, v)} invalid={fieldErrors.length > 0} describedBy="" />
              <Feedback messages={fieldErrors} />
            </div>
          );
        } else if (field.kind === "select") {
          const options = field.name === "municipio" ? geo.municipio : field.name === "localidad" ? geo.localidad : field.choices ?? [];
          body = (
            <div id={`div_${id}`} className="mb-3">
              {label}
              <select name={field.name} {...props} className={className} id={id} value={String(values[field.name] ?? "")}
                onChange={(e) => { set(field.name, e.target.value); onGeo(field.name, e.target.value); }}>
                {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <Feedback messages={fieldErrors} />
            </div>
          );
        } else {
          body = (
            <div id={`div_${id}`} className="mb-3">
              {label}
              <input name={field.name} {...props} className={className} id={id} value={String(values[field.name] ?? "")}
                onChange={(e) => set(field.name, e.target.value)} />
              <Feedback messages={fieldErrors} />
            </div>
          );
        }
        const containerId = field.name === "nivel_educativo_actual" ? "nivel-educativo-container"
          : field.name === "actividades_detalle" ? "actividades-detalle-container" : undefined;
        const extraError = field.name === "actividades_detalle" && (errors.__detalle ?? []).length;
        return (
          <div key={field.name} className={`${field.column}${extraError ? " is-invalid" : ""}`} id={containerId}
            style={containerId ? { display: hidden[field.name] ? "none" : "block" } : undefined}>
            {body}
            {extraError ? <div className="invalid-feedback d-block">{errors.__detalle[0]}</div> : null}
          </div>
        );
      })}
    </>
  );
}

function useGeo(urls: PreinscripcionData["urls"]) {
  const [geo, setGeo] = useState({ municipio: BLANK, localidad: BLANK });
  async function load(url: string): Promise<Choice[]> {
    try {
      const rows = await preinscripcionBrowser.load(url);
      return geoValid(rows) ? [...BLANK, ...rows.map((g) => ({ value: String(g.id), label: g.nombre }))] : BLANK;
    } catch {
      return BLANK;
    }
  }
  const municipios = (provincia: string) => load(`${urls.municipios}?provincia_id=${encodeURIComponent(provincia)}`);
  const localidades = (municipio: string) => load(`${urls.localidades}?municipio_id=${encodeURIComponent(municipio)}`);
  return { geo, setGeo, municipios, localidades };
}

const Spinner = ({ label }: { label: string }) => <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />{label}</>;

function SearchAlert({ alert, id }: { alert: Alert; id: string }) {
  return <div id={id} className={alert?.className || undefined} style={{ display: alert ? "block" : "none" }}>{alert?.message ?? ""}</div>;
}

export function PreinscripcionContent({ data }: { data: PreinscripcionData }) {
  const [round, setRound] = useState(0);
  const [toast, setToast] = useState<CdfMessage[]>([]);
  return (
    <>
      <InsumosToastList messages={toast} />
      <Preinscripcion key={round} data={data} done={() => { setToast([{ message: "Datos cargados con éxito", level: "success" }]); setRound((r) => r + 1); }} />
    </>
  );
}

function Preinscripcion({ data, done }: { data: PreinscripcionData; done: () => void }) {
  const [ben, setBen] = useState<Values>(() => ({ ...initialValues(data.beneficiario), ...Object.fromEntries(HIDDEN.map((h) => [h, ""])) }));
  const [resp, setResp] = useState<Values>(() => initialValues(data.responsable));
  const [benErrors, setBenErrors] = useState<Errors>({});
  const [respErrors, setRespErrors] = useState<Errors>({});
  const [showForm, setShowForm] = useState(false);
  const [showResp, setShowResp] = useState(false);
  const [cuil, setCuil] = useState("");
  const [dni, setDni] = useState("");
  const [sexo, setSexo] = useState("");
  const [cuilAlert, setCuilAlert] = useState<Alert>(null);
  const [respAlert, setRespAlert] = useState<Alert>(null);
  const [encontrado, setEncontrado] = useState<string | null>(null);
  const [busy, setBusy] = useState<"" | "cuil" | "resp" | "submit" | "uncertain">("");
  const benGeo = useGeo(data.urls);
  const respGeo = useGeo(data.urls);
  const focusFirst = useRef(false);

  useEffect(() => {
    if (!focusFirst.current) return;
    focusFirst.current = false;
    const first = document.querySelector<HTMLElement>(".is-invalid");
    first?.scrollIntoView?.({ behavior: "smooth", block: "center" });
    first?.focus();
  });

  const clearError = (setter: (f: (e: Errors) => Errors) => void, name: string) => setter((e) => {
    if (!e[name]) return e;
    const next = { ...e }; delete next[name]; return next;
  });
  const setBenValue = (name: string, value: Value) => {
    setBen((v) => ({ ...v, [name]: value }));
    clearError(setBenErrors, name);
    if (name === "estado_academico" && value === false) setBen((v) => ({ ...v, nivel_educativo_actual: "" }));
    if (name === "actividades_extracurriculares" && value === false) setBen((v) => ({ ...v, actividades_detalle: [] }));
  };
  const setRespValue = (name: string, value: Value) => { setResp((v) => ({ ...v, [name]: value })); clearError(setRespErrors, name); };
  function geoChange(g: ReturnType<typeof useGeo>, setValues: (f: (v: Values) => Values) => void) {
    return (name: string, value: string) => {
      if (name === "provincia") {
        g.setGeo((current) => ({ ...current, localidad: BLANK }));
        setValues((v) => ({ ...v, localidad: "" }));
        if (value) void g.municipios(value).then((rows) => g.setGeo((current) => ({ ...current, municipio: rows })));
        else { g.setGeo({ municipio: BLANK, localidad: BLANK }); setValues((v) => ({ ...v, municipio: "" })); }
      }
      if (name === "municipio") {
        if (value) void g.localidades(value).then((rows) => g.setGeo((current) => ({ ...current, localidad: rows })));
        else g.setGeo((current) => ({ ...current, localidad: BLANK }));
      }
    };
  }

  async function buscarCuil() {
    const raw = cuil.trim();
    if (!raw) { preinscripcionBrowser.alert("Debe ingresar un CUIL"); return; }
    setBusy("cuil");
    try {
      const { data: body } = await client.get(`${API}buscar-cuil/?cuil=${encodeURIComponent(raw.replace(/-/g, ""))}`, { validateStatus: () => true });
      setCuilAlert(null);
      if (!record(body)) return;
      if (body.status === "exists") { setCuilAlert({ className: "alert alert-warning text-center", message: String(body.message) }); setShowForm(false); }
      else if (body.status === "not_found") { setCuilAlert({ className: "alert alert-danger text-center", message: String(body.message) }); setShowForm(false); }
      else if (body.status === "possible" && record(body.data)) {
        setShowForm(true);
        const datos = body.data;
        setBen((v) => {
          const next = { ...v };
          for (const [key, value] of Object.entries(datos)) if (key in next && typeof next[key] === "string") next[key] = value === null || value === undefined || value === "" ? "" : String(value);
          return next;
        });
      }
    } catch (err) {
      setCuilAlert({ className: "alert alert-danger", message: `Error al buscar CUIL: ${String(err)}` });
      setShowForm(false);
    } finally {
      setBusy("");
    }
  }

  async function llenarResponsable(datos: Record<string, unknown>) {
    const values = initialValues(data.responsable);
    for (const [key, value] of Object.entries(datos)) if (key in values && typeof values[key] === "string") values[key] = value === null || value === undefined ? "" : String(value);
    respGeo.setGeo({ municipio: BLANK, localidad: BLANK });
    setResp(values);
    setRespErrors({});
    if (text(values.provincia) && values.provincia) {
      const municipios = await respGeo.municipios(values.provincia);
      const localidades = values.municipio ? await respGeo.localidades(String(values.municipio)) : BLANK;
      respGeo.setGeo({ municipio: municipios, localidad: localidades });
      setResp((v) => ({ ...v, municipio: values.municipio, localidad: values.localidad }));
    }
  }

  async function buscarResponsable() {
    setRespAlert(null);
    if (!dni.trim() || !sexo) {
      setRespAlert({ className: "alert alert-danger text-center", message: "Debe ingresar DNI y seleccionar sexo" });
      setShowResp(false);
      return;
    }
    setBusy("resp");
    try {
      const { data: body } = await client.get(`${API}buscar-responsable/?dni=${encodeURIComponent(dni.trim())}&sexo=${encodeURIComponent(SEXO[sexo])}`,
        { validateStatus: () => true });
      if (record(body) && (body.status === "exists" || body.status === "possible") && record(body.data)) {
        setEncontrado(body.status === "exists" ? String(body.message) : null);
        setShowResp(true);
        await llenarResponsable(body.data);
      } else {
        setEncontrado(null);
        setRespAlert({ className: "alert alert-danger text-center", message: record(body) && text(body.message) && body.message ? body.message : "No se encontró el Responsable" });
        setShowResp(false);
      }
    } catch (err) {
      setRespAlert({ className: "alert alert-danger text-center", message: `Error al consultar Responsable: ${String(err)}` });
      setShowResp(false);
    } finally {
      setBusy("");
    }
  }

  function validar() {
    const be: Errors = {}, re: Errors = {};
    for (const name of BENEFICIARIO_REQUIRED) {
      const value = ben[name];
      if (value === undefined) continue;
      if (Array.isArray(value) ? value.length === 0 : !String(value).trim()) be[name] = [REQUIRED];
    }
    for (const name of RESPONSABLE_REQUIRED) {
      const value = resp[name];
      if (value !== undefined && !String(value).trim()) re[name] = [REQUIRED];
    }
    if (ben.actividades_extracurriculares === true && !(ben.actividades_detalle as string[]).length) be.__detalle = ["Debe seleccionar al menos una actividad"];
    return { be, re };
  }

  function cuerpo() {
    const form = new FormData();
    form.append("csrfmiddlewaretoken", csrfToken());
    for (const f of data.beneficiario) {
      const value = ben[f.name];
      if (f.kind === "checkbox") form.append(`beneficiario_${f.name}`, String(value === true));
      else if (Array.isArray(value)) value.forEach((v) => form.append(`beneficiario_${f.name}`, v));
      else if (value) form.append(`beneficiario_${f.name}`, String(value));
    }
    for (const h of HIDDEN) if (ben[h]) form.append(`beneficiario_${h}`, String(ben[h]));
    for (const f of data.responsable) {
      const value = resp[f.name];
      if (f.kind === "checkbox") form.append(`responsable_${f.name}`, String(value === true));
      else if (value) form.append(`responsable_${f.name}`, String(value));
    }
    return form;
  }

  async function confirmar(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (!showForm || !showResp) { preinscripcionBrowser.alert("Debe completar la búsqueda de beneficiario y responsable antes de confirmar"); return; }
    const { be, re } = validar();
    setBenErrors(be); setRespErrors(re);
    if (Object.keys(be).length || Object.keys(re).length) { focusFirst.current = true; return; }
    setBusy("submit");
    try {
      const { data: body, status } = await client.post(`${API}preinscripcion/`, cuerpo(), { validateStatus: () => true });
      if (status === 200 && record(body) && body.status === "success") { done(); return; }
      if (status === 504 || !record(body)) { setBusy("uncertain"); return; }
      if (record(body.errors)) {
        const errores = body.errors as Record<string, unknown>;
        const pick = (v: unknown): Errors => (record(v) ? Object.fromEntries(Object.entries(v).filter(([, m]) => Array.isArray(m)).map(([k, m]) => [k, (m as unknown[]).map(String)])) : {});
        setBenErrors(pick(errores.beneficiario)); setRespErrors(pick(errores.responsable));
      }
      preinscripcionBrowser.alert(`Error al enviar los datos: ${text(body.message) && body.message ? body.message : "Error en el servidor"}`);
      setBusy("");
    } catch {
      setBusy("uncertain");
    }
  }

  const onEnter = (action: () => void) => (e: KeyboardEvent<HTMLInputElement>) => { if (e.key === "Enter") { e.preventDefault(); action(); } };
  const maskCuil = (raw: string) => {
    let value = raw.replace(/\D/g, "");
    if (value.length > 2) value = `${value.slice(0, 2)}-${value.slice(2)}`;
    if (value.length > 11) value = `${value.slice(0, 11)}-${value.slice(11, 13)}`;
    return value;
  };

  return (
    <div className="container mt-4">
      {/* `includes/base.html` loads the Select2 sheets in the head; the page adds its own. */}
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/duplasSelect2.min.css" />
      <div className="row mt-4">
        <div className="col-md-7 mx-auto">
          <div className="card card-primary card-outline">
            <div className="card-body">
              <SearchAlert id="resultado" alert={cuilAlert} />
              <div className="row align-items-center justify-content-center">
                <div className="col-auto mt-2 mb-2"><h5 className="mb-0">Buscar Preinscripto por CUIL</h5></div>
                <div className="col-auto mt-2 mb-2">
                  <div className="input-group">
                    <input type="text" id="cuil-input" className="form-control" placeholder="__-________-_" maxLength={13} size={13} value={cuil}
                      onChange={(e) => setCuil(maskCuil(e.target.value))} onKeyDown={onEnter(() => void buscarCuil())} />
                    <button type="button" id="buscar-btn" className="btn btn-primary" disabled={busy === "cuil" || undefined} onClick={() => void buscarCuil()}>
                      {busy === "cuil" ? <Spinner label="Buscando..." /> : "Buscar"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div id="form-container" style={{ display: showForm ? "block" : "none" }}>
        <div className="row mt-4">
          <div className="card">
            <div className="card-header"><h5 className="my-1">Completar el formulario de Beneficiario</h5></div>
            <div className="card-body">
              <form method="post" id="beneficiario-form" onSubmit={(e) => e.preventDefault()}>
                <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
                <div className="row g-3">
                  <FormFields fields={data.beneficiario} values={ben} errors={benErrors} set={setBenValue} geo={benGeo.geo}
                    onGeo={geoChange(benGeo, setBen)}
                    hidden={{ nivel_educativo_actual: ben.estado_academico !== true, actividades_detalle: ben.actividades_extracurriculares !== true }} />
                  {HIDDEN.map((h) => <input key={h} type="hidden" name={h} id={`id_${h}`} value={String(ben[h] ?? "")} />)}
                </div>
              </form>
            </div>
          </div>
          <div className="row mt-4">
            <div className="col-md-10 mx-auto">
              <div className="card card-primary card-outline">
                <div className="card-body">
                  <SearchAlert id="resultado_responsable" alert={respAlert} />
                  <div className="row align-items-center justify-content-center">
                    <div className="col-auto mt-2 mb-2"><h5 className="mb-0">Buscar Responsable por DNI</h5></div>
                    <div className="col-auto mt-2 mb-2">
                      <div className="input-group">
                        <input type="text" id="dni-input" className="form-control" maxLength={8} pattern="\d{8}" inputMode="numeric" size={10} value={dni}
                          onChange={(e) => setDni(e.target.value.replace(/\D/g, "").slice(0, 8))} onKeyDown={onEnter(() => void buscarResponsable())} />
                      </div>
                    </div>
                    <div className="col-auto mt-2 mb-2">
                      {[["femenino", "Femenino"], ["masculino", "Masculino"]].map(([value, label]) => (
                        <Fragment key={value}>
                          <div className="form-check form-check-inline">
                            <input className="form-check-input" type="radio" name="sexo_resposable" id={value} value={value} checked={sexo === value}
                              onChange={() => setSexo(value)} />{" "}
                            <label className="form-check-label" htmlFor={value}>{label}</label>
                          </div>{" "}
                        </Fragment>
                      ))}
                    </div>
                    <div className="col-auto mt-2 mb-2">
                      <button type="button" id="buscar-responsable-btn" className="btn btn-primary" disabled={busy === "resp" || undefined}
                        onClick={() => void buscarResponsable()}>
                        {busy === "resp" ? <Spinner label="Buscando..." /> : "Buscar"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div id="responsable-form-container" style={{ display: showResp ? "block" : "none" }}>
        <div className="row mt-4">
          <div className="card">
            <div className="card-header"><h5 className="my-1">Completar el formulario de Responsable</h5></div>
            <div className="card-body">
              <form method="post" id="responsable-form" onSubmit={(e) => e.preventDefault()}>
                <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
                <div id="responsable-alert-container">
                  {encontrado !== null && (
                    <div className="alert alert-warning alert-dismissible fade show mt-3 mb-3 text-center" role="alert">
                      <i className="fas fa-exclamation-triangle me-2" /><strong>Responsable encontrado:</strong>{` ${encontrado}`}
                      <button type="button" className="btn-close" data-bs-dismiss="alert" aria-label="Close" onClick={() => setEncontrado(null)} />
                    </div>
                  )}
                </div>
                <div className="row g-3">
                  <FormFields fields={data.responsable} values={resp} errors={respErrors} set={setRespValue} geo={respGeo.geo} onGeo={geoChange(respGeo, setResp)} />
                </div>
              </form>
            </div>
          </div>
        </div>
        {busy === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
        <div className="row mt-4 mb-3">
          <div className="d-flex justify-content-center">
            <button id="submit-todos-btn" className="btn btn-primary me-3" disabled={busy === "submit" || busy === "uncertain" || undefined}
              onClick={(e) => void confirmar(e)}>
              {busy === "submit" ? <Spinner label="Procesando..." /> : "Confirmar Preinscripción"}
            </button>{" "}
            <button type="button" className="btn btn-secondary" data-page-reload="true" onClick={() => preinscripcionBrowser.reload()}>Cancelar</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function PreinscripcionPage() {
  const state = useCdfPage(`${API}preinscripcion/options/`, preinscripcionValid);
  return renderCdf(state, (data) => ({
    title: "Preinscripto",
    heading: "Formulario de Preinscripto",
    breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <PreinscripcionContent data={data} />,
  }));
}
