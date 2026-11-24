/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, helpers and validators live here with the route. */
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type MouseEvent, type ReactNode } from "react";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import {
  aplicarHorarios, conPlaceholder, formatCuit, geography, opcionesDe, PLACEHOLDER, seleccion, type Choice, type Horarios,
} from "./cdiCentroFormBehavior";
import CentroMapa from "./cdiCentroFormMapa";
import { client, internal, messagesValid, navigation, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import { RenaperBloque, bloqueValid, useRenaperBloque, type BloqueConfig } from "./cdiRenaperBloque";
import { campoValid, CampoCrispy, Col, Feedback, Label, describedBy, type CampoWeb } from "./cdiRenaperBloqueCampos";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDI centre create and edit (`centrodeinfancia/centrodeinfancia_form.html`): the four section cards, the
 * check-box groups, the opening hours of the selected days, the cascading geography selects, the map pin
 * editor and the referente RENAPER block. The fields are the projection of `CentroDeInfanciaForm`
 * (`web_api_centro_form`): labels, widgets, RENAPER locks and error feedback come from the server; the
 * layout and the scripts of the template are drawn here. Saving goes to `/api/web/cdi/`, which runs the
 * native view (referente provisioning included); a saved centre returns to its detail, where the queued
 * messages show. A POST is sent once and never retried.
 */
type Opcion = { id: string; value: string; label: string; checked: boolean };
type Grupo = { label: string; required: boolean; options: Opcion[]; errors: string[] };
type Dia = { dia: string; etiqueta: string };
export type CentroFormData = {
  is_edit: boolean;
  non_field_errors: string[];
  fields: CampoWeb[];
  multiples: Record<string, Grupo>;
  dias: Dia[];
  renaper: BloqueConfig;
  urls: { cancelar: string; departamentos: string; municipios: string; localidades: string; address_preview: string };
  messages: CdiMessage[];
};

const MULTIPLES = ["meses_funcionamiento", "dias_funcionamiento", "oferta_servicios"];
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
const grupoValid = (g: unknown): g is Grupo => record(g) && text(g.label) && typeof g.required === "boolean" && strings(g.errors) &&
  Array.isArray(g.options) && g.options.every((o) => record(o) && text(o.id) && text(o.value) && text(o.label) && typeof o.checked === "boolean");

export function formValid(v: unknown): v is CentroFormData {
  if (!record(v) || !record(v.urls) || !record(v.multiples)) return false;
  const urls = v.urls as Record<string, unknown>;
  return typeof v.is_edit === "boolean" && strings(v.non_field_errors) && Array.isArray(v.fields) && v.fields.every(campoValid) &&
    MULTIPLES.every((name) => grupoValid((v.multiples as Record<string, unknown>)[name])) &&
    Array.isArray(v.dias) && v.dias.every((d) => record(d) && text(d.dia) && text(d.etiqueta)) && bloqueValid(v.renaper) &&
    ["cancelar", "departamentos", "municipios", "localidades", "address_preview"].every((k) => internal(urls[k])) && messagesValid(v.messages);
}

const CSS = `
.section-card .section-header.section-header-info-basica {
    background: linear-gradient(135deg, #0f4c5c 0%, #146c7b 100%) !important;
    border-bottom-color: #67e8f9;
}

.section-card .section-header.section-header-info-basica:hover {
    background: linear-gradient(135deg, #146c7b 0%, #198694 100%) !important;
}

.section-card .section-header.section-header-funcionamiento {
    background: linear-gradient(135deg, #6b2737 0%, #8f3550 100%) !important;
    border-bottom-color: #f9a8d4;
}

.section-card .section-header.section-header-funcionamiento:hover {
    background: linear-gradient(135deg, #8f3550 0%, #aa4361 100%) !important;
}

.horarios-funcionamiento-card {
    background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
    border: 1px solid #3d566e;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.horarios-funcionamiento-card .card-body,
.horarios-funcionamiento-card h5,
.horarios-funcionamiento-card .form-label {
    color: #e5e7eb;
}
`;

/** The attributes the server projects are HTML ones (`maxlength`, `readonly`...): React names them in camel case. */
const REACT_ATTR: Record<string, string> = { maxlength: "maxLength", minlength: "minLength", inputmode: "inputMode", tabindex: "tabIndex", readonly: "readOnly" };
function reactField(field: CampoWeb): CampoWeb {
  const attrs = Object.fromEntries(Object.entries(field.attrs).map(([key, value]) => [REACT_ATTR[key] ?? key, REACT_ATTR[key] === "readOnly" ? true : value]));
  return { ...field, attrs: attrs as Record<string, string> };
}

function Seccion({ icon, title, subtitle, extra = "", children }: { icon: string; title: string; subtitle: string; extra?: string; children: ReactNode }) {
  return (
    <div className="section-card mb-3">
      <div className={`section-header${extra}`}>
        <div className="section-header-left">
          <div className="section-icon"><i className={`fas ${icon}`} /></div>
          <div className="section-title-group">
            <h3 className="section-title">{title}</h3>
            <p className="section-subtitle">{subtitle}</p>
          </div>
        </div>
      </div>
      <div className="section-body show">{children}</div>
    </div>
  );
}

function Checks({ name, grupo, checked, onToggle }: { name: string; grupo: Grupo; checked?: string[]; onToggle?: (value: string, on: boolean) => void }) {
  const invalid = grupo.errors.length > 0 ? " is-invalid" : "";
  return (
    <div id={`div_id_${name}`} className="mb-3">
      <fieldset aria-describedby={invalid ? `id_${name}_error` : undefined}>
        <legend className={`form-label${grupo.required ? " requiredField" : ""} fs-6`}>{grupo.label}{grupo.required && <span className="asteriskField">*</span>}</legend>
        <div>
          {grupo.options.map((o, index) => (
            <div className="form-check" key={o.id}>
              <input type="checkbox" className={`form-check-input${invalid}`} name={name} value={o.value} id={o.id} aria-invalid={invalid ? "true" : undefined}
                {...(checked ? { checked: checked.includes(o.value), onChange: (e: ChangeEvent<HTMLInputElement>) => onToggle?.(o.value, e.target.checked) } : { defaultChecked: o.checked })} />{" "}
              <label htmlFor={o.id} className="form-check-label">{o.label}</label>
              {invalid && index === grupo.options.length - 1 && (
                <div id={`id_${name}_error`} className="invalid-feedback">
                  {grupo.errors.map((e, i) => <p key={i} id={`error_${i + 1}_id_${name}`}><strong>{e}</strong></p>)}
                </div>
              )}
            </div>
          ))}
        </div>
      </fieldset>
    </div>
  );
}

/** A crispy `<select>` (the choices come from the caller: the geography lists change on the page). */
function CampoSelect({ field, value, options, onChange }: { field: CampoWeb; value: string; options: Choice[]; onChange: (value: string) => void }) {
  const invalid = field.errors.length > 0 ? " is-invalid" : "";
  return (
    <div id={`div_id_${field.name}`} className="mb-3">
      <Label field={field} />
      <select id={`id_${field.name}`} name={field.name} className={`form-select${invalid}`} required={field.required || undefined}
        disabled={field.disabled || undefined} aria-invalid={invalid ? "true" : undefined} aria-describedby={describedBy(field)}
        value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <Feedback field={field} />
    </div>
  );
}

type PostResult = { kind: "redirect"; to: string } | { kind: "invalid"; data: unknown } | { kind: "forbidden"; data: unknown } | { kind: "rejected"; detail: string | null } | { kind: "uncertain" };

/** POST once, URL-encoded like the native form; an unconfirmed outcome is reported, never resubmitted. */
async function postOnce(endpoint: string, body: URLSearchParams): Promise<PostResult> {
  try {
    const { data, status } = await client.post(endpoint, body, { validateStatus: () => true });
    if (status === 400) return { kind: "invalid", data };
    if (status === 403 && record(data) && "state" in data) return { kind: "forbidden", data };
    if (status === 403 || status === 404) return { kind: "rejected", detail: record(data) && text(data.detail) ? data.detail : null };
    if (status >= 200 && status < 300 && record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect", to: data.redirect as string };
    return { kind: "uncertain" };
  } catch {
    return { kind: "uncertain" };
  }
}

const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const horarioName = (dia: string, momento: "apertura" | "cierre") => `horario_${dia}_${momento}`;

function horariosDe(values: Record<string, string>, dias: string[]): Horarios {
  return Object.fromEntries(dias.map((dia) => [dia, { apertura: values[horarioName(dia, "apertura")] ?? "", cierre: values[horarioName(dia, "cierre")] ?? "" }]));
}
function valoresDe(horarios: Horarios): Record<string, string> {
  return Object.fromEntries(Object.entries(horarios).flatMap(([dia, h]) => [[horarioName(dia, "apertura"), h.apertura], [horarioName(dia, "cierre"), h.cierre]]));
}

/** The first server error is where the page goes, as the native script does on load. */
function irAlPrimerError() {
  const primero = document.querySelector<HTMLElement>(".is-invalid");
  if (!primero) return;
  primero.scrollIntoView({ behavior: "smooth", block: "center" });
  primero.focus({ preventScroll: true });
}

function CentroFormBody({ data, pending, onSubmit }: { data: CentroFormData; pending: boolean; onSubmit: (form: HTMLFormElement) => void }) {
  const byName = new Map(data.fields.map((f) => [f.name, f]));
  const ordenDias = data.dias.map((d) => d.dia);
  const seleccionInicial = ordenDias.filter((dia) => data.multiples.dias_funcionamiento.options.some((o) => o.value === dia && o.checked));
  const [values, setValues] = useState<Record<string, string>>(() => {
    const base = Object.fromEntries(data.fields.map((f) => [f.name, f.value]));
    // `refreshHorarioRows` and `refreshConditionalFields` run when the page loads.
    const horarios = aplicarHorarios(ordenDias, seleccionInicial, horariosDe(base, ordenDias), {}).horarios;
    return {
      ...base, ...valoresDe(horarios), cuit_organizacion_gestiona: formatCuit(base.cuit_organizacion_gestiona ?? ""),
      ...(base.tipo_jornada === "other" ? {} : { tipo_jornada_otra: "" }),
      ...(base.modalidad_gestion === "otra" ? {} : { modalidad_gestion_otra: "" }),
    };
  });
  const [dias, setDias] = useState(seleccionInicial);
  const [tocados, setTocados] = useState<Record<string, boolean>>({});
  const [departamentos, setDepartamentos] = useState<Choice[]>(() => conPlaceholder(byName.get("departamento")?.choices ?? [], PLACEHOLDER.departamento));
  const [municipios, setMunicipios] = useState<Choice[]>(() => conPlaceholder(byName.get("municipio")?.choices ?? [], PLACEHOLDER.municipio));
  const [localidades, setLocalidades] = useState<Choice[]>(() => conPlaceholder(byName.get("localidad")?.choices ?? [], PLACEHOLDER.localidad));
  const { departamentos: urlDepartamentos, municipios: urlMunicipios, localidades: urlLocalidades } = data.urls;

  const set = (name: string, value: string) => setValues((prev) => ({ ...prev, [name]: value }));
  const io = { get: (name: string) => values[name] ?? "", set };
  const field = (name: string) => reactField(byName.get(name) as CampoWeb);
  const bind = (name: string) => ({ field: field(name), value: values[name] ?? "", onChange: (v: string) => set(name, v) });

  const block = useRenaperBloque({
    ...data.renaper, dni: "dni_referente", scope: data.renaper.campos.concat(["email_referente", "telefono_referente"]),
    serverLocked: data.renaper.campos.filter((n) => byName.get(n)?.renaper && byName.get(n)?.disabled),
  }, io);
  const bindRenaper = (name: string) => ({ ...bind(name), block: { api: block, dni: name === "dni_referente" } });
  const info = (name: string) => ({ label: field(name).label, type: field(name).widget, choices: field(name).choices });

  // The loads of the page start: the lists the server did not fill (`departamentoInicial` and the like).
  useEffect(() => {
    let vivo = true;
    void (async () => {
      const provincia = values.provincia;
      const cargar = async (url: string, parametro: string, id: string, placeholder: string) => opcionesDe(await geography.load(`${url}?${parametro}=${encodeURIComponent(id)}`).catch(() => []), placeholder);
      if (provincia && departamentos.length <= 1) {
        const opciones = await cargar(urlDepartamentos, "provincia_id", provincia, PLACEHOLDER.departamento);
        if (!vivo) return;
        setDepartamentos(opciones);
        set("departamento", seleccion(opciones, values.departamento));
        set("decil_ipi", opciones.find((o) => o.value === values.departamento)?.decil ?? "");
      }
      let municipio = values.municipio;
      if (provincia && municipios.length <= 1) {
        const opciones = await cargar(urlMunicipios, "provincia_id", provincia, PLACEHOLDER.municipio);
        if (!vivo) return;
        setMunicipios(opciones);
        municipio = seleccion(opciones, municipio);
        set("municipio", municipio);
      }
      if (municipio && localidades.length <= 1) {
        const opciones = await cargar(urlLocalidades, "municipio_id", municipio, PLACEHOLDER.localidad);
        if (!vivo) return;
        setLocalidades(opciones);
        set("localidad", seleccion(opciones, values.localidad));
      }
    })();
    return () => { vivo = false; };
    // Once, with the lists of the page: `data` is the whole state of this mounted form.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { irAlPrimerError(); }, []);

  async function onProvincia(value: string) {
    set("provincia", value);
    const cargar = async (url: string, placeholder: string) => (value ? opcionesDe(await geography.load(`${url}?provincia_id=${encodeURIComponent(value)}`).catch(() => []), placeholder) : opcionesDe([], placeholder));
    const nuevosDepartamentos = await cargar(urlDepartamentos, PLACEHOLDER.departamento);
    setDepartamentos(nuevosDepartamentos);
    setValues((prev) => ({ ...prev, departamento: "", decil_ipi: "" }));
    setMunicipios(await cargar(urlMunicipios, PLACEHOLDER.municipio));
    set("municipio", "");
    setLocalidades(opcionesDe([], PLACEHOLDER.localidad));
    set("localidad", "");
  }
  async function onMunicipio(value: string) {
    set("municipio", value);
    const opciones = value
      ? opcionesDe(await geography.load(`${urlLocalidades}?municipio_id=${encodeURIComponent(value)}`).catch(() => []), PLACEHOLDER.localidad)
      : opcionesDe([], PLACEHOLDER.localidad);
    setLocalidades(opciones);
    set("localidad", "");
  }
  // Only the options of an AJAX answer carry `data-decil-ipi`: the ones the server drew leave the decile empty.
  function onDepartamento(value: string) {
    setValues((prev) => ({ ...prev, departamento: value, decil_ipi: (value && departamentos.find((o) => o.value === value)?.decil) || "" }));
  }

  function onDia(dia: string, marcado: boolean) {
    const siguiente = ordenDias.filter((d) => (d === dia ? marcado : dias.includes(d)));
    const resultado = aplicarHorarios(ordenDias, siguiente, horariosDe(values, ordenDias), tocados);
    setDias(siguiente);
    setTocados(resultado.tocados);
    setValues((prev) => ({ ...prev, ...valoresDe(resultado.horarios) }));
  }
  function onHorario(dia: string, momento: "apertura" | "cierre", value: string) {
    const horarios = horariosDe(values, ordenDias);
    horarios[dia] = { ...horarios[dia], [momento]: value };
    const marcados = { ...tocados, [dia]: true };
    if (dias[0] === dia) {
      const resultado = aplicarHorarios(ordenDias, dias, horarios, marcados);
      setTocados(resultado.tocados);
      setValues((prev) => ({ ...prev, ...valoresDe(resultado.horarios) }));
    } else {
      setTocados(marcados);
      set(horarioName(dia, momento), value);
    }
  }

  const otraJornada = values.tipo_jornada === "other";
  const otraGestion = values.modalidad_gestion === "otra";
  const back = (event: MouseEvent) => { event.preventDefault(); window.history.back(); };

  return (
    <div className="container-fluid">
      <div className="d-flex justify-content-between mb-3">
        <div />
        <div><a href="#" data-history-back="true" className="btn btn-secondary" onClick={back}>Cancelar</a></div>
      </div>
      <form method="post" className="w-100" id="centrodesarrolloinfantil-form" noValidate
        onSubmit={(e: FormEvent<HTMLFormElement>) => { e.preventDefault(); onSubmit(e.currentTarget); }}>
        {(data.non_field_errors.length > 0 || data.fields.some((f) => f.errors.length > 0) || Object.values(data.multiples).some((g) => g.errors.length > 0)) && (
          <div className="alert alert-danger" role="alert">
            No se pudo guardar el legajo. Revisá los campos marcados.
            {data.non_field_errors.length > 0 && <div className="mt-2"><ul className="errorlist nonfield">{data.non_field_errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
          </div>
        )}

        <Seccion icon="fa-child" title="Información básica" subtitle="Datos principales del centro de desarrollo infantil" extra=" section-header-info-basica">
          <div className="form-group row">
            <div className="col-md-6"><CampoCrispy {...bind("nombre")} /></div>
            <div className="col-md-6"><CampoCrispy {...bind("organizacion")} /></div>
          </div>
          <div className="form-group row">
            <div className="col-md-6"><CampoCrispy {...bind("cuit_organizacion_gestiona")} onChange={(v) => set("cuit_organizacion_gestiona", formatCuit(v))} /></div>
            <div className="col-md-6"><CampoSelect field={field("ambito")} value={values.ambito ?? ""} options={field("ambito").choices ?? []} onChange={(v) => set("ambito", v)} /></div>
          </div>
          <div className="form-group row">
            <div className="col-md-4"><CampoCrispy {...bind("telefono")} /></div>
            <div className="col-md-4"><CampoCrispy {...bind("mail")} /></div>
            <div className="col-md-4"><CampoCrispy {...bind("fecha_inicio")} /></div>
          </div>
          <div className="form-group row">
            <div className="col-md-6">
              <CampoSelect field={field("modalidad_gestion")} value={values.modalidad_gestion ?? ""} options={field("modalidad_gestion").choices ?? []}
                onChange={(v) => setValues((prev) => ({ ...prev, modalidad_gestion: v, ...(v === "otra" ? {} : { modalidad_gestion_otra: "" }) }))} />
            </div>
            <div className={`col-md-6 modalidad-gestion-otra-wrapper${otraGestion ? "" : " d-none"}`}>
              <CampoCrispy {...bind("modalidad_gestion_otra")} field={{ ...field("modalidad_gestion_otra"), disabled: !otraGestion }} />
            </div>
          </div>
        </Seccion>

        <Seccion icon="fa-map-marker-alt" title="Ubicación" subtitle="Provincia, departamento, municipio, localidad y coordenadas">
          <div className="form-group row">
            <div className="col-md-4"><CampoSelect field={field("provincia")} value={values.provincia ?? ""} options={field("provincia").choices ?? []} onChange={(v) => void onProvincia(v)} /></div>
            <div className="col-md-4">
              <div id="departamento-loader" className="skeleton-loader d-none" />
              <div id="departamento-field"><CampoSelect field={field("departamento")} value={values.departamento ?? ""} options={departamentos} onChange={onDepartamento} /></div>
            </div>
            <div className="col-md-4"><CampoCrispy {...bind("decil_ipi")} /></div>
          </div>
          <div className="form-group row">
            <div className="col-md-4">
              <div id="municipio-loader" className="skeleton-loader d-none" />
              <div id="municipio-field"><CampoSelect field={field("municipio")} value={values.municipio ?? ""} options={municipios} onChange={(v) => void onMunicipio(v)} /></div>
            </div>
            <div className="col-md-4">
              <div id="localidad-loader" className="skeleton-loader d-none" />
              <div id="localidad-field"><CampoSelect field={field("localidad")} value={values.localidad ?? ""} options={localidades} onChange={(v) => set("localidad", v)} /></div>
            </div>
            <div className="col-md-4"><CampoCrispy {...bind("codigo_postal")} /></div>
          </div>
          <div className="form-group row">
            <div className="col-md-8"><CampoCrispy {...bind("calle")} /></div>
            <div className="col-md-4"><CampoCrispy {...bind("numero")} /></div>
          </div>
          <div className="form-group row">
            {(["latitud", "longitud"] as const).map((name) => (
              <div className="col-md-6" key={name}>
                <CampoCrispy {...bind(name)}>
                  <input type="number" name={name} id={`id_${name}`} className={`form-control numberinput${field(name).errors.length ? " is-invalid" : ""}`} defaultValue={field(name).value}
                    {...field(name).attrs} aria-invalid={field(name).errors.length ? "true" : undefined} aria-describedby={describedBy(field(name))} />
                </CampoCrispy>
              </div>
            ))}
          </div>
          <CentroMapa searchUrl={data.urls.address_preview} />
        </Seccion>

        <Seccion icon="fa-clock" title="Funcionamiento" subtitle="Meses, días, horarios y modalidad operativa" extra=" section-header-funcionamiento">
          <div className="form-group row">
            <div className="col-md-6"><Checks name="meses_funcionamiento" grupo={data.multiples.meses_funcionamiento} /></div>
            <div className="col-md-6"><Checks name="dias_funcionamiento" grupo={data.multiples.dias_funcionamiento} checked={dias} onToggle={onDia} /></div>
          </div>
          <div className="form-group row">
            <div className="col-12">
              <div className="card border-0 horarios-funcionamiento-card">
                <div className="card-body">
                  <h5 className="mb-3">Horarios por día</h5>
                  {data.dias.map(({ dia, etiqueta }) => {
                    const visible = dias.includes(dia);
                    const apertura = field(horarioName(dia, "apertura"));
                    const cierre = field(horarioName(dia, "cierre"));
                    return (
                      <div key={dia} className={`row align-items-start mb-3 horario-row${visible ? "" : " d-none"}`} data-dia={dia}>
                        <div className="col-md-4"><label className="form-label fw-semibold">{etiqueta}</label></div>
                        <div className="col-md-4">
                          <CampoCrispy field={{ ...apertura, disabled: !visible }} value={values[apertura.name] ?? ""} onChange={(v) => onHorario(dia, "apertura", v)} />
                        </div>
                        <div className="col-md-4">
                          <CampoCrispy field={{ ...cierre, disabled: !visible }} value={values[cierre.name] ?? ""} onChange={(v) => onHorario(dia, "cierre", v)} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
          <div className="form-group row">
            <div className="col-md-6">
              <CampoSelect field={field("tipo_jornada")} value={values.tipo_jornada ?? ""} options={field("tipo_jornada").choices ?? []}
                onChange={(v) => setValues((prev) => ({ ...prev, tipo_jornada: v, ...(v === "other" ? {} : { tipo_jornada_otra: "" }) }))} />
            </div>
            <div className={`col-md-6 tipo-jornada-otra-wrapper${otraJornada ? "" : " d-none"}`}>
              <CampoCrispy {...bind("tipo_jornada_otra")} field={{ ...field("tipo_jornada_otra"), disabled: !otraJornada }} />
            </div>
          </div>
          <div className="form-group row">
            <div className="col-md-6"><Checks name="oferta_servicios" grupo={data.multiples.oferta_servicios} /></div>
          </div>
        </Seccion>

        <Seccion icon="fa-user-tie" title="Referente" subtitle="Datos de contacto de la persona referente">
          <div className="form-group row">
            <Col className="col-md-3" hidden={block.hidden("dni_referente")}><CampoCrispy {...bindRenaper("dni_referente")} /></Col>
          </div>
          <RenaperBloque api={block} info={info} values={values} />
          <div className="form-group row">
            <Col className="col-md-3" hidden={block.hidden("nombre_referente")}><CampoCrispy {...bindRenaper("nombre_referente")} /></Col>
            <Col className="col-md-3" hidden={block.hidden("apellido_referente")}><CampoCrispy {...bindRenaper("apellido_referente")} /></Col>
            <Col className="col-md-3" hidden={block.hidden("cuil_referente")}><CampoCrispy {...bindRenaper("cuil_referente")} /></Col>
          </div>
          <div className="form-group row">
            <Col className="col-md-3" hidden={block.hidden("email_referente")}><CampoCrispy {...bindRenaper("email_referente")} /></Col>
            <Col className="col-md-3" hidden={block.hidden("telefono_referente")}><CampoCrispy {...bindRenaper("telefono_referente")} /></Col>
          </div>
        </Seccion>

        <div className="d-flex gap-2 justify-content-end mt-3">
          <button className="btn btn-primary" type="submit" disabled={pending || undefined}>Guardar</button>
          <a href={safeInternalPath(data.urls.cancelar) ?? "/"} className="btn btn-secondary">Cancelar</a>
        </div>
      </form>
    </div>
  );
}

export function CentroFormContent({ data: initial, endpoint }: { data: CentroFormData; endpoint: string }) {
  const [data, setData] = useState(initial);
  const [version, setVersion] = useState(0);
  const [toasts, setToasts] = useState<CdiMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const sending = useRef(false);

  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;

  async function submit(target: HTMLFormElement) {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    const body = new URLSearchParams();
    new FormData(target).forEach((value, key) => { if (typeof value === "string") body.append(key, value); });
    const result = await postOnce(endpoint, body);
    if (result.kind === "redirect") { navigation.assign(result.to); return; }
    if (result.kind === "invalid" && formValid(result.data)) {
      setData(result.data);
      setToasts(result.data.messages);
      setVersion((v) => v + 1);
      setUncertain(false);
      resetAfterRejectedPost();
    } else if (result.kind === "forbidden") setForbidden({ prerequisite: prerequisiteFromForbidden(result.data) });
    else if (result.kind === "rejected") window.alert(result.detail ?? "No se pudo completar la acción.");
    else setUncertain(true);
    sending.current = false;
    setPending(false);
  }

  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <style>{CSS}</style>
      {toasts.length > 0 && <NativeToasts messages={toasts} />}
      {uncertain && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
      <CentroFormBody key={version} data={data} pending={pending} onSubmit={(form) => void submit(form)} />
    </>
  );
}

function CentroFormPage({ id }: { id?: string }) {
  const endpoint = id ? `web/cdi/centros/${id}/editar/` : "web/cdi/centros/crear/";
  const [state] = useCdiPage(endpoint, formValid);
  return renderCdi(state, (data) => ({
    title: "Centro de Desarrollo Infantil",
    heading: "Centro de Desarrollo Infantil",
    bodyToasts: true,
    content: <CentroFormContent data={data} endpoint={endpoint} />,
  }));
}

const OWN = /^\/centrodeinfancia\/(?:crear|editar\/([1-9]\d*))$/;

// Native URLs of the CDI centre create and edit; no trailing slash, like the Django routes.
export const cdiCentroFormRoute: RouteDefinition<{ id?: string }> = {
  name: "cdi-centro-form",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { id: own[1] } : null;
  },
  render: ({ id }) => <CentroFormPage id={id} />,
};
