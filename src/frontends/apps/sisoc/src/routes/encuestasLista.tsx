/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useRef, useState, type FormEvent } from "react";
import { Breadcrumb, accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { Filters, Pagination, filtersConfigValid, type Favorites, type FiltersConfig } from "./listControls";
import { NativeToasts } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * Survey list (`encuestas/encuesta_list.html` + `components/search_bar.html`, `/encuestas/`). GET
 * `/api/web/encuestas/lista/?filters=&page=` runs `EncuestaListView` (403 without `encuestas.view_encuesta` or
 * `encuestas.ver_resultados`; the legacy `busqueda`/`estado` links answer the native redirect to `filters`).
 * "Solicitar publicación" posts to `.../<id>/publicar/` and "Importar" posts the chosen file to
 * `.../importar/`; both run the native view, leave its flash message queued and then navigate to its
 * redirect, as the native form does, so the next page load shows the message. Links go to the native pages.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Fila = {
  id: number; titulo: string; version: number; fecha_creacion: string; estado: string; estado_label: string; tiene_motivo_rechazo: boolean;
  modalidad: string; es_anonima: boolean; creador: string;
};
export type ListaData = {
  filters_config: FiltersConfig; favorites: Favorites; urls: { list: string; add: string; importar: string };
  puede_gestionar: boolean; puede_aprobar: boolean; puede_editar: boolean; puede_ver_resultados: boolean;
  pendientes_aprobacion: number; pendientes_url: string; results: Fila[];
  page: { is_paginated: boolean; number: number; count: number; previous: number | null; next: number | null; range: (number | string)[]; query_without_page: string };
  messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const flag = (v: unknown) => typeof v === "boolean";
const list = (v: unknown, ok: (x: unknown) => boolean) => Array.isArray(v) && v.every(ok);
const strings = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));
const redirectOnly = (v: unknown): v is { redirect: string } => record(v) && internal(v.redirect) && !("results" in v);

