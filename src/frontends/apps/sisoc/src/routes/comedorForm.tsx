/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { Fragment, useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import InspSelect2 from "./InspSelect2";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import Select2, { type Choice } from "./select2";
import type { RouteDefinition } from "./types";

/**
 * CO07.02 comedor create/edit form (`comedor_form.html`): five collapsible
 * sections with progress badges, `ComedorForm` + `ReferenteForm` controls drawn
 * as crispy does, the estado cascade (`estado-general-data`), provincia →
 * municipio → localidad, organización → programa → proyecto, the legajo photo
 * and the images (preview, mark for deletion), the map pin editor and the
 * `confirmSubmit` question. Data and writes go through
 * `/api/web/comedores/comedores/`, which runs the native views.
 */
type Option = { value: string; label: string };
export type Field = {
  name: string; section: string; label: string; type: string; required: boolean; disabled: boolean; help: string;
  value: string | string[]; options: Option[] | null; errors: string[]; attrs: Record<string, string>;
};
type Archivo = { url: string; name: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Tree = Record<string, { id: number; label: string; procesos: { id: number; label: string; detalles: { id: number; label: string }[] }[] }>;
export type FormData = {
  comedor_id: number | null; fields: Field[]; non_field_errors: string[]; referente_non_field_errors: string[]; estado_locked: boolean; estado_tree: Tree;
  codigo_de_proyecto_programa_ids: string;
  foto_legajo: { file: Archivo | null; required: boolean; initial_text: string; input_text: string; clear_label: string; errors: string[] };
  imagenes: (Archivo & { id: number })[];
  urls: { cancel: string; municipios: string; localidades: string; organizaciones: string; proyectos: string; address_preview: string };
};
export type FormPayload = { form: FormData; messages: Message[] };

const LEVELS = ["success", "error", "warning", "info"];
const UNCERTAIN: Message = { message: "No se pudo confirmar el resultado. Revisá el comedor antes de volver a intentar.", level: "error" };
const API = "web/comedores/comedores/";

const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every((x) => typeof x === "string");
const optionsValid = (v: unknown) => v === null || (Array.isArray(v) && v.every((o) => record(o) && typeof o.value === "string" && typeof o.label === "string"));
const archivo = (v: unknown): v is Archivo => record(v) && text(v.url) && text(v.name);

export function formValid(v: unknown): v is FormData {
  if (!record(v) || !Array.isArray(v.fields) || !record(v.estado_tree) || !record(v.foto_legajo) || !record(v.urls)) return false;
  const u = v.urls, f = v.foto_legajo;
  return (v.comedor_id === null || Number.isSafeInteger(v.comedor_id)) && strings(v.non_field_errors) && strings(v.referente_non_field_errors) && typeof v.estado_locked === "boolean" &&
    typeof v.codigo_de_proyecto_programa_ids === "string" &&
    v.fields.every((x) => record(x) && text(x.name) && text(x.section) && text(x.label) && text(x.type) && typeof x.required === "boolean" && typeof x.disabled === "boolean" &&
      (typeof x.value === "string" || strings(x.value)) && optionsValid(x.options) && strings(x.errors) && record(x.attrs)) &&
    (f.file === null || archivo(f.file)) && strings(f.errors) && Array.isArray(v.imagenes) && v.imagenes.every((i) => archivo(i) && Number.isSafeInteger((i as unknown as { id: unknown }).id)) &&
    ["cancel", "municipios", "localidades", "organizaciones", "proyectos", "address_preview"].every((k) => internal(u[k]));
}
const payloadValid = (v: unknown): v is FormPayload => record(v) && formValid(v.form) && Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

/** Full-page navigation, the confirm question and history back; replaceable in tests. */
export const comedorFormNavigation = {
  assign: (to: string) => window.location.assign(to),
  back: () => window.history.back(),
  confirm: (question: string) => window.confirm(question),
  print: () => window.print(),
  load: (url: string): Promise<unknown> => fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } }).then((r) => r.json()),
};

// --- Sections ---------------------------------------------------------------------------------

const SECCIONES = ["basic", "estado", "ubicacion", "referente", "multimedia"] as const;
type Seccion = (typeof SECCIONES)[number];
const CABECERAS: Record<Seccion, [string, string, string]> = {
  basic: ["fa-utensils", "Información Básica", "Datos generales del espacio comunitario"],
  estado: ["fa-tasks", "Estado y Proceso", "Seguimiento y estado actual del comedor"],
  ubicacion: ["fa-map-marker-alt", "Ubicación y Dirección", "Datos de geolocalización y domicilio"],
  referente: ["fa-user-tie", "Datos del Referente", "Información de contacto del responsable"],
  multimedia: ["fa-images", "Galería y Multimedia", "Foto de legajo e imágenes del comedor"],
};
type Badge = "complete" | "incomplete" | "empty";

