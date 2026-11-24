/* eslint-disable react-refresh/only-export-components -- route module: validators, seams and sections are exported for the tests. */
import { Fragment, useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { internal, record, renderMain, text, useMainResource, webClient, accepted } from "./MainFrame";
import Select2 from "./select2";
import type { RouteDefinition } from "./types";

/**
 * C05.02 "Alta y edición de ciudadano": `ciudadanos/ciudadano_form.html` (create and edit share it). GET
 * `/api/web/ciudadanos/crear/` (`?dni=&sexo=` runs the native RENAPER search) and `/api/web/ciudadanos/<pk>/editar/` run the
 * native view and return its form field by field; the multipart POST runs the native `post()` (identity rules, unique
 * identity, photo in the native storage). A saved form is a redirect to the ficha (full-page navigation, the message waits in
 * the queue); a rejected one comes back as 400 with the bound values and errors. The inline scripts of the template (identity
 * blocks, progress badges, cascading geography, photo preview) are reproduced here.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Choice = { value: string; label: string };
type Field = {
  name: string; label: string; required: boolean; disabled: boolean; help_text: string;
  widget: "text" | "number" | "email" | "date" | "select" | "checkbox" | "textarea" | "file";
  value: string | boolean; attrs: Record<string, string>; choices?: Choice[]; current?: { name: string; url: string; initial_text: string; clear_label: string; input_text: string } | null;
};
export type FormularioData = {
  modo: "crear" | "editar"; fields: Field[]; errors: Record<string, string[]>; non_field_errors: string[];
  fecha_nacimiento_inicial: string;
  revision: { sin_dni: boolean; no_validado: boolean; motivo_texto: string; descripcion_texto: string } | null;
  busqueda: { dni: string; sexo: string; sexos: Choice[] } | null;
  urls: { volver: string; municipios: string; localidades: string; address_preview: string };
  messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const WIDGETS = ["text", "number", "email", "date", "select", "checkbox", "textarea", "file"];
const choices = (v: unknown) => Array.isArray(v) && v.every((c) => record(c) && text(c.value) && text(c.label));
const UNCERTAIN = "No se pudo guardar el ciudadano. Recargá la página para ver el estado actual.";

const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && text(f.label) && typeof f.required === "boolean" && typeof f.disabled === "boolean" &&
  text(f.help_text) && text(f.widget) && WIDGETS.includes(f.widget) && (text(f.value) || typeof f.value === "boolean") &&
  record(f.attrs) && Object.values(f.attrs).every(text) && (f.choices === undefined || choices(f.choices)) &&
  (f.current === undefined || f.current === null || (record(f.current) && text(f.current.name) && text(f.current.url) && text(f.current.initial_text) && text(f.current.clear_label) && text(f.current.input_text)));

export function formularioValid(v: unknown): v is FormularioData {
  if (!record(v) || !record(v.urls) || !record(v.errors)) return false;
  const r = v.revision, b = v.busqueda;
  return (v.modo === "crear" || v.modo === "editar") && Array.isArray(v.fields) && v.fields.every(fieldValid) &&
    Object.values(v.errors).every((e) => Array.isArray(e) && e.every(text)) && Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) &&
    text(v.fecha_nacimiento_inicial) &&
    (r === null || (record(r) && typeof r.sin_dni === "boolean" && typeof r.no_validado === "boolean" && text(r.motivo_texto) && text(r.descripcion_texto))) &&
    (b === null || (record(b) && text(b.dni) && text(b.sexo) && choices(b.sexos))) &&
    internal(v.urls.volver) && internal(v.urls.municipios) && internal(v.urls.localidades) && internal(v.urls.address_preview) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Replaceable in tests: the confirmed redirect and the history back are full-page navigations, like the native ones. */
export const ciudadanoFormNavigation = { assign: (to: string) => window.location.assign(to), back: () => window.history.back() };
type Geo = { id: number; nombre: string };
/** Core geography endpoints (`/ajax/load-*`), same session; replaceable in tests. */
export const geografia = {
  load: (url: string): Promise<unknown> => fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } }).then((r) => r.json()),
};
const geoValid = (v: unknown): v is Geo[] => Array.isArray(v) && v.every((g) => record(g) && Number.isSafeInteger(g.id) && text(g.nombre));

// --- Sections (progress badges and collapse) ------------------------------------------------

