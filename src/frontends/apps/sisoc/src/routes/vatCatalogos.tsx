/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, type ReactNode } from "react";
import { Breadcrumb, internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { Filters, filtersConfigValid, type Favorites, type FiltersConfig } from "./listControls";
import { NativeToasts } from "./nativeParity";
import { CsrfInput, useForbidden } from "./vatFormShared";
import { bool, integer, listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, vatNavigation, type Message, type Page } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V07.01 catalogos: `vat/catalogo/{sector,subsector,modalidadcursada,titulorreferencia}_{list,detail}.html`. Data comes from
 * `/api/web/vat/catalogos/<slug>/`, which runs the native views; the forms and the delete confirmations live in
 * `vatCatalogosForm.tsx`.
 */
export type Catalogo = "sectores" | "subsectores" | "modalidades-cursado" | "titulos-referencia";
type Permisos = { editar: boolean; eliminar: boolean };
type Row = { id: number; nombre: string; detail_url: string; update_url: string; delete_url: string; [k: string]: unknown };
export type CatalogoListData = {
  results: Row[]; page: Page; busqueda: string; permisos: Permisos; urls: { list: string; create: string }; messages: Message[];
  filters_config?: FiltersConfig; favorites?: Favorites;
};
export type CatalogoDetailData = {
  id: number; nombre: string; descripcion?: string; subsectores?: string[]; sector?: { nombre: string; url: string }; activo?: boolean;
  plan_estudio?: string; codigo?: string; planes?: string[]; urls: { vat: string; list: string; update: string; delete: string }; messages: Message[];
};

const TEXT_COLUMNS: Record<Catalogo, string[]> = {
  sectores: ["descripcion"], subsectores: ["sector", "descripcion"], "modalidades-cursado": ["descripcion"], "titulos-referencia": ["plan_estudio", "codigo"],
};

export const catalogoListValid = (catalogo: Catalogo) => (v: unknown): v is CatalogoListData => record(v) && Array.isArray(v.results) &&
  v.results.every((r) => record(r) && integer(r.id) && text(r.nombre) && internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url) &&
    TEXT_COLUMNS[catalogo].every((k) => text(r[k])) && (catalogo === "sectores" ? integer(r.subsectores) : true) &&
    (catalogo === "modalidades-cursado" || catalogo === "titulos-referencia" ? bool(r.activo) : true)) &&
  pageValid(v.page) && text(v.busqueda) && record(v.permisos) && bool(v.permisos.editar) && bool(v.permisos.eliminar) && listUrlsValid(v.urls) && messagesValid(v.messages) &&
  (catalogo !== "modalidades-cursado" || (filtersConfigValid(v.filters_config) && record(v.favorites) && text(v.favorites.section) && internal(v.favorites.url) && text(v.favorites.detail_url_template)));

export const catalogoDetailValid = (catalogo: Catalogo) => (v: unknown): v is CatalogoDetailData => record(v) && integer(v.id) && text(v.nombre) &&
  record(v.urls) && internal(v.urls.vat) && internal(v.urls.list) && internal(v.urls.update) && internal(v.urls.delete) && messagesValid(v.messages) &&
  (catalogo === "sectores" ? text(v.descripcion) && Array.isArray(v.subsectores) && v.subsectores.every(text) : true) &&
  (catalogo === "subsectores" ? text(v.descripcion) && record(v.sector) && text(v.sector.nombre) && internal(v.sector.url) : true) &&
  (catalogo === "modalidades-cursado" ? text(v.descripcion) && bool(v.activo) : true) &&
  (catalogo === "titulos-referencia" ? text(v.plan_estudio) && text(v.codigo) && bool(v.activo) && Array.isArray(v.planes) && v.planes.every(text) : true);

