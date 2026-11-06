import { useLegacyScrollHints } from "./useLegacyScrollHints";
import { pageRange } from "./insumosPagination";
import {
  useEffect,
  useState,
  type FormEvent,
  type MouseEvent,
} from "react";
import { crearCliente, mensajeDeError, SinPermiso } from "@sisoc/api";
import InsumosAccessError from "./InsumosAccessError";
import {
  InsumosForbiddenError,
  rejectInsumosForbidden,
  validateInsumosStatus,
  type WebPrerequisite,
} from "./webAccess";

type CategoryOption = { id: number; nombre: string };
type InsumoRow = {
  id: number;
  titulo: string;
  activo: boolean;
  categoria: string;
  fecha_carga: string;
  cargado_por: string;
  download_url: string;
};
type InsumosPage = {
  count: number;
  page: number;
  page_size: number;
  pages: number;
  filters: { busqueda: string; categoria: string };
  results: InsumoRow[];
};
type LoadState =
  | { status: "loading" }
  | { status: "ready"; requestKey: string; categories: CategoryOption[]; page: InsumosPage }
  | { status: "error"; requestKey: string; message: string; forbidden: boolean; statusCode?: number; prerequisite?: WebPrerequisite | null };

const webClient = crearCliente("/api");
const LIST_PATH = "/v2/sisoc/insumos/";
const SIN_CATEGORIA = "sin";

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object";
}

function isNonnegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function isPositiveInteger(value: unknown): value is number {
  return isNonnegativeInteger(value) && value > 0;
}

function internalHref(value: unknown): value is string {
  if (
    typeof value !== "string" ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\")
  ) {
    return false;
  }
  try {
    return new URL(value, window.location.origin).origin === window.location.origin;
  } catch {
    return false;
  }
}

function isCategoryOption(value: unknown): value is CategoryOption {
  return (
    isRecord(value) &&
    isPositiveInteger(value.id) &&
    typeof value.nombre === "string"
  );
}

function isOptionsResponse(value: unknown): value is { categories: CategoryOption[] } {
  return isRecord(value) && Array.isArray(value.categories) && value.categories.every(isCategoryOption);
}

function isInsumoRow(value: unknown): value is InsumoRow {
  return (
    isRecord(value) &&
    isPositiveInteger(value.id) &&
    typeof value.titulo === "string" &&
    typeof value.activo === "boolean" &&
    typeof value.categoria === "string" &&
    typeof value.fecha_carga === "string" &&
    typeof value.cargado_por === "string" &&
    internalHref(value.download_url)
  );
}

function isInsumosPage(value: unknown): value is InsumosPage {
  if (!isRecord(value) || !isRecord(value.filters)) return false;
  return (
    isNonnegativeInteger(value.count) &&
    isPositiveInteger(value.page) &&
    isPositiveInteger(value.page_size) &&
    isNonnegativeInteger(value.pages) &&
    typeof value.filters.busqueda === "string" &&
    typeof value.filters.categoria === "string" &&
    Array.isArray(value.results) &&
    value.results.every(isInsumoRow)
  );
}

function pageHref(search: string, category: string, page?: number): string {
  const params = new URLSearchParams();
  if (search) params.set("busqueda", search);
  if (category) params.set("categoria", category);
  if (page !== undefined) params.set("page", String(page));
  const query = params.toString();
  return `${LIST_PATH}${query ? `?${query}` : ""}`;
}

function useListLocation() {
  const [search, setSearch] = useState(() => window.location.search);
  useEffect(() => {
    const syncLocation = () => setSearch(window.location.search);
    window.addEventListener("popstate", syncLocation);
    return () => window.removeEventListener("popstate", syncLocation);
  }, []);
  const navigate = (url: string) => {
    if (!internalHref(url)) return;
    window.history.pushState({}, "", url);
    setSearch(window.location.search);
  };
  return { search, navigate };
}

function isPlainNavigation(event: MouseEvent<HTMLAnchorElement>): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

function internalNavigation(navigate: (url: string) => void, href: string) {
  return (event: MouseEvent<HTMLAnchorElement>) => {
    if (!isPlainNavigation(event)) return;
    event.preventDefault();
    navigate(href);
  };
}

