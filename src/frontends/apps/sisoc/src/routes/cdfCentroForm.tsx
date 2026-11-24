/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Fragment, useEffect, useRef, useState, type FormEvent } from "react";
import { client, csrfToken, integer, internal, messagesValid, navigation, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import type { RouteDefinition } from "./types";

/**
 * CDF04.02: `centros/centro_form.html` (create and edit, crispy fields,
 * `centro_form.js` visibility and geography, `map_pin_editor.html`) and
 * `centros/centro_confirm_delete.html` (`components/delete_confirm.html` with
 * the cascade preview). Saving goes to `/api/web/cdf/`, which runs the native
 * view; a confirmed save returns to the native URL, where the queued message
 * shows once. A POST is never retried.
 */
const API = "web/cdf/centros/";
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

type Choice = { value: string; label: string };
type Field = {
  name: string; label: string; required: boolean; disabled: boolean; widget: string; help_text: string;
  value: string | boolean; attrs: Record<string, string>; choices?: Choice[]; current?: { name: string; url: string } | null;
};
type FieldError = { message: string; code: string };
export type CentroFormData = {
  fields: Field[]; locked: string[]; errors: Record<string, FieldError[]>; non_field_errors: string[];
  urls: { cancel: string; municipios: string; localidades: string; address_preview: string };
  messages: CdfMessage[];
};

const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && text(f.label) && typeof f.required === "boolean" &&
  typeof f.disabled === "boolean" && text(f.widget) && text(f.help_text) && (text(f.value) || typeof f.value === "boolean") &&
  record(f.attrs) && Object.values(f.attrs).every(text) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label)))) &&
  (f.current === undefined || f.current === null || (record(f.current) && text(f.current.name) && text(f.current.url)));

export function formValid(v: unknown): v is CentroFormData {
  if (!record(v) || !record(v.urls) || !record(v.errors)) return false;
  return Array.isArray(v.fields) && v.fields.every(fieldValid) && Array.isArray(v.locked) && v.locked.every(text) &&
    Object.values(v.errors).every((list) => Array.isArray(list) && list.every((e) => record(e) && text(e.message) && text(e.code))) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && text(v.urls.cancel) &&
    ["municipios", "localidades", "address_preview"].every((k) => internal((v.urls as Record<string, unknown>)[k])) && messagesValid(v.messages);
}

// `centro_form.js`: the visible wrappers per tipo (its `div_id_sitioweb`/`div_id_linkredes`
// never match the form's `sitio_web`/`link_redes`, so those stay hidden, as today).
const COMUNES = ["tipo"];
const FARO = ["nombre", "codigo", "organizacion_asociada", "foto", "referente", "activo", "provincia", "municipio", "localidad", "calle",
  "numero", "latitud", "longitud", "domicilio_actividad", "telefono", "celular", "correo", "sitioweb", "linkredes", "nombre_referente",
  "apellido_referente", "telefono_referente", "correo_referente"];
const ADHERIDO = [...FARO.slice(0, 3), "faro_asociado", ...FARO.slice(3)];
const visibleFor = (tipo: string) => new Set(tipo === "faro" ? [...COMUNES, ...FARO] : tipo === "adherido" ? [...COMUNES, ...ADHERIDO] : COMUNES);
const INPUT_CLASS: Record<string, string> = { text: "textinput", number: "numberinput", email: "emailinput", url: "urlinput" };

type Geo = { id: number; nombre: string };
/** Core geography endpoints (`/ajax/load-*`), same session; replaceable in tests. */
export const geography = {
  load: (url: string): Promise<unknown> => fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } }).then((r) => r.json()),
};
const geoValid = (v: unknown): v is Geo[] => Array.isArray(v) && v.every((g) => record(g) && integer(g.id) && text(g.nombre));

function Label({ field }: { field: Field }) {
  return (
    <label htmlFor={`id_${field.name}`} className={`form-label${field.required ? " requiredField" : ""}`}>
      {field.label}{field.required && <span className="asteriskField">*</span>}
    </label>
  );
}

function Feedback({ field, errors }: { field: Field; errors: FieldError[] }) {
  return <>
    {errors.map((e, i) => <span key={i} id={`error_${i + 1}_id_${field.name}`} className="invalid-feedback"><strong>{e.message}</strong></span>)}
    {field.help_text && <div id={`id_${field.name}_helptext`} className="form-text">{field.help_text}</div>}
  </>;
}