// `useMainResource` refetches when the validator changes: keep one per catalogo.
const CATALOGOS: Catalogo[] = ["sectores", "subsectores", "modalidades-cursado", "titulos-referencia"];
const LIST_VALID = Object.fromEntries(CATALOGOS.map((c) => [c, catalogoListValid(c)])) as Record<Catalogo, ReturnType<typeof catalogoListValid>>;
const DETAIL_VALID = Object.fromEntries(CATALOGOS.map((c) => [c, catalogoDetailValid(c)])) as Record<Catalogo, ReturnType<typeof catalogoDetailValid>>;

const ACTIVO = <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}Activo</span>;
const INACTIVO = <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}Inactivo</span>;

type Config = {
  title: string; search: string; placeholder: string; headers: { title: string; sortable?: { column: string }; notexport?: boolean }[]; sort: (r: Row) => string;
  empty: { title: string; text: string }; singular: string; cells: (r: Row, link: ReactNode) => ReactNode;
};
const link = (r: Row) => <a href={r.detail_url} className="link-handler" title="Ver detalles">{r.nombre}</a>;
const CONFIG: Record<Catalogo, Config> = {
  sectores: {
    title: "Sectores", search: "Buscar Sector", placeholder: "Buscar por nombre o descripción", singular: "sector",
    headers: [{ title: "Nombre", sortable: { column: "nombre" } }, { title: "Descripción" }, { title: "Subsectores" }, { title: "Acciones", notexport: true }], sort: (r) => r.nombre,
    empty: { title: "No se encontraron sectores", text: "No hay sectores registrados." },
    cells: (r, l) => <><td data-nombre={r.nombre}>{l}</td><td>{String(r.descripcion)}</td><td>{String(r.subsectores)}</td></>,
  },
  subsectores: {
    title: "Subsectores", search: "Buscar Subsector", placeholder: "Buscar por nombre o sector", singular: "subsector",
    headers: [{ title: "Sector", sortable: { column: "sector" } }, { title: "Nombre", sortable: { column: "nombre" } }, { title: "Descripción" }, { title: "Acciones", notexport: true }],
    sort: (r) => r.nombre, empty: { title: "No se encontraron subsectores", text: "No hay subsectores registrados." },
    cells: (r, l) => <><td data-sector={String(r.sector)}>{String(r.sector)}</td><td data-nombre={r.nombre}>{l}</td><td>{String(r.descripcion)}</td></>,
  },
  "modalidades-cursado": {
    title: "Modalidades de Cursado", search: "Buscar Modalidad de Cursado", placeholder: "", singular: "modalidad",
    headers: [{ title: "Nombre", sortable: { column: "nombre" } }, { title: "Descripción" }, { title: "Estado" }, { title: "Acciones", notexport: true }], sort: (r) => r.nombre,
    empty: { title: "No se encontraron modalidades de cursado", text: "No hay modalidades registradas." },
    cells: (r, l) => <><td data-nombre={r.nombre}>{l}</td><td>{String(r.descripcion)}</td><td>{r.activo ? ACTIVO : INACTIVO}</td></>,
  },
  "titulos-referencia": {
    title: "Títulos de Referencia", search: "Buscar Título de Referencia", placeholder: "Buscar por nombre, plan o código", singular: "título",
    headers: [{ title: "Nombre", sortable: { column: "nombre" } }, { title: "Plan de Estudio" }, { title: "Código" }, { title: "Estado" }, { title: "Acciones", notexport: true }], sort: (r) => r.nombre,
    empty: { title: "No se encontraron títulos de referencia", text: "No hay títulos registrados." },
    cells: (r, l) => <><td data-nombre={r.nombre}>{l}</td><td>{String(r.plan_estudio)}</td><td>{String(r.codigo)}</td><td>{r.activo ? ACTIVO : INACTIVO}</td></>,
  },
};
const sortKey = (catalogo: Catalogo, r: Row, column: string) => (column === "sector" ? String(r.sector) : CONFIG[catalogo].sort(r));

