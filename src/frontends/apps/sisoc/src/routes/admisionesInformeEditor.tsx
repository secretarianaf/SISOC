/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * AD02.01 technical-report editor (`comedores/admision/informe_tecnico/<tipo>/<admision_id>/crear/`
 * and `.../<pk>/editar/`), with the native template's markup: collapsible sections, geography selects
 * and the unsaved-changes warning of `informeTecnicoSecciones.js`, `geografiaProvinciaLocalidad.js`
 * and `informeTecnicoCambiosSinGuardar.js`. The effective form comes from
 * `/api/web/comedores/admisiones/informes/.../formulario/` and drafts and submissions are saved
 * through `.../guardar/`, which run the native form and service. The layout below mirrors
 * `partials/informe_tecnico_campos.html`; a field the form does not expose renders no control.
 */
type Params = { tipo: string; admision?: string; id?: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info"; tags?: string };
export type Choice = { value: string; label: string };
export type Value = string | boolean;
export type Field = {
  name: string; label: string; kind: "text" | "select" | "textarea" | "date" | "number" | "checkbox"; required: boolean;
  value: Value; help_text: string; max_length: number | null; errors: string[]; id: string;
  attrs: Record<string, string | boolean>; widget: string; choices?: Choice[];
};
type Antecedente = { admision_id: number; incluida: string; resolucion: string; convenio: string; expediente: string };
type Publicacion = { plantilla: { codigo: string; nombre: string; version: number } | null; error: string | null; configuracion_faltante: boolean; detalle_copiable: string };
export type FormData = {
  tipo: string; admision_id: number; informe_id: number | null; estado: string; comedor: string; permite_no_corresponde: boolean;
  fields: Field[]; antecedentes: Antecedente[]; non_field_errors: string[]; campos_a_subsanar: string[]; observacion: string;
  publicacion: Publicacion; urls: { volver: string; previsualizar: string | null; reportar_faltante: string; localidades: string }; messages: Message[];
};
type Layout = { id: string; title: string; fields: [string, string | null, string, number?][] };

const LEVELS = ["success", "error", "warning", "info"];
const KINDS = ["text", "select", "textarea", "date", "number", "checkbox"];
const API = "web/comedores/admisiones/informes/";
const DAYS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"];
const MEALS: [string, string][] = [["desayuno", "Desayuno"], ["almuerzo", "Almuerzo"], ["merienda", "Merienda"], ["cena", "Cena"]];
const EMPTY_LOCALIDAD: Choice = { value: "", label: "Seleccione una localidad" };
export const fieldValid = (f: unknown): f is Field => record(f) && ["name", "label", "id", "help_text", "widget"].every((k) => text(f[k])) &&
  KINDS.includes(f.kind as string) && typeof f.required === "boolean" && (text(f.value) || typeof f.value === "boolean") &&
  Array.isArray(f.errors) && f.errors.every(text) && record(f.attrs) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));
const messagesValid = (v: unknown): v is Message[] => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string) && (m.tags === undefined || text(m.tags)));
/** The native form draws this tag inside the form; the layout toast script cannot (its tags are not a valid call). */
const IN_FORM = "configuracion-template";
export const formValid = (v: unknown): v is FormData => record(v) && ["tipo", "estado", "comedor", "observacion"].every((k) => text(v[k])) &&
  Array.isArray(v.fields) && v.fields.every(fieldValid) && Array.isArray(v.antecedentes) && Array.isArray(v.non_field_errors) &&
  Array.isArray(v.campos_a_subsanar) && record(v.publicacion) && record(v.urls) && internal(v.urls.volver) && internal(v.urls.localidades) &&
  (v.urls.previsualizar === null || internal(v.urls.previsualizar)) && internal(v.urls.reportar_faltante) && messagesValid(v.messages);

