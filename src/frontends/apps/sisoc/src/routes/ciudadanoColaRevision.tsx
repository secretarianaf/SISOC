/* eslint-disable react-refresh/only-export-components -- route module: the validator and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeToasts } from "./nativeParity";
import { Pagination } from "./listControls";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * C02.01 / C02.02: `ciudadanos/cola_revision.html`. GET `/api/web/ciudadanos/revision/?estado=&page=` runs `ColaRevisionView`
 * (403 without `ciudadanos.revision_identidad`, 404 for a page out of range) and returns what the template prints. "Revisado"
 * and "Descartar" ask for the browser confirmation the native forms ask for, post to `.../<pk>/marcar-revisado/` and
 * `.../<pk>/descartar-revision/` with the native `next` (this queue and its filter) and the redirect is a full-page
 * navigation, so the native message shows on the reloaded queue. "Editar" is the native edit page.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Fila = {
  id: number; nombre_texto: string; identificador: string; documento: string; tipo_registro: string;
  motivo: { texto: string; descripcion: string | null }; provincia: string; estado_revision: string; editar_url: string;
};
export type ColaData = {
  total_pendientes: number; total_filtrado: number; estado: string; estados: { value: string; label: string }[]; filas: Fila[];
  paginacion: { paginated: boolean; number: number; previous: number | null; next: number | null; range: (number | string)[]; count: number | null };
  cola_url: string; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const count = (v: unknown): v is number => Number.isSafeInteger(v);
const pageNumber = (v: unknown) => v === null || count(v);
const UNCERTAIN = "No se pudo confirmar el resultado. Actualice la cola antes de volver a intentar.";
const plural = (n: number, suffix = "s") => (n === 1 ? "" : suffix);

export function colaValid(v: unknown): v is ColaData {
  if (!record(v) || !record(v.paginacion) || !Array.isArray(v.filas) || !Array.isArray(v.estados)) return false;
  const p = v.paginacion;
  return count(v.total_pendientes) && count(v.total_filtrado) && text(v.estado) && internal(v.cola_url) &&
    v.estados.every((e) => record(e) && text(e.value) && text(e.label)) &&
    v.filas.every((f) => record(f) && count(f.id) && text(f.nombre_texto) && text(f.identificador) && text(f.documento) && text(f.tipo_registro) &&
      record(f.motivo) && text(f.motivo.texto) && (f.motivo.descripcion === null || text(f.motivo.descripcion)) && text(f.provincia) && text(f.estado_revision) && internal(f.editar_url)) &&
    typeof p.paginated === "boolean" && count(p.number) && pageNumber(p.previous) && pageNumber(p.next) && (p.count === null || count(p.count)) &&
    Array.isArray(p.range) && p.range.every((n) => count(n) || n === "...") &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Replaceable in tests: the redirect is a full-page navigation, like the native 302. */
export const ciudadanoColaRevisionNavigation = { assign: (to: string) => window.location.assign(to) };

const TIPOS: Record<string, [string, string]> = {
  SIN_DNI: ["bg-warning text-dark", "Sin DNI"], DNI_NO_VALIDADO_RENAPER: ["bg-danger", "RENAPER no validado"],
};

/** `pagination.html`: every other query parameter is kept, in order, before `page`. */
function pageHref(page: number) {
  const kept = [...new URLSearchParams(window.location.search)].filter(([k]) => k !== "page");
  return `?${kept.map(([k, v]) => `${k}=${encodeURIComponent(v).replace(/%2F/g, "/")}&`).join("")}page=${page}`;
}

function Resolver({ fila, accion, estado, confirmacion, endpoint, clase, icono, etiqueta, titulo, onError }: {
  fila: Fila; accion: string; estado: string; confirmacion: string; endpoint: string; clase: string; icono: string; etiqueta: string; titulo: string;
  onError: (message: string) => void;
}) {
  const busy = useRef(false);
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || !window.confirm(confirmacion)) return;
    busy.current = true; setPending(true); onError("");
    const outcome = await postForm(endpoint, new URLSearchParams({ next: `/ciudadanos/revision/?estado=${estado}` }));
    if (outcome.kind === "redirect") { ciudadanoColaRevisionNavigation.assign(outcome.url); return; }
    onError(outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN);
    busy.current = false; setPending(false);
  }
  return (
    <form method="post" action={`/ciudadanos/${fila.id}/${accion}/`} className="d-inline" onSubmit={(e) => void submit(e)}>
      <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
      <input type="hidden" name="next" value={`/ciudadanos/revision/?estado=${estado}`} />
      <button type="submit" className={`btn btn-sm ${clase}`} title={titulo} disabled={pending}><i className={icono} /> {etiqueta}</button>
    </form>
  );
}