function Cabecera({ id, badge, abierta, alternar }: { id: Seccion; badge: Badge; abierta: boolean; alternar: () => void }) {
  const [icono, titulo, subtitulo] = CABECERAS[id];
  return (
    <div className={`section-header${abierta ? "" : " collapsed"}`} data-toggle-section={id} tabIndex={0} role="button" aria-expanded={abierta} onClick={alternar}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); alternar(); } }}>
      <div className="section-header-left">
        <div className="section-icon"><i className={`fas ${icono}`} /></div>
        <div className="section-title-group"><h3 className="section-title">{titulo}</h3><p className="section-subtitle">{subtitulo}</p></div>
      </div>
      <div className="section-status">
        <span className={`status-badge ${badge}`} id={`status-${id}`}>
          {badge === "complete" ? <><i className="fas fa-check-circle" />{" "}Completada</> : badge === "incomplete" ? <><i className="fas fa-exclamation-circle" />{" "}Incompleta</> : <><i className="fas fa-circle" />{" "}Sin completar</>}
        </span>
        <div className="collapse-indicator"><i className="fas fa-chevron-down" /></div>
      </div>
    </div>
  );
}

// --- Crispy fields ------------------------------------------------------------------------------

type Values = Record<string, string>;
type Ctx = {
  by: Map<string, Field>; organizacionesUrl: string; values: Values; set: (name: string, v: string) => void; validated: Record<string, "valid" | "invalid">;
  validate: (f: Field, value: string) => void; options: (f: Field) => Option[]; parents: Record<string, HTMLElement | null>; setParent: (name: string, el: HTMLElement | null) => void;
  geo: { cargando: { municipio: boolean; localidad: boolean }; onProvincia: (v: string) => void; onMunicipio: (v: string) => void };
  estadoDisabled: (name: string) => boolean; onOrganizacion: (v: string) => void;
};
const WIDGET_CLASS: Record<string, string> = { text: "textinput form-control", number: "numberinput form-control", email: "emailinput form-control", select: "select form-select", tel: "textinput form-control" };
const PLACEHOLDERS: Record<string, string> = { provincia: "Seleccione una provincia", municipio: "Seleccione un municipio", localidad: "Seleccione una localidad",
  estado_general: "Seleccione un estado general", subestado: "Seleccione un subestado", motivo: "Seleccione un motivo" };
const SELECT2: string[] = ["provincia", "municipio", "localidad", "estado_general", "subestado", "motivo"];
const inputId = (name: string) => `id_${name}`;
const TOOLTIPS: Record<string, string> = {
  proyecto: "Proyecto activo de la organización", comienzo: "Año de inicio (1900 en adelante)", codigo_postal: "Código postal (1000-999999)",
  latitud: "Coordenada latitud (-90 a 90)", longitud: "Coordenada longitud (-180 a 180)", "referente-mail": "Formato: correo@ejemplo.com",
};

function Tooltip({ name }: { name: string }) {
  return TOOLTIPS[name] ? <span className="field-tooltip tooltip-in-label"><i className="fas fa-info-circle" /><span className="tooltip-text">{TOOLTIPS[name]}</span></span> : null;
}