/** `[field, «campos a subsanar» key (null: the field name, "": no check), column class, 1 when the wrapper depends on the field]`. */
const LAYOUT: Layout[] = [
  { id: "Organizacion", title: "Datos de la Organización", fields: [["expediente_nro","Número Expediente","col-md-6"],["nombre_organizacion",null,"col-md-6"],["domicilio_organizacion",null,"col-md-6"],["localidad_organizacion",null,"col-md-6"],["partido_organizacion",null,"col-md-6"],["provincia_organizacion",null,"col-md-6"],["telefono_organizacion",null,"col-md-6"],["mail_organizacion",null,"col-md-6"],["cuit_organizacion",null,"col-md-6"]] },
  { id: "Representante", title: "Datos del Representante", fields: [["representante_nombre",null,"col-md-6"],["representante_cargo",null,"col-md-6"],["representante_dni",null,"col-md-6"]] },
  { id: "Espacio", title: "Datos del Comedor/Merendero", fields: [["tipo_espacio",null,"col-md-6"],["nombre_espacio",null,"col-md-6"],["domicilio_espacio",null,"col-md-6"],["barrio_espacio",null,"col-md-6"],["localidad_espacio",null,"col-md-6"],["partido_espacio",null,"col-md-6"],["provincia_espacio",null,"col-md-6"],["domicilio_electronico_espacio",null,"col-md-6"]] },
  { id: "Tarjeta", title: "Responsable de la Tarjeta", fields: [["responsable_tarjeta_nombre",null,"col-md-6"],["responsable_tarjeta_mail",null,"col-md-6"],["responsable_tarjeta_dni",null,"col-md-6"],["responsable_tarjeta_cuit",null,"col-md-6"],["responsable_tarjeta_domicilio",null,"col-md-6"],["responsable_tarjeta_localidad",null,"col-md-6"],["responsable_tarjeta_provincia",null,"col-md-6"],["responsable_tarjeta_telefono",null,"col-md-6"]] },
  { id: "Adicional", title: "Información Adicional", fields: [["total_acreditaciones",null,"col-md-6"],["plazo_ejecucion",null,"col-md-6"],["nota_gde_if",null,"col-md-6"],["constancia_subsidios_dnsa",null,"col-md-6"],["constancia_subsidios_pnud",null,"col-md-6"],["partido_poblacion_destinataria",null,"col-md-6"],["provincia_poblacion_destinataria",null,"col-md-6"],["fecha_vencimiento_mandatos",null,"col-md-6"],["criterio_seleccionado",null,"col-md-6"],["finalizacion_convenio_pnud_vigente","","col-md-6",1]] },
  { id: "EspecificosBase", title: "Campos Específicos - Organización de Base", fields: [["declaracion_jurada_recepcion_subsidios",null,"col-md-6"],["constancia_inexistencia_percepcion_otros_subsidios",null,"col-md-6"],["organizacion_avalista_1",null,"col-md-6"],["organizacion_avalista_2",null,"col-md-6"],["material_difusion_vinculado",null,"col-md-6"],["if_relevamiento",null,"col-md-6"]] },
  { id: "EspecificosJuridico", title: "Campos Específicos - Organización Jurídica", fields: [["validacion_registro_nacional",null,"col-md-6"],["IF_relevamiento_territorial",null,"col-md-6"]] },
  { id: "ReferenciaIncorporacion", title: "Referencia a la Incorporación", fields: [["expediente_incorporacion","","col-md-6"],["convenio_incorporacion","","col-md-6"],["presentacion_avales","","col-12",1],["informe_tecnico_complementario_modificacion_prestaciones","","col-12",1],["if_it_complementario","","col-12",1]] },
];
const section = (id: string) => LAYOUT.find((s) => s.id === id)!;
const ALL_SECTIONS = LAYOUT.map((s) => s.id).concat(["AprobadasUltimoConvenio", "Solicitudes", "Aprobadas", "Antecedentes", "Caratula"]);

