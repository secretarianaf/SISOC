/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * C01.01 / C01.02: `ciudadanos/importacion_masiva_form.html` and `importacion_masiva_job_detail.html`. GET
 * `/api/web/ciudadanos/importacion-masiva/` and `.../lotes/<pk>/?page=` run the native views (403 without
 * `ciudadanos.add_ciudadano`, 404 for a missing batch) and return what the templates print; the multipart POST creates the batch
 * (the worker processes it later, nothing calls RENAPER here) and "Reanudar" posts to `.../reanudar/`. A rejected upload comes back
 * as 400 with the bound form. The template and the Excel results are native downloads (plain links), as is "Actualizar estado".
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Reciente = {
  id: number; fecha_texto: string; usuario_texto: string; estado: string; creados: number; existentes: number; fallidos: number;
  pendientes: number; detalle_url: string;
};
export type ImportacionData = {
  campo: { label: string; accept: string }; errors: Record<string, string[]>; plantilla_url: string; volver_url: string;
  lotes: Reciente[]; messages: Message[];
};
type Fila = {
  fila: number; documento: string; dni: string; sexo: string; estado: string; sexos_intentados: string; intentos: number; mensaje: string;
  error_tipo: string; ciudadano_url: string | null;
};
type Ultimo = { documento: string; fila_texto: string };
export type LoteData = {
  id: number; archivo: string; fecha_texto: string; estado: string; reanudaciones: number; totales: number; procesadas: number; creados: number;
  existentes: number; fallidos: number; pendientes: number; ultimo_correcto: Ultimo; ultimo_intentado: Ultimo; error_mensaje: string;
  error_tipo: string; puede_reanudar: boolean; filas: Fila[]; paginacion: { number: number; num_pages: number; previous: boolean; next: boolean };
  volver_url: string; lista_url: string; lote_url: string; exportar_url: string; reanudar_url: string; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const count = (v: unknown): v is number => Number.isSafeInteger(v);
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
const UNCERTAIN = "No se pudo confirmar el resultado. Revise el historial de lotes antes de volver a intentar.";

export function importacionValid(v: unknown): v is ImportacionData {
  if (!record(v) || !record(v.campo) || !record(v.errors)) return false;
  return text(v.campo.label) && text(v.campo.accept) && Object.values(v.errors).every((e) => Array.isArray(e) && e.every(text)) &&
    internal(v.plantilla_url) && internal(v.volver_url) && messagesValid(v.messages) &&
    Array.isArray(v.lotes) && v.lotes.every((l) => record(l) && count(l.id) && text(l.fecha_texto) && text(l.usuario_texto) && text(l.estado) &&
      count(l.creados) && count(l.existentes) && count(l.fallidos) && count(l.pendientes) && internal(l.detalle_url));
}

const ultimoValid = (u: unknown) => record(u) && text(u.documento) && text(u.fila_texto);
export function loteValid(v: unknown): v is LoteData {
  if (!record(v) || !record(v.paginacion) || !Array.isArray(v.filas)) return false;
  const p = v.paginacion;
  return count(v.id) && text(v.archivo) && text(v.fecha_texto) && text(v.estado) && count(v.reanudaciones) && count(v.totales) && count(v.procesadas) &&
    count(v.creados) && count(v.existentes) && count(v.fallidos) && count(v.pendientes) && ultimoValid(v.ultimo_correcto) && ultimoValid(v.ultimo_intentado) &&
    text(v.error_mensaje) && text(v.error_tipo) && typeof v.puede_reanudar === "boolean" &&
    v.filas.every((f) => record(f) && count(f.fila) && text(f.documento) && text(f.dni) && text(f.sexo) && text(f.estado) && text(f.sexos_intentados) &&
      count(f.intentos) && text(f.mensaje) && text(f.error_tipo) && (f.ciudadano_url === null || internal(f.ciudadano_url))) &&
    count(p.number) && count(p.num_pages) && typeof p.previous === "boolean" && typeof p.next === "boolean" &&
    internal(v.volver_url) && internal(v.lista_url) && internal(v.lote_url) && internal(v.exportar_url) && internal(v.reanudar_url) && messagesValid(v.messages);
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const ciudadanoImportacionNavigation = { assign: (to: string) => window.location.assign(to) };

/** The native breadcrumbs: "Ciudadanos" is a plain item (not `active`), the links follow and the last item is `active`. */
function Migas({ enlaces, actual }: { enlaces: { text: string; url: string }[]; actual: string }) {
  return (
    <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item">Ciudadanos</li>
      {enlaces.map((e) => <li key={e.url} className="breadcrumb-item"><a href={e.url}>{e.text}</a></li>)}
      <li className="breadcrumb-item active">{actual}</li>
    </ol>
  );
}

const BADGES_LISTA: Record<string, [string, string]> = {
  completed: ["badge-success", "Completado"], completed_with_errors: ["badge-warning", "Con errores"],
  failed: ["badge-danger", "Fallido"], processing: ["badge-info", "Procesando"],
};
const BADGES_LOTE: Record<string, [string, string]> = {
  completed: ["badge-success", "Completado"], completed_with_errors: ["badge-warning", "Completado con errores"],
  failed: ["badge-danger", "Fallido"], processing: ["badge-info", "Procesando"],
};
const BADGES_FILA: Record<string, [string, string]> = {
  created: ["badge-success", "Creado"], existing: ["badge-primary", "Existente"], failed: ["badge-danger", "Fallido"],
};
function Badge({ map, estado }: { map: Record<string, [string, string]>; estado: string }) {
  const [clase, etiqueta] = map[estado] ?? ["badge-secondary", "Pendiente"];
  return <span className={`badge ${clase}`}>{etiqueta}</span>;
}

function Carga({ data, onData }: { data: ImportacionData; onData: (d: ImportacionData) => void }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [fileKey, setFileKey] = useState(0);
  const busy = useRef(false);
  const errores = data.errors.archivo ?? [];
  async function submit(event: FormEvent<HTMLFormElement>) {
    // "Descargar plantilla" is a native GET submit (formaction/formmethod): the browser follows it.
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    if (submitter && submitter.formMethod === "get") return;
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true); setError("");
    try {
      const { data: cuerpo, status } = await webClient.post("web/ciudadanos/importacion-masiva/", new FormData(event.currentTarget), {
        validateStatus: (s: number) => accepted(s) || s === 400,
      });
      if (status === 400 && importacionValid(cuerpo)) {
        onData(cuerpo); setFileKey((k) => k + 1); resetAfterRejectedPost();
      } else if (status === 403 && record(cuerpo) && text(cuerpo.detail)) setError(cuerpo.detail);
      else if (record(cuerpo) && cuerpo.ok === true && internal(cuerpo.redirect)) { ciudadanoImportacionNavigation.assign(cuerpo.redirect); return; }
      else setError(UNCERTAIN);
    } catch { setError(UNCERTAIN); }
    busy.current = false; setPending(false);
  }
  return (
    <form method="post" encType="multipart/form-data" noValidate onSubmit={(e) => void submit(e)}>
      <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
      <div className="mb-3">
        <div id="div_id_archivo" className="mb-3">
          <label htmlFor="id_archivo" className="form-label requiredField">{data.campo.label}<span className="asteriskField">*</span></label>
          <div className={errores.length > 0 ? "is-invalid" : undefined}>
            <input key={fileKey} type="file" name="archivo" className={`form-control form-control${errores.length > 0 ? " is-invalid" : ""}`} accept={data.campo.accept}
              id="id_archivo" required aria-invalid={errores.length > 0 ? true : undefined} aria-describedby={errores.length > 0 ? "id_archivo_error" : undefined} />
            {errores.length > 0 && (
              <div id="id_archivo_error" className="invalid-feedback">
                {errores.map((e, i) => <p key={i} id={`error_${i + 1}_id_archivo`}><strong>{e}</strong></p>)}
              </div>
            )}
          </div>
        </div>
      </div>
      {error && <p role="alert" className="text-danger">{error}</p>}
      <div className="d-flex flex-wrap gap-2">
        <button type="submit" className="btn btn-outline-primary" formAction={data.plantilla_url} formMethod="get" formNoValidate>Descargar plantilla</button>
        <button type="submit" className="btn btn-success" disabled={pending}>Crear lote</button>
      </div>
    </form>
  );
}

export function ImportacionContent({ initial }: { initial: ImportacionData }) {
  const [data, setData] = useState(initial);
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row justify-content-center">
        <div className="col-12 col-lg-9">
          <div className="card shadow-sm">
            <div className="card-header"><h3 className="mb-0">Nuevo lote</h3></div>
            <div className="card-body">
              <div className="alert alert-light border">
                <div className="font-weight-bold mb-2">Formato esperado</div>
                <ul className="mb-0 pl-3">
                  <li>La plantilla incluye <code>cuil_o_dni</code> y <code>sexo</code>.</li>
                  <li>Tambien se aceptan encabezados <code>cuil</code>, <code>dni</code> o <code>documento</code>.</li>
                  <li>Si <code>sexo</code> viene vacio, el worker intenta M, F y X.</li>
                  <li>El procesamiento queda en historial y se ejecuta fuera de la request web.</li>
                </ul>
              </div>
              <Carga data={data} onData={setData} />
              <hr className="my-4" />
              <h4 className="mb-3">Historial de lotes</h4>
              {data.lotes.length > 0 ? (
                <div className="table-responsive">
                  <table className="table table-bordered table-hover align-middle mb-0">
                    <thead>
                      <tr>
                        {["Lote", "Fecha", "Usuario", "Estado", "Creados", "Existentes", "Fallidos", "Pendientes", "Detalle"].map((t) => <th key={t} scope="col">{t}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {data.lotes.map((l) => (
                        <tr key={l.id}>
                          <td>#{l.id}</td>
                          <td>{l.fecha_texto}</td>
                          <td>{l.usuario_texto}</td>
                          <td><Badge map={BADGES_LISTA} estado={l.estado} /></td>
                          <td>{l.creados}</td>
                          <td>{l.existentes}</td>
                          <td>{l.fallidos}</td>
                          <td>{l.pendientes}</td>
                          <td><a href={l.detalle_url} className="btn btn-sm btn-outline-primary">Ver detalle</a></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <div className="alert alert-light border mb-0">Todavia no hay lotes de importacion masiva.</div>}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function ImportacionPage() {
  const [state] = useMainResource("web/ciudadanos/importacion-masiva/", importacionValid);
  return renderMain(state, "Cargando importación…", (data) => ({
    title: "Importacion masiva de ciudadanos", heading: "Importacion masiva de ciudadanos",
    breadcrumb: <Migas enlaces={[{ text: "Historia Social Digital", url: data.volver_url }]} actual="Importacion masiva" />,
    content: <ImportacionContent initial={data} />,
  }));
}

function Contador({ titulo, valor }: { titulo: string; valor: number }) {
  return (
    <div className="col-sm-6 col-xl-2">
      <div className="border rounded p-3 h-100">
        <div className="text-muted small">{titulo}</div>
        <div className="h4 mb-0">{valor}</div>
      </div>
    </div>
  );
}

function Ultimo({ titulo, ultimo, vacio }: { titulo: string; ultimo: Ultimo; vacio: string }) {
  return (
    <div className="col-md-6">
      <div className="alert alert-light border mb-0 h-100">
        <div className="font-weight-bold mb-2">{titulo}</div>
        {ultimo.documento ? <><div>{ultimo.documento}</div><small className="text-muted">Fila {ultimo.fila_texto}</small></> : <div className="text-muted">{vacio}</div>}
      </div>
    </div>
  );
}

function Reanudar({ data }: { data: LoteData }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true); setError("");
    try {
      const { data: cuerpo, status } = await webClient.post(`web/ciudadanos/importacion-masiva/lotes/${data.id}/reanudar/`, new URLSearchParams(), { validateStatus: accepted });
      if (status === 403 && record(cuerpo) && text(cuerpo.detail)) setError(cuerpo.detail);
      else if (record(cuerpo) && cuerpo.ok === true && internal(cuerpo.redirect)) { ciudadanoImportacionNavigation.assign(cuerpo.redirect); return; }
      else setError("No se pudo confirmar el resultado. Actualice el estado del lote antes de volver a intentar.");
    } catch { setError("No se pudo confirmar el resultado. Actualice el estado del lote antes de volver a intentar."); }
    busy.current = false; setPending(false);
  }
  return (
    <>
      <form method="post" action={data.reanudar_url} onSubmit={(e) => void submit(e)}>
        <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
        <button type="submit" className="btn btn-warning" disabled={pending}>Reanudar</button>
      </form>
      {error && <p role="alert" className="text-danger">{error}</p>}
    </>
  );
}

export function LoteContent({ data }: { data: LoteData }) {
  const p = data.paginacion;
  const detalle = (f: Fila): ReactNode => <>{f.mensaje}{f.error_tipo && <small className="text-muted d-block">{f.error_tipo}</small>}</>;
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          <div className="card shadow-sm mb-4">
            <div className="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
              <div>
                <h3 className="mb-0">Lote #{data.id}</h3>
                <small className="text-muted">{data.archivo} | {data.fecha_texto}</small>
              </div>
              <div className="d-flex flex-wrap gap-2">
                <a href={data.lote_url} className="btn btn-outline-primary">Actualizar estado</a>
                <a href={data.exportar_url} className="btn btn-outline-success">Exportar Excel</a>
                {data.puede_reanudar && <Reanudar data={data} />}
              </div>
            </div>
            <div className="card-body">
              <div className="mb-4">
                <Badge map={BADGES_LOTE} estado={data.estado} />{" "}
                <span className="ml-2 text-muted">Reanudaciones: <strong>{data.reanudaciones}</strong></span>
              </div>
              <div className="row g-3 mb-4">
                <Contador titulo="Totales" valor={data.totales} />
                <Contador titulo="Procesadas" valor={data.procesadas} />
                <Contador titulo="Creados" valor={data.creados} />
                <Contador titulo="Existentes" valor={data.existentes} />
                <Contador titulo="Fallidos" valor={data.fallidos} />
                <Contador titulo="Pendientes" valor={data.pendientes} />
              </div>
              <div className="row g-3 mb-4">
                <Ultimo titulo="Ultimo correcto" ultimo={data.ultimo_correcto} vacio="Todavia no hay filas creadas o existentes." />
                <Ultimo titulo="Ultimo intentado" ultimo={data.ultimo_intentado} vacio="Todavia no se intento ninguna fila." />
              </div>
              {data.error_mensaje ? (
                <div className="alert alert-danger">
                  <div className="font-weight-bold">Error sistemico</div>
                  <div>{data.error_mensaje}</div>
                  {data.error_tipo && <small className="d-block mt-2">Tipo: {data.error_tipo}</small>}
                </div>
              ) : (data.estado === "processing" || data.estado === "pending") && (
                <div className="alert alert-info">El lote se procesa fuera de la request web. Use <strong>Actualizar estado</strong> para refrescar.</div>
              )}
              <div className="table-responsive">
                <table className="table table-bordered table-hover align-middle mb-0">
                  <thead>
                    <tr>
                      {["Fila", "CUIL/DNI", "DNI", "Sexo", "Estado", "Intentos sexo", "Intentos", "Detalle", "Ciudadano"].map((t) => <th key={t} scope="col">{t}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {data.filas.length > 0 ? data.filas.map((f) => (
                      <tr key={f.fila}>
                        <td>{f.fila}</td>
                        <td>{f.documento}</td>
                        <td>{f.dni}</td>
                        <td>{f.sexo}</td>
                        <td><Badge map={BADGES_FILA} estado={f.estado} /></td>
                        <td>{f.sexos_intentados}</td>
                        <td>{f.intentos}</td>
                        <td>{detalle(f)}</td>
                        <td>{f.ciudadano_url ? <a href={f.ciudadano_url} className="btn btn-sm btn-outline-primary">Ver</a> : "-"}</td>
                      </tr>
                    )) : (
                      <tr><td colSpan={9} className="text-center text-muted py-4">Aun no hay filas registradas para este lote.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {p.num_pages > 1 && (
                <nav aria-label="Paginacion de filas" className="mt-3">
                  <ul className="pagination mb-0">
                    {p.previous && <li className="page-item"><a className="page-link" href={`?page=${p.number - 1}`}>Anterior</a></li>}
                    <li className="page-item active"><span className="page-link">Pagina {p.number} de {p.num_pages}</span></li>
                    {p.next && <li className="page-item"><a className="page-link" href={`?page=${p.number + 1}`}>Siguiente</a></li>}
                  </ul>
                </nav>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function LotePage({ pk }: { pk: string }) {
  const [state] = useMainResource(`web/ciudadanos/importacion-masiva/lotes/${pk}/${window.location.search}`, loteValid);
  return renderMain(state, "Cargando lote…", (data) => ({
    title: "Detalle de lote de importacion", heading: "Detalle de lote de importacion",
    breadcrumb: <Migas enlaces={[{ text: "Historia Social Digital", url: data.lista_url }, { text: "Importacion masiva", url: data.volver_url }]} actual={`Lote #${data.id}`} />,
    content: <LoteContent data={data} />,
  }));
}

export const ciudadanoImportacionRoute: RouteDefinition<Record<string, never>> = {
  name: "ciudadano-importacion",
  match: (pathname) => (pathname === "/ciudadanos/importacion-masiva/" ? {} : null),
  render: () => <ImportacionPage />,
};

const LOTE = /^\/ciudadanos\/importacion-masiva\/lotes\/([0-9]+)\/$/;

export const ciudadanoImportacionLoteRoute: RouteDefinition<{ pk: string }> = {
  name: "ciudadano-importacion-lote",
  match(pathname) {
    const found = LOTE.exec(pathname);
    return found ? { pk: found[1] } : null;
  },
  render: ({ pk }) => <LotePage pk={pk} />,
};