const SECCIONES = ["identidad", "domicilio", "contacto", "estado", "documentacion"] as const;
type Seccion = (typeof SECCIONES)[number];
const CABECERAS: Record<Seccion, [string, string, string]> = {
  identidad: ["fa-id-card", "Datos personales", "Identidad y documentación principal"],
  domicilio: ["fa-map-marker-alt", "Domicilio y ubicación", "Provincia, municipio y dirección declarada"],
  contacto: ["fa-phone-alt", "Contacto", "Datos de comunicación"],
  estado: ["fa-toggle-on", "Estado y notas", "Activación y observaciones internas"],
  documentacion: ["fa-camera", "Documentación", "Foto de legajo del ciudadano"],
};
/** Fields of every section, in the order of the template. No input is `required` in the markup, so every section is "optional". */
const CAMPOS_SECCION: Record<Seccion, string[]> = {
  identidad: ["tipo_registro_identidad", "motivo_sin_dni", "motivo_sin_dni_descripcion", "motivo_no_validacion_renaper", "motivo_no_validacion_descripcion",
    "apellido", "nombre", "fecha_nacimiento", "tipo_documento", "documento", "sexo", "nacionalidad"],
  domicilio: ["provincia", "municipio", "localidad", "barrio", "calle", "altura", "piso_departamento", "codigo_postal", "latitud", "longitud"],
  contacto: ["telefono", "telefono_alternativo", "email"],
  estado: ["activo", "observaciones"],
  documentacion: ["foto"],
};

type Values = Record<string, string | boolean>;

function Cabecera({ id, estado, abierta, alternar }: { id: Seccion; estado: "complete" | "empty"; abierta: boolean; alternar: () => void }) {
  const [icono, titulo, subtitulo] = CABECERAS[id];
  return (
    <div className={`section-header${abierta ? "" : " collapsed"}`} data-toggle-section-ciudadano={id} onClick={alternar}>
      <div className="section-header-left">
        <div className="section-icon"><i className={`fas ${icono}`} /></div>
        <div className="section-title-group"><h3 className="section-title">{titulo}</h3><p className="section-subtitle">{subtitulo}</p></div>
      </div>
      <div className="section-status">
        <span className={`status-badge ${estado}`} id={`status-${id}`}>
          {estado === "complete" ? <><i className="fas fa-check-circle" /> Completo (Opcional)</> : <><i className="fas fa-circle" /> Opcional</>}
        </span>
        <div className="collapse-indicator"><i className="fas fa-chevron-down" /></div>
      </div>
    </div>
  );
}

// --- Fields ---------------------------------------------------------------------------------

type Ctx = {
  by: Map<string, Field>; values: Values; errors: Record<string, string[]>; set: (name: string, v: string | boolean) => void;
  geo: { municipios: Choice[]; localidades: Choice[]; cargando: { municipio: boolean; localidad: boolean }; onProvincia: (v: string) => void; onMunicipio: (v: string) => void };
  parents: Record<string, HTMLElement | null>; setParent: (name: string, el: HTMLElement | null) => void;
};

const aria = (errors: string[], name: string) => (errors.length ? { "aria-invalid": true as const, "aria-describedby": `id_${name}_error` } : {});
const requiredMarks = (f: Field) => f.required && <><span className="text-danger fw-bold" aria-hidden="true">*</span>{" "}<span className="visually-hidden">Campo obligatorio</span></>;
const ErrorLine = ({ errors }: { errors: string[] }) => errors.length > 0 ? <div className="text-danger small mt-1">{errors.join(", ")}</div> : null;
const Help = ({ f }: { f: Field }) => f.help_text ? <small className="form-text text-muted">{f.help_text}</small> : null;