/** crispy-bootstrap5 field (`as_crispy_field`) with the widget attributes the native form computed. */
export function Crispy({ f, value, onChange, options }: { f: Field; value: Value; onChange: (v: Value) => void; options?: Choice[] }) {
  const invalid = f.errors.length > 0;
  const { class: widgetClass, maxlength, ...rest } = f.attrs;
  const props: Record<string, unknown> = { name: f.name, id: f.id, ...rest };
  if (maxlength !== undefined) props.maxLength = Number(maxlength);
  const base = f.kind === "select" ? "select form-select" : f.kind === "date" ? `${widgetClass ?? "form-control"} dateinput` : f.widget === "EmailInput" ? "emailinput form-control" : "textinput form-control";
  props.className = `${base}${invalid ? " is-invalid" : ""}`;
  if (invalid) { props["aria-invalid"] = "true"; props["aria-describedby"] = `${f.id}_error`; }
  const input = f.kind === "select"
    ? <select {...props} value={value as string} onChange={(e) => onChange(e.target.value)}>
      {(options ?? f.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>
    : <input {...props} type={f.kind === "date" ? "date" : f.widget === "EmailInput" ? "email" : "text"} value={value as string} onChange={(e) => onChange(e.target.value)} />;
  return <div id={`div_${f.id}`} className="mb-3">
    {f.label !== "" && <label htmlFor={f.id} className={`form-label${f.required ? " requiredField" : ""}`}>{f.label}{f.required && <span className="asteriskField">*</span>}</label>}
    {input}
    {invalid && <div id={`${f.id}_error`} className="invalid-feedback">
      {f.errors.map((e, i) => <p key={i} id={`error_${i + 1}_${f.id}`}><strong>{e}</strong></p>)}
    </div>}
    {f.help_text !== "" && <div id={`hint_${f.id}`} className="form-text">{f.help_text}</div>}
  </div>;
}

/** `{{ form.<name> }}` of the day tables: the bare widget. */
function Cell({ f, value, onChange }: { f: Field | undefined; value: Value; onChange: (v: Value) => void }) {
  if (!f) return null;
  const { class: widgetClass, ...rest } = f.attrs;
  return <input type="number" name={f.name} id={f.id} {...rest} {...(widgetClass !== undefined ? { className: String(widgetClass) } : {})} value={value as string} onChange={(e) => onChange(e.target.value)} />;
}

function Card({ id, title, open, toggle, children }: { id: string; title: string; open: boolean; toggle: () => void; children: ReactNode }) {
  const target = `informeSeccion${id}`;
  return <div className="card mb-4">
    <div className="card-header p-0">
      <button className={`btn btn-link w-100 d-flex justify-content-between align-items-center text-decoration-none text-reset px-3 py-2${open ? "" : " collapsed"}`}
        type="button" data-bs-toggle="collapse" data-bs-target={`#${target}`} aria-expanded={open} aria-controls={target} onClick={toggle}>
        <span className="h5 mb-0 text-start">{title}</span>
        <i className="fas fa-chevron-down informe-seccion-chevron" aria-hidden="true" />
      </button>
    </div>
    <div className={`card-body collapse${open ? " show" : ""}`} id={target} data-informe-seccion="1">{children}</div>
  </div>;
}

const HEAD_PLAIN = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];
const HEAD_ACCENT = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const initialValues = (fields: Field[]) => Object.fromEntries(fields.map((f) => [f.name, f.value])) as Record<string, Value>;

function Unsaved({ keep, leave, save }: { keep: () => void; leave: () => void; save: () => void }) {
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    document.body.classList.add("modal-open");
    dialog.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Tab" || !dialog.current) return;
      const items = [...dialog.current.querySelectorAll<HTMLElement>("button")];
      const first = items[0], last = items[items.length - 1], active = document.activeElement;
      if (!dialog.current.contains(active) || (event.shiftKey && (active === first || active === dialog.current)) || (!event.shiftKey && active === last)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.body.classList.remove("modal-open"); document.removeEventListener("keydown", onKey); };
  }, []);
  return <>
    <div ref={dialog} className="modal fade show" id="modalCambiosSinGuardar" tabIndex={-1} aria-labelledby="modalCambiosSinGuardarLabel" aria-modal="true" role="dialog" style={{ display: "block" }}>
      <div className="modal-dialog modal-dialog-centered"><div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id="modalCambiosSinGuardarLabel"><i className="fas fa-exclamation-triangle text-warning me-2" aria-hidden="true" /> Cambios sin guardar</h5>
        </div>
        <div className="modal-body">
          <p className="mb-1">Hay cambios en el Informe Técnico que todavía no se guardaron.</p>
          <p className="mb-0 text-muted small">Si salís sin guardar, se pierden. Al guardar como borrador vas a quedar en la pantalla que corresponde al informe, no necesariamente en el enlace que hiciste click.</p>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={keep}>Seguir editando</button>
          <button type="button" className="btn btn-outline-danger" onClick={leave}>Salir sin guardar</button>
          <button type="button" className="btn btn-primary" onClick={save}><i className="fas fa-save me-1" aria-hidden="true" /> Guardar borrador</button>
        </div>
      </div></div>
    </div>
    <div className="modal-backdrop fade show" />
  </>;
}

async function fetchLocalidades(url: string, provincia: string): Promise<Choice[]> {
  if (!provincia) return [EMPTY_LOCALIDAD];
  try {
    const response = await fetch(`${url}?provincia_id=${encodeURIComponent(provincia)}`, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!response.ok) throw new Error(`Error ${response.status}`);
    const lista = await response.json() as { id: number | string; nombre: string }[];
    return [EMPTY_LOCALIDAD, ...lista.map((l) => ({ value: String(l.id), label: l.nombre }))];
  } catch {
    return [EMPTY_LOCALIDAD];
  }
}

/** The cover of the expediente drawn inside the report form of the technical editor (`caratula_expediente_form.html`). */
export type Caratula = { num_expediente: string | null; borrador: boolean; fields: Field[] | null };
export type Embedded = { caratula: Caratula; onSaved: (messages: Message[]) => void; flash: (messages: Message[]) => void };