function FilaCola({ f, estado, onError }: { f: Fila; estado: string; onError: (message: string) => void }) {
  const tipo = TIPOS[f.tipo_registro];
  return (
    <tr>
      <td>{f.nombre_texto}</td>
      <td><code>{f.identificador}</code></td>
      <td>{f.documento}</td>
      <td><span className={`badge ${tipo ? tipo[0] : "bg-success"}`}>{tipo ? tipo[1] : "Estándar"}</span></td>
      <td className="text-muted small">
        {f.motivo.texto}
        {f.motivo.descripcion && <><br /><em>{f.motivo.descripcion}</em></>}
      </td>
      <td>{f.provincia}</td>
      <td className="text-center text-nowrap">
        {f.estado_revision === "APROBADA" ? (
          <span className="badge bg-success px-3 py-2"><i className="fas fa-check" /> Aprobado</span>
        ) : f.estado_revision === "DESCARTADA" ? (
          <span className="badge bg-danger px-3 py-2"><i className="fas fa-times" /> Descartado</span>
        ) : (
          <div className="d-inline-flex align-items-center gap-1 flex-nowrap">
            <a href={f.editar_url} className="btn btn-sm btn-warning" title="Editar legajo"><i className="fas fa-edit" /> Editar</a>
            <Resolver fila={f} accion="marcar-revisado" estado={estado} confirmacion="¿Marcar este ciudadano como revisado?" endpoint={`web/ciudadanos/${f.id}/marcar-revisado/`}
              clase="btn-outline-success" icono="fas fa-check" etiqueta="Revisado" titulo="Marcar como revisado" onError={onError} />
            <Resolver fila={f} accion="descartar-revision" estado={estado} confirmacion="¿Descartar esta solicitud?" endpoint={`web/ciudadanos/${f.id}/descartar-revision/`}
              clase="btn-outline-danger" icono="fas fa-times" etiqueta="Descartar" titulo="Descartar solicitud" onError={onError} />
          </div>
        )}
      </td>
    </tr>
  );
}

export function ColaContent({ data }: { data: ColaData }) {
  const [error, setError] = useState("");
  const p = data.paginacion;
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h3 className="mb-1">Revisión manual</h3>
          <p className="text-muted mb-0">
            {data.total_pendientes} ciudadano{plural(data.total_pendientes)} requiere{plural(data.total_pendientes, "n")} revisión manual.
          </p>
        </div>
      </div>
      <form method="get" className="card mb-3">
        <div className="card-body">
          <label htmlFor="estado" className="form-label fw-bold">Estado</label>
          <div className="d-flex flex-wrap gap-2 align-items-end">
            <select id="estado" name="estado" className="form-select" style={{ maxWidth: "280px" }} defaultValue={data.estado} onChange={(e) => e.currentTarget.form?.submit()}>
              {data.estados.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <span className="text-muted small">{data.total_filtrado} resultado{plural(data.total_filtrado)}</span>
          </div>
        </div>
      </form>
      {error && <p role="alert" className="text-danger">{error}</p>}
      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-bordered table-hover mb-0">
              <thead className="table-light">
                <tr>
                  <th>Apellido y nombre</th><th>Identificador</th><th>Documento</th><th>Tipo de registro</th><th>Motivo</th><th>Provincia</th>
                  <th className="text-center" style={{ width: "300px" }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {data.filas.length > 0 ? data.filas.map((f) => <FilaCola key={f.id} f={f} estado={data.estado} onError={setError} />) : (
                  <tr>
                    <td colSpan={7} className="text-center py-4 text-muted">
                      <i className="fas fa-check-circle fa-2x mb-2 d-block text-success" />
                      No hay ciudadanos para el filtro seleccionado.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      {p.paginated && (
        <div className="mt-3">
          <Pagination paginated number={p.number} previous={p.previous} next={p.next} range={p.range} href={pageHref} count={p.count} />
        </div>
      )}
    </>
  );
}

function ColaPage() {
  const [state] = useMainResource(`web/ciudadanos/revision/${window.location.search}`, colaValid);
  // The native template defines the page title and heading with the same text.
  return renderMain(state, "Cargando revisión…", (data) => ({
    title: "Revisión de Identidades No Validadas", heading: "Revisión de Identidades No Validadas", breadcrumb: null, content: <ColaContent data={data} />,
  }));
}

export const ciudadanoColaRevisionRoute: RouteDefinition<Record<string, never>> = {
  name: "ciudadano-cola-revision",
  match: (pathname) => (pathname === "/ciudadanos/revision/" ? {} : null),
  render: () => <ColaPage />,
};