/** `map_pin_editor.html` driven by the shared engine (`mapPinEditor.js`, `pin:init`/`pin:destroy`). */
const loaded = new Map<string, Promise<void>>();
function loadScript(src: string, integrity?: string) {
  if (!loaded.has(src)) loaded.set(src, new Promise<void>((resolve) => {
    const element = document.createElement("script");
    element.src = src;
    if (integrity) { element.integrity = integrity; element.crossOrigin = "anonymous"; }
    // Like the native page, the engine loads even when Leaflet does not.
    element.onload = () => resolve();
    element.onerror = () => { loaded.delete(src); resolve(); };
    document.head.appendChild(element);
  }));
  return loaded.get(src)!;
}

function MapPinEditor({ hidden, searchUrl }: { hidden: boolean; searchUrl: string }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let active = true;
    const element = root.current;
    loadScript("https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js", "sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH")
      .then(() => loadScript("/static/custom/js/mapPinEditor.js?v=2778-6"))
      .then(() => { if (active) document.dispatchEvent(new Event("pin:init")); });
    return () => { active = false; element?.querySelector("[data-pin-editor]")?.dispatchEvent(new Event("pin:destroy")); };
  }, []);
  useEffect(() => { if (!hidden) window.dispatchEvent(new Event("resize")); }, [hidden]);
  return (
    <div ref={root} data-centro-location-editor="" hidden={hidden}>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossOrigin="anonymous" />
      <link rel="stylesheet" href="/static/custom/css/mapPinEditor.css" />
      <div data-pin-editor="" data-always-visible="true" data-latitude-field="id_latitud" data-longitude-field="id_longitud" data-preview-frame=""
        data-generic-search="true" data-search-url={searchUrl} data-location-url="" data-address-fields="id_calle,id_numero,id_provincia,id_municipio,id_localidad">
        <button type="button" className="btn btn-secondary mb-2" data-pin-start="">Buscar dirección en el mapa</button>
        <div data-pin-panel="">
          <p>Arrastrá el pin hasta la ubicación correcta. El domicilio escrito se conserva. Los cambios se guardan al guardar el formulario.</p>
          <div className="map-pin-editor" data-pin-map="" aria-label="Mapa para ajustar la ubicación" />
          <div className="d-flex flex-wrap gap-2 my-2">
            <button type="button" className="btn btn-secondary" data-pin-center="">Colocar pin en el centro del mapa</button>{" "}
            <button type="button" className="btn btn-secondary" data-pin-cancel="">Descartar ajuste del pin</button>
          </div>
        </div>
        <p className="text-muted" role="status" aria-live="polite" data-pin-status="" />
      </div>
    </div>
  );
}