/** `partials/numero_expediente_estructurado.html`: the four parts of the expediente number. */
export function ExpedienteGrid({ fields, values, set, nonField = [] }: { fields: Field[]; values: Record<string, Value>; set: (name: string, v: string) => void; nonField?: string[] }) {
  const by = (short: string) => fields.find((f) => f.name.endsWith(short))!;
  const widget = (f: Field) => {
    const { class: cls, maxlength, ...rest } = f.attrs;
    return <input type="text" name={f.name} id={f.id} className={String(cls ?? "form-control")} maxLength={maxlength ? Number(maxlength) : undefined} {...rest}
      required={f.required} value={String(values[f.name] ?? "")} onChange={(e) => set(f.name, e.target.value)} />;
  };
  const err = (f: Field) => f.errors.length > 0 && <ul className="errorlist">{f.errors.map((m, i) => <li key={i}>{m}</li>)}</ul>;
  const a = by("expediente_anio"), n = by("expediente_numero"), r = by("expediente_reparticion"), o = by("expediente_organismo");
  return <>
    <div className="row g-3 expediente-estructurado-grid">
      <div className="col-12 col-md-2">
        <label className="form-label" htmlFor={a.id}>Año</label>
        <div className="input-group"><span className="input-group-text">EX-</span>{widget(a)}</div>
        {err(a)}
      </div>
      <div className="col-12 col-md-3">
        <label className="form-label" htmlFor={n.id}>Número</label>
        {widget(n)}
        {err(n)}
      </div>
      <div className="col-12 col-md-4">
        <label className="form-label" htmlFor={r.id}>Repartición</label>
        <div className="input-group"><span className="input-group-text">APN-</span>{widget(r)}</div>
        {err(r)}
      </div>
      <div className="col-12 col-md-3">
        <label className="form-label" htmlFor={o.id}>Organismo</label>
        <div className="input-group"><span className="input-group-text">#</span>{widget(o)}</div>
        {err(o)}
      </div>
    </div>
    {nonField.length > 0 && <div className="alert alert-danger mt-3 mb-0"><ul className="errorlist nonfield">{nonField.map((m, i) => <li key={i}>{m}</li>)}</ul></div>}
  </>;
}