function Control({ f, ctx }: { f: Field; ctx: Ctx }) {
  const id = inputId(f.name);
  const value = ctx.values[f.name] ?? "";
  const invalid = f.errors.length > 0;
  const cls = `${WIDGET_CLASS[f.type] ?? WIDGET_CLASS.text}${invalid ? " is-invalid" : ""}`;
  const disabled = f.disabled || ctx.estadoDisabled(f.name);
  const hasHint = f.help !== "";
  const describedBy = [hasHint ? `hint_${id}` : "", invalid ? `error_1_${id}` : ""].filter(Boolean).join(" ") || undefined;
  if (f.type === "select") {
    const opts = ctx.options(f);
    if (f.name === "organizacion") return <OrganizacionSelect f={f} ctx={ctx} />;
    if (SELECT2.includes(f.name)) {
      const dropdownParent = f.name === "municipio" || f.name === "localidad" ? ctx.parents[f.name] ?? null : undefined;
      return <Select2 id={id} name={f.name} choices={opts as Choice[]} value={[value]} invalid={invalid} disabled={disabled} placeholder={PLACEHOLDERS[f.name]}
        selectClassName="select form-select" selectProps={{ required: f.required || undefined, "aria-describedby": describedBy }} noResults="No se encontraron resultados"
        hideEmptyChoice clearTrigger={["motivo", "provincia", "municipio", "localidad"].includes(f.name) ? "mousedown" : "none"} focusMarker="container" termHandling="reset" enterOnSelected="toggle"
        outsideClick="dropdown" dropdownParent={dropdownParent}
        onChange={(v) => { const next = v[0] ?? ""; ctx.set(f.name, next); ctx.validate(f, next); if (f.name === "provincia") ctx.geo.onProvincia(next); if (f.name === "municipio") ctx.geo.onMunicipio(next); }} />;
    }
    return (
      <select name={f.name} className={cls} id={id} required={f.required || undefined} disabled={disabled || undefined} value={value} aria-describedby={describedBy}
        data-placeholder={f.attrs["data-placeholder"]}
        onChange={(e) => { ctx.set(f.name, e.target.value); ctx.validate(f, e.target.value); }}>
        {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  }
  const { maxlength, minlength, min, max, step } = f.attrs;
  return <input type={f.type} name={f.name} id={id} className={cls} value={value} required={f.required || undefined} maxLength={maxlength ? Number(maxlength) : undefined}
    minLength={minlength ? Number(minlength) : undefined} min={min} max={max} step={step} aria-describedby={describedBy}
    onChange={(e) => { ctx.set(f.name, e.target.value); if (ctx.validated[f.name]) ctx.validate(f, e.target.value); }} onBlur={(e) => ctx.validate(f, e.target.value)} />;
}

function OrganizacionSelect({ f, ctx }: { f: Field; ctx: Ctx }) {
  const actual = (f.options ?? []).find((o) => o.value !== "");
  const initial = actual ? { id: Number(actual.value), text: actual.label } : null;
  return (
    <div onChange={(e) => { const t = e.target as HTMLSelectElement; if (t.name === "organizacion") { ctx.set("organizacion", t.value); ctx.onOrganizacion(t.value); } }}>
      <InspSelect2 id={inputId(f.name)} name={f.name} placeholder="Seleccione una organización" minimum={0} initial={initial} autoSubmit={false} selectClass="select form-select"
        search={(term, signal) => fetch(`${ctx.organizacionesUrl}?q=${encodeURIComponent(term)}&page=1`, { credentials: "same-origin", signal }).then((r) => r.json())} />
    </div>
  );
}

/** One `{{ form.x|as_crispy_field }}`: label with the asterisk, widget, hint and errors. */
function Campo({ name, ctx }: { name: string; ctx: Ctx }) {
  const f = ctx.by.get(name);
  if (!f) return null;
  const id = inputId(name);
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${f.required ? " requiredField" : ""}`}>
        {f.label}{f.required && <span className="asteriskField">*</span>}
        <Tooltip name={name} />
      </label>
      <Control f={f} ctx={ctx} />
      {f.errors.map((e, i) => <p key={e} id={`error_${i + 1}_${id}`} className="invalid-feedback"><strong>{e}</strong></p>)}
      {f.help && <div id={`hint_${id}`} className="form-text">{f.help}</div>}
    </div>
  );
}

function Columna({ name, col, ctx, extra, hidden, children }: { name: string; col: string; ctx: Ctx; extra?: string; hidden?: boolean; children?: ReactNode }) {
  const f = ctx.by.get(name);
  const v = f && f.required && !f.disabled ? ctx.validated[name] : undefined;
  const clase = [col, extra, hidden ? "d-none" : "", v ? `field-validated ${v}` : ""].filter(Boolean).join(" ");
  return <div className={clase}>{children ?? <Campo name={name} ctx={ctx} />}</div>;
}

// --- Photo, images and map ----------------------------------------------------------------------

const kb = (bytes: number) => {
  if (bytes === 0) return "0 Bytes";
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${parseFloat((bytes / 1024 ** i).toFixed(2))} ${["Bytes", "KB", "MB", "GB"][i]}`;
};
const cortado = (name: string) => (name.includes("comedor/") ? name.slice(8) : name);

/** The thumbnail loads the image and swaps the placeholder, as `cargarFotoLegajoExistente`. */
function Miniatura({ url, clase, alt, big }: { url: string; clase: string; alt: string; big?: boolean }) {
  const [estado, setEstado] = useState<"cargando" | "ok" | "error" | "agotado">("cargando");
  useEffect(() => {
    const timer = setTimeout(() => setEstado((e) => (e === "cargando" ? "agotado" : e)), 10000);
    return () => clearTimeout(timer);
  }, []);
  return (
    <>
      {estado !== "ok" && (
        <div className={`preview-placeholder${big && estado === "cargando" ? " loading" : ""}`}
          style={estado === "error" ? { color: big ? undefined : "#e74c3c", background: big ? "#dc3545" : undefined } : estado === "agotado" ? { color: big ? "#000" : "#f39c12", background: big ? "#ffc107" : undefined } : undefined}
          title={estado === "error" ? "Error al cargar imagen" : estado === "agotado" ? "Imagen no disponible" : undefined}>
          {estado === "error" ? <><i className="fas fa-exclamation-triangle" />{big && <><br /><small>Error al cargar</small></>}</>
            : estado === "agotado" ? <><i className="fas fa-clock" />{big && <><br /><small>Tiempo agotado</small></>}</> : <i className="fas fa-image" />}
          {big && estado === "cargando" && <div className="loader"><div className="spinner-border spinner-border-sm" role="status"><span className="sr-only">Cargando...</span></div></div>}
        </div>
      )}
      <img className={clase} alt={alt} src={url} style={estado === "ok" ? undefined : { display: "none" }} onLoad={() => setEstado("ok")} onError={() => setEstado("error")} />
    </>
  );
}

function NuevaImagen({ file, onRemove }: { file: File; onRemove: () => void }) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    const lector = new FileReader();
    lector.onload = () => setSrc(String(lector.result));
    lector.readAsDataURL(file);
  }, [file]);
  return (
    <div className="preview-nueva-imagen">
      {src ? <img className="preview-imagen" alt="Vista previa" src={src} /> : <div className="preview-placeholder"><i className="fas fa-image" /></div>}
      <div className="preview-info">
        <div className="preview-info-content">{file.name}</div>
        <div className="preview-size">{kb(file.size)}</div>
        <div className="preview-status"><i className="fas fa-check-circle" />{" "}Seleccionada</div>
      </div>
      <button type="button" className="btn-eliminar-preview" title="Eliminar imagen" onClick={onRemove}><i className="fas fa-times" /></button>
    </div>
  );
}

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

