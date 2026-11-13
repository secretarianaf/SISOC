/* eslint-disable react-refresh/only-export-components -- the screen exports its validator and navigation seam for the unit tests. */
import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { InsumosToastList } from "../InsumosToast";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";

/**
 * O05.02 + O05.03 `organizacion_form.html` (alta y edición, programas y
 * proyectos con línea y territoriales en un solo POST). The API projects the
 * real `OrganizacionForm` (fields, options, values, errors) and saves through
 * the native `OrganizacionCreateView` / `OrganizacionUpdateView`; Django texts
 * come back verbatim. Section structure, crispy field markup and the
 * behaviors of `organizacionesform.js` and the template script (progress,
 * collapsible sections, CUIT check, tipo-de-entidad confirmation, cascading
 * ubicación, proyectos table) are reproduced here.
 */
export type Field = {
  name: string; label: string; type: string; required: boolean; help: string;
  value: unknown; options: { value: string; label: string }[] | null; errors: string[]; attrs: Record<string, string>;
};
type Proyecto = { id: number; codigo: string; linea: number | null; convenio: boolean };
export type OrganizacionFormData = {
  organizacion_id: number | null; fields: Field[]; non_field_errors: string[];
  data: { abordaje: { id: number; nombre: string }[]; territoriales: { id: number; nombre: string }[]; proyectos: Proyecto[]; inactivos: Record<string, number> };
  subzonas: { id: number; nombre: string; region_id: number | null }[] | null;
  tipo_entidad_actual: number | null; urls: { cancel: string; subtipos: string; cuil: string };
};
export type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Payload = { form: OrganizacionFormData; messages: Message[] };

const LEVELS = ["success", "error", "warning", "info"];
export const FLASH_KEY = "sisoc.organizaciones.flash";
/** Messages the ABM queued for the next screen (Django `messages` after its redirect). */
export function FlashToasts({ messages }: { messages: Message[] }) {
  const [flash] = useState<Message[]>(() => {
    try {
      const raw = window.sessionStorage.getItem(FLASH_KEY);
      window.sessionStorage.removeItem(FLASH_KEY);
      const parsed: unknown = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed.filter((m): m is Message => record(m) && text(m.message) && LEVELS.includes(m.level as string)) : [];
    } catch { return []; }
  });
  return <InsumosToastList messages={[...flash, ...messages]} />;
}

/** A page the native flow answers with a reload (form errors): scrolled to the top, nothing focused and the keyboard starting at the top. */
export function freshPage() {
  try {
    window.scrollTo(0, 0);
    (document.activeElement as HTMLElement | null)?.blur();
    document.body.setAttribute("tabindex", "-1");
    document.body.focus({ preventScroll: true });
    document.body.blur();
    document.body.removeAttribute("tabindex");
  } catch { /* cosmetic only */ }
}

export const organizacionesNavigation = { assign: (to: string) => window.location.assign(to) };