export function Editor({ initial, saveUrl, embedded }: { initial: FormData; saveUrl: string; embedded?: Embedded }) {
  const [form, setForm] = useState(initial);
  const [caratulaFields, setCaratulaFields] = useState<Field[] | null>(embedded?.caratula.fields ?? null);
  const [values, setValues] = useState(() => initialValues([...initial.fields, ...(embedded?.caratula.fields ?? [])]));
  const [options, setOptions] = useState<Record<string, Choice[]>>({});
  const [toasts, setToasts] = useState<{ key: number; items: Message[] }>({ key: 0, items: initial.messages });
  const [manual, setManual] = useState<Record<string, boolean>>({});
  const [modal, setModal] = useState(false);
  const reference = useRef(initialValues([...initial.fields, ...(embedded?.caratula.fields ?? [])]));
  const interacted = useRef(false);
  const sending = useRef(false);
  const pending = useRef<string | null>(null);
  const valuesRef = useRef(values);
  const byName = useMemo(() => new Map(form.fields.map((f) => [f.name, f])), [form.fields]);
  const pairs = useMemo(() => form.fields.filter((f) => f.attrs["data-geografia-provincia"]).map((f) => ({ provincia: f.name, localidad: String(f.attrs["data-geografia-provincia"]).replace(/^id_/, "") })), [form.fields]);
  const subsanar = form.campos_a_subsanar;
  const renovacion = byName.has("expediente_incorporacion");
  const dirtyRef = useRef<() => boolean>(() => false);
  useEffect(() => {
    valuesRef.current = values;
    dirtyRef.current = () => interacted.current && !sending.current && Object.keys(values).some((k) => reference.current[k] !== values[k]);
  });

  // `informeTecnicoSecciones.js`: sections with errors or fields to fix start open.
  const auto = useMemo(() => {
    const keys = new Set(subsanar);
    const open = new Set<string>();
    for (const s of LAYOUT) if (s.fields.some(([n, k]) => (byName.get(n)?.errors.length ?? 0) > 0 || (k !== "" && keys.has(k ?? n)))) open.add(s.id);
    for (const f of form.fields) {
      if (!f.errors.length) continue;
      if (f.name.startsWith("solicitudes_")) open.add("Solicitudes");
      else if (f.name.startsWith("aprobadas_ultimo_convenio_")) open.add("AprobadasUltimoConvenio");
      else if (f.name.startsWith("aprobadas_")) open.add("Aprobadas");
      else if (f.name.startsWith("antecedente_")) open.add("Antecedentes");
    }
    if (caratulaFields?.some((f) => f.errors.length > 0)) open.add("Caratula");
    return open;
  }, [form.fields, byName, subsanar, caratulaFields]);
  const isOpen = (id: string) => manual[id] ?? auto.has(id);

  // `geografiaProvinciaLocalidad.js`: populate the localities of the province already selected.
  useEffect(() => {
    let active = true;
    for (const { provincia, localidad } of pairs) {
      const id = valuesRef.current[provincia] as string;
      if (!id) continue;
      void fetchLocalidades(form.urls.localidades, id).then((lista) => {
        if (!active) return;
        const keep = String(valuesRef.current[localidad] ?? "");
        setOptions((o) => ({ ...o, [localidad]: lista }));
        setValues((v) => ({ ...v, [localidad]: lista.some((c) => c.value === keep) ? keep : "" }));
      });
    }
    return () => { active = false; };
  }, [pairs, form.urls.localidades]);

  // `informeTecnicoCambiosSinGuardar.js`: external links ask first, tab close uses the browser prompt.
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
      const link = (event.target as Element).closest<HTMLAnchorElement>("a[href]");
      if (!link || !dirtyRef.current()) return;
      const href = link.getAttribute("href") ?? "";
      if (href.startsWith("#") || href.startsWith("javascript:") || (link.target && link.target !== "_self") || link.hasAttribute("download") || link.dataset.bsToggle) return;
      event.preventDefault();
      pending.current = link.href;
      setModal(true);
    };
    const onUnload = (event: BeforeUnloadEvent) => { if (dirtyRef.current()) { event.preventDefault(); event.returnValue = ""; } };
    const onShow = () => { sending.current = false; };
    document.addEventListener("click", onClick, true);
    window.addEventListener("beforeunload", onUnload);
    window.addEventListener("pageshow", onShow);
    return () => { document.removeEventListener("click", onClick, true); window.removeEventListener("beforeunload", onUnload); window.removeEventListener("pageshow", onShow); };
  }, []);

  const set = (name: string, value: Value) => {
    interacted.current = true;
    setValues((v) => ({ ...v, [name]: value }));
    const localidad = pairs.find((p) => p.provincia === name)?.localidad;
    if (!localidad) return;
    void fetchLocalidades(form.urls.localidades, value as string).then((lista) => {
      setOptions((o) => ({ ...o, [localidad]: lista }));
      setValues((v) => ({ ...v, [localidad]: "" }));
    });
  };

  const save = async (action: "draft" | "submit") => {
    sending.current = true;
    const toast = (items: Message[]) => setToasts((t) => ({ key: t.key + 1, items }));
    try {
      const { data, status } = await webClient.post(saveUrl, { action, values }, { validateStatus: (s: number) => s >= 200 && s < 500 });
      if (embedded && record(data) && data.success === true) { embedded.onSaved(messagesValid(data.messages) ? data.messages : []); return; }
      if (record(data) && data.success === true && internal(data.redirect)) { window.location.assign(data.redirect); return; }
      sending.current = false;
      if (status === 400 && record(data) && Array.isArray(data.fields) && data.fields.every(fieldValid)) {
        const cover = Array.isArray(data.caratula_fields) && data.caratula_fields.every(fieldValid) ? data.caratula_fields as Field[] : null;
        setForm((f) => ({ ...f, fields: data.fields as Field[], non_field_errors: Array.isArray(data.non_field_errors) ? (data.non_field_errors as string[]) : [] }));
        if (cover) setCaratulaFields(cover);
        setValues(initialValues([...(data.fields as Field[]), ...(cover ?? [])]));
        setManual({}); // the native page reloads: only the sections with errors stay open.
        if (embedded) {
          embedded.flash(messagesValid(data.messages) ? data.messages : []);
          // The native page reloads and scrolls to the section: keyboard focus starts at the document start.
          document.getElementById("informe-tecnico-seccion")?.scrollIntoView({ behavior: "smooth", block: "start" });
          const marker = document.createElement("span");
          marker.tabIndex = -1;
          document.body.prepend(marker);
          marker.focus({ preventScroll: true });
          marker.remove();
          return;
        }
        toast(text(data.message) ? [{ message: data.message, level: "error" }] : []);
        return;
      }
      if (embedded && record(data) && messagesValid(data.messages) && data.messages.length) { embedded.flash(data.messages); return; }
      toast([{ message: record(data) && text(data.error) ? data.error : "No se pudo guardar el informe técnico.", level: "error" }]);
    } catch {
      sending.current = false;
      toast([{ message: "No se pudo guardar el informe técnico.", level: "error" }]);
    }
  };
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    if (submitter?.getAttribute("formaction")) return; // «Notificar a referentes del sistema»: native POST.
    event.preventDefault();
    void save(submitter?.value === "submit" ? "submit" : "draft");
  };
  // The click (capture) opens every section before the browser validates, as the native script does.
  const abrirTodo = (event: { target: EventTarget }) => {
    if ((event.target as Element).closest('button[type="submit"], input[type="submit"]')) setManual(Object.fromEntries(ALL_SECTIONS.map((id) => [id, true])));
  };
  const toggle = (id: string) => setManual((m) => ({ ...m, [id]: !(m[id] ?? auto.has(id)) }));
  const field = (name: string) => byName.get(name);
  const crispy = (name: string) => {
    const f = field(name);
    return f ? <Crispy f={f} value={values[name] ?? ""} options={options[name]} onChange={(v) => set(name, v)} /> : null;
  };
  const wrapper = ([name, key, col, opt]: Layout["fields"][number]) => {
    if (opt && !field(name)) return null;
    const border = key !== "" && subsanar.includes(key ?? name) ? " border border-danger rounded p-2" : "";
    const check = name === "fecha_vencimiento_mandatos" && form.permite_no_corresponde ? field("no_corresponde_fecha_vencimiento") : undefined;
    return <div key={name} className={`${col} mb-3${border}`}>
      {crispy(name)}
      {check && <div className="form-check mt-2">
        <input type="checkbox" name={check.name} id={String(check.attrs.id)} className={String(check.attrs.class ?? "")} checked={values[check.name] === true} onChange={(e) => set(check.name, e.target.checked)} />{" "}
        <label className="form-check-label" htmlFor="no_corresponde_fecha_vencimiento">No corresponde</label>
      </div>}
    </div>;
  };
  const plain = (id: string) => {
    const s = section(id);
    return <Card key={id} id={id} title={s.title} open={isOpen(id)} toggle={() => toggle(id)}><div className="row">{s.fields.map(wrapper)}</div></Card>;
  };
  const tabla = (id: string, title: string, prefix: string, head: string[], th: (label: string) => ReactNode) =>
    <Card id={id} title={title} open={isOpen(id)} toggle={() => toggle(id)}>
      <div className="table-responsive">
        <table className="table table-sm table-bordered align-middle text-center mb-0">
          <thead className="table-dark"><tr className="text-uppercase small">
            <th scope="col" className="fw-semibold">Comida</th>{head.map((h) => <th key={h} scope="col">{h}</th>)}
          </tr></thead>
          <tbody>{MEALS.map(([meal, label]) => <tr key={meal}>
            {th(label)}
            {DAYS.map((day) => { const n = `${prefix}_${meal}_${day}`; return <td key={day} className="p-1"><Cell f={field(n)} value={values[n] ?? ""} onChange={(v) => set(n, v)} /></td>; })}
          </tr>)}</tbody>
        </table>
      </div>
    </Card>;
  const pub = form.publicacion;

  const cover = embedded && <Card id="Caratula" title="Carátula del Expediente" open={isOpen("Caratula")} toggle={() => toggle("Caratula")}>
    {embedded.caratula.num_expediente ? <>
      <p className="mb-0">Expediente caratulado: <strong>{embedded.caratula.num_expediente}</strong></p>
      <small className="text-muted">Para modificarlo usá la edición del número de expediente en la ficha de la admisión.</small>
    </> : caratulaFields ? <>
      {embedded.caratula.borrador && <p className="mb-2"><span className="badge bg-secondary">Borrador</span>{" "}<small className="text-muted ms-1">Guardado sin caratular todavía.</small></p>}
      <ExpedienteGrid fields={caratulaFields} values={values} set={(name, v) => set(name, v)} />
      <small className="text-muted d-block mt-2">
        Se guarda junto con el informe técnico: <strong>Guardar Borrador</strong> conserva el avance aunque esté incompleto, y <strong>Finalizar</strong> valida y caratula el expediente.
      </small>
    </> : <p className="text-muted mb-0">La caratulación no está disponible en el estado actual de la admisión.</p>}
  </Card>;
  const formEl = (
      <form method="post" encType="multipart/form-data" data-localidades-url={form.urls.localidades} data-avisar-cambios-sin-guardar="1" onSubmit={onSubmit} onClickCapture={abrirTodo}>
        {/* `{% csrf_token %}`: the notification button posts to the native URL. */}
        <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
        {embedded && <input type="hidden" name="btnInformeTecnicoCaratula" value="1" />}
        {cover}
        {toasts.items.filter((m) => m.tags?.includes(IN_FORM)).map((m, i) => <section key={i} className="alert border-0 shadow-sm mb-4" role="status" style={{ background: "#0b5f8a", color: "#fff" }}>
          <div className="d-flex align-items-center gap-3">
            <span className="rounded-circle d-inline-flex align-items-center justify-content-center flex-shrink-0" style={{ width: "2.25rem", height: "2.25rem", background: "#9ee7ff", color: "#06415f" }}><i className="fas fa-check" aria-hidden="true" /></span>
            <div><strong>Notificación enviada</strong><div>{m.message}</div></div>
          </div>
        </section>)}
        {form.non_field_errors.length > 0 && <div className="alert alert-danger">{form.non_field_errors.map((e, i) => <p key={i} className="mb-0">{e}</p>)}</div>}
        {pub.plantilla ? <div className="alert alert-info">
          Al finalizar se generará el DOCX con el template <strong>{pub.plantilla.codigo} — {pub.plantilla.nombre}</strong>, versión {pub.plantilla.version}.
          {form.urls.previsualizar && <a href={form.urls.previsualizar} className="btn btn-sm btn-outline-primary ms-2"><i className="fas fa-eye" /> Vista previa DOCX</a>}
        </div> : pub.error ? <section className="alert shadow-sm mb-4" role="alert" style={{ background: "#103a5d", border: "1px solid #3b82c4", color: "#f8fbff" }}>
          <div className="d-flex align-items-start gap-3">
            <span className="rounded-circle d-inline-flex align-items-center justify-content-center flex-shrink-0" style={{ width: "2.5rem", height: "2.5rem", background: "#7dd3fc", color: "#073655" }}><i className="fas fa-cog" aria-hidden="true" /></span>
            <div className="flex-grow-1">
              <h2 className="h5 fw-bold mb-2">Configuración pendiente</h2>
              <p className="mb-2">Todavía no está configurado el template necesario para generar este Informe Técnico.</p>
              <p className="mb-0">No podrá finalizar el informe hasta que exista una versión dinámica publicada. Notifique a los referentes del sistema para que completen la configuración.</p>
            </div>
          </div>
          {pub.configuracion_faltante && <>
            <details className="mt-3"><summary className="fw-semibold">Ver detalle para soporte</summary>
              <textarea id="detalle-configuracion-faltante" className="form-control form-control-sm mt-2 font-monospace" rows={5} readOnly value={pub.detalle_copiable} /></details>
            <button type="submit" formAction={form.urls.reportar_faltante} formMethod="post" formNoValidate name="informe_id" value={form.informe_id ?? ""} className="btn mt-3" style={{ background: "#f6c453", borderColor: "#f6c453", color: "#18212b" }}>
              <i className="fas fa-bell me-1" aria-hidden="true" /> Notificar a referentes del sistema
            </button>
          </>}
        </section> : null}
        {subsanar.length > 0 && <div className="alert alert-danger"><h5>Campos para subsanar</h5></div>}
        {form.observacion !== "" && <div className="alert alert-info"><h6>Observaciones:</h6>{form.observacion}</div>}
        {["Organizacion", "Representante", "Espacio", "Tarjeta"].map(plain)}
        {renovacion && tabla("AprobadasUltimoConvenio", "Prestaciones aprobadas en el ultimo convenio", "aprobadas_ultimo_convenio", HEAD_PLAIN, (m) => <th>{m}</th>)}
        {tabla("Solicitudes", "Solicitudes", "solicitudes", HEAD_ACCENT, (m) => <th scope="row" className="text-nowrap fw-semibold">{m}</th>)}
        {tabla("Aprobadas", "Prestaciones Aprobadas", "aprobadas", HEAD_ACCENT, (m) => <th>{m}</th>)}
        {plain("Adicional")}
        {form.tipo === "base" ? plain("EspecificosBase") : form.tipo === "juridico" ? plain("EspecificosJuridico") : null}
        {renovacion && plain("ReferenciaIncorporacion")}
        {renovacion && form.antecedentes.length > 0 && <Card id="Antecedentes" title="Antecedentes de Renovaciones" open={isOpen("Antecedentes")} toggle={() => toggle("Antecedentes")}>
          {form.antecedentes.map((a) => {
            const inc = field(a.incluida);
            return <div key={a.admision_id} className="border rounded p-3 mb-3">
              <strong className="d-block mb-2">Admisión #{a.admision_id}</strong>
              <div className="form-check mb-2">
                {inc && <input type="checkbox" name={inc.name} id={inc.id} checked={values[inc.name] === true} onChange={(e) => set(inc.name, e.target.checked)} />}{" "}
                <label className="form-check-label" htmlFor={inc?.id}>Incluir en el informe</label>
              </div>
              <div className="row">{[a.resolucion, a.convenio, a.expediente].map((n) => <div key={n} className="col-md-4">{crispy(n)}</div>)}</div>
            </div>;
          })}
        </Card>}
        {embedded ? <div className="d-flex justify-content-end gap-2">
          <button type="submit" name="action" value="draft" formNoValidate className="btn btn-primary"><i className="fas fa-save" /> Guardar Borrador</button>
          <button type="submit" name="action" value="submit" className="btn btn-success"><i className="fas fa-paper-plane" /> Finalizar</button>
        </div> : <div className="card"><div className="card-body"><div className="d-flex justify-content-between">
          <a href={form.urls.volver} className="btn btn-secondary"><i className="fas fa-arrow-left" /> Volver</a>
          <div>
            <button type="submit" name="action" value="draft" className="btn btn-primary me-2"><i className="fas fa-save" /> Guardar Borrador</button>{" "}
            <button type="submit" name="action" value="submit" className="btn btn-success"><i className="fas fa-paper-plane" /> Finalizar</button>
          </div>
        </div></div></div>}
      </form>
  );
  const unsaved = modal && <Unsaved keep={() => { pending.current = null; setModal(false); }}
        leave={() => { const destino = pending.current; pending.current = null; reference.current = { ...values }; interacted.current = false; setModal(false); if (destino) window.location.href = destino; }}
        save={() => { pending.current = null; setModal(false); void save("draft"); }} />;
  const head = <>
    {createPortal(<InsumosToastList key={toasts.key} messages={toasts.items.filter((m) => !m.tags?.includes(IN_FORM))} />, document.body)}
    <link rel="stylesheet" href="/static/custom/css/informeTecnicoSecciones.css" />
  </>;
  if (embedded) {
    return <>
      {head}
      <div className="row" id="informe-tecnico-seccion"><div className="col-12">
        <div className="card card-primary card-outline">
          <div className="card-header"><h2 className="card-title fw-bold fs-3 mb-0">Informe Técnico y Carátula del Expediente</h2></div>
          <div className="card-body pb-0">
            <p className="text-muted mb-0">
              <i className="fas fa-info-circle me-1" aria-hidden="true" />{" "}
              <strong>Finalizar</strong> resuelve en un solo paso la caratulación del expediente y el informe técnico, aplicando las validaciones de cada uno.{" "}
              <strong>Guardar Borrador</strong> guarda el avance de ambos sin exigir los campos obligatorios, incluida una carátula a medio cargar.
            </p>
          </div>
          <div className="card-body">{formEl}</div>
        </div>
      </div></div>
      {unsaved}
    </>;
  }
  return <>
    {head}
    <div className="container-fluid">
      {formEl}
      {unsaved}
    </div>
  </>;
}