/** `components/map_pin_editor.html`: the shared native engine drives the markup. */
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
        data-search-url={searchUrl} data-location-url="" data-address-fields="id_calle,id_numero,id_provincia,id_municipio,id_localidad">
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

function FotoModal({ modal, cerrar }: { modal: Archivo | null; cerrar: () => void }) {
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
    enlace.href = modal.url; enlace.download = modal.name || "foto_legajo.jpg"; enlace.style.display = "none";
    document.body.appendChild(enlace); enlace.click(); document.body.removeChild(enlace);
  }
  return (
    <Fragment>
      <div className={`modal fade${abierto ? " show" : ""}`} id="fotoLegajoModal" tabIndex={-1} aria-labelledby="fotoLegajoModalLabel" aria-hidden={abierto ? undefined : true}
        aria-modal={abierto ? true : undefined} role={abierto ? "dialog" : undefined} style={abierto ? { display: "block" } : undefined} ref={dialogo}>
        <div className="modal-dialog modal-lg modal-dialog-centered">
          <div className="modal-content modal-foto-legajo">
            <div className="modal-header border-0">
              <h5 className="modal-title" id="fotoLegajoModalLabel"><i className="fas fa-camera mr-2" />{" "}Foto de Legajo</h5>
              <button type="button" className="btn-close" aria-label="Cerrar" onClick={cerrar}><i className="fas fa-times" /></button>
            </div>
            <div className="modal-body p-0"><div className="foto-legajo-modal-container"><div className="foto-legajo-principal"><img id="fotoLegajoPrincipal" src={modal?.url ?? ""} alt="Foto de legajo ampliada" className="img-fluid" /></div></div></div>
            <div className="modal-footer border-0 justify-content-between">
              <div className="info-foto"><span className="nombre-archivo" id="nombreArchivoLegajo">{modal?.name || "foto_legajo.jpg"}</span></div>
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

// --- The page ----------------------------------------------------------------------------------

type Proyectos = { proyectos: { id: number; codigo: string; linea: number | string | null }[]; programas: number[] };
const proyectosValid = (v: unknown): v is Partial<Proyectos> => record(v);
const opcionesDe = (f: Field | undefined): Option[] => f?.options ?? [];
const valoresIniciales = (data: FormData): Values => Object.fromEntries(data.fields.map((f) => [f.name, Array.isArray(f.value) ? (f.value[0] ?? "") : f.value]));

export function ComedorFormContent({ data: inicial, messages }: { data: FormData; messages: Message[] }) {
  const [data, setData] = useState(inicial);
  const [values, setValues] = useState<Values>(() => valoresIniciales(inicial));
  const [abiertas, setAbiertas] = useState<Record<Seccion, boolean>>({ basic: true, estado: true, ubicacion: true, referente: true, multimedia: true });
  const [validated, setValidated] = useState<Record<string, "valid" | "invalid">>({});
  const [toasts, setToasts] = useState(messages);
  const [enviando, setEnviando] = useState(false);
  const [municipios, setMunicipios] = useState<Option[]>(() => opcionesDe(inicial.fields.find((f) => f.name === "municipio")));
  const [localidades, setLocalidades] = useState<Option[]>(() => opcionesDe(inicial.fields.find((f) => f.name === "localidad")));
  const [cargando, setCargando] = useState({ municipio: false, localidad: false });
  const [parents, setParents] = useState<Record<string, HTMLElement | null>>({});
  const [datosOrg, setDatosOrg] = useState<{ cargados: boolean; proyectos: Proyectos["proyectos"]; programas: number[] }>({ cargados: false, proyectos: [], programas: [] });
  const [nuevaFoto, setNuevaFoto] = useState<File | null>(null);
  const [archivos, setArchivos] = useState<File[]>([]);
  const [marcadas, setMarcadas] = useState<Set<number>>(new Set());
  const [modal, setModal] = useState<Archivo | null>(null);
  const [fotoKey, setFotoKey] = useState(0);
  const busy = useRef(false);
  const [iniciales] = useState(() => ({ programa: valoresIniciales(inicial).programa ?? "", proyecto: valoresIniciales(inicial).proyecto ?? "" }));
  const by = useMemo(() => new Map(data.fields.map((f) => [f.name, f])), [data]);

  // Dependent fields clear when their parent changes (the native page scripts).
  const set = (name: string, v: string) => setValues((cur) => {
    const next = { ...cur, [name]: v };
    if (name === "categoria_espacio_comunitario" && v !== "otra") next.categoria_espacio_comunitario_otra = "";
    if (name === "estado_general") { next.subestado = ""; next.motivo = ""; }
    if (name === "subestado") next.motivo = "";
    if (name === "programa" && !data.codigo_de_proyecto_programa_ids.split(",").filter(Boolean).includes(v)) next.proyecto = "";
    return next;
  });
  const validate = (f: Field, v: string) => {
    if (!f.required || f.disabled) return;
    setValidated((cur) => ({ ...cur, [f.name]: v.trim() ? "valid" : "invalid" }));
  };

  // categoría "otra": the extra field shows only for it and is cleared otherwise.
  const esOtra = values.categoria_espacio_comunitario === "otra";

  // geography
  const vacias = (clave: "municipio" | "localidad"): Option[] => [{ value: "", label: clave === "municipio" ? "Seleccione un municipio" : "Seleccione una localidad" }];
  async function cargar(url: string): Promise<Option[]> {
    try {
      const rows = await comedorFormNavigation.load(url);
      return Array.isArray(rows) ? rows.filter((g) => record(g) && Number.isSafeInteger(g.id) && text(g.nombre)).map((g) => ({ value: String((g as { id: number }).id), label: String((g as { nombre: string }).nombre) })) : [];
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

  // estado cascade: Estado general > Subestado > Motivo
  const actividad = data.estado_tree[values.estado_general ?? ""];
  const procesos = actividad?.procesos ?? [];
  const detalles = procesos.find((p) => String(p.id) === values.subestado)?.detalles ?? [];
  const opcionesEstado = (name: string, placeholder: string): Option[] => {
    const lista = name === "subestado" ? procesos : detalles;
    return lista.length === 0 ? [{ value: "", label: "---------" }] : [{ value: "", label: placeholder }, ...lista.map((o) => ({ value: String(o.id), label: o.label }))];
  };
  const estadoDisabled = (name: string) => {
    if (data.estado_locked || !["subestado", "motivo"].includes(name)) return false;
    return (name === "subestado" ? procesos : detalles).length === 0;
  };

  // organización > programa > proyecto
  const permitidos = data.codigo_de_proyecto_programa_ids.split(",").filter(Boolean);
  const programaPermite = permitidos.includes(values.programa ?? "");
  async function cargarOrganizacion(id: string) {
    if (!id) { setDatosOrg({ cargados: false, proyectos: [], programas: [] }); return; }
    try {
      const body = await comedorFormNavigation.load(data.urls.proyectos.replace("/0/", `/${id}/`));
      if (!proyectosValid(body)) throw new Error("bad");
      setDatosOrg({ cargados: true, proyectos: body.proyectos ?? [], programas: (body.programas ?? []).map(Number) });
    } catch {
      setDatosOrg({ cargados: false, proyectos: [], programas: [] });
    }
  }
  const orgInicial = useRef(values.organizacion ?? "");
  useEffect(() => { if (orgInicial.current) void cargarOrganizacion(orgInicial.current); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  function onOrganizacion(id: string) {
    setValues((cur) => ({ ...cur, proyecto: "" }));
    void cargarOrganizacion(id);
  }
  const opcionesPrograma = opcionesDe(by.get("programa")).filter((o) => !(o.value && datosOrg.programas.length && !datosOrg.programas.map(String).includes(o.value) && o.value !== iniciales.programa));
  const aplicaLinea = datosOrg.programas.length > 0;
  const opcionesProyecto: Option[] = datosOrg.cargados
    ? [{ value: "", label: "Seleccione un proyecto" }, ...datosOrg.proyectos
      .filter((p) => !(aplicaLinea && String(p.id) !== iniciales.proyecto && String(p.linea) !== values.programa))
      .map((p) => ({ value: String(p.id), label: p.codigo }))]
    : opcionesDe(by.get("proyecto"));

  const options = (f: Field): Option[] => {
    if (f.name === "municipio") return municipios;
    if (f.name === "localidad") return localidades;
    if (data.estado_locked) return opcionesDe(f);
    if (f.name === "subestado") return opcionesEstado("subestado", "Seleccione un subestado");
    if (f.name === "motivo") return opcionesEstado("motivo", "Seleccione un motivo");
    if (f.name === "programa") return opcionesPrograma;
    if (f.name === "proyecto") return opcionesProyecto;
    return opcionesDe(f);
  };

  // progress
  const lleno = (n: string) => (values[n] ?? "").trim() !== "";
  const completa: Record<Seccion, boolean> = {
    basic: lleno("nombre") && lleno("tipocomedor") && lleno("organizacion"),
    estado: lleno("estado_general") && lleno("subestado"),
    ubicacion: lleno("provincia") && lleno("municipio") && lleno("localidad"),
    referente: lleno("referente-nombre") && lleno("referente-apellido") && lleno("referente-celular"),
    multimedia: data.foto_legajo.file !== null || nuevaFoto !== null || data.imagenes.length > 0 || archivos.length > 0,
  };
  const conDatos = (s: Seccion) => data.fields.some((f) => f.section === s && lleno(f.name)) || (s === "multimedia" && (marcadas.size > 0 || nuevaFoto !== null));
  const badge = (s: Seccion): Badge => (completa[s] ? "complete" : conDatos(s) ? "incomplete" : "empty");
  const completas = SECCIONES.filter((s) => completa[s]).length;

  function aplicarRechazo(cuerpo: FormPayload) {
    setData(cuerpo.form); setValues(valoresIniciales(cuerpo.form)); setValidated({}); setNuevaFoto(null); setArchivos([]); setMarcadas(new Set()); setFotoKey((k) => k + 1);
    setMunicipios(opcionesDe(cuerpo.form.fields.find((f) => f.name === "municipio"))); setLocalidades(opcionesDe(cuerpo.form.fields.find((f) => f.name === "localidad")));
    orgInicial.current = valoresIniciales(cuerpo.form).organizacion ?? ""; if (orgInicial.current) void cargarOrganizacion(orgInicial.current);
    setAbiertas({ basic: true, estado: true, ubicacion: true, referente: true, multimedia: true });
    setToasts(cuerpo.messages); resetAfterRejectedPost();
  }

  async function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    if (!comedorFormNavigation.confirm("¿Estás seguro de que deseas guardar el comedor?")) return;
    busy.current = true; setEnviando(true);
    try {
      const cuerpo = new window.FormData(event.currentTarget);
      cuerpo.delete("imagenes");
      archivos.forEach((a) => cuerpo.append("imagenes", a));
      const destino = data.comedor_id === null ? `${API}crear/` : `${API}${data.comedor_id}/editar/`;
      const { data: body, status } = await webClient.post(destino, cuerpo, { validateStatus: (s: number) => accepted(s) || s === 400 });
      if (status >= 200 && status < 300 && record(body) && internal(body.redirect)) { comedorFormNavigation.assign(body.redirect); return; }
      if (status === 403) setToasts([{ message: record(body) && text(body.detail) ? body.detail : UNCERTAIN.message, level: "error" }]);
      else if (status === 400 && record(body) && formValid(body.form)) aplicarRechazo({ form: body.form, messages: [] });
      else setToasts([UNCERTAIN]);
    } catch {
      setToasts([UNCERTAIN]);
    } finally { busy.current = false; setEnviando(false); }
  }

  const ctx: Ctx = {
    by, organizacionesUrl: data.urls.organizaciones, values, set, validated, validate, options, parents,
    setParent: (name, el) => { if (el && parents[name] !== el) setParents((cur) => (cur[name] === el ? cur : { ...cur, [name]: el })); },
    geo: { cargando, onProvincia: (v) => void onProvincia(v), onMunicipio: (v) => void onMunicipio(v) }, estadoDisabled, onOrganizacion,
  };
  const col = (name: string, c: string, extra?: string, hidden?: boolean) => <Columna key={name} name={name} col={c} ctx={ctx} extra={extra} hidden={hidden} />;
  const seccion = (id: Seccion, hijos: ReactNode) => (
    <div className="section-card" data-section={id} {...(id === "estado" ? { "data-estado-locked": data.estado_locked ? "true" : "false" } : {})}>
      <Cabecera id={id} badge={badge(id)} abierta={abiertas[id]} alternar={() => setAbiertas((cur) => ({ ...cur, [id]: !cur[id] }))} />
      <div className={`section-body collapse${abiertas[id] ? " show" : ""}`} id={`section-${id}`}>{hijos}</div>
    </div>
  );
  const ubicacion = (name: "municipio" | "localidad") => (
    <div className="col-md-4">
      <div id={`${name}-loader`} className={`skeleton-loader${cargando[name] ? "" : " d-none"}`} />
      <div id={`${name}-field`} ref={(el) => ctx.setParent(name, el)} style={cargando[name] ? { opacity: "0.3" } : undefined}><Campo name={name} ctx={ctx} /></div>
    </div>
  );
  const ref = (n: string) => `referente-${n}`;
  const foto = data.foto_legajo;
  const mostrado = foto.file ? cortado(foto.file.name) : "";

  return (
    <>
      <NativeToasts messages={toasts} />
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/comedorRelevamiento.css" />
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <div className="d-flex justify-content-between mb-3">
        <div>
          <a className="btn btn-secondary print mr-1 d-none d-sm-inline" onClick={() => comedorFormNavigation.print()}>Imprimir</a>{" "}
          <a href="#" data-history-back="true" className="btn btn-secondary" onClick={(e) => { e.preventDefault(); comedorFormNavigation.back(); }}>Cancelar</a>
        </div>
      </div>
      <div className="row comedor-form">
        <div className="col-12">
          <form method="post" id="comedorForm" className="w-100" encType="multipart/form-data" onSubmit={(e) => void enviar(e)} key={fotoKey} data-call-submit="confirmSubmit">
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <div className="progress-indicator">
              <div className="progress-header">
                <h4 className="progress-title"><i className="fas fa-clipboard-check mr-2" />{" "}Progreso del Formulario</h4>
                <span className="progress-stats"><span id="completedSections">{completas}</span>/5 secciones completadas</span>
              </div>
              <div className="progress-bar-container"><div className="progress-bar-fill" id="progressBarFill" style={{ width: `${(completas / 5) * 100}%` }} /></div>
            </div>
            {seccion("basic", <>
              <div className="form-group row">{col("nombre", "col-md-4")}{col("id_externo", "col-md-4")}{col("tipocomedor", "col-md-4")}</div>
              <div className="form-group row">
                {col("categoria_espacio_comunitario", "col-md-6")}
                <div id="categoria-espacio-otra-wrapper" className={`col-md-6${esOtra ? "" : " d-none"}`}><Campo name="categoria_espacio_comunitario_otra" ctx={ctx} /></div>
              </div>
              <div className="form-group row">
                {col("organizacion", "col-md-3")}{col("programa", "col-md-3")}
                <div id="codigo-proyecto-wrapper" className={`col-md-2${programaPermite ? "" : " d-none"}`} data-programa-ids={data.codigo_de_proyecto_programa_ids} data-proyectos-url={data.urls.proyectos}>
                  <Campo name="proyecto" ctx={ctx} />
                </div>
                {col("es_judicializado", "col-md-2")}{col("es_caritas", "col-md-2")}
              </div>
            </>)}
            {seccion("estado", <div className="form-group row">{col("estado_general", "col-md-3")}{col("subestado", "col-md-3")}{col("motivo", "col-md-3")}{col("comienzo", "col-md-3")}</div>)}
            {seccion("ubicacion", <>
              <div className="form-group row">{col("provincia", "col-md-4")}{ubicacion("municipio")}{ubicacion("localidad")}</div>
              <div className="form-group row">{col("partido", "col-md-4")}{col("barrio", "col-md-4")}{col("codigo_postal", "col-md-4")}</div>
              <div className="form-group row">{col("calle", "col-md-4")}{col("numero", "col-md-2")}{col("piso", "col-md-2")}{col("departamento", "col-md-4")}</div>
              <div className="form-group row">{col("manzana", "col-md-3")}{col("lote", "col-md-3")}{col("entre_calle_1", "col-md-3")}{col("entre_calle_2", "col-md-3")}</div>
              <div className="form-group row">{col("latitud", "col-md-6")}{col("longitud", "col-md-6")}</div>
              <MapaPin searchUrl={data.urls.address_preview} />
            </>)}
            {seccion("referente", <>
              <div className="form-group row">{col(ref("nombre"), "col-md-4")}{col(ref("apellido"), "col-md-4")}{col(ref("mail"), "col-md-4")}</div>
              <div className="form-group row">{col(ref("celular"), "col-md-4")}{col(ref("documento"), "col-md-4")}{col(ref("funcion"), "col-md-4")}</div>
            </>)}
            {seccion("multimedia", <>
              <div className="form-group">
                <label htmlFor="id_foto_legajo" className="form-label text-light font-weight-bold"><i className="fas fa-camera mr-2" />{" "}Foto de Legajo</label>
                {foto.file && (
                  <div className="foto-legajo-existente mb-3">
                    <h6 className="text-light mb-2"><i className="fas fa-image mr-1" />{" "}Foto actual:</h6>
                    <div className="foto-existente-container">
                      <div className="foto-thumbnail-container" data-image-url={foto.file.url}><Miniatura url={foto.file.url} clase="" alt="Foto de legajo" big /></div>
                      <div className="foto-info">
                        <div className="foto-nombre">{mostrado}</div>
                        <div className="foto-status"><i className="fas fa-check-circle text-success" />{" "}<span className="text-success">Guardada</span></div>
                      </div>
                      <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => setModal(foto.file)}><i className="fas fa-expand-alt mr-1" />{" "}Ver completa</button>
                    </div>
                  </div>
                )}
                <div className="nueva-foto-section">
                  <h6 className="text-light mb-2"><i className="fas fa-upload mr-1" />{" "}{foto.file ? "Cambiar foto:" : "Seleccionar foto:"}</h6>
                  {foto.file && <>{foto.initial_text}: <a href={foto.file.url}>{foto.file.name}</a>{!foto.required && <><input type="checkbox" name="foto_legajo-clear" id="foto_legajo-clear_id" /><label htmlFor="foto_legajo-clear_id">{foto.clear_label}</label></>}<br />{foto.input_text}:</>}
                  <input type="file" name="foto_legajo" accept="image/*" id="id_foto_legajo" onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    const f = e.target.files?.[0] ?? null;
                    if (f && !f.type.startsWith("image/")) { window.alert("Por favor selecciona un archivo de imagen válido."); e.target.value = ""; setNuevaFoto(null); return; }
                    setNuevaFoto(f);
                  }} />
                </div>
                <FotoNueva file={nuevaFoto} quitar={() => { const el = document.getElementById("id_foto_legajo") as HTMLInputElement | null; if (el) el.value = ""; setNuevaFoto(null); }} />
              </div>
              <div className="imagenes-existentes-section mt-4">
                <h5 className="imagen-header">Imágenes Existentes:</h5>
                <div className="imagenes-container">
                  {data.imagenes.map((img) => {
                    const marcada = marcadas.has(img.id);
                    const alternar = () => setMarcadas((cur) => { const n = new Set(cur); if (n.has(img.id)) n.delete(img.id); else n.add(img.id); return n; });
                    return (
                      <div key={img.id} className={`imagen-existente imagen-item${marcada ? " imagen-eliminada" : ""}`} data-image-id={img.id}>
                        <div className="imagen-card-content">
                          <div className="imagen-thumbnail-container" data-image-url={img.url}><Miniatura url={img.url} clase="imagen-thumbnail" alt="Imagen del comedor" /></div>
                          <div className="imagen-info-content">
                            <div className="imagen-filename-display">{cortado(img.name)}</div>
                            <div className="imagen-status"><i className="fas fa-check-circle" />{" "}Guardada</div>
                          </div>
                          <div className="imagen-actions">
                            <input type="checkbox" name={`imagen_ciudadano-borrar-${img.id}`} id={`imagen_borrar_${img.id}`} className="checkbox-eliminar-custom" data-image-id={img.id} checked={marcada} onChange={alternar} />
                            <button type="button" className="btn-eliminar-custom" onClick={alternar} title={marcada ? "Desmarcar para eliminar" : "Marcar para eliminar"}
                              style={{ backgroundColor: marcada ? "#27ae60" : "#e74c3c" }}><i className={`fas ${marcada ? "fa-undo" : "fa-trash-alt"}`} /></button>
                          </div>
                        </div>
                        <div className={`overlay-eliminar${marcada ? "" : " d-none"}`}><div className="overlay-text"><i className="fas fa-trash-alt" /><br />MARCADA PARA ELIMINAR</div></div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="seccion-nuevas">
                <h5 className="nuevas-header">Agregar Nuevas Imágenes:</h5>
                <input type="file" name="imagenes" id="imagenesInput" className="d-none" multiple accept="image/*"
                  onChange={(e) => { setArchivos((cur) => [...cur, ...Array.from(e.target.files ?? [])]); e.target.value = ""; }} />
                <button type="button" id="addImagesBtn" className="btn-seleccionar" onClick={() => document.getElementById("imagenesInput")?.click()}><i className="fas fa-plus" />{" "}Seleccionar Imágenes</button>
                <div id="selectedImagesInfo" className={`contador-imagenes${archivos.length ? "" : " d-none"}`}><span id="imageCount">{archivos.length}</span> imagen(es) seleccionada(s)</div>
                <div id="imagePreviewContainer" className="nuevas-imagenes-container">
                  {archivos.filter((a) => a.type.startsWith("image/")).map((a, i) => <NuevaImagen key={`${a.name}-${a.size}-${i}`} file={a} onRemove={() => setArchivos((cur) => cur.filter((x) => x !== a))} />)}
                </div>
              </div>
            </>)}
            <div className="sticky-actions">
              <div>
                <button type="button" data-history-back="true" className="btn btn-secondary mr-2" onClick={() => comedorFormNavigation.back()}><i className="fas fa-times mr-1" />{" "}Cancelar</button>{" "}
                <button className="btn btn-success" type="submit" disabled={enviando}><i className="fas fa-save mr-1" />{" "}Guardar comedor</button>
              </div>
            </div>
          </form>
        </div>
      </div>
      <FotoModal modal={modal} cerrar={() => setModal(null)} />
    </>
  );
}

function FotoNueva({ file, quitar }: { file: File | null; quitar: () => void }) {
  const [leida, setLeida] = useState<{ file: File; src: string } | null>(null);
  useEffect(() => {
    if (!file) return undefined;
    const lector = new FileReader();
    lector.onload = () => setLeida({ file, src: String(lector.result) });
    lector.readAsDataURL(file);
    return () => { lector.onload = null; };
  }, [file]);
  const src = file && leida?.file === file ? leida.src : "";
  return (
    <div id="fotoLegajoPreviewContainer" className={`nueva-foto-preview mt-3${file && src ? "" : " d-none"}`}>
      <h6 className="text-light mb-2"><i className="fas fa-eye mr-1" />{" "}Vista previa:</h6>
      <div className="nueva-foto-container">
        <div className="foto-preview-wrapper">
          <img id="fotoLegajoPreview" src={src} alt="Vista previa de foto legajo" className="foto-preview-img" />
          <button type="button" className="btn-remover-preview" onClick={quitar}><i className="fas fa-times" /></button>
        </div>
        <div className="foto-preview-info">
          <div className="preview-nombre" id="fotoLegajoNombre">{file?.name ?? "imagen.jpg"}</div>
          <div className="preview-size" id="fotoLegajoSize">{file ? kb(file.size) : "0 KB"}</div>
          <div className="preview-status"><i className="fas fa-clock text-warning" />{" "}<span className="text-warning">Pendiente de guardar</span></div>
        </div>
      </div>
    </div>
  );
}

function FormPage({ id }: { id?: string }) {
  const [state] = useMainResource(id ? `${API}${id}/formulario/` : `${API}formulario/`, payloadValid);
  return renderMain(state, "Cargando comedor…", (data) => ({
    title: "Espacios Comunitarios", heading: "Espacios Comunitarios", breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <ComedorFormContent data={data.form} messages={data.messages} />,
  }));
}

// Native pages `comedores/crear` and `comedores/<pk>/editar` (no trailing slash).
export const comedorFormRoute: RouteDefinition<{ id?: string }> = {
  name: "comedores-form",
  match(pathname) {
    if (pathname === "/comedores/crear") return {};
    const m = pathname.match(/^\/comedores\/([0-9]+)\/editar$/);
    return m ? { id: m[1] } : null;
  },
  render(params) {
    return <FormPage key={params.id ?? "crear"} id={params.id} />;
  },
};