/** `components/search_bar.html` in filters mode (`filters_mode=True`) with Resetear and the add button. */
function FilterBar({ title, data }: { title: string; data: CatalogoListData }) {
  return <>
    <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
    <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
    <h2 className="text-center mb-4 poncho-titulo">{title}</h2>
    <Filters config={data.filters_config!} action={data.urls.list} favorites={data.favorites!} />
    <div className="row mt-3"><div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
      <a href={data.urls.list} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
      <a href={data.urls.create} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar</a>
    </div></div>
  </>;
}

export function CatalogoListContent({ catalogo, data }: { catalogo: Catalogo; data: CatalogoListData }) {
  const config = CONFIG[catalogo];
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    {catalogo === "modalidades-cursado"
      ? <FilterBar title={config.search} data={data} />
      : <VatSearchBar title={config.search} placeholder={config.placeholder} query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />}
    <VatTable headers={config.headers} rows={data.results} columns={config.headers.length} sortValue={(r, column) => sortKey(catalogo, r, column)} empty={config.empty}
      renderRow={(r) => <tr key={r.id}>
        {config.cells(r, link(r))}
        <td><div className="action-buttons" role="group">
          <a href={r.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
          {data.permisos.editar && <>{" "}<a href={r.update_url} className="btn btn-editar link-handler" title={`Editar ${config.singular}`}><i className="fas fa-edit" />{" "}Editar</a></>}
          {data.permisos.eliminar && <>{" "}<a href={r.delete_url} className="btn btn-eliminar link-handler" title={`Eliminar ${config.singular}`}><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
        </div></td>
      </tr>} />
    <VatPagination page={data.page} shown={data.results.length} />
  </>;
}

const API = (catalogo: Catalogo) => `web/vat/catalogos/${catalogo}/`;

function ListPage({ catalogo }: { catalogo: Catalogo }) {
  const [state] = useMainResource(`${API(catalogo)}${window.location.search}`, LIST_VALID[catalogo]);
  return renderMain(state, "Cargando listado…", (data) => ({ title: CONFIG[catalogo].title, breadcrumb: null, content: <CatalogoListContent catalogo={catalogo} data={data} /> }));
}

const DETAIL_TITLE: Record<Catalogo, string> = {
  sectores: "Detalle Sector", subsectores: "Detalle Subsector", "modalidades-cursado": "Detalle Modalidad de Cursado", "titulos-referencia": "Detalle Título",
};
const CRUMB: Record<Catalogo, string> = { sectores: "Sectores", subsectores: "Subsectores", "modalidades-cursado": "Modalidades de Cursado", "titulos-referencia": "Títulos" };

function DeleteForm({ endpoint, forbidden }: { endpoint: string; forbidden: (d: unknown) => void }) {
  const busy = useRef(false);
  async function submit(event: { preventDefault: () => void }) {
    event.preventDefault();
    // `onsubmit="return confirm('¿Está seguro?')"` of the native form.
    if (busy.current || !vatNavigation.confirm("¿Está seguro?")) return;
    busy.current = true;
    const result = await postForm(endpoint, new URLSearchParams());
    busy.current = false;
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
  }
  return <form method="post" action={endpoint} style={{ display: "inline" }} onSubmit={(e) => void submit(e)}>
    <CsrfInput />
    <button type="submit" className="btn btn-sm btn-danger"><i className="fas fa-trash" /></button>
  </form>;
}

/** Native `card-tools`: the delete is a confirming POST form in the sector and title pages, a plain link in the others. */
function Tools({ catalogo, data, endpoint, forbidden }: { catalogo: Catalogo; data: CatalogoDetailData; endpoint: string; forbidden: (d: unknown) => void }) {
  return <div className="card-tools">
    <a href={data.urls.update} className="btn btn-sm btn-warning"><i className="fas fa-edit" /></a>{" "}
    {catalogo === "sectores" || catalogo === "titulos-referencia"
      ? <DeleteForm endpoint={endpoint} forbidden={forbidden} />
      : <a href={data.urls.delete} className="btn btn-sm btn-danger"><i className="fas fa-trash" /></a>}
  </div>;
}

export function CatalogoDetailContent({ catalogo, data, forbidden }: { catalogo: Catalogo; data: CatalogoDetailData; forbidden: (d: unknown) => void }) {
  const endpoint = `${API(catalogo)}${data.id}/eliminar/`;
  let body: ReactNode;
  if (catalogo === "sectores") {
    const subs = data.subsectores ?? [];
    body = <>
      <p><strong>Descripción:</strong></p>
      <p>{data.descripcion}</p>
      <hr />
      <h5>Subsectores ({subs.length})</h5>
      {subs.length ? <ul>{subs.map((s, n) => <li key={n}>{s}</li>)}</ul> : <p className="text-muted">Sin subsectores</p>}
    </>;
  } else if (catalogo === "subsectores") {
    body = <>
      <p><strong>Sector:</strong>{" "}<a href={data.sector!.url}>{data.sector!.nombre}</a></p>
      <p><strong>Descripción:</strong></p>
      <p>{data.descripcion}</p>
    </>;
  } else if (catalogo === "modalidades-cursado") {
    body = <>
      <p><strong>Descripción:</strong></p>
      <p>{data.descripcion}</p>
      <p><strong>Activo:</strong>{" "}{data.activo ? "Sí" : "No"}</p>
    </>;
  } else {
    const planes = data.planes ?? [];
    body = <>
      <dl className="row">
        <dt className="col-sm-3">Plan de Estudio:</dt>
        <dd className="col-sm-9">{data.plan_estudio}</dd>
        <dt className="col-sm-3">Código:</dt>
        <dd className="col-sm-9">{data.codigo}</dd>
        <dt className="col-sm-3">Estado:</dt>
        <dd className="col-sm-9">{data.activo ? <span className="badge badge-success">Activo</span> : <span className="badge badge-danger">Inactivo</span>}</dd>
      </dl>
      <hr />
      <h5>Planes de Estudio ({planes.length})</h5>
      {planes.length ? <ul>{planes.map((p, n) => <li key={n}>{p}</li>)}</ul> : <p className="text-muted">Sin planes</p>}
    </>;
  }
  return <>
    <NativeToasts messages={data.messages} />
    <div className="row"><div className="col-md-8"><div className="card">
      <div className="card-header bg-primary text-white">
        <h3 className="card-title">{data.nombre}</h3>
        <Tools catalogo={catalogo} data={data} endpoint={endpoint} forbidden={forbidden} />
      </div>
      <div className="card-body">{body}</div>
    </div></div></div>
  </>;
}

function DetailPage({ catalogo, id }: { catalogo: Catalogo; id: string }) {
  const [state, setState] = useMainResource(`${API(catalogo)}${id}/`, DETAIL_VALID[catalogo]);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando detalle…", (data) => ({
    title: DETAIL_TITLE[catalogo],
    breadcrumb: <Breadcrumb items={[
      ...(catalogo === "titulos-referencia" ? [] : [{ text: "VAT", url: data.urls.vat }]),
      { text: CRUMB[catalogo], url: data.urls.list }, { text: data.nombre, url: null },
    ]} />,
    content: <CatalogoDetailContent catalogo={catalogo} data={data} forbidden={forbidden} />,
  }));
}

type Params = { catalogo: Catalogo; id?: string };

// Native URLs of `VAT/urls.py`; `nuevo|nueva/`, `<id>/editar/` and `<id>/eliminar/` belong to the form module.
const PATH = /^\/vat\/catalogos\/(sectores|subsectores|modalidades-cursado|titulos-referencia)\/(?:([0-9]+)\/)?$/;

export const vatCatalogosRoute: RouteDefinition<Params> = {
  name: "vat-catalogos",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { catalogo: m[1] as Catalogo, id: m[2] } : null;
  },
  render({ catalogo, id }) {
    return id ? <DetailPage key={`${catalogo}:${id}`} catalogo={catalogo} id={id} /> : <ListPage key={catalogo} catalogo={catalogo} />;
  },
};