function EditorRoute({ tipo, admision, id }: Params) {
  const base = admision ? `${API}${tipo}/admision/${admision}/` : `${API}${tipo}/${id}/`;
  const [state] = useMainResource(`${base}formulario/`, formValid);
  return renderMain(state, "Cargando informe…", (data) => ({
    title: `Informe Técnico: ${data.comedor}`,
    heading: `Informe Técnico: ${data.comedor} - Estado: ${data.estado}`,
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <div className="breadcrumb-item"><a href={data.urls.volver}>{data.comedor}</a></div>
      <div className="breadcrumb-item active">Informe Técnico</div>
    </ol>,
    content: <Editor initial={data} saveUrl={`${base}guardar/`} />,
  }));
}

// Native GET pages of `admisiones/urls/web_urls.py`, same trailing slashes.
const PATH = /^\/comedores\/admision\/informe_tecnico\/([a-z]+)\/([0-9]+)\/(crear|editar)\/$/;

export const admisionesInformeEditorRoute: RouteDefinition<Params> = {
  name: "comedores-informe-tecnico-editor",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[3] === "crear" ? { tipo: m[1], admision: m[2] } : { tipo: m[1], id: m[2] };
  },
  render({ tipo, admision, id }) {
    return <EditorRoute key={`${tipo}-${admision ?? ""}-${id ?? ""}`} tipo={tipo} admision={admision} id={id} />;
  },
};