export function CentroFormContent({ data, endpoint }: { data: CentroFormData; endpoint: string }) {
  const [form, setForm] = useState(data);
  const byName = new Map(form.fields.map((f) => [f.name, f]));
  const initial = (name: string) => String(byName.get(name)?.value ?? "");
  const [tipo, setTipo] = useState(initial("tipo"));
  const [municipios, setMunicipios] = useState<{ options: Choice[]; fetched: Set<string> }>(() => ({ options: byName.get("municipio")?.choices ?? [], fetched: new Set() }));
  const [localidades, setLocalidades] = useState<Choice[]>(() => byName.get("localidad")?.choices ?? []);
  const [state, setState] = useState<"idle" | "sending" | "uncertain">("idle");
  const visible = visibleFor(tipo);

  async function cargar(url: string): Promise<Choice[]> {
    try {
      const rows = await geography.load(url);
      return geoValid(rows) ? rows.map((g) => ({ value: String(g.id), label: g.nombre })) : [];
    } catch {
      return [];
    }
  }
  function onProvincia(value: string) {
    setMunicipios({ options: [{ value: "", label: "Seleccionar municipio..." }], fetched: new Set() });
    setLocalidades([{ value: "", label: "Seleccionar localidad..." }]);
    if (!value) return;
    void cargar(`${form.urls.municipios}?provincia_id=${encodeURIComponent(value)}`).then((rows) =>
      setMunicipios({ options: [{ value: "", label: "Seleccionar municipio..." }, ...rows], fetched: new Set(rows.map((r) => r.value)) }));
  }
  function onMunicipio(value: string) {
    setLocalidades([{ value: "", label: "Seleccionar localidad..." }]);
    // Only options loaded by the province change carry `data-municipio-id`.
    if (!value || !municipios.fetched.has(value)) return;
    void cargar(`${form.urls.localidades}?municipio_id=${encodeURIComponent(value)}`).then((rows) =>
      setLocalidades([{ value: "", label: "Seleccionar localidad..." }, ...rows]));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state !== "idle") return;
    setState("sending");
    try {
      const { data: body, status } = await client.post(endpoint, new FormData(event.currentTarget), { validateStatus: (s: number) => s === 200 || s === 201 || s === 400 });
      if ((status === 200 || status === 201) && record(body) && internal(body.url)) { navigation.assign(body.url); return; }
      if (status === 400 && formValid(body)) { setForm(body); setState("idle"); return; }
      setState("uncertain");
    } catch {
      setState("uncertain");
    }
  }

  return (
    <>
      <div className="card card-body shadow">
        <h2 className="text-center mb-4" />
        {state === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
        <form method="post" encType="multipart/form-data" onSubmit={submit} key={JSON.stringify(form.errors)}>
          <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
          {form.non_field_errors.length > 0 && (
            <div className="alert alert-danger" role="alert"><ul className="errorlist nonfield">{form.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul></div>
          )}
          {form.fields.map((field) => {
            const errors = form.errors[field.name] ?? [];
            const id = `id_${field.name}`;
            const style = { display: visible.has(field.name) ? "block" : "none" };
            const invalid = errors.length ? " is-invalid" : "";
            const common = { name: field.name, id, disabled: field.disabled || undefined, required: field.required || undefined };
            let control;
            if (field.widget === "hidden") {
              return <input key={field.name} type="hidden" {...common} required={undefined} defaultValue={String(field.value)} />;
            }
            if (field.widget === "checkbox") {
              control = (
                <div className="mb-3">
                  <div id={`div_${id}`} className="form-check" style={style}>
                    <input type="checkbox" {...common} className={`checkboxinput form-check-input${invalid}`} defaultChecked={field.value === true} />
                    <label htmlFor={id} className="form-check-label">{field.label}</label>
                    <Feedback field={field} errors={errors} />
                  </div>
                </div>
              );
              return <Fragment key={field.name}>{control}</Fragment>;
            }
            if (field.widget === "select") {
              const options = field.name === "municipio" ? municipios.options : field.name === "localidad" ? localidades : field.choices ?? [];
              control = (
                <select {...common} className={`select form-select${invalid}`} defaultValue={String(field.value)}
                  key={field.name === "municipio" || field.name === "localidad" ? options.map((o) => o.value).join(",") : field.name}
                  onChange={(e) => {
                    if (field.name === "tipo") setTipo(e.target.value);
                    if (field.name === "provincia") onProvincia(e.target.value);
                    if (field.name === "municipio") onMunicipio(e.target.value);
                  }}>
                  {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              );
            } else if (field.widget === "file") {
              control = (
                <div>
                  {field.current && <>Actualmente: <a href={field.current.url}>{field.current.name}</a><br />Modificar: </>}
                  <input type="file" name={field.name} className={`form-control${invalid}`} accept="image/*" id={id} />
                </div>
              );
            } else {
              control = (
                <input type={field.widget} {...common} {...field.attrs} className={`${INPUT_CLASS[field.widget] ?? "textinput"} form-control${invalid}`}
                  defaultValue={String(field.value)} />
              );
            }
            return (
              <Fragment key={field.name}>
                <div id={`div_${id}`} className="mb-3" style={style}>
                  <Label field={field} />
                  {control}
                  <Feedback field={field} errors={errors} />
                </div>
                {field.name === "longitud" && <MapPinEditor hidden={!["faro", "adherido"].includes(tipo)} searchUrl={form.urls.address_preview} />}
              </Fragment>
            );
          })}
          <div className="text-center mt-4">
            <button type="submit" className="btn btn-primary" disabled={state !== "idle" || undefined}>Guardar</button>{" "}
            {/* `href=""` (no cancel URL in the native context) reloads the page; React drops an empty href. */}
            <a ref={(el) => { el?.setAttribute("href", form.urls.cancel); }} className="btn btn-secondary">Cancelar</a>
          </div>
        </form>
      </div>
    </>
  );
}

function CentroForm({ id }: { id?: string }) {
  const read = id ? `${API}${id}/editar/` : `${API}options/${window.location.search}`;
  const write = id ? `${API}${id}/editar/` : `${API}crear/${window.location.search}`;
  const state = useCdfPage(read, formValid);
  return renderCdf(state, (data) => ({
    title: "Nuevo Centro",
    breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <CentroFormContent data={data} endpoint={write} />,
  }));
}

// --- Delete (`components/delete_confirm.html`) ------------------------------

type Desglose = { modelo: string; cantidad: number; modo: string; ejemplos: string[] };
export type CentroDeleteData = {
  id: number; nombre: string; confirm_text: string; cancel_text: string;
  preview: { total_afectados: number; total_baja_logica?: number; total_borrado_fisico?: number; desglose_por_modelo: Desglose[] } | null;
  urls: { cancel: string }; messages: CdfMessage[];
};

export function deleteValid(v: unknown): v is CentroDeleteData {
  if (!record(v) || !record(v.urls)) return false;
  const p = v.preview;
  return integer(v.id) && text(v.nombre) && text(v.confirm_text) && text(v.cancel_text) && internal(v.urls.cancel) && messagesValid(v.messages) &&
    (p === null || (record(p) && integer(p.total_afectados) && Array.isArray(p.desglose_por_modelo) &&
      p.desglose_por_modelo.every((d) => record(d) && text(d.modelo) && integer(d.cantidad) && text(d.modo) && Array.isArray(d.ejemplos) && d.ejemplos.every(text))));
}

export function CentroDeleteContent({ data }: { data: CentroDeleteData }) {
  const [state, setState] = useState<"idle" | "sending" | "uncertain">("idle");
  const p = data.preview;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state !== "idle") return;
    setState("sending");
    try {
      const { data: body } = await client.post(`${API}${data.id}/eliminar/`, new FormData(event.currentTarget));
      if (record(body) && internal(body.url)) { navigation.assign(body.url); return; }
      setState("uncertain");
    } catch {
      setState("uncertain");
    }
  }
  return (
    <div className="error-page mt-5 px-3">
      <div className="error-content">
        <h3><i className="fas fa-exclamation-triangle text-danger px-2" /> Atención!</h3>
        <p>
          ¿Estás seguro que deseas realizar una baja lógica en cascada del registro{" "}
          <span className="font-weight-bold">{data.nombre.toUpperCase()}</span>?
        </p>
        {p && <>
          <div className="alert alert-info">
            <div><strong>Total de registros afectados:</strong> {p.total_afectados}</div>
            {!!p.total_baja_logica && <div>Bajas lógicas: {p.total_baja_logica}</div>}
            {!!p.total_borrado_fisico && <div>Borrados físicos técnicos: {p.total_borrado_fisico}</div>}
          </div>
          <div className="table-responsive mb-3">
            <table className="table table-sm table-striped mb-0">
              <thead><tr><th>Modelo</th><th>Cantidad</th><th>Acción</th><th>Ejemplos</th></tr></thead>
              <tbody>
                {p.desglose_por_modelo.map((d) => (
                  <tr key={d.modelo}>
                    <td>{d.modelo}</td>
                    <td>{d.cantidad}</td>
                    <td>{d.modo === "baja_logica" ? "Baja lógica" : "Borrado físico técnico"}</td>
                    <td>{d.ejemplos.length ? d.ejemplos.join(", ") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>}
        {state === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
        <div className="text-left">
          <form method="post" action="" onSubmit={submit}>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
            <button type="submit" className="btn btn-danger btn-sm" disabled={state !== "idle" || undefined}>{data.confirm_text}</button>{" "}
            <a href={data.urls.cancel} className="btn btn-secondary btn-sm">{data.cancel_text}</a>
          </form>
        </div>
      </div>
    </div>
  );
}

function CentroDelete({ id }: { id: string }) {
  const state = useCdfPage(`${API}${id}/eliminar/`, deleteValid);
  return renderCdf(state, (data) => ({
    title: "Confirmar Eliminación",
    breadcrumb: null,
    content: <CentroDeleteContent data={data} />,
  }));
}

// --- Route ------------------------------------------------------------------

type FormParams = { id?: string; action: "nuevo" | "editar" | "eliminar" };

// Native URLs of the CDF centre create, edit and delete (CDF04.02).
export const cdfCentroFormRoute: RouteDefinition<FormParams> = {
  name: "cdf-centro-form",
  match: (pathname) => {
    if (pathname === "/centrodefamilia/centros/nuevo/") return { action: "nuevo" };
    const m = /^\/centrodefamilia\/centros\/([1-9]\d*)\/(editar|eliminar)\/$/.exec(pathname);
    return m ? { id: m[1], action: m[2] as "editar" | "eliminar" } : null;
  },
  render: ({ id, action }) => (action === "eliminar" && id ? <CentroDelete id={id} /> : <CentroForm id={id} />),
};
