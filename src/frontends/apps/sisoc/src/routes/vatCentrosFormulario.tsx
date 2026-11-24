/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { internal, postForm, record, renderMain, text, useMainResource, type MainState } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { Choice } from "./select2";
import { integer, messagesValid, vatNavigation, type Message } from "./vatShared";
import { Select2Links, useForbidden } from "./vatFormShared";
import { UncertainNotice } from "./vatCentrosListaShared";
import { vatGeography } from "./vatUbicacionesForm";
import {
  CrispyCampo, UsuariosBusqueda, campoValid, contactoValid, isSelect2, usuariosValid, type Campo, type ContactoData, type UsuariosData,
} from "./vatCentrosFormularioCampos";
import { CENTRO_FORMULARIO_CSS } from "./vatCentrosFormularioStyles";
import type { RouteDefinition } from "./types";

/**
 * V06.02 alta y edición de un centro: `vat/centros/centro_create_form.html` and `centro_create_form.js`. Fields, widget
 * attributes, referente/revisor options and the formset of contacts come from `/api/web/vat/centros-formulario/`, which runs
 * `CentroCreateView`/`CentroUpdateView`; the POST persists through their `post`. The page script is reproduced: the
 * referente/revisor search with chips, the jurisdiction -> municipio -> localidad cascade over the core AJAX endpoints (a new
 * jurisdiction reloads the municipios and leaves the localidad as it was, like the script) and the add/remove of contacts
 * (the last one cannot be removed and an added one carries the script's own classes). A rejected POST shows the bound form.
 */
type Actions = { cancel: string; submit: string; submit_continue: string; save_continue: boolean };
type Activo = { id: string; label: string; checked: boolean; errors: string[] };
export type CentroFormularioData = {
  editing: boolean; title: string; fields: Campo[]; referentes: UsuariosData; referente: Campo; revisores: UsuariosData; non_field_errors: string[];
  contactos: { initial_forms: number; min_num: number; max_num: number; forms: ContactoData[]; empty: ContactoData; non_form_errors: string[] };
  activo: Activo | null; actions: Actions; urls: { municipios: string; localidades: string }; messages: Message[];
};

const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);

export function centroFormularioValid(v: unknown): v is CentroFormularioData {
  return record(v) && typeof v.editing === "boolean" && text(v.title) && Array.isArray(v.fields) && v.fields.every(campoValid) &&
    usuariosValid(v.referentes) && campoValid(v.referente) && usuariosValid(v.revisores) && strings(v.non_field_errors) &&
    record(v.contactos) && integer(v.contactos.initial_forms) && integer(v.contactos.min_num) && integer(v.contactos.max_num) &&
    Array.isArray(v.contactos.forms) && v.contactos.forms.every(contactoValid) && contactoValid(v.contactos.empty) && strings(v.contactos.non_form_errors) &&
    (v.activo === null || (record(v.activo) && text(v.activo.id) && text(v.activo.label) && typeof v.activo.checked === "boolean" && strings(v.activo.errors))) &&
    record(v.actions) && text(v.actions.cancel) && text(v.actions.submit) && text(v.actions.submit_continue) && typeof v.actions.save_continue === "boolean" &&
    record(v.urls) && internal(v.urls.municipios) && internal(v.urls.localidades) && messagesValid(v.messages);
}

const API = "web/vat/centros-formulario/";
const COLS: Record<string, string> = {
  nombre: "col-md-8", codigo: "col-md-4", clase_institucion: "col-md-4", tipo_gestion: "col-md-4", situacion: "col-md-4", domicilio_actividad: "col-md-12",
  calle: "col-md-6", numero: "col-md-2", codigo_postal: "col-md-4", lote: "col-md-4", manzana: "col-md-4", entre_calles: "col-md-4", provincia: "col-md-4",
  municipio: "col-md-4", localidad: "col-md-4", correo: "col-md-4", telefono: "col-md-4", celular: "col-md-4", sitio_web: "col-md-12",
};
const CONTACT_COLS: Record<string, string> = { nombre_contacto: "col-md-4", rol_area: "col-md-4", documento: "col-md-4", telefono_contacto: "col-md-6", email_contacto: "col-md-6" };
const INSTITUCION = ["nombre", "codigo", "clase_institucion", "tipo_gestion", "situacion"];
const UBICACION = ["domicilio_actividad", "calle", "numero", "codigo_postal", "lote", "manzana", "entre_calles", "provincia", "municipio", "localidad"];
const CONTACTO = ["correo", "telefono", "celular", "sitio_web"];
const EMPTY_LABEL = { municipio: "Seleccionar municipio...", localidad: "Seleccionar localidad..." };
const REFERENTE_REQUERIDO = "Selecciona al menos un usuario valido de la lista.";

