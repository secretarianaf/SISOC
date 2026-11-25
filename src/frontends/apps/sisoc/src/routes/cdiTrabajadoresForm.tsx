/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, helpers and validators live here with the route. */
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type MouseEvent, type ReactNode } from "react";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import { client, internal, messagesValid, navigation, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import { bindTrabajadorForm, type GeographyUrls } from "./cdiTrabajadoresForm.behavior";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDI05 worker create and edit (`centrodeinfancia/trabajador_form.html`): the DNI
 * search, the progress bar and the seven collapsible section cards. The fields
 * are the server-rendered `as_crispy_field` markup of the native form (labels,
 * widgets, RENAPER locks and error feedback come from `TrabajadorCDIForm`); the
 * layout, the check-box groups, the collapse and the submit are drawn here and
 * the scripts of the template run as `cdiTrabajadoresForm.behavior.ts`. Saving
 * goes to `/api/web/cdi/`, which runs the native view (provisioning included);
 * a saved worker returns to the centre where the queued messages show. A POST
 * is sent once and never retried.
 */
type Opcion = { id: string; value: string; label: string; checked: boolean };
type Grupo = { label: string; options: Opcion[]; errors: string[] };
type Ciudadano = { id: number; apellido: string; nombre: string; documento: string };
type Busqueda = {
  query: string; ciudadanos: Ciudadano[]; selected: Ciudadano | null; no_resultados: boolean; renaper_precarga: boolean; renaper_prefill_token: string | null;
};
export type TrabajadorFormData = {
  is_edit: boolean;
  centro: { id: number; nombre: string; url: string; provincia: string; departamento: string; municipio: string; localidad: string; codigo_cdi: string };
  search: Busqueda | null;
  mostrar_formulario: boolean;
  non_field_errors: string[];
  fields: Record<string, string>;
  multiples: Record<string, Grupo>;
  ciudadano_id: number | null;
  urls: { cancelar: string; departamentos: string; municipios: string; localidades: string };
  messages: CdiMessage[];
};

const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
const ciudadanoValid = (c: unknown): c is Ciudadano => record(c) && Number.isSafeInteger(c.id) && text(c.apellido) && text(c.nombre) && text(c.documento);
const busquedaValid = (b: unknown): b is Busqueda => record(b) && text(b.query) && Array.isArray(b.ciudadanos) && b.ciudadanos.every(ciudadanoValid) &&
  (b.selected === null || ciudadanoValid(b.selected)) && typeof b.no_resultados === "boolean" && typeof b.renaper_precarga === "boolean" &&
  (b.renaper_prefill_token === null || text(b.renaper_prefill_token));
const grupoValid = (g: unknown): g is Grupo => record(g) && text(g.label) && strings(g.errors) && Array.isArray(g.options) &&
  g.options.every((o) => record(o) && text(o.id) && text(o.value) && text(o.label) && typeof o.checked === "boolean");

export function formValid(v: unknown): v is TrabajadorFormData {
  if (!record(v) || !record(v.centro) || !record(v.urls) || !record(v.fields) || !record(v.multiples)) return false;
  const c = v.centro;
  return typeof v.is_edit === "boolean" && Number.isSafeInteger(c.id) && ["nombre", "provincia", "departamento", "municipio", "localidad", "codigo_cdi"].every((k) => text(c[k])) &&
    internal(c.url) && (v.search === null || busquedaValid(v.search)) && typeof v.mostrar_formulario === "boolean" && strings(v.non_field_errors) &&
    Object.values(v.fields).every(text) && Object.values(v.multiples).every(grupoValid) && (v.ciudadano_id === null || Number.isSafeInteger(v.ciudadano_id)) &&
    ["cancelar", "departamentos", "municipios", "localidades"].every((k) => internal((v.urls as Record<string, unknown>)[k])) && messagesValid(v.messages);
}

/** A native column whose body is the crispy markup of one or more fields (the DOM ids of the scripts stay). */
function Col({ cls, id, fields, names }: { cls: string; id?: string; fields: Record<string, string>; names: string[] }) {
  return <div className={cls} id={id} dangerouslySetInnerHTML={{ __html: names.map((n) => fields[n] ?? "").join("") }} />;
}

const LABEL_STYLE = { color: "#e5e7eb" };

function Checks({ name, grupo, cols, rowId, title }: { name: string; grupo: Grupo | undefined; cols: string; rowId?: string; title?: string }) {
  if (!grupo) return null;
  return (
    <div className="form-group">
      <p className="form-label fw-semibold mb-2" style={LABEL_STYLE}>{title ?? grupo.label}</p>
      <div className="row g-2" id={rowId}>
        {grupo.options.map((o) => (
          <div key={o.id} className={cols}>
            <div className="form-check">
              <input type="checkbox" name={name} value={o.value} id={o.id} defaultChecked={o.checked} />{" "}
              <label className="form-check-label" htmlFor={o.id}>{o.label}</label>
            </div>
          </div>
        ))}
      </div>
      {grupo.errors.length > 0 && <div className="text-danger small mt-1"><ul className="errorlist">{grupo.errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
    </div>
  );
}

/** The native header gets `role=button`, `tabindex=0` and `aria-expanded`; Enter and Space toggle it. */
function Section({ id, icon, title, subtitle, status = true, children }: { id: string; icon: string; title: string; subtitle: string; status?: boolean; children: ReactNode }) {
  const [open, setOpen] = useState(true);
  const toggle = () => setOpen((current) => !current);
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
  };
  return (
    <div className="section-card" data-section={id}>
      <div className={`section-header${open ? "" : " collapsed"}`} data-toggle-section={id} tabIndex={0} role="button" aria-expanded={open} onClick={toggle} onKeyDown={onKey}>
        <div className="section-header-left">
          <div className="section-icon"><i className={`fas ${icon}`} /></div>
          <div className="section-title-group">
            <h3 className="section-title">{title}</h3>
            <p className="section-subtitle">{subtitle}</p>
          </div>
        </div>
        <div className="section-status">
          {status && <span className="status-badge empty" id={`status-${id}`}><i className="fas fa-circle" /> Sin completar</span>}
          <div className="collapse-indicator"><i className="fas fa-chevron-down" /></div>
        </div>
      </div>
      <div className={`section-body collapse${open ? " show" : ""}`} id={`section-${id}`}>{children}</div>
    </div>
  );
}

const CARD = { background: "#2c3e50", border: "1px solid #374151" };

function Search({ search }: { search: Busqueda }) {
  return (
    <>
      <div className="card mb-4" style={CARD}>
        <div className="card-body">
          <h5 className="mb-3" style={LABEL_STYLE}><i className="fas fa-search me-2" style={{ color: "#f39c12" }} />Buscar por DNI</h5>
          <form method="get" className="row g-2 align-items-end">
            <div className="col-md-4">
              <label htmlFor="busqueda-dni" className="form-label">DNI</label>
              <input type="text" className="form-control" name="query" id="busqueda-dni" placeholder="Ingrese DNI (mín. 4 dígitos)" defaultValue={search.query} />
            </div>
            <div className="col-auto"><button className="btn btn-warning" type="submit">Buscar</button></div>
          </form>
        </div>
      </div>
      {search.ciudadanos.length > 0 && !search.selected && (
        <div className="card mb-4" style={CARD}>
          <div className="card-body">
            <h6 className="mb-3" style={LABEL_STYLE}>Resultados de búsqueda</h6>
            <div className="table-responsive">
              <table className="table table-hover mb-0" style={LABEL_STYLE}>
                <thead style={{ borderColor: "#374151" }}><tr><th>Apellido</th><th>Nombre</th><th>DNI</th><th /></tr></thead>
                <tbody>
                  {search.ciudadanos.map((c) => (
                    <tr key={c.id} style={{ borderColor: "#374151" }}>
                      <td>{c.apellido}</td><td>{c.nombre}</td><td>{c.documento}</td>
                      <td><a href={`?query=${search.query}&ciudadano_id=${c.id}`} className="btn btn-sm btn-success">Completar ficha</a></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
      {search.query && search.no_resultados && (
        <div className="alert mb-4" style={{ background: "rgba(243,156,18,0.15)", border: "1px solid rgba(243,156,18,0.4)", color: "#f39c12" }}>
          <i className="fas fa-info-circle me-2" />{" "}
          {search.renaper_precarga
            ? "No se encontró el DNI en el sistema. Se precargaron datos desde RENAPER; complete la ficha para agregar al CDI."
            : "No se encontraron coincidencias. Puede completar la ficha manualmente."}
        </div>
      )}
      {search.selected && (
        <div className="alert mb-4" style={{ background: "rgba(52,152,219,0.15)", border: "1px solid rgba(52,152,219,0.4)", color: "#74b9e7" }}>
          <i className="fas fa-user-check me-2" />{" "}
          Ficha para: <strong>{search.selected.apellido}, {search.selected.nombre}</strong>{" "}
          (DNI {search.selected.documento})
        </div>
      )}
    </>
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

export function TrabajadorFormContent({ data: initial, endpoint }: { data: TrabajadorFormData; endpoint: string }) {
  const [data, setData] = useState(initial);
  const [version, setVersion] = useState(0);
  const [toasts, setToasts] = useState<CdiMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const sending = useRef(false);
  const form = useRef<HTMLFormElement>(null);
  const { departamentos, municipios, localidades } = data.urls;

  useEffect(() => {
    if (!form.current) return undefined;
    const urls: GeographyUrls = { departamentos, municipios, localidades };
    return bindTrabajadorForm(form.current, urls);
  }, [version, data.mostrar_formulario, departamentos, municipios, localidades]);

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

  const { fields, multiples, centro, search } = data;
  const save = (event: MouseEvent<HTMLButtonElement>) => {
    // The native button submits with `form.submit()`: no browser validation, the server answers.
    event.preventDefault();
    if (event.currentTarget.form) void submit(event.currentTarget.form);
  };
  const titulo = data.is_edit ? "Editar trabajador" : "Agregar trabajador";
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      {toasts.length > 0 && <NativeToasts messages={toasts} />}
      <div className="container-fluid">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item"><a href={safeInternalPath(centro.url) ?? "/"}>{centro.nombre}</a></li>
              <li className="breadcrumb-item active">{titulo}</li>
            </ol>
          </nav>
        </div>
        {!data.is_edit && search && <Search search={search} />}
        {data.mostrar_formulario && (
          <form method="post" id="trabajadorForm" className="w-100" ref={form} key={version} onSubmit={(e: FormEvent<HTMLFormElement>) => { e.preventDefault(); void submit(e.currentTarget); }}>
            {data.ciudadano_id !== null && <input type="hidden" name="ciudadano_id" value={data.ciudadano_id} />}
            {search?.renaper_prefill_token && <input type="hidden" name="renaper_prefill_token" value={search.renaper_prefill_token} />}
            {data.non_field_errors.length > 0 && <div className="alert alert-danger mb-3"><ul className="errorlist nonfield">{data.non_field_errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
            <div className="progress-indicator">
              <div className="progress-header">
                <h4 className="progress-title"><i className="fas fa-clipboard-check mr-2" />Progreso del Formulario</h4>
                <span className="progress-stats"><span id="completedSections">0</span>/7 secciones completadas</span>
              </div>
              <div className="progress-bar-container"><div className="progress-bar-fill" id="progressBarFill" style={{ width: "0%" }} /></div>
            </div>

            <Section id="institucion" icon="fa-building" title="Institución" subtitle="Datos del CDI" status={false}>
              <div className="form-group row">
                {([["cdi-jurisdiccion", "Jurisdicción", centro.provincia], ["cdi-departamento", "Departamento", centro.departamento], ["cdi-municipio", "Municipio", centro.municipio], ["cdi-localidad", "Localidad", centro.localidad]] as const).map(([id, label, value]) => (
                  <div className="col-md-3" key={id}>
                    <label htmlFor={id} className="form-label">{label}</label>
                    <input id={id} type="text" className="form-control" defaultValue={value} readOnly />
                  </div>
                ))}
              </div>
              <div className="form-group row">
                <div className="col-md-6">
                  <label htmlFor="cdi-nombre" className="form-label">Nombre del CDI</label>
                  <input id="cdi-nombre" type="text" className="form-control" defaultValue={centro.nombre} readOnly />
                </div>
                <div className="col-md-3">
                  <label htmlFor="cdi-codigo" className="form-label">Código CDI</label>
                  <input id="cdi-codigo" type="text" className="form-control" defaultValue={centro.codigo_cdi} readOnly />
                </div>
              </div>
            </Section>

            <Section id="espacio_temporal" icon="fa-calendar-alt" title="Espacio Temporal" subtitle="Fecha de carga del registro">
              <div className="form-group row"><Col cls="col-md-3" fields={fields} names={["fecha_carga"]} /></div>
            </Section>

            <Section id="fuerza_trabajo" icon="fa-id-card" title="Fuerza de trabajo" subtitle="Rol, función y datos personales (RENAPER/ANSES)">
              <div className="form-group row">
                <Col cls="col-md-3" fields={fields} names={["subcomponente"]} />
                <Col cls="col-md-4" id="row-funcion-pfpi" fields={fields} names={["funcion_pfpi"]} />
                <Col cls="col-md-4" id="row-funcion-egp" fields={fields} names={["funcion_egp"]} />
                <Col cls="col-md-4" id="row-funcion-cdi" fields={fields} names={["funcion_cdi"]} />
                <Col cls="col-md-3" id="row-sala-cdi" fields={fields} names={["sala_cdi"]} />
                <Col cls="col-md-4" id="row-funcion-uaf" fields={fields} names={["funcion_uaf"]} />
              </div>
              <div className="form-group row">
                <Col cls="col-md-3" fields={fields} names={["registro_tipo"]} />
                <Col cls="col-md-3" fields={fields} names={["fecha_actualizacion"]} />
              </div>
              <hr style={{ borderColor: "#374151" }} />
              <div className="form-group row">
                <Col cls="col-md-3" fields={fields} names={["nombre"]} />
                <Col cls="col-md-3" fields={fields} names={["apellido"]} />
                <Col cls="col-md-2" fields={fields} names={["fecha_nacimiento"]} />
                <div className="col-md-2">
                  <label htmlFor="id_edad_calculada" className="form-label">Edad (años)</label>
                  <input type="text" id="id_edad_calculada" className="form-control" readOnly />
                </div>
                <Col cls="col-md-2" fields={fields} names={["sexo_registral"]} />
              </div>
              <div className="form-group row">
                <Col cls="col-md-3" fields={fields} names={["dni"]} />
                <Col cls="col-md-3" fields={fields} names={["cuit", "sin_cuil"]} />
                <Col cls="col-md-5" fields={fields} names={["tipo_documentacion"]} />
              </div>
              <div className="form-group row">
                <Col cls="col-md-4" fields={fields} names={["pais_nacimiento"]} />
                <Col cls="col-md-4" fields={fields} names={["nacionalidad_trabajador"]} />
              </div>
            </Section>

            <Section id="formacion" icon="fa-graduation-cap" title="Formación y experiencia" subtitle="Nivel educativo, capacitaciones y trayectoria">
              <div className="form-group row">
                <Col cls="col-md-4" fields={fields} names={["nivel_educativo"]} />
                <Col cls="col-md-4" id="row-formacion-academica" fields={fields} names={["formacion_academica"]} />
                <Col cls="col-md-3" fields={fields} names={["anos_trabajo_primera_infancia"]} />
              </div>
              <Checks name="capacitaciones_certificadas" grupo={multiples.capacitaciones_certificadas} cols="col-md-4 col-sm-6" title="Capacitaciones certificadas (últimos tres años)" />
            </Section>

            <Section id="contratacion" icon="fa-file-contract" title="Contratación" subtitle="Tipo de contrato y carga horaria">
              <div className="form-group row">
                <Col cls="col-md-4" fields={fields} names={["tipo_contratacion"]} />
                <Col cls="col-md-3" fields={fields} names={["carga_horaria_semanal"]} />
              </div>
            </Section>

            <Section id="contacto" icon="fa-phone" title="Contacto" subtitle="Datos de contacto y domicilio">
              <div className="form-group row">
                <Col cls="col-md-4" fields={fields} names={["email"]} />
                <Col cls="col-md-3" fields={fields} names={["telefono"]} />
              </div>
              <div className="form-group row">
                <Col cls="col-md-4" fields={fields} names={["calle_contacto"]} />
                <Col cls="col-md-3" fields={fields} names={["unidad_funcional"]} />
                <Col cls="col-md-3" fields={fields} names={["tipo_barrio"]} />
              </div>
              <div className="form-group row">
                <Col cls="col-md-3" fields={fields} names={["provincia_contacto"]} />
                <Col cls="col-md-3" fields={fields} names={["departamento_contacto"]} />
                <Col cls="col-md-3" fields={fields} names={["municipio_contacto"]} />
                <Col cls="col-md-3" fields={fields} names={["localidad_contacto"]} />
              </div>
            </Section>

            <Section id="identidad" icon="fa-globe-americas" title="Cultura e identidad" subtitle="Pertenencia, lenguajes e interculturalidad">
              <Checks name="grupo_pertenencia" grupo={multiples.grupo_pertenencia} cols="col-md-6" rowId="id_grupo_pertenencia" />
              <div className="form-group row" id="row-pueblo-originario"><Col cls="col-md-5" fields={fields} names={["pueblo_originario"]} /></div>
              <Checks name="lenguajes" grupo={multiples.lenguajes} cols="col-md-4 col-sm-6" />
              <div className="form-group row"><Col cls="col-md-3" fields={fields} names={["es_interprete"]} /></div>
            </Section>

            <Section id="discapacidad" icon="fa-heartbeat" title="Discapacidad" subtitle="Condición, apoyos y Certificado Único de Discapacidad">
              <div className="form-group row"><Col cls="col-md-4" fields={fields} names={["tiene_discapacidad"]} /></div>
              <div id="bloque-discapacidad">
                <Checks name="tipo_discapacidad" grupo={multiples.tipo_discapacidad} cols="col-md-4" />
                <div className="form-group row"><Col cls="col-md-4" fields={fields} names={["recibe_apoyo_discapacidad"]} /></div>
                <div className="form-group row">
                  <Col cls="col-md-3" fields={fields} names={["tiene_cud"]} />
                  <Col cls="col-md-3" id="row-numero-cud" fields={fields} names={["numero_cud"]} />
                </div>
              </div>
            </Section>

            {uncertain && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
            <div className="d-flex gap-2 mt-3 mb-5">
              <button type="submit" className="btn btn-warning" data-submit-with-spinner="Guardando..." disabled={pending || undefined} onClick={save}>
                {pending
                  ? <><span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" /> Guardando...</>
                  : <><i className="fas fa-save me-1" />{" "}{data.is_edit ? "Guardar cambios" : "Agregar trabajador"}</>}
              </button>
              <a href={safeInternalPath(data.urls.cancelar) ?? "/"} className="btn btn-secondary">Cancelar</a>
            </div>
          </form>
        )}
      </div>
    </>
  );
}

function TrabajadorFormPage({ centro, id }: { centro: string; id?: string }) {
  const base = `web/cdi/centros/${centro}/trabajadores/`;
  const endpoint = id ? `${base}${id}/editar/` : `${base}crear/`;
  const [state] = useCdiPage(id ? endpoint : `${endpoint}${window.location.search}`, formValid);
  return renderCdi(state, (data) => ({
    title: data.is_edit ? "Editar trabajador" : "Agregar trabajador",
    heading: data.is_edit ? "Editar trabajador" : "Agregar trabajador",
    // The native form posts to the page URL, query included, so the rejected page keeps the search.
    content: <TrabajadorFormContent data={data} endpoint={id ? endpoint : `${endpoint}${window.location.search}`} />,
  }));
}

const OWN = /^\/centrodeinfancia\/([1-9]\d*)\/trabajadores\/(?:crear|([1-9]\d*)\/editar)\/$/;

// Native URLs of the CDI worker create and edit (CDI05); same trailing slash.
export const cdiTrabajadorFormRoute: RouteDefinition<{ centro: string; id?: string }> = {
  name: "cdi-trabajador-form",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { centro: own[1], id: own[2] } : null;
  },
  render: ({ centro, id }) => <TrabajadorFormPage centro={centro} id={id} />,
};