export default function InsumosList({
  showManagement,
  showCategories,
}: {
  showManagement: boolean;
  showCategories: boolean;
}) {
  const { search: locationSearch, navigate } = useListLocation();
  const searchParams = new URLSearchParams(locationSearch);
  const busqueda = (searchParams.get("busqueda") ?? "").trim();
  const categoria = (searchParams.get("categoria") ?? "").trim();
  const pageParam = searchParams.get("page");
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const requestKey = JSON.stringify([busqueda, categoria, pageParam, reloadKey]);

  useEffect(() => {
    let current = true;
    const controller = new AbortController();
    const params: Record<string, string | number> = {};
    if (busqueda) params.busqueda = busqueda;
    if (categoria) params.categoria = categoria;
    if (pageParam !== null && pageParam !== "1") params.page = pageParam;

    Promise.all([
      rejectInsumosForbidden(webClient.get<unknown>("web/insumos/options/", {
        signal: controller.signal,
        validateStatus: validateInsumosStatus,
      })),
      rejectInsumosForbidden(webClient.get<unknown>("web/insumos/", {
        params,
        signal: controller.signal,
        validateStatus: validateInsumosStatus,
      })),
    ])
      .then(([optionsResponse, pageResponse]) => {
        if (!current) return;
        if (!isOptionsResponse(optionsResponse.data) || !isInsumosPage(pageResponse.data)) {
          setState({
            status: "error",
            requestKey,
            message: "El servidor devolvió una respuesta inválida.",
            forbidden: false,
            prerequisite: null,
          });
          return;
        }
        setState({
          status: "ready",
          requestKey,
          categories: optionsResponse.data.categories,
          page: pageResponse.data,
        });
      })
      .catch((error: unknown) => {
        if (!current || controller.signal.aborted) return;
        const statusCode =
          isRecord(error) && isRecord(error.response) && typeof error.response.status === "number"
            ? error.response.status
            : undefined;
        setState({
          status: "error",
          requestKey,
          message: error instanceof SinPermiso ? error.message : mensajeDeError(error),
          forbidden: error instanceof SinPermiso || statusCode === 403,
          statusCode,
          prerequisite: error instanceof InsumosForbiddenError ? error.prerequisite : null,
        });
      });

    return () => {
      current = false;
      controller.abort();
    };
  }, [busqueda, categoria, pageParam, reloadKey, requestKey]);

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const search = String(values.get("busqueda") ?? "").trim();
    const selectedCategory = String(values.get("categoria") ?? "").trim();
    navigate(pageHref(search, selectedCategory));
  };
  const reset = internalNavigation(navigate, LIST_PATH);
  const renderActions = (
    <div className="row mt-3">
      <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
      <a className="poncho-btn poncho-btn--neutro" href={LIST_PATH} onClick={reset}>
        Resetear
      </a>
      {showManagement && (
        <a className="poncho-btn poncho-btn--cta" href={`${LIST_PATH}crear/`}>
          <i className="fas fa-plus" aria-hidden="true" /> Agregar insumo
        </a>
      )}
      {showCategories && (
        <a className="poncho-btn poncho-btn--neutro" href={`${LIST_PATH}categorias/`}>
          Categorías
        </a>
      )}
      </div>
    </div>
  );

  const visibleState =
    state.status !== "loading" && state.requestKey !== requestKey
      ? ({ status: "loading" } as const)
      : state;
  const categories = visibleState.status === "ready" ? visibleState.categories : [];
  const visibleCategory =
    categoria === SIN_CATEGORIA || categories.some((item) => String(item.id) === categoria)
      ? categoria
      : "";
  const { cardRef, tableRef, classes: scrollClasses } = useLegacyScrollHints(
    visibleState.status === "ready" ? visibleState.requestKey : null,
  );

  if (visibleState.status === "error" && visibleState.statusCode === 403) {
    return <InsumosAccessError prerequisite={visibleState.prerequisite} />;
  }

  return (
    <>
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
    <div className="list-container sisoc-insumos-list">
      <h2 className="text-center mb-4 poncho-titulo">Buscar insumos</h2>
      <form id="insumos-search-form" key={locationSearch} onSubmit={handleSearch}>
        <div className="poncho-search poncho-search--solo">
          <div className="poncho-search__box">
            <input
              type="search"
              name="busqueda"
              className="poncho-search__input"
              placeholder="Buscar por título o descripción"
              title="Buscar por título o descripción."
              aria-label="Buscar por título o descripción"
              autoComplete="off"
              defaultValue={busqueda}
            />
            <button type="submit" className="poncho-search__go" aria-label="Buscar">
              <i className="fas fa-search" aria-hidden="true" />
            </button>
          </div>
        </div>
        <div className="poncho-search__meta">
          <span />
        </div>
      </form>
      {renderActions}
      <div className="poncho-filtros-modulo">
        <label htmlFor="categoria" className="mb-0">
          Categoría
        </label>
        <select
          key={visibleState.status}
          name="categoria"
          id="categoria"
          form="insumos-search-form"
          className="form-select"
          defaultValue={visibleCategory}
        >
          <option value="">Todas las categorías</option>
          <option value={SIN_CATEGORIA}>Sin categoría</option>
          {categories.map((item) => (
            <option key={item.id} value={String(item.id)}>
              {item.nombre}
            </option>
          ))}
        </select>
      </div>

      {visibleState.status === "loading" && (
        <p className="text-center py-4" role="status">
          Cargando insumos…
        </p>
      )}
      {visibleState.status === "error" && (
        <div className="alert alert-danger" role="alert">
          <p>{visibleState.forbidden ? visibleState.message : "No se pudieron cargar los insumos."}</p>
          {visibleState.statusCode === 404 && <p>{visibleState.message}</p>}
          {!visibleState.forbidden && (
            <button type="button" className="btn btn-ver" onClick={() => setReloadKey((key) => key + 1)}>
              Reintentar
            </button>
          )}
        </div>
      )}
      {visibleState.status === "ready" && (
        <>
          <div className="card comedor-table-card">
            <div className={`card-body ${scrollClasses.card}`} ref={cardRef}>
              <div className={`table-responsive-lg ${scrollClasses.table}`} ref={tableRef}>
                <table className="table table-comedor-moderno">
                  <thead>
                    <tr>
                      <th scope="col">Título</th>
                      <th scope="col">Categoría</th>
                      <th scope="col">Fecha de carga</th>
                      <th scope="col">Cargado por</th>
                      <th scope="col">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleState.page.results.map((item) => (
                      <tr key={item.id}>
                        <td>
                          {item.titulo}
                          {!item.activo && (
                            <>
                              {" "}
                              <span className="badge bg-secondary">Inactivo</span>
                            </>
                          )}
                        </td>
                        <td>{item.categoria}</td>
                        <td>{item.fecha_carga}</td>
                        <td>{item.cargado_por}</td>
                        <td>
                          <div className="comedor-actions">
                            <a className="btn btn-ver" href={item.download_url} title="Descargar">
                              <i className="fas fa-download" aria-hidden="true" /> Descargar
                            </a>
                            {showManagement && (
                              <>
                                <a
                                  className="btn btn-editar"
                                  href={`${LIST_PATH}${item.id}/editar/`}
                                  title="Editar"
                                >
                                  <i className="fas fa-edit" aria-hidden="true" /> Editar
                                </a>
                                <a
                                  className="btn btn-eliminar"
                                  href={`${LIST_PATH}${item.id}/eliminar/`}
                                  title="Eliminar"
                                >
                                  <i className="fas fa-trash-alt" aria-hidden="true" /> Eliminar
                                </a>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {visibleState.page.results.length === 0 && (
                      <tr>
                        <td colSpan={5}>
                          <div className="no-data-message">
                            <h3>No se encontraron insumos</h3>
                            <p>No hay insumos que coincidan con los criterios de búsqueda.</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <Pagination page={visibleState.page} onNavigate={navigate} />
        </>
      )}
    </div>
    </>
  );
}

function Pagination({
  page,
  onNavigate,
}: {
  page: InsumosPage;
  onNavigate: (url: string) => void;
}) {
  if (page.pages <= 1) {
    return (
      <div className="mt-2">
        {page.count > 0 && (
          <p className="text-center text-muted mb-0 mt-1">Se encontraron {page.count} resultados</p>
        )}
      </div>
    );
  }
  const current = Math.min(Math.max(page.page, 1), page.pages);
  const hrefFor = (number: number) => pageHref(page.filters.busqueda, page.filters.categoria, number);
  return (
    <div className="mt-2">
      <ul className="pagination">
        <li className={`page-item${current <= 1 ? " disabled" : ""}`}>
          {current > 1 ? (
            <a className="page-link" href={hrefFor(current - 1)} onClick={internalNavigation(onNavigate, hrefFor(current - 1))}>
              Volver
            </a>
          ) : (
            <span className="page-link" aria-disabled="true">
              Volver
            </span>
          )}
        </li>
        {pageRange(current, page.pages).map((number, index) => (
          <li className={`page-item${number === current ? " active" : ""}`} key={`${number}-${index}`}>
            {number === "…" ? (
              <span className="page-link" aria-hidden="true">
                …
              </span>
            ) : (
              <a
                className="page-link"
                href={hrefFor(number)}
                aria-current={number === current ? "page" : undefined}
                onClick={internalNavigation(onNavigate, hrefFor(number))}
              >
                {number}
              </a>
            )}
          </li>
        ))}
        <li className={`page-item${current >= page.pages ? " disabled" : ""}`}>
          {current < page.pages ? (
            <a className="page-link" href={hrefFor(current + 1)} onClick={internalNavigation(onNavigate, hrefFor(current + 1))}>
              Continuar
            </a>
          ) : (
            <span className="page-link" aria-disabled="true">
              Continuar
            </span>
          )}
        </li>
      </ul>
      {page.count > 0 && <p className="text-center text-muted mb-0 mt-1">Se encontraron {page.count} resultados</p>}
    </div>
  );
}
