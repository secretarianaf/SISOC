/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { NativeToasts } from "./nativeParity";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { count, messagesValid, strings, urlsValid, type CoreMessage } from "./coreCommon";
import type { RouteDefinition } from "./types";

/**
 * T06.01: `core/trash_list.html`. GET `/api/web/core/papelera/` (the page's own query string) runs the same
 * filter form, search, date range, ordering and 25-per-page pagination as `TrashListView`; superusers only
 * (403 for anyone else). The filter form is a plain GET form, so "Aplicar" reloads the page like the native one.
 */
type Filter = { id: string; label: string; value: string; attrs: Record<string, string>; choices?: { value: string; label: string }[] };
const NAMES = ["model", "q", "deleted_by", "deleted_from", "deleted_to"] as const;
export type PapeleraData = {
  filters: Record<(typeof NAMES)[number], Filter>; filter_errors: string[]; active_filters: { label: string; value: string }[];
  selected_model_label: string; show_all_models: boolean; deleted_count: number;
  rows: { id: number; label: string; model_label: string; deleted_at: string; deleted_by: string | null; restore_url: string }[];
  pagination: { num_pages: number; number: number; previous: number | null; next: number | null; querystring: string };
  urls: { list: string; home: string }; messages: CoreMessage[];
};

const filterValid = (f: unknown): f is Filter =>
  record(f) && text(f.id) && text(f.label) && text(f.value) && record(f.attrs) && Object.values(f.attrs).every(text) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));

export const papeleraValid = (v: unknown): v is PapeleraData => {
  if (!record(v) || !record(v.filters) || !NAMES.every((n) => filterValid((v.filters as Record<string, unknown>)[n]))) return false;
  const p = v.pagination;
  return strings(v.filter_errors) && messagesValid(v.messages) && urlsValid(v.urls, ["list", "home"]) &&
    Array.isArray(v.active_filters) && v.active_filters.every((a) => record(a) && text(a.label) && text(a.value)) &&
    text(v.selected_model_label) && typeof v.show_all_models === "boolean" && count(v.deleted_count) &&
    Array.isArray(v.rows) && v.rows.every((r) => record(r) && count(r.id) && text(r.label) && text(r.model_label) && text(r.deleted_at) && (r.deleted_by === null || text(r.deleted_by)) && internal(r.restore_url)) &&
    record(p) && count(p.num_pages) && count(p.number) && (p.previous === null || count(p.previous)) && (p.next === null || count(p.next)) && text(p.querystring);
};

function Input({ filter, name }: { filter: Filter; name: string }) {
  const a = filter.attrs;
  if (filter.choices) {
    return (
      <select name={name} className={a.class} id={filter.id} defaultValue={filter.value}>
        {filter.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
    );
  }
  return <input type={a.type ?? "text"} name={name} className={a.class} placeholder={a.placeholder} id={filter.id} defaultValue={filter.value} />;
}

export function PapeleraContent({ data }: { data: PapeleraData }) {
  const f = data.filters;
  const p = data.pagination;
  const more = p.querystring ? `&${p.querystring}` : "";
  const col = (name: (typeof NAMES)[number], size: string, hint?: string) => (
    <div className={size}>
      <label htmlFor={f[name].id}>{f[name].label}:</label>{" "}
      <Input filter={f[name]} name={name} />
      {hint && <small className="form-text text-muted">{hint}</small>}
    </div>
  );
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row">
        <div className="col-12">
          <div className="card mb-3">
            <div className="card-header"><h3 className="card-title">Filtros</h3></div>
            <div className="card-body">
              <form method="get" className="row g-3">
                {col("model", "col-md-4")}
                {col("q", "col-md-4", "Busca por ID o texto del registro eliminado.")}
                {col("deleted_by", "col-md-4", "Filtra por usuario o nombre de quien eliminó.")}
                {col("deleted_from", "col-md-3")}
                {col("deleted_to", "col-md-3")}
                <div className="col-md-6 d-flex align-items-end gap-2">
                  <button className="btn btn-primary" type="submit">Aplicar</button>
                  <a href={data.urls.list} className="btn btn-outline-secondary">Limpiar</a>
                </div>
              </form>
              {data.filter_errors.length > 0 && (
                <div className="alert alert-warning mt-3 mb-0">
                  {data.filter_errors.map((line) => <div key={line}>{line}</div>)}
                </div>
              )}
              {data.active_filters.length > 0 && (
                <div className="mt-3" aria-label="Resumen de filtros activos">
                  <span className="small text-muted me-2">Filtros activos:</span>{" "}
                  {data.active_filters.map((item) => (
                    <span key={item.label}><span className="badge bg-light text-dark border me-1 mb-1">{item.label}: {item.value}</span>{" "}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
              <div className="d-flex align-items-center gap-2">
                <span className="fw-semibold">{data.selected_model_label}</span>
                {data.show_all_models && <span className="badge bg-info text-dark">Listado combinado</span>}
              </div>
              <span className="badge bg-secondary">Eliminados: {data.deleted_count}</span>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="table table-hover table-striped mb-0">
                  <thead>
                    <tr><th>ID</th><th>Registro</th><th>Eliminado en</th><th>Eliminado por</th><th className="text-end">Acción</th></tr>
                  </thead>
                  <tbody>
                    {data.rows.map((row) => (
                      <tr key={`${row.model_label}-${row.id}`}>
                        <td>{row.id}</td>
                        <td>
                          {row.label}
                          <div className="small text-muted">{row.model_label}</div>
                        </td>
                        <td>{row.deleted_at}</td>
                        <td>{row.deleted_by ?? <span className="text-muted">-</span>}</td>
                        <td className="text-end"><a href={row.restore_url} className="btn btn-sm btn-outline-success">Restaurar</a></td>
                      </tr>
                    ))}
                    {data.rows.length === 0 && (
                      <tr>
                        <td colSpan={5} className="text-center py-4">
                          <div className="fw-semibold">No hay registros eliminados para este modelo.</div>
                          <div className="small text-muted mt-1">Ajustá los filtros o usá “Limpiar” para volver al listado completo.</div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            {p.num_pages > 1 && (
              <div className="card-footer">
                <nav aria-label="Paginación de papelera">
                  <ul className="pagination mb-0 justify-content-center">
                    {p.previous !== null && <li className="page-item"><a className="page-link" href={`?page=${p.previous}${more}`}>Anterior</a></li>}
                    <li className="page-item disabled"><span className="page-link">Página {p.number} de {p.num_pages}</span></li>
                    {p.next !== null && <li className="page-item"><a className="page-link" href={`?page=${p.next}${more}`}>Siguiente</a></li>}
                  </ul>
                </nav>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function PapeleraPage() {
  const [state] = useMainResource(`web/core/papelera/${window.location.search}`, papeleraValid);
  return renderMain(state, "Cargando papelera…", (data) => ({
    title: "Papelera",
    activePath: "papelera/",
    heading: "Papelera Global",
    breadcrumb: (
      <>
        <li className="breadcrumb-item"><a href={data.urls.home}>Inicio</a></li>
        <li className="breadcrumb-item active">Papelera</li>
      </>
    ),
    content: <PapeleraContent data={data} />,
  }));
}

export const corePapeleraRoute: RouteDefinition<Record<string, never>> = {
  name: "core-papelera",
  match: (pathname) => (pathname === "/papelera/" ? {} : null),
  render: () => <PapeleraPage />,
};
