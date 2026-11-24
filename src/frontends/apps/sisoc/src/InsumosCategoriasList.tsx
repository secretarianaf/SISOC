import { useEffect, useState } from "react";
import { crearCliente, SinPermiso } from "@sisoc/api";
import InsumosAccessError from "./InsumosAccessError";
import { pageRange } from "./insumosPagination";
import { InsumosForbiddenError, rejectInsumosForbidden, validateInsumosStatus, type WebPrerequisite } from "./webAccess";

type Row = { id: number; nombre: string; programa: string; orden: number; activo: boolean };
type Page = { count: number; page: number; page_size: number; pages: number; capabilities: { can_add: boolean; can_change: boolean; can_delete: boolean }; results: Row[] };
type State = { status: "loading" } | { status: "ready"; data: Page } | { status: "error"; forbidden: boolean; prerequisite?: WebPrerequisite | null };
const client = crearCliente("/api");
const LIST = "/v2/sisoc/insumos/categorias/";
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";
function isPage(value: unknown): value is Page {
  if (!record(value) || !record(value.capabilities) || !Array.isArray(value.results)) return false;
  const permissions = value.capabilities;
  return ["count", "page", "page_size", "pages"].every((name) => Number.isSafeInteger(value[name]) && Number(value[name]) >= 0) &&
    ["can_add", "can_change", "can_delete"].every((name) => typeof permissions[name] === "boolean") &&
    value.results.every((row) => record(row) && Number.isSafeInteger(row.id) && Number(row.id) > 0 && typeof row.nombre === "string" && typeof row.programa === "string" && Number.isSafeInteger(row.orden) && typeof row.activo === "boolean");
}

export default function InsumosCategoriasList() {
  const [state, setState] = useState<State>({ status: "loading" });
  const search = window.location.search;
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    rejectInsumosForbidden(client.get(`web/insumos/categorias/${search}`, { signal: controller.signal, validateStatus: validateInsumosStatus }))
      .then(({ data }: { data: unknown }) => {
        if (!current) return;
        if (!isPage(data)) throw new Error("Invalid category list");
        setState({ status: "ready", data });
      }).catch((error: unknown) => {
        if (!current) return;
        setState({ status: "error", forbidden: error instanceof SinPermiso || (error as { response?: { status?: number } })?.response?.status === 403, prerequisite: error instanceof InsumosForbiddenError ? error.prerequisite : null });
      });
    return () => { current = false; controller.abort(); };
  }, [search]);
  if (state.status === "loading") return <div className="list-container" role="status">Cargando categorías…</div>;
  if (state.status === "error") return state.forbidden ? <InsumosAccessError prerequisite={state.prerequisite} /> : <div className="list-container"><div className="alert alert-danger" role="alert">No se pudieron cargar las categorías.</div></div>;
  const { data } = state;
  const pageHref = (page: number) => { const query = new URLSearchParams(search); query.set("page", String(page)); return `${LIST}?${query}`; };
  return <><link rel="stylesheet" href="/static/custom/css/listModerno.css" /><div className="list-container">
    <div className="d-flex flex-wrap justify-content-between align-items-center mb-3"><h2 className="mb-2">Categorías de insumos</h2><div className="d-flex gap-2">{data.capabilities.can_add && <a href={`${LIST}crear`} className="btn btn-success"><i className="fas fa-plus" aria-hidden="true" /> Agregar categoría</a>}</div></div>
    <div className="card comedor-table-card"><div className="card-body"><div className="table-responsive-lg"><table className="table table-comedor-moderno">
      <thead><tr><th>Nombre</th><th>Programa</th><th>Orden</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody>{data.results.length ? data.results.map((row) => <tr key={row.id}><td>{row.nombre}</td><td>{row.programa}</td><td>{row.orden}</td><td><span className={`badge ${row.activo ? "bg-success" : "bg-secondary"}`}>{row.activo ? "Activa" : "Inactiva"}</span></td><td><div className="comedor-actions">
        {data.capabilities.can_change && <a href={`${LIST}${row.id}/editar`} className="btn btn-editar" title="Editar"><i className="fas fa-edit" aria-hidden="true" /> Editar</a>}
        {data.capabilities.can_delete && <a href={`${LIST}${row.id}/eliminar`} className="btn btn-eliminar" title="Eliminar"><i className="fas fa-trash-alt" aria-hidden="true" /> Eliminar</a>}
      </div></td></tr>) : <tr><td colSpan={5}><div className="no-data-message"><h3>No hay categorías</h3><p>Todavía no se crearon categorías de insumos.</p></div></td></tr>}</tbody>
    </table></div></div></div>
    <div className="mt-2">{data.pages > 1 && <ul className="pagination">
      <li className={`page-item${data.page <= 1 ? " disabled" : ""}`}><a href={data.page > 1 ? pageHref(data.page - 1) : "#"} className="page-link">Volver</a></li>
      {pageRange(data.page, data.pages).map((page, index) => <li key={`${page}-${index}`} className={`page-item${typeof page === "string" ? " disabled" : page === data.page ? " active" : ""}`}><a href={typeof page === "number" ? pageHref(page) : "#"} className="page-link">{typeof page === "number" ? page : "..."}</a></li>)}
      <li className={`page-item${data.page >= data.pages ? " disabled" : ""}`}><a href={data.page < data.pages ? pageHref(data.page + 1) : "#"} className="page-link">Continuar</a></li>
    </ul>}<p className="text-center text-muted mb-0 mt-1">Se encontraron {data.count} resultados</p></div>
  </div></>;
}
