/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { NativeToasts } from "./nativeParity";
import { Pagination } from "./listControls";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { count, messagesValid, paginationValid, urlsValid, type CoreMessage, type CorePagination } from "./coreCommon";
import type { RouteDefinition } from "./types";

/**
 * T05.01: `programa_list.html` and `programa_detail.html`. GET `/api/web/core/programas/` (`?page`) and
 * `/api/web/core/programas/<pk>/` run `ProgramaListView` / `ProgramaDetailView`; access is the current one
 * (any authenticated user, decision 2026-11-10). Every link goes to its native route.
 */
type Urls = { detail: string; edit: string; delete: string };
export type ProgramasListData = {
  items: { id: number; nombre: string; organismo: string | null; estado: boolean; urls: Urls }[];
  urls: { create: string }; pagination: CorePagination; messages: CoreMessage[];
};
export type ProgramaDetailData = {
  id: number; nombre: string; estado: boolean; organismo: string | null; observaciones: string | null; descripcion: string | null;
  urls: { list: string } & Urls; messages: CoreMessage[];
};

const nullableText = (v: unknown) => v === null || text(v);
const rowUrls = (v: unknown) => urlsValid(v, ["detail", "edit", "delete"]);

export const programasListValid = (v: unknown): v is ProgramasListData =>
  record(v) && messagesValid(v.messages) && paginationValid(v.pagination) && urlsValid(v.urls, ["create"]) &&
  Array.isArray(v.items) && v.items.every((i) => record(i) && count(i.id) && text(i.nombre) && nullableText(i.organismo) && typeof i.estado === "boolean" && rowUrls(i.urls));

export const programaDetailValid = (v: unknown): v is ProgramaDetailData =>
  record(v) && count(v.id) && text(v.nombre) && typeof v.estado === "boolean" && nullableText(v.organismo) && nullableText(v.observaciones) &&
  nullableText(v.descripcion) && messagesValid(v.messages) && urlsValid(v.urls, ["list", "detail", "edit", "delete"]);

/** `{{ value|default:"-" }}`. */
const orDash = (v: string | null) => (v ? v : "-");

export function ProgramasListContent({ data, search = "" }: { data: ProgramasListData; search?: string }) {
  const p = data.pagination;
  // `request.GET` keeps every other parameter, only `page` changes.
  const href = (page: number) => {
    const params = new URLSearchParams(search);
    params.delete("page");
    params.append("page", String(page));
    return `?${params.toString()}`;
  };
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="action-bar mb-3">
        <a href={data.urls.create} className="btn btn-primary">
          <i className="fas fa-plus" />{" "}
          Agregar
        </a>
      </div>
      <div className="row mt-3">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <table className="table table-bordered table-striped">
                <thead>
                  <tr><th>Nombre</th><th>Organismo</th><th>Estado</th><th>Acciones</th></tr>
                </thead>
                <tbody>
                  {data.items.map((programa) => (
                    <tr key={programa.id}>
                      <td>{programa.nombre}</td>
                      <td>{orDash(programa.organismo)}</td>
                      <td>{programa.estado ? <span className="badge badge-success">Activo</span> : <span className="badge badge-secondary">Inactivo</span>}</td>
                      <td>
                        <a href={programa.urls.detail} className="btn btn-sm btn-info">Ver</a>{" "}
                        <a href={programa.urls.edit} className="btn btn-sm btn-warning">Editar</a>{" "}
                        <a href={programa.urls.delete} className="btn btn-sm btn-danger">Eliminar</a>
                      </td>
                    </tr>
                  ))}
                  {data.items.length === 0 && <tr><td colSpan={4} className="text-center">No hay programas registrados.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <Pagination paginated={p.paginated} number={p.number} previous={p.previous} next={p.next} range={p.range} href={href} count={p.count} />
    </>
  );
}

export function ProgramaDetailContent({ data }: { data: ProgramaDetailData }) {
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row">
        <div className="col-md-8">
          <div className="card">
            <div className="card-header bg-primary text-white">
              <h3 className="card-title">{data.nombre}</h3>
              <div className="card-tools">
                <a href={data.urls.edit} className="btn btn-sm btn-warning"><i className="fas fa-edit" />{" "}Editar</a>{" "}
                <a href={data.urls.delete} className="btn btn-sm btn-danger"><i className="fas fa-trash" />{" "}Eliminar</a>
              </div>
            </div>
            <div className="card-body">
              <p><strong>Estado:</strong>{" "}{data.estado ? "Activo" : "Inactivo"}</p>
              <p><strong>Organismo:</strong>{" "}{orDash(data.organismo)}</p>
              <p><strong>Observaciones:</strong>{" "}{orDash(data.observaciones)}</p>
              <p><strong>Descripción:</strong></p>
              <p>{orDash(data.descripcion)}</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// The templates define `title` but no `titulo-pagina`: the heading row is empty. The breadcrumb block is
// itself an `<ol>` placed inside the shell's `<ol>`, and the nested list is kept.
function ListPage() {
  const [state] = useMainResource(`web/core/programas/${window.location.search}`, programasListValid);
  return renderMain(state, "Cargando programas…", (data) => ({
    title: "Programas",
    activePath: "programas/",
    breadcrumb: <ol className="breadcrumb float-sm-right"><li className="breadcrumb-item active">Programas</li></ol>,
    content: <ProgramasListContent data={data} search={window.location.search} />,
  }));
}

function DetailPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`web/core/programas/${pk}/`, programaDetailValid);
  return renderMain(state, "Cargando programa…", (data) => ({
    title: "Detalle Programa",
    activePath: "programas/<int:pk>/",
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <li className="breadcrumb-item"><a href={internal(data.urls.list) ? data.urls.list : "/programas/"}>Programas</a></li>
        <li className="breadcrumb-item active">{data.nombre}</li>
      </ol>
    ),
    content: <ProgramaDetailContent data={data} />,
  }));
}

type Params = { mode: "list" } | { mode: "detail"; pk: string };

export const coreProgramasRoute: RouteDefinition<Params> = {
  name: "core-programas",
  match(pathname) {
    if (pathname === "/programas/") return { mode: "list" };
    const found = /^\/programas\/([0-9]+)\/$/.exec(pathname);
    return found ? { mode: "detail", pk: found[1] } : null;
  },
  render: (params) => (params.mode === "list" ? <ListPage /> : <DetailPage pk={params.pk} />),
};