/** Native controls of `{{ field }}` (crispy-free widgets with bootstrap classes). */
function Control({ f, ctx }: { f: Field; ctx: Ctx }) {
  const errors = ctx.errors[f.name] ?? [];
  const id = `id_${f.name}`;
  const value = ctx.values[f.name];
  if (f.widget === "select") {
    const opts = f.name === "municipio" ? ctx.geo.municipios : f.name === "localidad" ? ctx.geo.localidades : f.choices ?? [];
    if (["provincia", "municipio", "localidad", "nacionalidad"].includes(f.name)) {
      const placeholder = { provincia: "Seleccione una provincia", municipio: "Seleccione un municipio", localidad: "Seleccione una localidad", nacionalidad: "Seleccione una nacionalidad" }[f.name];
      return <Select2 id={id} name={f.name} choices={opts} value={[String(value)]} invalid={errors.length > 0} disabled={f.disabled} placeholder={placeholder}
        selectClassName="form-select" selectProps={aria(errors, f.name)} noResults="No hay resultados" hideEmptyChoice clearTrigger="mousedown" focusMarker="container"
        termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown" dropdownParent={f.name === "nacionalidad" ? undefined : ctx.parents[f.name] ?? null}
        onChange={(v) => { const next = v[0] ?? ""; ctx.set(f.name, next); if (f.name === "provincia") ctx.geo.onProvincia(next); if (f.name === "municipio") ctx.geo.onMunicipio(next); }} />;
    }
    return (
      <select name={f.name} className="form-select" id={id} disabled={f.disabled || undefined} value={String(value)} {...aria(errors, f.name)}
        onChange={(e) => ctx.set(f.name, e.target.value)}>
        {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  }
  if (f.widget === "textarea") {
    return <textarea name={f.name} cols={Number(f.attrs.cols ?? 40)} rows={Number(f.attrs.rows ?? 3)} className="form-control" id={id} value={String(value)} {...aria(errors, f.name)}
      onChange={(e) => ctx.set(f.name, e.target.value)} />;
  }
  const { maxlength, min, max, step } = f.attrs;
  return <input type={f.widget} name={f.name} value={String(value)} maxLength={maxlength ? Number(maxlength) : undefined} min={min} max={max} step={step} className="form-control" id={id}
    {...aria(errors, f.name)} onChange={(e) => ctx.set(f.name, e.target.value)} />;
}

/** The `{% with field=... %}` block of the template: label (+ required marks), widget, help and errors. */
function Bloque({ name, ctx, extra, oculto }: { name: string; ctx: Ctx; extra?: "identidad" | "motivo" | "ubicacion"; oculto?: boolean }) {
  const f = ctx.by.get(name);
  if (!f) return null;
  const errors = ctx.errors[name] ?? [];
  const label = extra === "identidad"
    ? <label className="form-label fw-bold" htmlFor={`id_${name}`}>{f.label}{" "}<span className="text-danger fw-bold" aria-hidden="true">*</span></label>
    : extra === "motivo" && name.startsWith("motivo_") && !name.endsWith("descripcion")
      ? <label className="form-label" htmlFor={`id_${name}`}>{f.label}{" "}<span className="text-danger fw-bold">*</span></label>
      : <label className="form-label" htmlFor={`id_${name}`}>{f.label}{f.required && " "}{requiredMarks(f)}</label>;
  if (extra === "ubicacion") {
    const geoName = name as "provincia" | "municipio" | "localidad";
    return (
      <div className="form-group ubicacion-select-group">
        {label}
        {geoName !== "provincia" && <div id={`${name}-loader`} className={`skeleton-loader${ctx.geo.cargando[geoName] ? "" : " d-none"}`} />}
        <div id={`${name}-field`} className="ubicacion-select-wrapper" ref={(el) => ctx.setParent(name, el)}><Control f={f} ctx={ctx} /></div>
        <Help f={f} /><ErrorLine errors={errors} />
      </div>
    );
  }
  return <div className="form-group" style={oculto ? { display: "none" } : undefined}>{label}<Control f={f} ctx={ctx} /><Help f={f} /><ErrorLine errors={errors} /></div>;
}

function Foto({ f, errors, existente, previsualizacion, onFile, onRemove, abrirModal }: {
  f: Field; errors: string[]; existente: Field["current"]; previsualizacion: { src: string; name: string; size: string } | null;
  onFile: (e: ChangeEvent<HTMLInputElement>) => void; onRemove: () => void; abrirModal: (url: string, name: string) => void;
}) {
  const picker = useRef<HTMLInputElement>(null);
  const mostrado = existente?.name.includes("comedor/") ? existente.name.slice(8) : existente?.name;
  return (
    <div className="form-group">
      <label htmlFor="foto-input" className="form-label font-weight-bold text-light">
        <i className="fas fa-camera mr-2" />{" "}Foto de Legajo{f.required && <> <span className="text-danger fw-bold" aria-hidden="true">*</span> <span className="visually-hidden">Campo obligatorio</span></>}
      </label>
      {existente && (
        <div className="foto-legajo-existente mb-3">
          <h6 className="text-light mb-2"><i className="fas fa-image mr-1" />{" "}Foto actual:</h6>
          <div className="foto-existente-container">
            <div className="foto-thumbnail-container" data-image-url={existente.url}>
              <div className="preview-placeholder"><i className="fas fa-image" /><div className="loader"><div className="spinner-border spinner-border-sm" role="status"><span className="sr-only">Cargando...</span></div></div></div>
            </div>
            <div className="foto-info">
              <div className="foto-nombre">{mostrado}</div>
              <div className="foto-status"><i className="fas fa-check-circle text-success" />{" "}<span className="text-success">Guardada</span></div>
            </div>
            <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => abrirModal(existente.url, existente.name)}><i className="fas fa-expand-alt mr-1" />{" "}Ver completa</button>
          </div>
        </div>
      )}
      <div className="nueva-foto-section">
        <h6 className="text-light mb-2"><i className="fas fa-upload mr-1" />{" "}{existente ? "Cambiar foto:" : "Seleccionar foto:"}</h6>
        {existente && <>{existente.initial_text}: <a href={existente.url}>{existente.name}</a>{!f.required && <>{" "}<input type="checkbox" name="foto-clear" id="foto-clear_id" />{" "}<label htmlFor="foto-clear_id">{existente.clear_label}</label></>}<br />{existente.input_text}: </>}
        <input type="file" name="foto" accept="image/*" className="d-none" id="foto-input" ref={picker} onChange={onFile} {...aria(errors, "foto")} />
        <button type="button" id="foto-picker-btn" className="btn-seleccionar mt-2" onClick={() => picker.current?.click()}><i className="fas fa-upload" />{" "}Seleccionar imagen</button>
        <div className={`contador-imagenes mt-2${previsualizacion ? "" : " d-none"}`} id="foto-selected-info"><span id="foto-selected-name">{previsualizacion ? `Imagen seleccionada: ${previsualizacion.name}` : ""}</span></div>
      </div>
      <div id="fotoCiudadanoPreviewContainer" className={`nueva-foto-preview mt-3${previsualizacion ? "" : " d-none"}`}>
        <h6 className="text-light mb-2"><i className="fas fa-eye mr-1" />{" "}Vista previa:</h6>
        <div className="nueva-foto-container">
          <div className="foto-preview-wrapper">
            <img id="fotoCiudadanoPreview" src={previsualizacion?.src} alt="Vista previa de foto legajo" className="foto-preview-img" />
            <button type="button" className="btn-remover-preview" onClick={onRemove}><i className="fas fa-times" /></button>
          </div>
          <div className="foto-preview-info">
            <div className="preview-nombre" id="fotoCiudadanoNombre">{previsualizacion?.name ?? "imagen.jpg"}</div>
            <div className="preview-size" id="fotoCiudadanoSize">{previsualizacion?.size ?? "0 KB"}</div>
            <div className="preview-status"><i className="fas fa-clock text-warning" />{" "}<span className="text-warning">Pendiente de guardar</span></div>
          </div>
        </div>
      </div>
      <ErrorLine errors={errors} />
    </div>
  );
}

// --- Map pin editor (shared engine of the native `map_pin_editor.html`) -----------------------

const cargados = new Map<string, Promise<void>>();
function cargarScript(src: string, integrity?: string) {
  if (!cargados.has(src)) cargados.set(src, new Promise<void>((resolve) => {
    const el = document.createElement("script");
    el.src = src;
    if (integrity) { el.integrity = integrity; el.crossOrigin = "anonymous"; }
    el.onload = () => resolve();
    el.onerror = () => { cargados.delete(src); resolve(); };
    document.head.appendChild(el);
  }));
  return cargados.get(src)!;
}

function MapaPin({ searchUrl }: { searchUrl: string }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let activo = true;
    const el = root.current;
    cargarScript("https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js", "sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH")
      .then(() => cargarScript("/static/custom/js/mapPinEditor.js?v=2778-6"))
      .then(() => { if (activo) document.dispatchEvent(new Event("pin:init")); });
    return () => { activo = false; el?.querySelector("[data-pin-editor]")?.dispatchEvent(new Event("pin:destroy")); };
  }, []);
  return (
    <div ref={root}>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css" integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossOrigin="anonymous" />
      <link rel="stylesheet" href="/static/custom/css/mapPinEditor.css" />
      <div data-pin-editor="" data-always-visible="true" data-latitude-field="id_latitud" data-longitude-field="id_longitud" data-preview-frame="" data-generic-search="true"
        data-search-url={searchUrl} data-location-url="" data-address-fields="id_calle,id_altura,id_provincia,id_municipio,id_localidad">
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

// --- The page -----------------------------------------------------------------------------------

const ISO = /^\d{4}-\d{2}-\d{2}$/;
function valoresIniciales(data: FormularioData): Values {
  return Object.fromEntries(data.fields.filter((f) => f.widget !== "file").map((f) => {
    let v = f.value;
    // The template script: an empty date input takes the instance date in ISO format.
    if (f.name === "fecha_nacimiento") v = ISO.test(String(v)) ? String(v) : data.fecha_nacimiento_inicial;
    return [f.name, v];
  }));
}
const llena = (v: string | boolean | undefined) => (typeof v === "boolean" ? v : String(v ?? "").trim() !== "");
const kb = (size: number) => `${(size / 1024).toFixed(1)} KB`;
const cols: Record<string, string> = {
  tipo_registro_identidad: "col-md-6", apellido: "col-md-4", nombre: "col-md-4", fecha_nacimiento: "col-md-4", tipo_documento: "col-md-4", documento: "col-md-4", sexo: "col-md-4",
  nacionalidad: "col-md-4", provincia: "col-md-4", municipio: "col-md-4", localidad: "col-md-4", barrio: "col-md-3", calle: "col-md-3", altura: "col-md-3", piso_departamento: "col-md-3",
  codigo_postal: "col-md-4", telefono: "col-md-4", telefono_alternativo: "col-md-4", email: "col-md-4", activo: "col-md-4", observaciones: "col-12",
};

export function FormularioContent({ data: inicial, pk }: { data: FormularioData; pk?: string }) {
  const [data, setData] = useState(inicial);
  const [values, setValues] = useState<Values>(() => valoresIniciales(inicial));
  const [abiertas, setAbiertas] = useState<Record<Seccion, boolean>>({ identidad: true, domicilio: true, contacto: true, estado: true, documentacion: true });
  const [tocados, setTocados] = useState<Set<string>>(new Set());
  const [toasts, setToasts] = useState(inicial.messages);
  const [enviando, setEnviando] = useState(false);
  const [municipios, setMunicipios] = useState<Choice[]>(() => inicial.fields.find((f) => f.name === "municipio")?.choices ?? []);
  const [localidades, setLocalidades] = useState<Choice[]>(() => inicial.fields.find((f) => f.name === "localidad")?.choices ?? []);
  const [cargando, setCargando] = useState({ municipio: false, localidad: false });
  const [parents, setParents] = useState<Record<string, HTMLElement | null>>({});
  const [foto, setFoto] = useState<{ src: string; name: string; size: string } | null>(null);
  const [modal, setModal] = useState<{ url: string; name: string } | null>(null);
  const [fotoKey, setFotoKey] = useState(0);
  const busy = useRef(false);
  const by = useMemo(() => new Map(data.fields.map((f) => [f.name, f])), [data]);

  const set = (name: string, v: string | boolean) => {
    setValues((cur) => ({ ...cur, [name]: v }));
    if (typeof v === "boolean") setTocados((cur) => new Set(cur).add(name));
  };
  const vacias = (clave: "municipio" | "localidad"): Choice[] => [{ value: "", label: clave === "municipio" ? "Seleccione un municipio" : "Seleccione una localidad" }];

  async function cargar(url: string): Promise<Choice[]> {
    try {
      const rows = await geografia.load(url);
      return geoValid(rows) ? rows.map((g) => ({ value: String(g.id), label: g.nombre })) : [];
    } catch { return []; }
  }
  async function onProvincia(valor: string) {
    set("municipio", ""); set("localidad", "");
    setMunicipios(vacias("municipio")); setLocalidades(vacias("localidad"));
    if (!valor) return;
    setCargando((c) => ({ ...c, municipio: true }));
    const filas = await cargar(`${data.urls.municipios}?provincia_id=${encodeURIComponent(valor)}`);
    setMunicipios([...vacias("municipio"), ...filas]);
    setCargando((c) => ({ ...c, municipio: false }));
  }
  async function onMunicipio(valor: string) {
    set("localidad", "");
    setLocalidades(vacias("localidad"));
    if (!valor) return;
    setCargando((c) => ({ ...c, localidad: true }));
    const filas = await cargar(`${data.urls.localidades}?municipio_id=${encodeURIComponent(valor)}`);
    setLocalidades([...vacias("localidad"), ...filas]);
    setCargando((c) => ({ ...c, localidad: false }));
  }

  function elegirFoto(event: ChangeEvent<HTMLInputElement>) {
    const archivo = event.target.files?.[0];
    if (!archivo) { setFoto(null); return; }
    const lector = new FileReader();
    lector.onload = () => setFoto({ src: String(lector.result), name: archivo.name, size: kb(archivo.size) });
    lector.readAsDataURL(archivo);
    setFoto({ src: "", name: archivo.name, size: kb(archivo.size) });
  }
  function quitarFoto() {
    const el = document.getElementById("foto-input") as HTMLInputElement | null;
    if (el) el.value = "";
    setFoto(null);
  }

  const tipo = String(values.tipo_registro_identidad ?? "ESTANDAR");
  const estadoSeccion = (s: Seccion): "complete" | "empty" => CAMPOS_SECCION[s].some((n) => {
    if (n === "foto") return foto !== null;
    const f = by.get(n);
    if (!f) return false;
    // Checkboxes only count once the user has changed them (`data-user-modified`).
    return f.widget === "checkbox" ? tocados.has(n) && llena(values[n]) : llena(values[n]);
  }) ? "complete" : "empty";
  const completas = SECCIONES.filter((s) => estadoSeccion(s) === "complete").length;

  function aplicarRechazo(cuerpo: FormularioData) {
    // The native page reloads with the bound form: values, options and errors, sections open, view at the top.
    setData(cuerpo); setValues(valoresIniciales(cuerpo)); setTocados(new Set()); setFoto(null); setFotoKey((k) => k + 1);
    setMunicipios(cuerpo.fields.find((f) => f.name === "municipio")?.choices ?? []);
    setLocalidades(cuerpo.fields.find((f) => f.name === "localidad")?.choices ?? []);
    setAbiertas({ identidad: true, domicilio: true, contacto: true, estado: true, documentacion: true });
    setToasts(cuerpo.messages); resetAfterRejectedPost();
  }

  async function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setEnviando(true);
    try {
      const destino = data.modo === "crear" ? "web/ciudadanos/crear/" : `web/ciudadanos/${pk}/editar/`;
      const { data: cuerpo, status } = await webClient.post(destino, new FormData(event.currentTarget), { validateStatus: (s: number) => accepted(s) || s === 400 });
      if (status >= 200 && status < 300 && record(cuerpo) && internal(cuerpo.redirect)) { ciudadanoFormNavigation.assign(cuerpo.redirect); return; }
      if (status === 403) setToasts([{ message: record(cuerpo) && text(cuerpo.detail) ? cuerpo.detail : UNCERTAIN, level: "error" }]);
      else if (status === 400 && formularioValid(cuerpo)) aplicarRechazo(cuerpo);
      else setToasts([{ message: UNCERTAIN, level: "error" }]);
    } catch {
      setToasts([{ message: UNCERTAIN, level: "error" }]);
    } finally { busy.current = false; setEnviando(false); }
  }

  const ctx: Ctx = {
    by, values, errors: data.errors, set,
    geo: { municipios, localidades, cargando, onProvincia: (v) => void onProvincia(v), onMunicipio: (v) => void onMunicipio(v) },
    parents, setParent: (name, el) => { if (parents[name] !== el && el) setParents((cur) => (cur[name] === el ? cur : { ...cur, [name]: el })); },
  };
  const celda = (name: string, extra?: "identidad" | "motivo" | "ubicacion") => by.has(name) && <div className={cols[name] ?? "col-md-4"}><Bloque name={name} ctx={ctx} extra={extra} /></div>;
  const seccion = (id: Seccion, hijos: ReactNode) => (
    <div className="section-card" data-section={id}>
      <Cabecera id={id} estado={estadoSeccion(id)} abierta={abiertas[id]} alternar={() => setAbiertas((cur) => ({ ...cur, [id]: !cur[id] }))} />
      <div className={`section-body collapse${abiertas[id] ? " show" : ""}`} id={`section-${id}`}>{hijos}</div>
    </div>
  );
  const editando = data.modo === "editar";
  const r = data.revision;

  return (
    <>
      <NativeToasts messages={toasts} />
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/comedorRelevamiento.css" />
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/ciudadanoUbicacion.css" />
      <link rel="stylesheet" href="/static/custom/css/fotos.css" />
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <div><h3 className="mb-0">{editando ? "Actualizar ciudadano" : "Registrar ciudadano"}</h3></div>
        <div className="d-flex gap-2"><a href="#" data-history-back="true" className="btn btn-outline-secondary" onClick={(e) => { e.preventDefault(); ciudadanoFormNavigation.back(); }}>Cancelar</a></div>
      </div>
      {data.busqueda && (
        <div className="card mb-3">
          <div className="card-header font-weight-bold">Buscar Ciudadano</div>
          <div className="card-body">
            <form method="get" className="form-inline">
              <div className="form-group mr-2">
                <label htmlFor="busqueda-dni" className="sr-only">DNI</label>
                <input type="text" className="form-control" name="dni" id="busqueda-dni" placeholder="Ingrese DNI (7-8 digitos)" defaultValue={data.busqueda.dni} />
              </div>
              <div className="form-group mr-2">
                <label htmlFor="busqueda-sexo" className="sr-only">Sexo</label>
                <select name="sexo" id="busqueda-sexo" className="form-control" defaultValue={data.busqueda.sexo}>
                  {data.busqueda.sexos.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>
              <button className="btn btn-secondary mt-3" type="submit">Buscar</button>
            </form>
            <small className="form-text text-muted mt-2">Si existe, se abrira el legajo para edicion. Si no existe, se precargara el formulario con datos de RENAPER.</small>
          </div>
        </div>
      )}
      {r && (
        <div className="alert alert-warning d-flex align-items-start gap-3 mb-3">
          <i className="fas fa-exclamation-triangle fa-lg mt-1" />
          <div>
            <strong>Este ciudadano requiere revisión de identidad.</strong>
            {(r.sin_dni || r.no_validado) && <>
              <br />Tipo: <strong>{r.sin_dni ? "Sin DNI" : "DNI no validado por RENAPER"}</strong>
              {r.motivo_texto && <>{" "}— Motivo: {r.motivo_texto}</>}
              {r.descripcion_texto && <><br /><em>{r.descripcion_texto}</em></>}
            </>}
            <br /><small className="text-muted">Corregí los datos y luego marcá como revisado desde el detalle del ciudadano.</small>
          </div>
        </div>
      )}
      <div className="row comedor-form">
        <div className="col-12">
          <form method="post" id="ciudadanoForm" className="w-100" encType="multipart/form-data" noValidate onSubmit={(e) => void enviar(e)} key={fotoKey}
            data-ajax-municipios-url={data.urls.municipios} data-ajax-localidades-url={data.urls.localidades}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            {data.non_field_errors.length > 0 && <ul className="errorlist nonfield">{data.non_field_errors.map((m) => <li key={m}>{m}</li>)}</ul>}
            <div className="progress-indicator">
              <div className="progress-header">
                <h4 className="progress-title"><i className="fas fa-clipboard-check mr-2" />{" "}Progreso del Formulario</h4>
                <span className="progress-stats"><span id="completedSections">{completas}</span>/<span id="totalSections">{SECCIONES.length}</span> secciones completadas</span>
              </div>
              <div className="progress-bar-container"><div className="progress-bar-fill" id="progressBarFill" style={{ width: `${(completas / SECCIONES.length) * 100}%` }} /></div>
            </div>
            {seccion("identidad", <>
              <div className="form-group row mb-3">{celda("tipo_registro_identidad", "identidad")}</div>
              <div id="bloque-sin-dni" className="alert alert-warning mb-3" style={{ display: tipo === "SIN_DNI" ? "" : "none" }}>
                <div className="row"><div className="col-md-4">{by.has("motivo_sin_dni") && <Bloque name="motivo_sin_dni" ctx={ctx} extra="motivo" />}</div>
                  <div className="col-md-8">{by.has("motivo_sin_dni_descripcion") && <Bloque name="motivo_sin_dni_descripcion" ctx={ctx} extra="motivo" />}</div></div>
              </div>
              <div id="bloque-no-validado" className="alert alert-danger mb-3" style={{ display: tipo === "DNI_NO_VALIDADO_RENAPER" ? "" : "none" }}>
                <div className="row"><div className="col-md-4">{by.has("motivo_no_validacion_renaper") && <Bloque name="motivo_no_validacion_renaper" ctx={ctx} extra="motivo" />}</div>
                  <div className="col-md-8">{by.has("motivo_no_validacion_descripcion") && <Bloque name="motivo_no_validacion_descripcion" ctx={ctx} extra="motivo" />}</div></div>
              </div>
              <div className="form-group row">{celda("apellido")}{celda("nombre")}{celda("fecha_nacimiento")}</div>
              <div className="form-group row">
                {celda("tipo_documento")}
                {by.has("documento") && <div className="col-md-4"><Bloque name="documento" ctx={ctx} oculto={tipo === "SIN_DNI"} /></div>}
                {celda("sexo")}
              </div>
              <div className="form-group row">{celda("nacionalidad")}</div>
            </>)}
            {seccion("domicilio", <>
              <div className="form-group row">{celda("provincia", "ubicacion")}{celda("municipio", "ubicacion")}{celda("localidad", "ubicacion")}</div>
              <div className="form-group row">{celda("barrio")}{celda("calle")}{celda("altura")}{celda("piso_departamento")}</div>
              <div className="form-group row">{celda("codigo_postal")}</div>
              <div className="row">
                {["latitud", "longitud"].map((n) => by.has(n) && (
                  <div className="col-md-6" key={n}>
                    <label htmlFor={`id_${n}`}>{by.get(n)!.label}:</label>
                    {(data.errors[n] ?? []).length > 0 && <ul className="errorlist">{data.errors[n].map((m) => <li key={m}>{m}</li>)}</ul>}
                    <Control f={by.get(n)!} ctx={ctx} />
                  </div>
                ))}
              </div>
              <MapaPin searchUrl={data.urls.address_preview} />
            </>)}
            {seccion("contacto", <div className="form-group row">{celda("telefono")}{celda("telefono_alternativo")}{celda("email")}</div>)}
            {seccion("estado", <>
              <div className="form-group row"><div className="col-md-4">{by.has("activo") && (() => {
                const f = by.get("activo")!;
                const errors = data.errors.activo ?? [];
                return (
                  <div className="form-check form-switch mt-2">
                    <input type="checkbox" name="activo" className="form-check-input form-check-input" role="switch" id="id_activo" checked={values.activo === true}
                      disabled={f.disabled || undefined} {...aria(errors, "activo")} onChange={(e) => set("activo", e.target.checked)} />
                    <label className="form-check-label ms-2" htmlFor="id_activo">{f.label}{f.required && " "}{requiredMarks(f)}</label>
                    {f.help_text && <small className="form-text text-muted d-block">{f.help_text}</small>}<ErrorLine errors={errors} />
                  </div>
                );
              })()}</div></div>
              <div className="form-group row">{celda("observaciones")}</div>
            </>)}
            {seccion("documentacion", by.has("foto") && (
              <Foto f={by.get("foto")!} errors={data.errors.foto ?? []} existente={by.get("foto")!.current} previsualizacion={foto} onFile={elegirFoto} onRemove={quitarFoto}
                abrirModal={(url, name) => setModal({ url, name })} />
            ))}
            <div className="sticky-actions">
              <div><a href={data.urls.volver} className="btn btn-secondary"><i className="fas fa-arrow-left mr-1" />{" "}Volver</a></div>
              <div>
                <button type="button" data-history-back="true" className="btn btn-secondary mr-2" onClick={() => ciudadanoFormNavigation.back()}><i className="fas fa-times mr-1" />{" "}Cancelar</button>
                {" "}<button type="submit" className="btn btn-success" disabled={enviando}><i className="fas fa-save mr-1" />{" "}{editando ? "Guardar cambios" : "Crear ciudadano"}</button>
              </div>
            </div>
          </form>
        </div>
      </div>
      <FotoModal modal={modal} cerrar={() => setModal(null)} />
    </>
  );
}

function FotoModal({ modal, cerrar }: { modal: { url: string; name: string } | null; cerrar: () => void }) {
  const abierto = modal !== null;
  const dialogo = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!abierto) return undefined;
    document.body.classList.add("modal-open");
    dialogo.current?.focus();
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") cerrar(); };
    document.addEventListener("keydown", tecla);
    return () => { document.body.classList.remove("modal-open"); document.removeEventListener("keydown", tecla); };
  }, [abierto, cerrar]);
  function descargar() {
    if (!modal) return;
    const enlace = document.createElement("a");
    enlace.href = modal.url; enlace.download = modal.name || "foto.jpg";
    document.body.appendChild(enlace); enlace.click(); document.body.removeChild(enlace);
  }
  return (
    <Fragment>
      <div className={`modal fade${abierto ? " show" : ""}`} id="fotoCiudadanoModal" tabIndex={-1} aria-labelledby="fotoCiudadanoModalLabel" aria-hidden={abierto ? undefined : true}
        aria-modal={abierto ? true : undefined} role={abierto ? "dialog" : undefined} style={abierto ? { display: "block" } : undefined} ref={dialogo}>
        <div className="modal-dialog modal-lg modal-dialog-centered">
          <div className="modal-content modal-foto-legajo">
            <div className="modal-header border-0">
              <h5 className="modal-title" id="fotoCiudadanoModalLabel"><i className="fas fa-camera mr-2" />{" "}Foto del ciudadano</h5>
              <button type="button" className="btn-close" aria-label="Cerrar" onClick={cerrar}><i className="fas fa-times" /></button>
            </div>
            <div className="modal-body p-0"><div className="foto-legajo-modal-container"><div className="foto-legajo-principal"><img id="fotoCiudadanoPrincipal" src={modal?.url} alt="Foto ampliada" className="img-fluid" /></div></div></div>
            <div className="modal-footer border-0 justify-content-between">
              <div className="info-foto"><span className="nombre-archivo" id="nombreArchivoCiudadano">{modal?.name ?? "foto.jpg"}</span></div>
              <div className="acciones-foto">
                <button type="button" className="btn btn-outline-success btn-sm" onClick={descargar}><i className="fas fa-download mr-1" />Descargar</button>{" "}
                <button type="button" className="btn btn-secondary btn-sm" onClick={cerrar}><i className="fas fa-times mr-1" />Cerrar</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      {abierto && <div className="modal-backdrop fade show" />}
    </Fragment>
  );
}

function FormularioPage({ pk }: { pk?: string }) {
  const endpoint = pk ? `web/ciudadanos/${pk}/editar/` : `web/ciudadanos/crear/${window.location.search}`;
  const [state] = useMainResource(endpoint, formularioValid);
  return renderMain(state, "Cargando ciudadano…", (data) => {
    const titulo = data.modo === "editar" ? "Editar ciudadano" : "Nuevo ciudadano";
    return { title: titulo, heading: titulo, breadcrumb: null, content: <FormularioContent data={data} pk={pk} /> };
  });
}

const CREAR = /^\/ciudadanos\/crear\/?$/;
const EDITAR = /^\/ciudadanos\/editar\/([0-9]+)$/;

export const ciudadanoFormRoute: RouteDefinition<{ pk?: string }> = {
  name: "ciudadano-form",
  match(pathname) {
    if (CREAR.test(pathname)) return {};
    const found = EDITAR.exec(pathname);
    return found ? { pk: found[1] } : null;
  },
  render({ pk }) {
    return <FormularioPage pk={pk} />;
  },
};
