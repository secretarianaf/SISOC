/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { Fragment, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * AD01.01 template manager queries (`comedores/configuracion/templates/`):
 * templates list and detail, documentary variables and incidents, with the
 * native templates' markup. Data comes from
 * `/api/web/comedores/admisiones/plantillas-informe/`, which runs the native
 * views. Every action keeps the native form POST to its native URL (AD01.02),
 * and the create form, version editor and DOCX preview stay Django pages.
 */
type Page = "templates" | "detalle" | "variables" | "incidencias" | "incidencia";
type Params = { page: Page; id?: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Choice = { value: string; label: string };
type Nav = { templates: string; variables: string; incidencias: string };
type Pagination = { is_paginated: boolean; number: number; count: number; has_rows: boolean; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
type Plantilla = { id: number; codigo: string; nombre: string; descripcion: string; combinacion: string; version_vigente: number | null; estado: string; estado_display: string; url: string };
const FILTROS = ["tipo_admision", "tipo_convenio", "es_ex_pnud", "estado_convenio_pnud", "tipo_renovacion", "estado_financiamiento", "informe_complementario_modifica_prestaciones"] as const;
const OPCIONES = ["tipos_admision", "tipos_convenio", "opciones_ex_pnud", "estados_convenio_pnud", "tipos_renovacion", "estados_financiamiento", "opciones_informe_complementario"] as const;
type ListData = {
  estado_filtro: string; busqueda: string; filtros: Record<(typeof FILTROS)[number], string>;
  opciones: Record<(typeof OPCIONES)[number], Choice[]>; results: Plantilla[]; page: Pagination; urls: Nav & { crear: string }; messages: Message[];
};
type Version = { id: number; numero: number; estado: string; estado_display: string; creado: string; publicado: string | null };
type DetailData = {
  id: number; codigo: string; nombre: string; descripcion: string; estado: string; estado_display: string; condiciones: { term: string; value: string }[];
  borrador: { id: number; numero: number; modificado: string; urls: { editar: string; publicar: string; descartar: string } } | null;
  historial: Version[]; urls: Nav & { version_crear: string; inactivar: string }; messages: Message[];
};
type Variable = { id: number; categoria: string; nombre: string; descripcion: string; token: string; activo: boolean; alternar_url: string };
type VariablesData = { estado_filtro: string; busqueda: string; results: Variable[]; urls: Nav; messages: Message[] };
type Incidencia = { id: number; codigo: string; clave_condiciones: string; cantidad_casos: number; ultima_fecha: string; estado: string; estado_display: string; url: string };
type IncidenciasData = { estado_filtro: string; busqueda: string; estados: Choice[]; results: Incidencia[]; page: Pagination; urls: Nav; messages: Message[] };
type FormField = { name: string; label: string; required: boolean; value: string; choices?: Choice[] };
type Caso = { id: number; admision: string; informe: string; comedor: string; organizacion: string; reportado_por: string; creado: string };
type IncidenciaData = {
  id: number; codigo: string; cantidad_casos: number; primera_fecha: string; ultima_fecha: string; incidencia_anterior: string | null;
  clave_condiciones: string; condiciones: { clave: string; descripcion: string }[]; form: FormField[]; casos: Caso[];
  urls: Nav & { gestionar: string }; messages: Message[];
};

const API = "web/comedores/admisiones/plantillas-informe/";
const BASE = "/comedores/configuracion/templates/";
const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const nullable = <T,>(v: unknown, ok: (x: unknown) => x is T) => v === null || ok(v);
const texts = (v: unknown, keys: readonly string[]) => record(v) && keys.every((k) => text(v[k]));
const choices = (v: unknown): v is Choice[] => Array.isArray(v) && v.every((c) => texts(c, ["value", "label"]));
const messagesValid = (v: unknown): v is Message[] => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
const navValid = (v: unknown, extra: string[] = []) => record(v) && ["templates", "variables", "incidencias", ...extra].every((k) => internal(v[k]));
const pageValid = (p: unknown): p is Pagination => record(p) && typeof p.is_paginated === "boolean" && typeof p.has_rows === "boolean" &&
  int(p.number) && int(p.count) && nullable(p.previous, int) && nullable(p.next, int) &&
  Array.isArray(p.range) && p.range.every((n) => n === "…" || int(n)) && text(p.query_without_page);
const plantillaValid = (p: unknown): p is Plantilla => texts(p, ["codigo", "nombre", "descripcion", "combinacion", "estado", "estado_display"]) &&
  int((p as Plantilla).id) && nullable((p as Plantilla).version_vigente, int) && internal((p as Plantilla).url);
const listValid = (v: unknown): v is ListData => record(v) && text(v.estado_filtro) && text(v.busqueda) && texts(v.filtros, FILTROS) &&
  record(v.opciones) && OPCIONES.every((k) => choices((v.opciones as Record<string, unknown>)[k])) &&
  Array.isArray(v.results) && v.results.every(plantillaValid) && pageValid(v.page) && navValid(v.urls, ["crear"]) && messagesValid(v.messages);
const versionValid = (x: unknown): x is Version => texts(x, ["estado", "estado_display", "creado"]) && int((x as Version).id) &&
  int((x as Version).numero) && nullable((x as Version).publicado, text);
const borradorValid = (b: unknown) => record(b) && int(b.id) && int(b.numero) && text(b.modificado) &&
  record(b.urls) && ["editar", "publicar", "descartar"].every((k) => internal((b.urls as Record<string, unknown>)[k]));
const detailValid = (v: unknown): v is DetailData => texts(v, ["codigo", "nombre", "descripcion", "estado", "estado_display"]) &&
  record(v) && int(v.id) && Array.isArray(v.condiciones) && v.condiciones.every((c) => texts(c, ["term", "value"])) &&
  (v.borrador === null || borradorValid(v.borrador)) && Array.isArray(v.historial) && v.historial.every(versionValid) &&
  navValid(v.urls, ["version_crear", "inactivar"]) && messagesValid(v.messages);
const variableValid = (x: unknown): x is Variable => texts(x, ["categoria", "nombre", "descripcion", "token"]) &&
  int((x as Variable).id) && typeof (x as Variable).activo === "boolean" && internal((x as Variable).alternar_url);
const variablesValid = (v: unknown): v is VariablesData => record(v) && text(v.estado_filtro) && text(v.busqueda) &&
  Array.isArray(v.results) && v.results.every(variableValid) && navValid(v.urls) && messagesValid(v.messages);
const incidenciaRowValid = (x: unknown): x is Incidencia => texts(x, ["codigo", "clave_condiciones", "ultima_fecha", "estado", "estado_display"]) &&
  int((x as Incidencia).id) && int((x as Incidencia).cantidad_casos) && internal((x as Incidencia).url);
const incidenciasValid = (v: unknown): v is IncidenciasData => record(v) && text(v.estado_filtro) && text(v.busqueda) && choices(v.estados) &&
  Array.isArray(v.results) && v.results.every(incidenciaRowValid) && pageValid(v.page) && navValid(v.urls) && messagesValid(v.messages);
const fieldValid = (f: unknown): f is FormField => texts(f, ["name", "label", "value"]) && typeof (f as FormField).required === "boolean" &&
  ((f as FormField).choices === undefined || choices((f as FormField).choices));
const incidenciaValid = (v: unknown): v is IncidenciaData => texts(v, ["codigo", "primera_fecha", "ultima_fecha", "clave_condiciones"]) &&
  record(v) && int(v.id) && int(v.cantidad_casos) && nullable(v.incidencia_anterior, text) &&
  Array.isArray(v.condiciones) && v.condiciones.every((c) => texts(c, ["clave", "descripcion"])) &&
  Array.isArray(v.form) && v.form.length === 3 && v.form.every(fieldValid) &&
  Array.isArray(v.casos) && v.casos.every((c) => texts(c, ["admision", "informe", "comedor", "organizacion", "reportado_por", "creado"]) && int((c as Caso).id)) &&
  navValid(v.urls, ["gestionar"]) && messagesValid(v.messages);

/** `{% csrf_token %}` of the native forms (the entry sets the cookie). */
function Csrf() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

function Frame({ section, urls, children }: { section: "templates" | "variables" | "incidencias"; urls: Nav; children: ReactNode }) {
  const link = (key: keyof Nav, icon: string, label: string) =>
    <a href={urls[key]} className={`nav-link ${section === key ? "active" : ""}`}><i className={`fas ${icon}`} />{label}</a>;
  return <>
    <link rel="stylesheet" href="/static/custom/css/gestor_templates.css" />
    <div className="gestor-templates"><div className="gt-page">
      <nav className="gt-section-nav" aria-label="Secciones del Gestor de templates">
        <p className="gt-section-nav__title"><i className="fas fa-file-alt" />Gestor de templates</p>
        <div className="nav nav-pills gt-section-links">
          {link("templates", "fa-copy", "Templates")}
          {link("variables", "fa-code", "Variables documentales")}
          {link("incidencias", "fa-exclamation-triangle", "Incidencias")}
        </div>
      </nav>
      {children}
    </div></div>
  </>;
}

function Hero({ eyebrow, title, children, actions }: { eyebrow: string; title: string; children: ReactNode; actions?: ReactNode }) {
  return <section className="gt-hero">
    <div><span className="gt-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{children}</p></div>
    {actions !== undefined && <div className="gt-hero__actions">{actions}</div>}
  </section>;
}

/** `components/empty_state.html` with `container_class="gt-empty"`. */
function Empty({ icon, title, message, color = "muted" }: { icon: string; title: string; message: string; color?: string }) {
  return <div className="empty-state text-center py-5 gt-empty">
    <div className="empty-state-icon mb-4"><i className={`${icon} fa-4x text-${color}`} /></div>
    <h4 className={`empty-state-title text-${color} mb-3`}>{title}</h4>
    <p className="empty-state-message text-muted mb-4">{message}</p>
  </div>;
}

/** `components/pagination.html` with «Volver» / «Continuar». */
function Paginator({ page }: { page: Pagination }) {
  const href = (n: number) => `?${page.query_without_page}page=${n}`;
  const item = (label: string, target: number | null, extra = "") => target === null
    ? <li className={`page-item disabled${extra}`}><a href="#" className="page-link">{label}</a></li>
    : <li className={`page-item${extra}`}><a href={href(target)} className="page-link">{label}</a></li>;
  return <div className="mt-2">
    {page.is_paginated && <ul className="pagination">
      {item("Volver", page.previous)}
      {page.range.map((n, i) => <Fragment key={i}>{n === "…" ? item("...", null) : item(String(n), n, page.number === n ? " active" : " ")}</Fragment>)}
      {item("Continuar", page.next)}
    </ul>}
    {page.has_rows && <p className="text-center text-muted mb-0 mt-1">Se encontraron {page.count} resultados</p>}
  </div>;
}

function Status({ tone, children }: { tone: "success" | "pending" | "muted"; children: ReactNode }) {
  return <span className={`gt-status gt-status--${tone}`}>{children}</span>;
}

function Card({ icon, title, extra = "", children }: { icon: string; title: string; extra?: string; children: ReactNode }) {
  return <section className={`card gt-card${extra}`}>
    <div className="card-header"><h2 className="card-title"><i className={`fas ${icon}`} />{title}</h2></div>
    {children}
  </section>;
}

function Table({ headers, children, hidden = true }: { headers: string[]; children: ReactNode; hidden?: boolean }) {
  return <div className="table-responsive"><table className="table gt-table">
    <thead><tr>{headers.map((h) => <th key={h}>{h}</th>)}{hidden && <th><span className="visually-hidden">Acciones</span></th>}</tr></thead>
    <tbody>{children}</tbody>
  </table></div>;
}

function FilterSelect({ name, label, empty, options, value, group, hidden, onChange, extra }: {
  name: string; label?: string; empty: string; options: Choice[]; value: string; group?: "incorporacion" | "renovacion"; hidden?: boolean; onChange?: (v: string) => void; extra?: ReactNode;
}) {
  const select = <select name={name} className={`form-select${label ? "" : " mt-2"}`} defaultValue={value} onChange={onChange && ((e) => onChange(e.target.value))}
    {...(name === "tipo_admision" ? { "data-template-filter": "tipo-admision" } : {})}>
    <option value="">{empty}</option>
    {options.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
  </select>;
  if (!label) return select;
  return <label {...(group ? { "data-template-filter-group": group } : {})} hidden={hidden}><span>{label}</span>{select}{extra}</label>;
}

function TemplatesPage({ data }: { data: ListData }) {
  const [tipo, setTipo] = useState(data.filtros.tipo_admision);
  const o = data.opciones, f = data.filtros;
  // `list.html` script: a group is hidden when a type is chosen and it is not that type.
  const hidden = (group: string) => Boolean(tipo) && group !== tipo;
  const estado = (value: string, label: string) =>
    <button type="submit" name="estado" value={value} className={`btn ${data.estado_filtro === value ? "btn-primary" : "btn-outline-primary"}`}>{label}</button>;
  return <Frame section="templates" urls={data.urls}>
    <InsumosToastList messages={data.messages} />
    <Hero eyebrow="Configuración documental" title="Templates de informes técnicos"
      actions={<a href={data.urls.crear} className="btn btn-primary"><i className="fas fa-plus" /> Crear template</a>}>
      Administrá las combinaciones que determinan qué modelo de documento se usará en cada admisión.
    </Hero>
    <Card icon="fa-copy" title="Templates configurados" extra=" gt-card--list">
      <div className="card-body">
        <form method="get" className="gt-filters" role="search">
          <input type="hidden" name="estado" value={data.estado_filtro} />
          <div className="gt-toolbar">
            <div className="btn-group" aria-label="Filtrar por estado">{estado("activa", "Activas")}{estado("inactiva", "Inactivas")}{estado("todas", "Todas")}</div>
            <div className="gt-search"><div className="input-group">
              <span className="input-group-text"><i className="fas fa-search" /></span>
              <input type="search" name="q" defaultValue={data.busqueda} className="form-control" placeholder="Buscar por código o nombre" />
              <button type="submit" className="btn btn-outline-primary">Buscar</button>
            </div></div>
          </div>
          <div className="gt-filters__fields">
            <FilterSelect name="tipo_admision" label="Tipo de admisión" empty="Todos" options={o.tipos_admision} value={f.tipo_admision} onChange={setTipo} />
            <FilterSelect name="tipo_convenio" label="Tipo de convenio" empty="Todos" options={o.tipos_convenio} value={f.tipo_convenio} />
            <FilterSelect name="es_ex_pnud" label="Ex PNUD" empty="Todos" options={o.opciones_ex_pnud} value={f.es_ex_pnud} group="incorporacion" hidden={hidden("incorporacion")} />
            <FilterSelect name="estado_convenio_pnud" label="Estado convenio PNUD" empty="Todos" options={o.estados_convenio_pnud} value={f.estado_convenio_pnud} group="incorporacion" hidden={hidden("incorporacion")} />
            <FilterSelect name="tipo_renovacion" label="Renovación que tramita" empty="Todas" options={o.tipos_renovacion} value={f.tipo_renovacion} group="renovacion" hidden={hidden("renovacion")} />
            <FilterSelect name="estado_financiamiento" label="Estado del financiamiento" empty="Todos" options={o.estados_financiamiento} value={f.estado_financiamiento} group="renovacion" hidden={hidden("renovacion")}
              extra={<FilterSelect name="informe_complementario_modifica_prestaciones" empty="Informe complementario: todos" options={o.opciones_informe_complementario} value={f.informe_complementario_modifica_prestaciones} />} />
          </div>
          <div className="gt-filters__actions">
            <button type="submit" className="btn btn-primary"><i className="fas fa-filter" /> Aplicar filtros</button>
            <a href={data.urls.templates} className="btn btn-outline-secondary">Limpiar</a>
          </div>
        </form>
      </div>
      {data.results.length ? <Table headers={["Código", "Nombre", "Combinación", "Versión vigente", "Estado"]}>
        {data.results.map((p) => <tr key={p.id}>
          <td><span className="gt-row-title">{p.codigo}</span></td>
          <td><span className="gt-row-title">{p.nombre}</span>{p.descripcion && <span className="gt-row-subtitle">{p.descripcion}</span>}</td>
          <td>{p.combinacion}</td>
          <td>{p.version_vigente !== null ? <Status tone="success">v{p.version_vigente} publicada</Status> : <Status tone="pending">Sin versión publicada</Status>}</td>
          <td><Status tone={p.estado === "activa" ? "success" : "muted"}>{p.estado_display}</Status></td>
          <td className="text-end"><a href={p.url} className="btn btn-sm btn-outline-primary">Gestionar</a></td>
        </tr>)}
      </Table> : <Empty icon="fas fa-copy" title="No hay templates para este filtro" message="Podés crear una nueva combinación o cambiar los filtros de búsqueda." />}
    </Card>
    <Paginator page={data.page} />
  </Frame>;
}

function PostButton({ action, className, children, confirm, hidden }: { action: string; className: string; children: ReactNode; confirm?: string; hidden?: Record<string, string> }) {
  const submit = (event: FormEvent<HTMLFormElement>) => { if (confirm && !window.confirm(confirm)) event.preventDefault(); };
  return <form method="post" action={action} onSubmit={confirm ? submit : undefined}>
    <Csrf />
    {Object.entries(hidden ?? {}).map(([name, value]) => <input key={name} type="hidden" name={name} value={value} />)}
    <button type="submit" className={className}>{children}</button>
  </form>;
}

const DISCARD = "¿Descartar la versión en preparación? Esta acción no se puede deshacer.";

function DetailPage({ data }: { data: DetailData }) {
  const activa = data.estado === "activa";
  const b = data.borrador;
  return <Frame section="templates" urls={data.urls}>
    <InsumosToastList messages={data.messages} />
    <Hero eyebrow={data.codigo} title={data.nombre}
      actions={!b && activa ? <PostButton action={data.urls.version_crear} className="btn btn-primary"><i className="fas fa-plus" /> Crear nueva versión</PostButton> : null}>
      {data.descripcion || "Configuración de condiciones y versiones de este template lógico."}
    </Hero>
    <section className="gt-template-context" aria-labelledby="condiciones-template">
      <div className="gt-template-context__header">
        <h2 id="condiciones-template"><i className="fas fa-sliders-h" /> Condiciones del template</h2>
        <div className="gt-template-context__actions">
          {activa ? <>
            <Status tone="success">{data.estado_display}</Status>
            <PostButton action={data.urls.inactivar} className="btn btn-sm btn-danger">Inactivar template</PostButton>
          </> : <Status tone="muted">{data.estado_display}</Status>}
        </div>
      </div>
      <dl className="gt-template-context__items">
        {data.condiciones.map((c) => <div key={c.term} className="gt-template-context__item"><dt>{c.term}</dt><dd>{c.value}</dd></div>)}
      </dl>
    </section>
    {b && <section className="gt-working-version" aria-labelledby="version-preparacion">
      <div>
        <span className="gt-eyebrow">Versión en preparación</span>
        <h2 id="version-preparacion">v{b.numero}</h2>
        <p>Estos cambios todavía no se usan en las admisiones. Podés continuar editando y guardar las veces que necesites antes de publicar.</p>
        <small>Última modificación: {b.modificado}</small>
      </div>
      <div className="gt-working-version__actions">
        <a href={b.urls.editar} className="btn btn-primary"><i className="fas fa-pen" /> Continuar editando</a>
        <PostButton action={b.urls.publicar} className="btn btn-success">Publicar versión</PostButton>
        <PostButton action={b.urls.descartar} className="btn btn-outline-secondary" confirm={DISCARD}>Descartar versión</PostButton>
      </div>
    </section>}
    <Card icon="fa-history" title="Historial de versiones" extra=" gt-card--versions">
      {data.historial.length ? <Table headers={["Versión", "Estado", "Creada", "Publicada"]}>
        {data.historial.map((v) => <tr key={v.id}>
          <td><span className="gt-row-title">v{v.numero}</span></td>
          <td><Status tone={v.estado === "publicada" ? "success" : "pending"}>{v.estado_display}</Status></td>
          <td>{v.creado}</td>
          <td>{v.publicado ?? <span className="text-muted">—</span>}</td>
          <td className="text-end"><div className="gt-version-actions">
            {activa && <PostButton action={data.urls.version_crear} className="btn btn-sm btn-outline-secondary" hidden={{ origen_version_id: String(v.id) }}>Usar como punto de partida</PostButton>}
          </div></td>
        </tr>)}
      </Table> : <Empty icon="fas fa-file" title="No hay versiones publicadas todavía" message="Creá una versión en preparación para empezar a cargar el contenido del documento." />}
    </Card>
  </Frame>;
}

function SearchForm({ estado, busqueda, placeholder, type }: { estado: string; busqueda: string; placeholder: string; type?: "search" }) {
  return <form method="get" className="gt-search" role="search">
    <input type="hidden" name="estado" value={estado} />
    <div className="input-group">
      <span className="input-group-text"><i className="fas fa-search" /></span>
      <input type={type} name="q" defaultValue={busqueda} className="form-control" placeholder={placeholder} />
      <button type="submit" className="btn btn-outline-primary">Buscar</button>
    </div>
  </form>;
}

function stateLinks(base: string, current: string, busqueda: string, options: Choice[]) {
  const q = busqueda ? `&q=${encodeURIComponent(busqueda)}` : "";
  return options.map((o) => <a key={o.value} href={`${base}?estado=${o.value}${q}`} className={`btn ${current === o.value ? "btn-primary" : "btn-outline-primary"}`}>{o.label}</a>);
}

function VariablesPage({ data }: { data: VariablesData }) {
  const next = `${window.location.pathname}${window.location.search}`;
  return <Frame section="variables" urls={data.urls}>
    <InsumosToastList messages={data.messages} />
    <Hero eyebrow="Catálogo documental" title="Variables documentales">Valores disponibles para insertar en el contenido de los templates de informe técnico.</Hero>
    <div className="gt-help mb-3">
      <h2><i className="fas fa-info-circle" /> Cómo funciona este catálogo</h2>
      <p className="mb-0">Estas variables se resuelven con datos que ya existen en SISOC. Podés activarlas o eliminarlas de forma lógica; para crear una nueva, antes debe existir el dato que el sistema pueda completar.</p>
    </div>
    <Card icon="fa-code" title="Variables disponibles" extra=" gt-card--list">
      <div className="card-body"><div className="gt-toolbar">
        <div className="btn-group" aria-label="Filtrar variables por estado">
          {stateLinks(data.urls.variables, data.estado_filtro, data.busqueda, [{ value: "activas", label: "Activas" }, { value: "inactivas", label: "Eliminadas" }, { value: "todas", label: "Todas" }])}
        </div>
        <SearchForm estado={data.estado_filtro} busqueda={data.busqueda} placeholder="Buscar por nombre, categoría o código" />
      </div></div>
      {data.results.length ? <Table headers={["Categoría", "Variable", "Código insertado", "Estado"]}>
        {data.results.map((v) => <tr key={v.id}>
          <td>{v.categoria}</td>
          <td><span className="gt-row-title">{v.nombre}</span>{v.descripcion && <span className="gt-row-subtitle">{v.descripcion}</span>}</td>
          <td><code>{v.token}</code></td>
          <td>{v.activo ? <Status tone="success">Activa</Status> : <Status tone="muted">Eliminada</Status>}</td>
          <td className="text-end"><PostButton action={v.alternar_url} className={`btn btn-sm ${v.activo ? "btn-danger" : "btn-success"}`} hidden={{ next }}>{v.activo ? "Eliminar" : "Activar"}</PostButton></td>
        </tr>)}
      </Table> : <Empty icon="fas fa-code" title="No se encontraron variables" message="Probá con otra búsqueda o cambiá el filtro de estado." />}
    </Card>
  </Frame>;
}

const INCIDENCIA_TONE: Record<string, "pending" | "success" | "muted"> = { pendiente: "pending", resuelta: "success" };

function IncidenciasPage({ data }: { data: IncidenciasData }) {
  return <Frame section="incidencias" urls={data.urls}>
    <InsumosToastList messages={data.messages} />
    <Hero eyebrow="Seguimiento de configuración" title="Incidencias de templates">Casos reportados al intentar generar un informe técnico sin un template publicado que coincida.</Hero>
    <Card icon="fa-exclamation-triangle" title="Configuraciones faltantes" extra=" gt-card--list">
      <div className="card-body"><div className="gt-toolbar">
        <div className="btn-group" aria-label="Filtrar incidencias por estado">
          {stateLinks(data.urls.incidencias, data.estado_filtro, data.busqueda, [...data.estados, { value: "todas", label: "Todas" }])}
        </div>
        <SearchForm estado={data.estado_filtro} busqueda={data.busqueda} placeholder="Código, combinación, comedor u organización" type="search" />
      </div></div>
      {data.results.length ? <Table headers={["Código", "Combinación", "Casos", "Último reporte", "Estado"]}>
        {data.results.map((i) => <tr key={i.id}>
          <td><span className="gt-row-title">{i.codigo}</span></td>
          <td><code>{i.clave_condiciones}</code></td>
          <td>{i.cantidad_casos}</td>
          <td>{i.ultima_fecha}</td>
          <td><Status tone={INCIDENCIA_TONE[i.estado] ?? "muted"}>{i.estado_display}</Status></td>
          <td className="text-end"><a href={i.url} className="btn btn-sm btn-outline-primary">Gestionar</a></td>
        </tr>)}
      </Table> : <Empty icon="fas fa-check-circle" color="success" title="No hay incidencias para este filtro" message="Las incidencias aparecen cuando no hay un template publicado para una combinación." />}
    </Card>
    <Paginator page={data.page} />
  </Frame>;
}

/** `{{ form.<campo>|as_crispy_field }}` (Bootstrap 5) for the management form. */
function CrispyField({ field }: { field: FormField }) {
  const id = `id_${field.name}`;
  return <div id={`div_${id}`} className="mb-3">
    <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>{field.label}{field.required && <span className="asteriskField">*</span>}</label>
    {field.choices
      ? <select name={field.name} className="form-select" id={id} defaultValue={field.value}>{field.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select>
      : <textarea name={field.name} cols={40} rows={4} className="form-control textarea" id={id} defaultValue={field.value} />}
  </div>;
}

function Summary({ label, value }: { label: string; value: ReactNode }) {
  return <div className="gt-summary__item"><span className="gt-summary__label">{label}</span><span className="gt-summary__value">{value}</span></div>;
}

function IncidenciaPage({ data }: { data: IncidenciaData }) {
  return <Frame section="incidencias" urls={data.urls}>
    <InsumosToastList messages={data.messages} />
    <Hero eyebrow={data.codigo} title="Gestionar incidencia">Registrá cómo se resolvió la falta de template para esta combinación y revisá las admisiones afectadas.</Hero>
    <div className="row g-3">
      <div className="col-lg-5">
        <section className="card gt-card mb-3">
          <div className="card-header"><h2 className="card-title"><i className="fas fa-info-circle" />Detalle del reporte</h2></div>
          <div className="card-body">
            <div className="gt-summary mb-3">
              <Summary label="Casos agrupados" value={data.cantidad_casos} />
              <Summary label="Primer reporte" value={data.primera_fecha} />
              <Summary label="Último reporte" value={data.ultima_fecha} />
              {data.incidencia_anterior !== null && <Summary label="Incidencia anterior" value={data.incidencia_anterior} />}
            </div>
            <h3 className="h6 fw-bold">Combinación</h3>
            <p><code>{data.clave_condiciones}</code></p>
            <h3 className="h6 fw-bold">Condiciones reportadas</h3>
            {data.condiciones.map((c, i) => <p key={i} className="mb-1"><strong>{c.clave}:</strong> {c.descripcion}</p>)}
          </div>
        </section>
        <section className="card gt-card">
          {/* AD01.02 stays native: the form posts to the native URL, as the Django page does. */}
          <form method="post" action={data.urls.gestionar} className="gt-form">
            <Csrf />
            <div className="card-header"><h2 className="card-title"><i className="fas fa-tasks" />Gestión</h2></div>
            <div className="card-body">{data.form.map((f) => <CrispyField key={f.name} field={f} />)}</div>
            <div className="card-footer gt-actions">
              <a href={data.urls.incidencias} className="btn btn-outline-secondary">Cancelar</a>
              <button type="submit" className="btn btn-primary">Guardar gestión</button>
            </div>
          </form>
        </section>
      </div>
      <div className="col-lg-7">
        <Card icon="fa-list" title="Admisiones afectadas" extra=" h-100">
          {data.casos.length ? <Table headers={["Admisión", "Informe", "Comedor", "Organización", "Reportado por", "Fecha"]} hidden={false}>
            {data.casos.map((c) => <tr key={c.id}>
              <td>{c.admision}</td><td>{c.informe}</td><td>{c.comedor}</td><td>{c.organizacion}</td><td>{c.reportado_por}</td><td>{c.creado}</td>
            </tr>)}
          </Table> : <Empty icon="fas fa-inbox" title="No hay casos registrados" message="Todavía no se registraron admisiones para esta incidencia." />}
        </Card>
      </div>
    </div>
  </Frame>;
}

function Crumbs({ items }: { items: [string, string | null][] }) {
  return <ol className="breadcrumb float-sm-right">
    {items.map(([label, url], i) => <li key={i} className={`breadcrumb-item${url ? "" : " active"}`}>{url ? <a href={url}>{label}</a> : label}</li>)}
  </ol>;
}

const HEADING = "Gestor de templates";
const ROOT: [string, string] = ["Gestor de templates", BASE];

function TemplatesRoute() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando templates…", (data) => ({ title: "Gestor de templates", heading: HEADING, breadcrumb: <Crumbs items={[["Gestor de templates", null]]} />, content: <TemplatesPage data={data} /> }));
}

function DetailRoute({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, detailValid);
  return renderMain(state, "Cargando template…", (data) => ({ title: `${data.codigo} · Gestor de templates`, heading: HEADING, breadcrumb: <Crumbs items={[ROOT, [data.codigo, null]]} />, content: <DetailPage data={data} /> }));
}

function VariablesRoute() {
  const [state] = useMainResource(`${API}variables/${window.location.search}`, variablesValid);
  return renderMain(state, "Cargando variables…", (data) => ({ title: "Variables documentales · Gestor de templates", heading: HEADING, breadcrumb: <Crumbs items={[ROOT, ["Variables documentales", null]]} />, content: <VariablesPage data={data} /> }));
}

function IncidenciasRoute() {
  const [state] = useMainResource(`${API}incidencias/${window.location.search}`, incidenciasValid);
  return renderMain(state, "Cargando incidencias…", (data) => ({ title: "Incidencias de templates", heading: HEADING, breadcrumb: <Crumbs items={[ROOT, ["Incidencias", null]]} />, content: <IncidenciasPage data={data} /> }));
}

function IncidenciaRoute({ id }: { id: string }) {
  const [state] = useMainResource(`${API}incidencias/${id}/`, incidenciaValid);
  return renderMain(state, "Cargando incidencia…", (data) => ({
    title: `${data.codigo} · Incidencias`, heading: HEADING, breadcrumb: <Crumbs items={[ROOT, ["Incidencias", data.urls.incidencias], [data.codigo, null]]} />, content: <IncidenciaPage data={data} />,
  }));
}

// Native GET pages of `admisiones/urls/web_urls.py`, same trailing slashes.
const PATH = /^\/comedores\/configuracion\/templates\/(?:(variables|incidencias)\/|incidencias\/([0-9]+)\/|([0-9]+)\/)?$/;

export const admisionesTemplatesRoute: RouteDefinition<Params> = {
  name: "comedores-gestor-templates",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    if (m[2]) return { page: "incidencia", id: m[2] };
    if (m[3]) return { page: "detalle", id: m[3] };
    return { page: (m[1] as Page | undefined) ?? "templates" };
  },
  render({ page, id }) {
    if (page === "detalle") return <DetailRoute key={id} id={id!} />;
    if (page === "variables") return <VariablesRoute />;
    if (page === "incidencias") return <IncidenciasRoute />;
    if (page === "incidencia") return <IncidenciaRoute key={id} id={id!} />;
    return <TemplatesRoute />;
  },
};