/** Next request number of a target (the counters are mutable on purpose: they only discard stale answers). */
function siguiente(tickets: Record<string, number>, target: string) {
  tickets[target] += 1;
  return tickets[target];
}

type Geo = { id: number; nombre: string };
const geoValid = (v: unknown): v is Geo[] => Array.isArray(v) && v.every((g) => record(g) && integer(g.id) && text(g.nombre));
type Item = { key: number; nuevo: boolean; hidden: ContactoData["hidden"]; values: Record<string, string>; errors: ContactoData["errors"] };

/** A plain select with no matching option shows (and posts) its first one, as the browser does. */
function valorInicial(f: Campo) {
  const plain = f.tag === "select" && !isSelect2(f);
  return plain && !f.choices.some((c) => c.value === f.value) ? f.choices[0]?.value ?? "" : String(f.value);
}

function Formulario({ data, endpoint, forbidden, rejected }: {
  data: CentroFormularioData; endpoint: string; forbidden: (d: unknown) => void; rejected: (d: CentroFormularioData) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(data.fields.map((f) => [f.name, valorInicial(f)])));
  const [activo, setActivo] = useState(data.activo?.checked ?? false);
  const [referentes, setReferentes] = useState(data.referentes.selected);
  const [revisores, setRevisores] = useState(data.revisores.selected);
  const [items, setItems] = useState<Item[]>(() => data.contactos.forms.map((c, index) => ({
    key: index, nuevo: false, hidden: c.hidden, errors: c.errors, values: Object.fromEntries(c.fields.map((f) => [f.name, String(f.value)])),
  })));
  const [geo, setGeo] = useState<Record<"municipio" | "localidad", Choice[]>>(() => ({
    municipio: data.fields.find((f) => f.name === "municipio")?.choices ?? [], localidad: data.fields.find((f) => f.name === "localidad")?.choices ?? [],
  }));
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const continuar = useRef(false);
  // Counters that drop the answer of a request that a newer one replaced (not read while rendering).
  const [tickets] = useState(() => ({ municipio: 0, localidad: 0 }));
  const referentesInput = useRef<HTMLInputElement>(null);
  const revisoresInput = useRef<HTMLInputElement>(null);
  const set = (name: string, value: string) => setValues((v) => ({ ...v, [name]: value }));
  const vacio = (target: "municipio" | "localidad"): Choice[] => [{ value: "", label: EMPTY_LABEL[target] }];

  /** `loadOptions`: the select empties at once, then takes the options of the endpoint (none if the request fails). */
  async function cargar(target: "municipio" | "localidad", url: string) {
    const mine = siguiente(tickets, target);
    setGeo((g) => ({ ...g, [target]: vacio(target) }));
    set(target, "");
    let rows: unknown;
    try { rows = await vatGeography.load(url); } catch { return; }
    if (mine !== tickets[target] || !geoValid(rows)) return;
    setGeo((g) => ({ ...g, [target]: [...vacio(target), ...rows.map((r) => ({ value: String(r.id), label: r.nombre }))] }));
  }
  function limpiar(...targets: ("municipio" | "localidad")[]) {
    for (const t of targets) { siguiente(tickets, t); set(t, ""); }
    setGeo((g) => ({ ...g, ...Object.fromEntries(targets.map((t) => [t, vacio(t)])) }));
  }
  function cambio(name: string, value: string) {
    set(name, value);
    if (name === "provincia") { if (value) void cargar("municipio", `${data.urls.municipios}?provincia_id=${value}`); else limpiar("municipio", "localidad"); }
    if (name === "municipio") { if (value) void cargar("localidad", `${data.urls.localidades}?municipio_id=${value}`); else limpiar("localidad"); }
  }

  function agregar() {
    const base = data.contactos.empty;
    setItems((current) => [...current, {
      key: Math.max(-1, ...current.map((i) => i.key)) + 1, nuevo: true, hidden: base.hidden, errors: [], values: Object.fromEntries(base.fields.map((f) => [f.name, ""])),
    }]);
  }
  function quitar(key: number) { setItems((current) => (current.length <= 1 ? current : current.filter((i) => i.key !== key))); }
  const editar = (key: number, name: string, value: string) => setItems((current) => current.map((i) => (i.key === key ? { ...i, values: { ...i.values, [name]: value } } : i)));

  async function submit(event: FormEvent) {
    event.preventDefault();
    const continua = continuar.current;
    continuar.current = false;
    revisoresInput.current?.setCustomValidity("");
    if (referentes.length === 0) {
      referentesInput.current?.setCustomValidity(REFERENTE_REQUERIDO);
      referentesInput.current?.reportValidity();
      return;
    }
    referentesInput.current?.setCustomValidity("");
    if (busy.current || uncertain) return;
    busy.current = true;
    const body = new URLSearchParams({ csrfmiddlewaretoken: leerCookie("csrftoken") ?? "" });
    const add = (name: string, value: string) => body.append(name, value);
    // Only what the native template renders; a locked (disabled) control is not posted, as in the browser.
    const campo = (f: Campo) => { if (!f.disabled) add(f.name, values[f.name] ?? ""); };
    data.fields.filter((f) => INSTITUCION.includes(f.name)).forEach(campo);
    referentes.forEach((v) => add("referentes", v));
    if (!data.referente.disabled) add("referente", String(data.referente.value));
    revisores.forEach((v) => add("revisores", v));
    data.fields.filter((f) => !INSTITUCION.includes(f.name)).forEach(campo);
    add("contactos-TOTAL_FORMS", String(items.length));
    add("contactos-INITIAL_FORMS", String(data.contactos.initial_forms));
    add("contactos-MIN_NUM_FORMS", String(data.contactos.min_num));
    add("contactos-MAX_NUM_FORMS", String(data.contactos.max_num));
    items.forEach((item, index) => {
      item.hidden.forEach((h) => add(`contactos-${index}-${h.name}`, h.value));
      data.contactos.empty.fields.forEach((f) => add(`contactos-${index}-${f.name}`, item.values[f.name] ?? ""));
    });
    if (data.activo) { add("activo_present", "1"); if (activo) add("activo", "on"); }
    if (continua) add("save_continue", "1");
    const result = await postForm(endpoint, body);
    busy.current = false;
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else if (result.kind === "invalid" && centroFormularioValid(result.data)) { rejected(result.data); resetAfterRejectedPost(); }
    else setUncertain(true);
  }

  const campos = (nombres: string[]) => data.fields.filter((f) => nombres.includes(f.name)).map((f) => (
    <CrispyCampo key={f.name} f={f} id={f.id} name={f.name} col={COLS[f.name]} value={values[f.name] ?? ""} onChange={(v) => cambio(f.name, v)}
      choices={f.name === "municipio" || f.name === "localidad" ? geo[f.name] : undefined} />
  ));
  const panel = (icon: string, title: string, subtitle: string, body: ReactNode, extra?: ReactNode) => (
    <div className="card vp-panel">
      <div className="vp-panel-header">
        <div>
          <h3 className="card-title"><i className={`${icon} mr-2`} />{title}</h3>
          <div className="small">{subtitle}</div>
        </div>
        {extra}
      </div>
      <div className="vp-section"><div className="row">{body}</div></div>
    </div>
  );

  return (
    <div className="vp-shell">
      <div className="vp-hero"><h1>{data.title}</h1></div>
      <form method="post" encType="multipart/form-data" id="centro-alta-form" noValidate onSubmit={(e) => void submit(e)}>
        <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} readOnly />
        {data.non_field_errors.length > 0 && <div className="alert alert-danger"><ul className="errorlist nonfield">{data.non_field_errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
        {data.contactos.non_form_errors.length > 0 && <div className="alert alert-danger"><ul className="errorlist nonform">{data.contactos.non_form_errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
        <UncertainNotice show={uncertain} />
        {panel("fas fa-info-circle", "Datos de la institución", "Definí la identidad principal del centro.", <>
          {campos(INSTITUCION)}
          <UsuariosBusqueda nombre="referentes" data={data.referentes} selected={referentes} onChange={setReferentes} inputRef={referentesInput}
            empty="No hay usuarios CFP para esa busqueda." placeholder="Buscar referente por usuario o nombre">
            <input type="hidden" name="referente" id={data.referente.id} value={String(data.referente.value)} readOnly />
          </UsuariosBusqueda>
          <UsuariosBusqueda nombre="revisores" data={data.revisores} selected={revisores} onChange={setRevisores} inputRef={revisoresInput}
            empty="No hay usuarios CFPRevisor para esa busqueda." placeholder="Buscar revisor por usuario o nombre" />
        </>)}
        {panel("fas fa-map-marker-alt", "Ubicación", "Completá la localización física y referencias del domicilio.", campos(UBICACION))}
        {panel("fas fa-phone-alt", "Contacto institucional", "Canales oficiales de comunicación del centro.", campos(CONTACTO))}
        <div className="card vp-panel">
          <div className="vp-panel-header">
            <div>
              <h3 className="card-title"><i className="fas fa-address-book mr-2" />Contactos adicionales</h3>
              <div className="small">Podés cargar responsables o contactos adicionales en la misma tabla institucional.</div>
            </div>
            <button type="button" className="btn btn-sm btn-outline-light" id="add-contacto-btn" onClick={agregar}><i className="fas fa-plus mr-1" />Agregar contacto</button>
          </div>
          <div className="vp-section">
            <div id="contactos-formset">
              {items.map((item, index) => (
                <div key={item.key} className={`${item.nuevo ? "border rounded p-3" : "vp-contact-item"} mb-3 contacto-form-item`} data-form-index={index}>
                  {item.hidden.map((h) => <input key={h.name} type="hidden" name={`contactos-${index}-${h.name}`} id={`id_contactos-${index}-${h.name}`} value={h.value} readOnly />)}
                  <div className="row">
                    {data.contactos.empty.fields.map((f) => (
                      <CrispyCampo key={f.name} f={{ ...f, errors: item.errors.find((e) => e.field === f.name)?.messages ?? [] }} id={`id_contactos-${index}-${f.name}`}
                        name={`contactos-${index}-${f.name}`} col={CONTACT_COLS[f.name]} value={item.values[f.name] ?? ""} onChange={(v) => editar(item.key, f.name, v)} />
                    ))}
                    <div className="col-md-12 d-flex align-items-center justify-content-end">
                      <button type="button" className="btn btn-outline-danger btn-sm remove-contacto-btn" onClick={() => quitar(item.key)}><i className="fas fa-trash mr-1" />Quitar</button>
                    </div>
                  </div>
                  {item.errors.length > 0 && <div className="alert alert-danger mt-2 mb-0"><ul className="errorlist">
                    {item.errors.map((e) => <li key={e.field}>{e.field}<ul className={e.field === "__all__" ? "errorlist nonfield" : "errorlist"} id={e.field === "__all__" ? undefined : `id_contactos-${index}-${e.field}_error`}>
                      {e.messages.map((m, i) => <li key={i}>{m}</li>)}
                    </ul></li>)}
                  </ul></div>}
                </div>
              ))}
            </div>
          </div>
          {data.activo && (
            <div className="card vp-panel">
              <div className="vp-panel-header">
                <div>
                  <h3 className="card-title"><i className="fas fa-check-circle mr-2" />Estado de Centro de Formación Profesional</h3>
                  <div className="small">Las ediciones conservan el estado actual salvo que lo cambies de forma explícita.</div>
                </div>
              </div>
              <div className="vp-section">
                <div className="vp-status-card">
                  <input type="hidden" name="activo_present" value="1" readOnly />
                  <div className="vp-switch form-check mb-0">
                    <input type="checkbox" name="activo" className="form-check-input" id={data.activo.id} checked={activo} onChange={(e) => setActivo(e.target.checked)} />{" "}
                    <label className="form-check-label" htmlFor={data.activo.id}>{data.activo.label}</label>
                  </div>
                  {data.activo.errors.length > 0 && <div className="vp-inline-errors">{data.activo.errors[0]}</div>}
                </div>
              </div>
            </div>
          )}
          <div className="vp-actions">
            <a href={data.actions.cancel} className="btn btn-secondary">Cancelar</a>{" "}
            <button type="submit" className="btn btn-primary">{data.actions.submit}</button>
            {data.actions.save_continue && <>{" "}<button type="submit" name="save_continue" value="1" className="btn btn-outline-primary" onClick={() => { continuar.current = true; }}>
              {data.actions.submit_continue}
            </button></>}
          </div>
        </div>
      </form>
    </div>
  );
}

function FormularioPage({ id }: { id?: string }) {
  const endpoint = `${API}${id ? `${id}/editar/` : "nuevo/"}`;
  const [state, setState] = useMainResource(endpoint, centroFormularioValid);
  const [rechazo, setRechazo] = useState<{ version: number; data: CentroFormularioData } | null>(null);
  const forbidden = useForbidden(setState as (s: MainState<CentroFormularioData>) => void);
  return renderMain(state, "Cargando formulario…", (inicial) => {
    const data = rechazo?.data ?? inicial;
    return {
      title: data.title, breadcrumb: null,
      content: <>
        <Select2Links />
        <link rel="stylesheet" href="/static/custom/css/cardsDetail.css" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <style>{CENTRO_FORMULARIO_CSS}</style>
        <NativeToasts messages={data.messages} />
        <Formulario key={rechazo?.version ?? 0} data={data} endpoint={endpoint} forbidden={forbidden}
          rejected={(next) => setRechazo((r) => ({ version: (r?.version ?? 0) + 1, data: next }))} />
      </>,
    };
  });
}

// Native URLs of `VAT/urls.py` (`vat_centro_create`, `vat_centro_update`).
export const vatCentrosFormularioRoute: RouteDefinition<{ id?: string }> = {
  name: "vat-centros-formulario",
  match(pathname) {
    const m = pathname.match(/^\/vat\/centros\/(?:(nuevo)|([0-9]+)\/editar)\/$/);
    return m ? (m[1] ? {} : { id: m[2] }) : null;
  },
  render: ({ id }) => <FormularioPage key={id ?? "nuevo"} id={id} />,
};