export function listaValid(v: unknown): v is ListaData {
  if (!record(v) || !record(v.urls) || !record(v.favorites) || !record(v.page)) return false;
  const p = v.page;
  return filtersConfigValid(v.filters_config) && strings(v.favorites, ["section", "url", "detail_url_template"]) &&
    internal(v.urls.list) && internal(v.urls.add) && internal(v.urls.importar) &&
    ["puede_gestionar", "puede_aprobar", "puede_editar", "puede_ver_resultados"].every((k) => flag(v[k])) &&
    int(v.pendientes_aprobacion) && internal(v.pendientes_url) &&
    list(v.results, (r) => record(r) && int(r.id) && int(r.version) && strings(r, ["titulo", "fecha_creacion", "estado", "estado_label", "modalidad", "creador"]) && flag(r.tiene_motivo_rechazo) && flag(r.es_anonima)) &&
    flag(p.is_paginated) && int(p.number) && int(p.count) && (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    list(p.range, (n) => int(n) || text(n)) && text(p.query_without_page) &&
    list(v.messages, (m) => strings(m, ["message"]) && LEVELS.includes((m as Message).level));
}

const TOAST_ERROR_STYLE = `
        #toast-container > .toast-error {
            background-color: #bd362f;
            color: #fff;
            opacity: 1;
        }
    `;

function Estado({ r }: { r: Fila }) {
  const icon = r.estado === "pendiente_aprobacion" ? "fas fa-clock" : r.estado === "publicada" ? "fas fa-check-circle" : "fas fa-file-alt";
  return <span className={`encuesta-estado encuesta-estado--${r.estado}`}><i className={icon} aria-hidden="true"></i> {r.estado_label}</span>;
}

type Post = (url: string, body?: FormData) => Promise<void>;

function Acciones({ r, data, post, busy }: { r: Fila; data: ListaData; post: Post; busy: boolean }) {
  const pendiente = r.estado === "pendiente_aprobacion";
  const publicar = (e: FormEvent) => { e.preventDefault(); void post(`web/encuestas/${r.id}/publicar/`); };
  return (
    <div className="encuesta-acciones">
      {data.puede_editar && !pendiente && (
        <>
          <a href={`/encuestas/${r.id}/editar/`} className="btn btn-sm btn-secondary px-2 py-1 text-nowrap"><i className="fas fa-edit" aria-hidden="true"></i> Editar</a>{" "}
          <a href={`/encuestas/${r.id}/segmentacion/`} className="btn btn-sm btn-secondary px-2 py-1 text-nowrap"><i className="fas fa-users" aria-hidden="true"></i> Segmentación</a>{" "}
          {r.estado === "borrador" && (
            <form method="post" className="m-0" onSubmit={publicar}>
              <button type="submit" className="btn btn-sm btn-success" disabled={busy}><i className="fas fa-paper-plane" aria-hidden="true"></i> Solicitar publicación</button>
            </form>
          )}
        </>
      )}
      {pendiente && (data.puede_editar || data.puede_aprobar) && (
        <a href={`/encuestas/${r.id}/revision/`} className="btn btn-sm btn-success"><i className="fas fa-clipboard-check" aria-hidden="true"></i>Revisar solicitud</a>
      )}
      {data.puede_ver_resultados && (
        <a href={`/encuestas/${r.id}/resultados/`} className="btn btn-sm btn-secondary px-2 py-1 text-nowrap"><i className="fas fa-chart-bar" aria-hidden="true"></i> Resultados</a>
      )}
    </div>
  );
}

export function ListaContent({ data }: { data: ListaData }) {
  const [busy, setBusy] = useState(false);
  const [importing, setImporting] = useState(false);
  const [toasts, setToasts] = useState<Message[]>(data.messages);
  const file = useRef<HTMLInputElement>(null);
  const form = useRef<HTMLFormElement>(null);

  const post: Post = async (url, body) => {
    setBusy(true);
    try {
      const { data: result, status } = await webClient.post(url, body ?? new URLSearchParams(), { validateStatus: accepted });
      if (status === 200 && record(result) && result.ok === true && internal(result.redirect)) { window.location.assign(result.redirect); return; }
      setToasts([{ message: "No se pudo completar la operación.", level: "error" }]);
    } catch {
      setToasts([{ message: "No se pudo completar la operación.", level: "error" }]);
    }
    setBusy(false);
    setImporting(false);
  };
  const importar = () => {
    if (!file.current?.files?.length || !form.current) return;
    setImporting(true);
    void post("web/encuestas/importar/?mensajes=en-cola", new FormData(form.current));
  };

  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <style>{TOAST_ERROR_STYLE}</style>
      <link rel="stylesheet" href="/static/custom/css/encuestaGestion.css" />
      <div className="list-container encuestas-gestion">
        <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
        <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
        <h2 className="text-center mb-4 poncho-titulo">Buscar encuestas</h2>
        <Filters config={data.filters_config} action="" favorites={data.favorites} />
        <div className="row mt-3">
          <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
            {data.puede_gestionar && (
              <button type="button" className="poncho-btn poncho-btn--cta" id="importar-encuesta-btn" disabled={importing} aria-busy={importing ? "true" : undefined}
                onClick={() => file.current?.click()}>
                {importing ? <><span className="spinner-border spinner-border-sm" aria-hidden="true"></span>Importando…</> : <><i className="fas fa-file-import" aria-hidden="true"></i>Importar</>}
              </button>
            )}
            <a href={data.urls.list} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
            {data.puede_gestionar && <a href={data.urls.add} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true"></i>Crear encuesta</a>}
          </div>
        </div>
        {data.puede_gestionar && (
          <form method="post" id="importar-encuesta-form" encType="multipart/form-data" hidden ref={form} onSubmit={(e) => e.preventDefault()}>
            <input type="file" name="archivo" id="archivo-encuesta" accept=".json,application/json" hidden ref={file} onChange={importar} />
          </form>
        )}
        {data.puede_aprobar && (
          <div className="encuesta-bandeja">
            <div>
              <strong><i className="fas fa-clipboard-check me-2" aria-hidden="true"></i>Solicitudes de publicación</strong>
              <p className="encuesta-meta mb-0">{data.pendientes_aprobacion} pendiente{data.pendientes_aprobacion === 1 ? "" : "s"} de aprobación. Revisá el contenido antes de publicar.</p>
            </div>
            <a href={data.pendientes_url} className="poncho-btn poncho-btn--neutro"><i className="fas fa-clock" aria-hidden="true"></i>Ver pendientes</a>
          </div>
        )}
        <div className="card mt-3">
          <div className="card-body">
            <div className="table-responsive">
              <table className="table">
                <thead><tr><th>Encuesta</th><th>Estado</th><th>Modalidad</th><th>Creada por</th><th>Acciones</th></tr></thead>
                <tbody>
                  {data.results.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <div className="encuesta-titulo">{r.titulo}</div>
                        <div className="encuesta-meta">Versión {r.version} · {r.fecha_creacion}</div>
                      </td>
                      <td>
                        <Estado r={r} />
                        {r.estado === "borrador" && r.tiene_motivo_rechazo && data.puede_editar && (
                          <a href={`/encuestas/${r.id}/editar/`} className="d-block mt-2 small"><i className="fas fa-comment-alt me-1" aria-hidden="true"></i>Ver motivo del rechazo</a>
                        )}
                      </td>
                      <td>{r.modalidad}<div className="encuesta-meta">{r.es_anonima ? "Anónima" : "Identificada"}</div></td>
                      <td>{r.creador}</td>
                      <td><Acciones r={r} data={data} post={post} busy={busy} /></td>
                    </tr>
                  ))}
                  {data.results.length === 0 && (
                    <tr><td colSpan={5}><div className="no-data-message"><h3>No se encontraron encuestas</h3><p>No hay encuestas que coincidan con los criterios de búsqueda.</p></div></td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        {/* `pagination.html` prints the total only when the page object is truthy, which an empty page is not. */}
        <Pagination paginated={data.page.is_paginated} number={data.page.number} previous={data.page.previous} next={data.page.next} range={data.page.range}
          href={(n) => `?${data.page.query_without_page}page=${n}`} count={data.results.length > 0 ? data.page.count : null} />
      </div>
      <NativeToasts messages={toasts} />
    </>
  );
}

const pageValid = (v: unknown): v is ListaData | { redirect: string } => listaValid(v) || redirectOnly(v);

function ListaPage() {
  const [state] = useMainResource(`web/encuestas/lista/${window.location.search}`, pageValid);
  if (state.status === "ready" && redirectOnly(state.data)) {
    window.location.replace(state.data.redirect);
    return <main role="status">Cargando encuestas…</main>;
  }
  return renderMain(state, "Cargando encuestas…", (data) => ({
    title: "Encuestas", heading: "Encuestas", activePath: "/encuestas/",
    breadcrumb: <Breadcrumb items={[]} />,
    content: listaValid(data) ? <ListaContent data={data} /> : null,
  }));
}

export const encuestasListaRoute: RouteDefinition<Record<string, never>> = {
  name: "encuestas-lista",
  match: (pathname) => (pathname === "/encuestas/" ? {} : null),
  render: () => <ListaPage />,
};