export function formValid(v: unknown): v is Payload {
  if (!record(v) || !record(v.form) || !Array.isArray(v.messages)) return false;
  const f = v.form;
  return Array.isArray(f.fields) && f.fields.every((x) => record(x) && text(x.name) && text(x.label) && text(x.type) && Array.isArray(x.errors)) &&
    record(f.data) && record(f.urls) && internal(f.urls.cancel) && internal(f.urls.subtipos) && internal(f.urls.cuil) &&
    v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Fields `organizacion_form.html` renders or posts; the rest of `fields = "__all__"` is never sent. */
const POSTED = ["nombre", "cuit", "tipo_entidad", "subtipo_entidad", "telefono", "email", "provincia", "municipio", "localidad", "partido", "domicilio", "fecha_vencimiento",
  "sin_vencimiento", "programas", "region_abordaje", "subzona_abordaje", "proyectos_lineas", "asignaciones_territoriales", "quitar_territoriales_sin_proyecto",
  "cuil_duplicado_confirmado", "cuil_duplicado_confirmado_valor"];
const SECTIONS = ["basic", "contacto", "ubicacion", "vigencia", "programas", "abordaje"] as const;
type Section = (typeof SECTIONS)[number];
const TIPO_WARNING = "Al cambiar el Tipo de Entidad se reiniciará la documentación del legajo (se eliminarán los archivos ya cargados). Las admisiones vinculadas mostrarán una advertencia para resincronizarse o continuar con la información actual.";

// --- crispy field markup (`as_crispy_field`, bootstrap5) --------------------------------

/** Django widget attributes in their React spelling. */
const reactAttrs = (attrs: Record<string, string>) => Object.fromEntries(Object.entries(attrs).map(([k, v]) => [k === "maxlength" ? "maxLength" : k === "minlength" ? "minLength" : k, v]));
const cls = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");
const widgetClass: Record<string, string> = { text: "textinput form-control", email: "emailinput form-control", number: "numberinput form-control", date: "form-control dateinput" };

function Errors({ id, errors }: { id: string; errors: string[] }) {
  return <>{errors.map((e, i) => <span key={e} id={`error_${i + 1}_id_${id}`} className="invalid-feedback"><strong>{e}</strong></span>)}</>;
}

function Control({ f, value, onChange }: { f: Field; value: unknown; onChange: (v: unknown) => void }) {
  const invalid = f.errors.length > 0;
  if (f.type === "select") {
    return (
      <select name={f.name} className={cls("select form-select", invalid && "is-invalid")} id={`id_${f.name}`} value={String(value ?? "")} required={f.required}
        onChange={(e) => onChange(e.target.value)}>
        {(f.options ?? []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  }
  return (
    <input type={f.type} name={f.name} className={cls(widgetClass[f.type] ?? "form-control", invalid && "is-invalid")} id={`id_${f.name}`} required={f.required}
      value={String(value ?? "")} onChange={(e) => onChange(e.target.value)} {...reactAttrs(f.attrs)} />
  );
}

export function CrispyField({ f, values, set }: { f: Field; values: Record<string, unknown>; set: (name: string, v: unknown) => void }) {
  const value = values[f.name];
  if (f.type === "checkbox") {
    return (
      <div id={`div_id_${f.name}`} className="form-check">
        <input type="checkbox" name={f.name} className={cls("checkboxinput form-check-input", f.errors.length > 0 && "is-invalid")} id={`id_${f.name}`} checked={value === true}
          onChange={(e) => set(f.name, e.target.checked)} />
        <label htmlFor={`id_${f.name}`} className="form-check-label">{f.label}</label>
        <Errors id={f.name} errors={f.errors} />
      </div>
    );
  }
  if (f.type === "multiple") {
    const chosen = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div id={`div_id_${f.name}`} className="mb-3">
        <fieldset>
          <legend className="form-label fs-6">{f.label}</legend>
          <div>
            {(f.options ?? []).map((o, i) => (
              <div key={o.value} className="form-check">
                <input type="checkbox" className="form-check-input" name={f.name} value={o.value} id={`id_${f.name}_${i}`} checked={chosen.includes(o.value)}
                  onChange={(e) => set(f.name, e.target.checked ? [...chosen, o.value] : chosen.filter((x) => x !== o.value))} />
                <label htmlFor={`id_${f.name}_${i}`} className="form-check-label">{o.label}</label>
              </div>
            ))}
          </div>
          <Errors id={f.name} errors={f.errors} />
        </fieldset>
      </div>
    );
  }
  return (
    <div id={`div_id_${f.name}`} className="mb-3">
      <label htmlFor={`id_${f.name}`} className={cls("form-label", f.required && "requiredField")}>
        {f.label}{f.required && <span className="asteriskField">*</span>}
      </label>
      <Control f={f} value={value} onChange={(v) => set(f.name, v)} />
      <Errors id={f.name} errors={f.errors} />
    </div>
  );
}

// --- sections --------------------------------------------------------------------------

function SectionCard({ id, icon, title, subtitle, status, open, toggle, children, hidden }: {
  hidden?: boolean; id: Section; icon: string; title: string; subtitle: string; status: boolean; open: boolean; toggle: () => void; children: ReactNode;
}) {
  return (
    <div className={cls("section-card", hidden && "d-none")} data-section={id} id={id === "abordaje" ? "abordaje-card" : undefined}>
      <div className={cls("section-header", !open && "collapsed")} data-toggle-section={id} onClick={toggle}>
        <div className="section-header-left">
          <div className="section-icon"><i className={`fas ${icon}`} /></div>
          <div className="section-title-group"><h3 className="section-title">{title}</h3><p className="section-subtitle">{subtitle}</p></div>
        </div>
        <div className="section-status">
          <span className={`status-badge ${status ? "complete" : "empty"}`} id={`status-${id}`}>
            <i className={`fas ${status ? "fa-check-circle" : "fa-circle"}`} /> {status ? "Completo" : "Sin completar"}
          </span>
          <div className="collapse-indicator"><i className="fas fa-chevron-down" /></div>
        </div>
      </div>
      <div className={`section-body collapse${open ? " show" : ""}`} id={`section-${id}`}>{children}</div>
    </div>
  );
}

type Duplicado = Record<string, string | number>;
type Asignacion = { proyecto: string; territorial: number };

export function OrganizacionFormContent({ initial, messages: initialMessages }: { initial: OrganizacionFormData; messages: Message[] }) {
  const [form, setForm] = useState(initial);
  const fields = useMemo(() => Object.fromEntries(form.fields.map((f) => [f.name, f])), [form]);
  const [values, setValues] = useState<Record<string, unknown>>(() => Object.fromEntries(initial.fields.map((f) => [f.name, f.value])));
  const [open, setOpen] = useState<Record<string, boolean>>(() => Object.fromEntries(SECTIONS.map((s) => [s, true])));
  const [toasts, setToasts] = useState<Message[]>(initialMessages);
  const [pending, setPending] = useState(false);
  const [duplicados, setDuplicados] = useState<Duplicado[]>([]);
  const [confirmado, setConfirmado] = useState(false);
  const [tipoModal, setTipoModal] = useState(false);
  const [tipoConfirmado, setTipoConfirmado] = useState(false);
  const [subtipos, setSubtipos] = useState<{ value: string; label: string }[] | null>(null);
  const [ubicacion, setUbicacion] = useState<{ municipio?: { value: string; label: string }[]; localidad?: { value: string; label: string }[] }>({});
  const [proyectos, setProyectos] = useState<string[]>(() => initial.data.proyectos.map((p) => p.codigo));
  const [lineas, setLineas] = useState<Record<string, number | null>>(() => Object.fromEntries(initial.data.proyectos.map((p) => [p.codigo, p.linea])));
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>(() => {
    const raw = initial.fields.find((f) => f.name === "asignaciones_territoriales")?.value;
    try { const parsed: unknown = typeof raw === "string" ? JSON.parse(raw) : raw; return Array.isArray(parsed) ? (parsed as Asignacion[]) : []; } catch { return []; }
  });
  const [nuevo, setNuevo] = useState("");
  const [nuevoError, setNuevoError] = useState("");
  const set = (name: string, v: unknown) => {
    if (name === "cuit") setConfirmado(false);
    setValues((cur) => ({ ...cur, [name]: v }));
  };
  const editing = form.organizacion_id !== null;
  const cuit = String(values.cuit ?? "");
  const shown = /^\d{11}$/.test(cuit) ? duplicados : [];

  // `RenderSubtipoEntidad`: the subtipos of the chosen tipo (the native select starts empty).
  const tipo = String(values.tipo_entidad ?? "");
  useEffect(() => {
    if (!tipo) return undefined;
    let active = true;
    fetch(`${form.urls.subtipos}?tipo_entidad=${encodeURIComponent(tipo)}`, { credentials: "same-origin" })
      .then((r) => r.json()).then((rows: { id: number; text: string }[]) => { if (active) setSubtipos(rows.map((r) => ({ value: String(r.id), label: r.text }))); })
      .catch(() => undefined);
    return () => { active = false; };
  }, [tipo, form.urls.subtipos]);

  // `cuil-check`: 400 ms after eleven digits, and on load when editing.
  useEffect(() => {
    if (!/^\d{11}$/.test(cuit)) return undefined;
    let active = true;
    const timer = window.setTimeout(() => {
      const exclude = form.organizacion_id ? `&exclude=${form.organizacion_id}` : "";
      fetch(`${form.urls.cuil}?cuil=${cuit}${exclude}`, { credentials: "same-origin" })
        .then((r) => r.json()).then((d: { organizaciones: Duplicado[] }) => { if (active) setDuplicados(d.organizaciones); }).catch(() => undefined);
    }, editing ? 0 : 400);
    return () => { active = false; window.clearTimeout(timer); };
  }, [cuit, form.organizacion_id, form.urls.cuil, editing]);

  async function cascade(kind: "municipio" | "localidad", id: string) {
    const url = kind === "municipio" ? `/ajax/load-municipios/?provincia_id=${id}` : `/ajax/load-localidades/?municipio_id=${id}`;
    const rows = (await (await fetch(url, { credentials: "same-origin" })).json()) as { id: number; nombre?: string; nombre_region?: string }[];
    return rows.map((r) => ({ value: String(r.id), label: (r.nombre || r.nombre_region) ?? "" }));
  }
  async function onProvincia(id: string) {
    set("provincia", id);
    const municipios = await cascade("municipio", id);
    const first = municipios[0]?.value ?? "";
    setUbicacion({ municipio: municipios, localidad: [] });
    set("municipio", first);
    set("localidad", "");
    if (first) {
      const localidades = await cascade("localidad", first);
      setUbicacion({ municipio: municipios, localidad: localidades });
      set("localidad", localidades[0]?.value ?? "");
    }
  }
  async function onMunicipio(id: string) {
    set("municipio", id);
    const localidades = await cascade("localidad", id);
    setUbicacion((cur) => ({ ...cur, localidad: localidades }));
    set("localidad", localidades[0]?.value ?? "");
  }

  const abordajeIds = form.data.abordaje.map((a) => String(a.id));
  const programas = Array.isArray(values.programas) ? (values.programas as string[]) : [];
  const elegidas = form.data.abordaje.filter((a) => programas.includes(String(a.id)));
  // `selectorLinea`: with one chosen Abordaje line it is assigned on its own and shown as a badge.
  const lineaDe = (codigo: string) => (elegidas.length === 1 && (!lineas[codigo] || lineas[codigo] === elegidas[0].id) ? elegidas[0].id : lineas[codigo] ?? null);
  const quitar = fields.quitar_territoriales_sin_proyecto;
  const conDatos = Boolean(quitar?.options?.length || values.region_abordaje || values.subzona_abordaje || proyectos.length);
  const showAbordaje = conDatos || programas.some((p) => abordajeIds.includes(p));
  const filled = (name: string) => { const v = values[name]; return Array.isArray(v) ? v.length > 0 : typeof v === "boolean" ? v : String(v ?? "").trim() !== "" && String(v) !== "0"; };
  // `updateSectionStatus`: a section counts when any of its visible inputs has a value.
  const complete: Record<Section, boolean> = {
    basic: ["nombre", "cuit", "tipo_entidad", "subtipo_entidad"].some(filled) || confirmado,
    contacto: ["telefono", "email"].some(filled),
    ubicacion: ["provincia", "municipio", "localidad", "partido", "domicilio"].some(filled),
    vigencia: ["fecha_vencimiento", "sin_vencimiento"].some(filled),
    programas: programas.length > 0,
    abordaje: ["region_abordaje", "subzona_abordaje", "quitar_territoriales_sin_proyecto"].some(filled) || nuevo.trim() !== "",
  };
  const visible = SECTIONS.filter((s) => s !== "abordaje" || showAbordaje);
  const completed = visible.filter((s) => complete[s]).length;

  function addProyecto() {
    const codigo = nuevo.trim();
    if (!codigo) { setNuevoError("Ingresá un código de proyecto."); return; }
    if (codigo.includes(",")) { setNuevoError("El código no puede tener comas."); return; }
    if (proyectos.includes(codigo)) { setNuevoError("Ese código de proyecto ya está en la lista."); return; }
    setNuevoError("");
    setProyectos([...proyectos, codigo].sort());
    setLineas((cur) => (codigo in cur ? cur : { ...cur, [codigo]: form.data.inactivos[codigo] ?? null }));
    setNuevo("");
  }
  const territorial = (id: number) => form.data.territoriales.find((t) => t.id === id)?.nombre ?? String(id);
  const guardados = Object.fromEntries(form.data.proyectos.map((p) => [p.codigo, p]));

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (editing && !tipoConfirmado && form.tipo_entidad_actual !== null && String(values.tipo_entidad ?? "") !== String(form.tipo_entidad_actual)) { setTipoModal(true); return; }
    const body = new URLSearchParams();
    for (const f of form.fields.filter((x) => POSTED.includes(x.name))) {
      const v = values[f.name];
      if (f.name === "proyectos_lineas") body.set(f.name, JSON.stringify(proyectos.map((codigo) => ({ codigo, linea: lineaDe(codigo) || null }))));
      else if (f.name === "asignaciones_territoriales") body.set(f.name, JSON.stringify(asignaciones.filter((a) => proyectos.includes(a.proyecto))));
      else if (f.type === "multiple") (Array.isArray(v) ? v : []).forEach((x) => body.append(f.name, String(x)));
      else if (Array.isArray(v)) v.forEach((x) => body.append(f.name, String(x)));
      else if (typeof v === "boolean") { if (v) body.set(f.name, "on"); }
      else if (f.name === "cuil_duplicado_confirmado") { if (confirmado) body.set(f.name, "on"); }
      else if (f.name === "cuil_duplicado_confirmado_valor") { if (confirmado) body.set(f.name, cuit); }
      else body.set(f.name, v == null ? "" : String(v));
    }
    setPending(true);
    try {
      const url = editing ? `web/comedores/organizaciones/${form.organizacion_id}/editar/` : "web/comedores/organizaciones/crear/";
      const { data, status } = await webClient.post(url, body, { validateStatus: (s: number) => accepted(s) || s === 400 });
      if ((status === 200 || status === 201) && record(data) && internal(data.redirect)) {
        if (Array.isArray(data.messages) && data.messages.length) { try { window.sessionStorage.setItem(FLASH_KEY, JSON.stringify(data.messages)); } catch { /* the message is optional */ } }
        organizacionesNavigation.assign(data.redirect);
        return;
      }
      if (status === 400 && formValid({ form: (data as Payload["form"] | undefined) && (data as { form: unknown }).form, messages: [] })) {
        const bound = (data as { form: OrganizacionFormData }).form;
        // The server echo is what the native page re-renders: values, options and errors.
        setForm(bound);
        setValues(Object.fromEntries(bound.fields.map((x) => [x.name, x.value])));
        setUbicacion({});
        setSubtipos(null);
        setTipoConfirmado(false);
        return;
      }
      setToasts([{ message: "No se pudo guardar la organización. Recargá la página para ver el estado actual.", level: "error" }]);
    } catch {
      setToasts([{ message: "No se pudo guardar la organización. Recargá la página para ver el estado actual.", level: "error" }]);
    } finally { setPending(false); }
  }

  const f = (name: string) => fields[name];
  const sub = tipo ? subtipos ?? f("subtipo_entidad")?.options ?? [] : [];
  const withOptions = (field: Field, options?: { value: string; label: string }[]): Field => (options ? { ...field, options } : field);
  const cell = (name: string, md: string, extra?: ReactNode, options?: { value: string; label: string }[]) =>
    f(name) && <div className={`col-md-${md}`}><CrispyField f={withOptions(f(name), options)} values={values} set={set} />{extra}</div>;
  const tip = (t: string) => <span className="field-tooltip"><i className="fas fa-info-circle" /><span className="tooltip-text" style={{ display: "block" }}>{t}</span></span>;
  const toggle = (s: Section) => setOpen((cur) => ({ ...cur, [s]: !cur[s] }));
  const subzonas = (form.subzonas ?? []).filter((s) => String(s.region_id) === String(values.region_abordaje));
  const muni = (field: Field) => (ubicacion.municipio ? withOptions(field, ubicacion.municipio) : field);

  return (
    <>
      <InsumosToastList messages={toasts} />
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <div className="d-flex justify-content-between mb-3"><div><a href="#" data-history-back="true" className="btn btn-secondary" onClick={(e) => { e.preventDefault(); window.history.back(); }}>Cancelar</a></div></div>
      <div className="row comedor-form">
        <div className="col-12">
          <form method="post" id="organizacionForm" className="w-100" encType="multipart/form-data" onSubmit={submit}>
            {form.non_field_errors.length > 0 && <div className="alert alert-block alert-danger"><ul className="m-0">{form.non_field_errors.map((e) => <li key={e}>{e}</li>)}</ul></div>}
            <div className="progress-indicator">
              <div className="progress-header">
                <h4 className="progress-title"><i className="fas fa-clipboard-check mr-2" />{" "}Progreso del Formulario</h4>
                <span className="progress-stats"><span id="completedSections">{completed}</span>/<span id="totalSections">{visible.length}</span> secciones completadas</span>
              </div>
              <div className="progress-bar-container"><div className="progress-bar-fill" id="progressBarFill" style={{ width: `${visible.length ? (completed / visible.length) * 100 : 0}%` }} /></div>
            </div>

            <SectionCard id="basic" icon="fa-building" title="Información Básica" subtitle="Datos generales de la organización" status={complete.basic} open={open.basic} toggle={() => toggle("basic")}>
              <div className="form-group row">
                {cell("nombre", "6")}
                {cell("cuit", "6", tip("CUIT de 11 dígitos"))}
                <div className="col-md-12">
                  <div id="cuil-warning" className={`alert alert-warning mt-2${shown.length ? "" : " d-none"}`} role="alert">
                    <strong><i className="fas fa-exclamation-triangle mr-1" />Atención:</strong> Este CUIT ya está registrado en las siguientes organizaciones:
                    <div className="table-responsive mt-2">
                      <table className="table table-sm table-bordered mb-2" id="cuil-duplicados-tabla">
                        <thead className="thead-light"><tr>{["Nombre", "Tipo de entidad", "Subtipo", "Teléfono", "Email", "Domicilio", "Provincia", "Municipio", "Localidad"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
                        <tbody id="cuil-duplicados-tbody">
                          {shown.map((d) => <tr key={String(d.id)}>{["nombre", "tipo_entidad", "subtipo_entidad", "telefono", "email", "domicilio", "provincia", "municipio", "localidad"].map((k) => <td key={k}>{d[k]}</td>)}</tr>)}
                        </tbody>
                      </table>
                    </div>
                    <div className="form-check mt-1">
                      <input className="form-check-input" type="checkbox" id="cuil-confirmar-check" checked={confirmado} onChange={(e) => setConfirmado(e.target.checked)} />
                      <label className="form-check-label font-weight-bold" htmlFor="cuil-confirmar-check">Revisé la información y confirmo la creación del nuevo registro</label>
                    </div>
                  </div>
                </div>
              </div>
              <div className="form-group row">
                {cell("tipo_entidad", "6", <div id="tipo-entidad-warning" className={`alert alert-warning mt-2${editing && form.tipo_entidad_actual !== null && tipo !== String(form.tipo_entidad_actual) ? "" : " d-none"}`} role="alert">
                  <strong><i className="fas fa-exclamation-triangle mr-1" />Atención:</strong> {TIPO_WARNING}</div>)}
                {cell("subtipo_entidad", "6", null, sub)}
              </div>
            </SectionCard>

            <SectionCard id="contacto" icon="fa-phone-alt" title="Contacto" subtitle="Datos de comunicación" status={complete.contacto} open={open.contacto} toggle={() => toggle("contacto")}>
              <div className="form-group row">{cell("telefono", "6")}{cell("email", "6")}</div>
            </SectionCard>

            <SectionCard id="ubicacion" icon="fa-map-marker-alt" title="Ubicación y Domicilio" subtitle="Datos de geolocalización y dirección" status={complete.ubicacion} open={open.ubicacion} toggle={() => toggle("ubicacion")}>
              <div className="form-group row">
                {f("provincia") && <div className="col-md-4"><CrispyField f={f("provincia")} values={values} set={(n, v) => (n === "provincia" ? void onProvincia(String(v)) : set(n, v))} /></div>}
                {f("municipio") && <div className="col-md-4"><div id="municipio-loader" className="skeleton-loader d-none" /><div id="municipio-field"><CrispyField f={muni(f("municipio"))} values={values} set={(n, v) => (n === "municipio" ? void onMunicipio(String(v)) : set(n, v))} /></div></div>}
                {f("localidad") && <div className="col-md-4"><div id="localidad-loader" className="skeleton-loader d-none" /><div id="localidad-field"><CrispyField f={withOptions(f("localidad"), ubicacion.localidad)} values={values} set={set} /></div></div>}
              </div>
              <div className="form-group row">{cell("partido", "6")}{cell("domicilio", "6")}</div>
            </SectionCard>

            <SectionCard id="vigencia" icon="fa-calendar-alt" title="Vigencia" subtitle="Fecha de vencimiento de la organización" status={complete.vigencia} open={open.vigencia} toggle={() => toggle("vigencia")}>
              <div className="form-group row">
                <div className="col-md-6">
                  <CrispyField f={f("fecha_vencimiento")} values={values} set={set} />
                  <div className="mb-3"><CrispyField f={f("sin_vencimiento")} values={values} set={(n, v) => { set(n, v); if (v) set("fecha_vencimiento", ""); }} /></div>
                  {tip("Fecha de vencimiento del convenio o acuerdo")}
                </div>
              </div>
            </SectionCard>

            <SectionCard id="programas" icon="fa-layer-group" title="Programas" subtitle="Programas en los que participa la organización" status={complete.programas} open={open.programas} toggle={() => toggle("programas")}>
              <CrispyField f={f("programas")} values={values} set={set} />
              <p className="text-muted small mb-0">"Datos Abordaje Comunitario" se habilita al elegir Línea Secos o Línea Tradicional.</p>
            </SectionCard>

            {(
              <SectionCard id="abordaje" hidden={!showAbordaje} icon="fa-users" title="Datos Abordaje Comunitario" subtitle="Región, subzona y proyectos con su línea y territoriales" status={complete.abordaje} open={open.abordaje} toggle={() => toggle("abordaje")}>
                <div className="form-group row">
                  {cell("region_abordaje", "6")}
                  {cell("subzona_abordaje", "6", null, [{ value: "", label: "---------" }, ...subzonas.map((s) => ({ value: String(s.id), label: s.nombre }))])}
                </div>
                {["proyectos_lineas", "asignaciones_territoriales"].map((n) => f(n)?.errors.map((e) => <div key={n + e} className="alert alert-danger" role="alert">{e}</div>))}
                <select id="territoriales-opciones" className="d-none" aria-hidden="true" tabIndex={-1} defaultValue="">
                  {form.data.territoriales.map((t) => <option key={t.id} value={t.id}>{t.nombre}</option>)}
                </select>
                <label className="form-label fw-bold mb-2">Proyectos</label>
                <div className="table-responsive">
                  <table className="table align-middle mb-2">
                    <thead><tr><th scope="col">Código de Proyecto</th><th scope="col">Línea</th><th scope="col">Territoriales</th><th scope="col">Convenio</th><th scope="col"><span className="visually-hidden">Quitar</span></th></tr></thead>
                    <tbody id="proyectos-listado" aria-live="polite">
                      {proyectos.map((codigo) => {
                        const asignados = asignaciones.filter((a) => a.proyecto === codigo);
                        const guardado = guardados[codigo];
                        return (
                          <tr key={codigo}>
                            <td><span className="badge rounded-pill text-bg-primary text-break">{codigo}</span></td>
                            <td>
                              {elegidas.length === 1 && lineaDe(codigo) === elegidas[0].id ? <span className="badge text-bg-info">{elegidas[0].nombre}</span> : (
                              <select className="form-select form-select-sm" aria-label={`Línea del proyecto ${codigo}`} value={String(lineas[codigo] ?? "")} onChange={(e) => setLineas((cur) => ({ ...cur, [codigo]: e.target.value ? Number(e.target.value) : null }))}>
                                <option value="">Sin línea</option>
                                {elegidas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
                              </select>)}
                            </td>
                            <td>
                              {asignados.map((a) => (
                                <span key={a.territorial} className="badge rounded-pill text-bg-primary d-inline-flex align-items-center gap-1 me-1 mb-1">
                                  {territorial(a.territorial)}
                                  <button type="button" className="btn-close btn-close-white" style={{ fontSize: "0.6rem" }} aria-label={`Quitar a ${territorial(a.territorial)} del proyecto ${codigo}`}
                                    onClick={() => setAsignaciones((cur) => cur.filter((o) => !(o.proyecto === codigo && o.territorial === a.territorial)))} />
                                </span>
                              ))}
                              <select className="form-select form-select-sm d-inline-block w-auto" aria-label={`Agregar territorial al proyecto ${codigo}`} value=""
                                onChange={(e) => e.target.value && setAsignaciones((cur) => [...cur, { proyecto: codigo, territorial: Number(e.target.value) }])}>
                                <option value="">+ Territorial</option>
                                {form.data.territoriales.filter((t) => !asignados.some((a) => a.territorial === t.id)).map((t) => <option key={t.id} value={t.id}>{t.nombre}</option>)}
                              </select>
                            </td>
                            <td>
                              {guardado?.linea && guardado.linea === lineaDe(codigo)
                                ? <a className="btn btn-outline-primary btn-sm" href={`/organizaciones/proyecto/${guardado.id}/convenio`}>{guardado.convenio ? "Editar convenio" : "Cargar convenio"}</a>
                                : <span className="text-muted small">Disponible al guardar con su línea</span>}
                            </td>
                            <td className="text-end">
                              <button type="button" className="btn btn-outline-danger btn-sm" aria-label={`Quitar proyecto ${codigo}`}
                                onClick={() => { setProyectos((cur) => cur.filter((c) => c !== codigo)); setAsignaciones((cur) => cur.filter((a) => a.proyecto !== codigo)); }}>Quitar</button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {proyectos.length === 0 && <p id="proyectos-vacio" className="text-muted py-2">No hay proyectos agregados.</p>}
                <div className="row g-2 align-items-end">
                  <div className="col-md-6">
                    <label htmlFor="nuevo-codigo-proyecto" className="form-label">Nuevo código de proyecto</label>
                    <input type="text" id="nuevo-codigo-proyecto" className="form-control" maxLength={255} autoComplete="off" value={nuevo} onChange={(e) => setNuevo(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addProyecto(); } }} />
                  </div>
                  <div className="col-md-3"><button type="button" className="btn btn-primary" id="agregarProyectoBtn" onClick={addProyecto}><i className="fas fa-plus me-1" /> Agregar proyecto</button></div>
                </div>
                <div id="nuevo-codigo-proyecto-error" className={`text-danger small mt-2${nuevoError ? "" : " d-none"}`} role="alert">{nuevoError}</div>
                <p className="text-muted small mt-2 mb-0">Cada proyecto pertenece a una línea de Abordaje Comunitario. Quitar un proyecto lo desactiva: su línea y su convenio se conservan; sus territoriales se quitan.</p>
                {quitar?.options?.length ? (
                  <div className="mt-3">
                    <p className="fw-bold mb-1">Territoriales anteriores sin proyecto</p>
                    <p className="text-muted mb-1">Asignados a la organización antes de que los territoriales fueran por proyecto. Se conservan hasta que los agregues a un proyecto o marques su baja.</p>
                    <CrispyField f={quitar} values={values} set={set} />
                  </div>
                ) : null}
              </SectionCard>
            )}

            <div className="sticky-actions">
              <div>
                <button type="button" data-history-back="true" className="btn btn-secondary mr-2" onClick={() => window.history.back()}><i className="fas fa-times mr-1" /> Cancelar</button>{" "}
                <button className="btn btn-success" type="submit" id="organizacionSubmitBtn" disabled={pending || (shown.length > 0 && !confirmado)}><i className="fas fa-save mr-1" /> Guardar organización</button>
              </div>
            </div>
          </form>
          {tipoModal && (
            <div className="modal fade show d-block" id="modalConfirmarTipoEntidad" tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="modalConfirmarTipoEntidadLabel">
              <div className="modal-dialog modal-dialog-centered"><div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title" id="modalConfirmarTipoEntidadLabel"><i className="fas fa-exclamation-triangle text-warning mr-2" /> Confirmar cambio de Tipo de Entidad</h5>
                  <button type="button" className="btn-close" aria-label="Close" onClick={() => setTipoModal(false)} />
                </div>
                <div className="modal-body">
                  <p>Al cambiar el <strong>Tipo de Entidad</strong> se reiniciara el listado de documentos del legajo de la organizacion (se eliminaran los archivos ya cargados).</p>
                  <p className="mb-0">Ademas, las admisiones vinculadas mostraran una advertencia para resincronizarse o continuar con la informacion actual.</p>
                  <p className="mt-2 mb-0"><strong>¿Esta seguro de continuar?</strong></p>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setTipoModal(false)}>Cancelar</button>
                  <button type="button" className="btn btn-warning" id="confirmarCambioTipoEntidadBtn" onClick={() => { setTipoModal(false); setTipoConfirmado(true); window.setTimeout(() => (document.getElementById("organizacionForm") as HTMLFormElement | null)?.requestSubmit(), 0); }}>Confirmar cambio</button>
                </div>
              </div></div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function OrganizacionForm({ id }: { id: number | null }) {
  const [state] = useMainResource(id === null ? "web/comedores/organizaciones/formulario/" : `web/comedores/organizaciones/${id}/formulario/`, formValid);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: "Organizaciones",
    heading: "Organizaciones",
    // The native form fills `breadcrumb_items` with nothing: an empty breadcrumb.
    breadcrumb: <></>,
    content: <OrganizacionFormContent initial={data.form} messages={data.messages} />,
  }));
}
