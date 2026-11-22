/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Fragment, useCallback, useEffect, useRef, useState, type ChangeEvent } from "react";
import { renderWithNativeToasts } from "./cdfActividades";
import { csrfToken, integer, internal, messagesValid, navigation, record, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import { NativeModal } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDF01: `informecabal/list.html` (history with the "Procesar nuevo archivo" and "Reprocesar
 * rechazados" modals and their script `informecabal.js`), `archivo_detail.html`,
 * `registro_detail.html` and `archivo_por_centro.html`. The API runs the native views; the upload
 * preview, the processing and the reprocess are the native AJAX endpoints, posted exactly as the
 * native script does (multipart or urlencoded, `X-CSRFToken`), so nothing is retried and nothing
 * is duplicated. The native `registro_detail.html` reads a variable its view never sets: it
 * renders empty values and this screen keeps that.
 */
const PAGE_SIZE = 25;

type Archivo = {
  id: number; nombre_original: string; fecha_subida: string; fecha_orden: string; usuario: string;
  total_filas: number; total_validas: number; total_invalidas: number; urls: { detail: string };
};
export type CabalListData = {
  page: number; has_previous: boolean; has_next: boolean; previous_page: number | null; next_page: number | null;
  results: Archivo[]; alerts: { message: string; tags: string }[];
  urls: { list: string; preview: string; process: string; reprocess: string }; messages: CdfMessage[];
};
type Registro = {
  numero: number; nro_comercio: string; razon_social: string; importe: string; fecha_trx: string; moneda_origen: string;
  importe_pesos: string; pago_aceptado: boolean; impactado: boolean;
};
export type CabalArchivoData = {
  archivo: { id: number; nombre_original: string; fecha_subida: string; usuario: string; total_filas: number; total_validas: number; total_invalidas: number };
  registros: Registro[]; urls: { list: string }; messages: CdfMessage[];
};
export type CabalRegistroData = { messages: CdfMessage[] };
type FilaCentro = { numero: number; nro_comercio: string; razon_social: string; importe: string; fecha_trx: string; pago_aceptado: boolean };
export type CabalCentroData = {
  centro: { id: number; nombre: string }; count: number; page: number; num_pages: number;
  has_previous: boolean; has_next: boolean; previous_page: number | null; next_page: number | null;
  results: FilaCentro[]; messages: CdfMessage[];
};

const nullableInteger = (v: unknown) => v === null || integer(v);
const strings = (o: Record<string, unknown>, keys: string[]) => keys.every((k) => text(o[k]));
const numbers = (o: Record<string, unknown>, keys: string[]) => keys.every((k) => integer(o[k]));
const neighboursValid = (v: Record<string, unknown>) => typeof v.has_previous === "boolean" && typeof v.has_next === "boolean" &&
  nullableInteger(v.previous_page) && nullableInteger(v.next_page);

const archivoValid = (a: unknown): a is Archivo => record(a) && integer(a.id) && strings(a, ["nombre_original", "fecha_subida", "fecha_orden", "usuario"]) &&
  numbers(a, ["total_filas", "total_validas", "total_invalidas"]) && record(a.urls) && internal(a.urls.detail);

export function listValid(v: unknown): v is CabalListData {
  return record(v) && integer(v.page) && neighboursValid(v) && Array.isArray(v.results) && v.results.every(archivoValid) &&
    Array.isArray(v.alerts) && v.alerts.every((a) => record(a) && text(a.message) && text(a.tags)) &&
    record(v.urls) && ["list", "preview", "process", "reprocess"].every((k) => internal((v.urls as Record<string, unknown>)[k])) && messagesValid(v.messages);
}

const registroValid = (r: unknown): r is Registro => record(r) && integer(r.numero) &&
  strings(r, ["nro_comercio", "razon_social", "importe", "fecha_trx", "moneda_origen", "importe_pesos"]) &&
  typeof r.pago_aceptado === "boolean" && typeof r.impactado === "boolean";

export function archivoValidator(v: unknown): v is CabalArchivoData {
  if (!record(v) || !record(v.archivo) || !record(v.urls)) return false;
  const a = v.archivo;
  return integer(a.id) && strings(a, ["nombre_original", "fecha_subida", "usuario"]) && numbers(a, ["total_filas", "total_validas", "total_invalidas"]) &&
    Array.isArray(v.registros) && v.registros.every(registroValid) && internal(v.urls.list) && messagesValid(v.messages);
}

export const registroValidator = (v: unknown): v is CabalRegistroData => record(v) && messagesValid(v.messages);

export function centroValidator(v: unknown): v is CabalCentroData {
  return record(v) && record(v.centro) && integer(v.centro.id) && text(v.centro.nombre) && numbers(v, ["count", "page", "num_pages"]) && neighboursValid(v) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && integer(r.numero) && strings(r, ["nro_comercio", "razon_social", "importe", "fecha_trx"]) && typeof r.pago_aceptado === "boolean") &&
    messagesValid(v.messages);
}

// --- Local sort (`listSort.js`) ----------------------------------------------------------------

type Sort = { column: string | null; direction: "asc" | "desc" | null };
const COLUMNS: { key: string; title: string; value: (a: Archivo) => string }[] = [
  { key: "archivo", title: "Archivo", value: (a) => a.nombre_original },
  { key: "fecha", title: "Fecha", value: (a) => a.fecha_orden },
  { key: "usuario", title: "Usuario", value: (a) => a.usuario },
  { key: "total", title: "Total", value: (a) => String(a.total_filas) },
  { key: "validas", title: "Válidas", value: (a) => String(a.total_validas) },
  { key: "invalidas", title: "Inválidas", value: (a) => String(a.total_invalidas) },
];

function parseDateForSort(value: string): number | null {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(value.trim());
  if (!match) return null;
  const [day, month, year] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day ? parsed.getTime() : null;
}

function compare(a: string, b: string): number {
  const ad = parseDateForSort(a), bd = parseDateForSort(b);
  if (ad !== null && bd !== null) return ad - bd;
  const an = parseFloat(a), bn = parseFloat(b);
  if (!Number.isNaN(an) && !Number.isNaN(bn) && a !== "" && b !== "") return an - bn;
  const plain = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  return plain(a).localeCompare(plain(b), "es", { sensitivity: "base" });
}

// --- Native AJAX (`informecabal.js`) ------------------------------------------------------------

type Alert = { text: string; type: "warning" | "danger" | "success" | "info" };
type PreviewRow = { fila?: unknown; no_coincidente?: unknown; data?: Record<string, unknown> };
const cell = (v: unknown) => (v === null || v === undefined ? "" : String(v));
const PREVIEW_COLUMNS = ["NroComercio", "RazonSocial", "Importe", "FechaTRX", "MonedaOrigen", "ImportePesos", "MotivoRechazo"];

function ProcesarModal({ urls, close }: { urls: CabalListData["urls"]; close: () => void }) {
  const file = useRef<File | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [rows, setRows] = useState<PreviewRow[]>([]);
  const [canProcess, setCanProcess] = useState(false);
  const [spin, setSpin] = useState(false);
  const [alert, setAlert] = useState<Alert | null>(null);

  const clearTable = () => { setRows([]); setTotal(0); setPage(1); setCanProcess(false); };
  const headers = () => ({ "X-CSRFToken": csrfToken() });
  const totalPages = Math.ceil(total / PAGE_SIZE);

  async function fetchPreview(target: number) {
    const chosen = file.current;
    if (!chosen) return;
    const form = new FormData();
    form.append("file", chosen);
    form.append("page", String(target));
    setCanProcess(false);
    try {
      const reply = await fetch(urls.preview, { method: "POST", credentials: "same-origin", headers: headers(), body: form });
      const body: unknown = await reply.json();
      if (!record(body) || !body.ok) {
        setAlert({ text: (record(body) && text(body.error) && body.error) || "Error al previsualizar", type: "danger" });
        clearTable();
        return;
      }
      const received = Array.isArray(body.rows) ? (body.rows as PreviewRow[]) : [];
      if (received.length) { setTotal(integer(body.total) ? body.total : 0); setRows(received); setPage(target); }
      else clearTable();
      setCanProcess(true);
      setAlert(Array.isArray(body.not_matching) && body.not_matching.length
        ? { text: `Registros no coincidentes: (${body.not_matching.join(", ")})`, type: "warning" } : null);
    } catch {
      setAlert({ text: "Error inesperado al previsualizar", type: "danger" });
      clearTable();
    }
  }

  async function processFile(force: boolean) {
    const chosen = file.current;
    if (!chosen) return;
    const form = new FormData();
    form.append("file", chosen);
    form.append("force", force ? "true" : "false");
    setSpin(true);
    setCanProcess(false);
    try {
      const reply = await fetch(urls.process, { method: "POST", credentials: "same-origin", headers: headers(), body: form });
      const body: unknown = await reply.json();
      setSpin(false);
      if (record(body) && body.ok) {
        setAlert({ text: `Archivo procesado. Total: ${cell(body.total)}, Válidas: ${cell(body.validas)}, Inválidas: ${cell(body.invalidas)}`, type: "success" });
        setCanProcess(false);
        window.setTimeout(() => navigation.assign(window.location.href), 800);
        return;
      }
      if (reply.status === 409 && record(body) && body.duplicate_name) {
        if (navigation.confirm("Ya se subió un archivo con este nombre. ¿Desea proseguir?")) void processFile(true);
        else setCanProcess(true);
        return;
      }
      setAlert({ text: (record(body) && text(body.error) && body.error) || "Error al procesar", type: "danger" });
      setCanProcess(true);
    } catch {
      setSpin(false);
      setAlert({ text: "Error inesperado al procesar", type: "danger" });
      setCanProcess(true);
    }
  }

  function chosen(event: ChangeEvent<HTMLInputElement>) {
    file.current = event.target.files?.[0] ?? null;
    if (!file.current) { clearTable(); return; }
    setPage(1);
    void fetchPreview(1);
  }
  function go(target: number) { setPage(target); void fetchPreview(target); }

  return (
    <NativeModal id="modalCabal" title="Procesar nuevo archivo CABAL" close={close} size=" modal-xl">
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title">Procesar nuevo archivo CABAL</h5>
          <button type="button" className="close" aria-label="Cerrar" onClick={close}><span aria-hidden="true">&times;</span></button>
        </div>
        <div className="modal-body">
          <div id="alert-zone">{alert && <div className={`alert alert-${alert.type} fade show`} role="alert">{alert.text}</div>}</div>
          <div className="form-group">
            <label htmlFor="fileCabal">Archivo Excel (.xlsx)</label>
            <input type="file" className="form-control" id="fileCabal" accept=".xlsx" onChange={chosen} />
          </div>
          <div className="d-flex justify-content-between align-items-center mb-2">
            <strong>Previsualización (25 por página)</strong>
            <div>
              <button className="btn btn-sm btn-outline-secondary" id="btn-prev" disabled={page <= 1} onClick={() => go(page - 1)}>◀</button>{" "}
              <span className="mx-2" id="page-indicator">{page}</span>{" "}
              <button className="btn btn-sm btn-outline-secondary" id="btn-next" disabled={page >= totalPages || totalPages <= 1} onClick={() => go(page + 1)}>▶</button>
            </div>
          </div>
          <div className="table-responsive" style={{ maxHeight: "55vh", overflow: "auto" }}>
            <table className="table table-sm table-bordered" id="preview-table">
              <thead>
                <tr><th>#</th>{PREVIEW_COLUMNS.map((c) => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {rows.length ? rows.map((row, index) => (
                  <tr key={index} className={row.no_coincidente ? "table-warning" : undefined}>
                    <td>{cell(row.fila)}</td>
                    {PREVIEW_COLUMNS.map((c) => <td key={c}>{cell(row.data?.[c])}</td>)}
                  </tr>
                )) : <tr><td colSpan={8} className="text-center">Sin datos</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" id="btn-cancelar" onClick={close}>Cancelar</button>
          <button className="btn btn-primary" id="btn-procesar" disabled={!canProcess} onClick={() => void processFile(false)}>
            <span className={`spinner-border spinner-border-sm${spin ? "" : " d-none"}`} id="spin-procesar" />{" "}
            Procesar
          </button>
        </div>
      </div>
    </NativeModal>
  );
}

type Reprocess = { kind: "alert-success" | "alert-danger" | "alert-info"; text: string };

function ReprocesarModal({ url, close, report }: { url: string; close: () => void; report: (r: Reprocess) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => input.current?.focus(), 150);
    return () => window.clearTimeout(timer);
  }, []);

  async function confirm() {
    const codigo = (input.current?.value ?? "").trim();
    if (!codigo) {
      report({ kind: "alert-danger", text: "Debés ingresar un código de centro." });
      input.current?.focus();
      return;
    }
    setBusy(true);
    report({ kind: "alert-info", text: `Procesando centro ${codigo}...` });
    try {
      const reply = await fetch(url, {
        method: "POST", credentials: "same-origin",
        headers: { "X-CSRFToken": csrfToken(), "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ codigo }).toString(),
      });
      let data: Record<string, unknown>;
      if ((reply.headers.get("content-type") ?? "").includes("application/json")) data = (await reply.json()) as Record<string, unknown>;
      else data = { ok: false, error: `Respuesta no JSON (status ${reply.status}). ${(await reply.text()).slice(0, 200)}` };
      if (!reply.ok || !data.ok) {
        report({ kind: "alert-danger", text: `Error: ${cell(data.error || data.detail) || `HTTP ${reply.status}`}` });
      } else {
        const porArchivo = record(data.por_archivo)
          ? ` | por archivo: ${Object.entries(data.por_archivo).map(([id, count]) => `${id}:${cell(count)}`).join(", ")}` : "";
        report({ kind: "alert-success", text: `OK. Procesados: ${cell(data.procesados ?? 0)} | Impactados: ${cell(data.impactados ?? 0)}${porArchivo}` });
        close();
      }
    } catch (error) {
      report({ kind: "alert-danger", text: `Error de red: ${error instanceof Error ? error.message : String(error)}` });
    } finally {
      setBusy(false);
    }
  }

  return (
    <NativeModal id="modalReprocesarCentro" title="Reprocesar centro" close={close} size=" modal-sm modal-dialog-centered">
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id="modalReprocesarLabel">Reprocesar centro</h5>
          <button type="button" className="close" aria-label="Cerrar" onClick={close}><span aria-hidden="true">&times;</span></button>
        </div>
        <div className="modal-body">
          <label htmlFor="codigoCentro" className="col-form-label">Código de centro</label>
          <input ref={input} type="text" id="codigoCentro" className="form-control" placeholder="Ej: FARO-001" />
          <small className="form-text text-muted">Ingresá el código exactamente como figura en el sistema.</small>
        </div>
        <div className="modal-footer">
          <button type="button" id="btnConfirmReprocesar" className="btn btn-primary" disabled={busy} onClick={() => void confirm()}>Reprocesar</button>
        </div>
      </div>
    </NativeModal>
  );
}

// --- History list ------------------------------------------------------------------------------

export function CabalListContent({ data }: { data: CabalListData }) {
  const [rows, setRows] = useState(data.results);
  const [sort, setSort] = useState<Sort>({ column: null, direction: null });
  // `listSort.js` edits classList: a header sorted once keeps `sort-icon` before its state class.
  const [touched, setTouched] = useState<string[]>([]);
  const [modal, setModal] = useState<"cabal" | "reprocess" | null>(null);
  const [reprocess, setReprocess] = useState<Reprocess | null>(null);
  // Stable: a new `close` on every render would re-run the modal's focus trap and steal the focus.
  const closeModal = useCallback(() => setModal(null), []);

  function sortBy(column: (typeof COLUMNS)[number]) {
    const direction = sort.column === column.key ? (sort.direction === "asc" ? "desc" : sort.direction === "desc" ? null : "asc") : "asc";
    setSort({ column: direction ? column.key : null, direction });
    setTouched((current) => (current.includes(column.key) ? current : [...current, column.key]));
    if (!direction) return;
    setRows((current) => [...current].sort((a, b) => {
      const value = compare(column.value(a), column.value(b));
      return direction === "asc" ? value : -value;
    }));
  }

  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <div className="container-fluid">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h3 className="mb-0">Historial de Archivos CABAL</h3>
          <div>
            <button className="btn btn-primary" id="btn-open-modal" onClick={() => setModal("cabal")}>
              <span className="spinner-border spinner-border-sm d-none" id="btn-open-modal-spin" />
              Procesar nuevo archivo
            </button>{" "}
            <button id="btn-reprocesar" className="btn btn-warning" data-url={data.urls.reprocess} onClick={() => setModal("reprocess")}>
              Reprocesar rechazados
            </button>{" "}
            <div id="reprocess-result" className={`mt-2 ${reprocess ? "" : "d-none "}alert${reprocess ? ` ${reprocess.kind}` : ""}`} role="alert">{reprocess?.text}</div>
          </div>
        </div>
        {data.alerts.map((a, i) => <div key={i} className={`alert alert-${a.tags} fade show`} role="alert">{a.message}</div>)}
        <div className="card">
          <div className="card-body table-responsive">
            <table className="table table-striped table-bordered projects">
              <thead>
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className={`sortable${sort.column === c.key ? ` sort-${sort.direction}` : ""}`} data-column={c.key} onClick={() => sortBy(c)}>
                      {c.title}{" "}
                      <i className={sort.column === c.key ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}`
                        : touched.includes(c.key) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon"} />
                    </th>
                  ))}
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {rows.length ? rows.map((a) => (
                  <tr key={a.id}>
                    <td data-archivo={a.nombre_original}>{a.nombre_original}</td>
                    <td data-fecha={a.fecha_orden}>{a.fecha_subida}</td>
                    <td data-usuario={a.usuario}>{a.usuario}</td>
                    <td data-total={a.total_filas}>{a.total_filas}</td>
                    <td data-validas={a.total_validas}>{a.total_validas}</td>
                    <td data-invalidas={a.total_invalidas}>{a.total_invalidas}</td>
                    <td><a href={a.urls.detail} className="btn btn-sm btn-info">Ver detalle</a></td>
                  </tr>
                )) : <tr><td colSpan={7} className="text-center">Sin archivos procesados aún.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="card-footer">
            <nav aria-label="Paginación">
              <ul className="pagination mb-0">
                {data.has_previous
                  ? <li className="page-item"><a className="page-link" href={`?page=${data.previous_page}`}>Anterior</a></li>
                  : <li className="page-item disabled"><span className="page-link">Anterior</span></li>}
                <li className="page-item active"><span className="page-link">{data.page}</span></li>
                {data.has_next
                  ? <li className="page-item"><a className="page-link" href={`?page=${data.next_page}`}>Siguiente</a></li>
                  : <li className="page-item disabled"><span className="page-link">Siguiente</span></li>}
              </ul>
            </nav>
          </div>
        </div>
      </div>
      {modal === "cabal" && <ProcesarModal urls={data.urls} close={closeModal} />}
      {modal === "reprocess" && <ReprocesarModal url={data.urls.reprocess} close={closeModal} report={setReprocess} />}
    </>
  );
}

// --- File detail -------------------------------------------------------------------------------

const BADGES = `
  /* Colores de estados más sutiles */
  .badge-success {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
  }
  .badge-danger {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
  }
  .badge-info {
    background-color: #d1ecf1;
    color: #0c5460;
    border: 1px solid #bee5eb;
  }
    `;

export function CabalArchivoContent({ data }: { data: CabalArchivoData }) {
  const { archivo: a } = data;
  const fields: [string, string | number, string?][] = [
    ["Nombre Original", a.nombre_original], ["Fecha de Subida", a.fecha_subida], ["Usuario", a.usuario], ["Total Filas", a.total_filas],
    ["Válidas (Impactadas)", a.total_validas, "text-success"], ["Inválidas (Rechazadas)", a.total_invalidas, "text-danger"],
  ];
  return (
    <>
      <style>{BADGES}</style>
      <div className="container-fluid">
        <div className="mb-3"><a href={data.urls.list} className="btn btn-secondary btn-sm">← Volver</a></div>
        <div className="card mb-3">
          <div className="card-header bg-primary text-white"><h5 className="mb-0">Detalle del Archivo</h5></div>
          <div className="card-body">
            <dl className="row mb-0">
              {fields.map(([label, value, extra]) => (
                <Fragment key={label}>
                  <dt className="col-sm-3">{label}</dt>
                  <dd className={`col-sm-9${extra ? ` ${extra}` : ""}`}>{value}</dd>
                </Fragment>
              ))}
            </dl>
          </div>
        </div>
        <div className="card">
          <div className="card-header bg-secondary text-white">Registros Procesados</div>
          <div className="card-body table-responsive">
            <table className="table table-sm table-bordered table-hover">
              <thead>
                <tr><th>#</th><th>NroComercio</th><th>RazonSocial</th><th>Importe</th><th>FechaTRX</th><th>MonedaOrigen</th><th>ImportePesos</th><th>Pago</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {data.registros.length ? data.registros.map((r) => (
                  <tr key={r.numero}>
                    <td>{r.numero}</td><td>{r.nro_comercio}</td><td>{r.razon_social}</td><td>{r.importe}</td><td>{r.fecha_trx}</td>
                    <td>{r.moneda_origen}</td><td>{r.importe_pesos}</td>
                    <td>{r.pago_aceptado ? <span className="badge badge-success">Pago aceptado</span> : <span className="badge badge-danger">Pago no aceptado</span>}</td>
                    <td>{r.impactado ? <span className="badge badge-success">Impactado</span> : <span className="badge badge-danger">Rechazado</span>}</td>
                  </tr>
                )) : <tr><td colSpan={9} className="text-center">No hay registros asociados a este archivo.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

// --- Registro detail (the native template reads an unset variable) ------------------------------

export function CabalRegistroContent() {
  const fields: [string, string][] = [
    ["Centro", "—"], ["NroComercio", ""], ["RazonSocial", ""], ["FechaTRX", ""], ["Importe", ""], ["ImportePesos", ""],
    ["MonedaOrigen", ""], ["MotivoRechazo", ""], ["Desc Motivo Rechazo", ""], ["No coincidente", "No"], ["Fila (Excel)", ""],
  ];
  return (
    <div className="container">
      <h3>Detalle de Registro CABAL #</h3>
      <div className="card">
        <div className="card-body">
          <dl className="row">
            {fields.map(([label, value]) => (
              <Fragment key={label}>
                <dt className="col-sm-3">{label}</dt>
                <dd className="col-sm-9">{value}</dd>
              </Fragment>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
}

// --- Per-centre detail --------------------------------------------------------------------------

export function CabalCentroContent({ data }: { data: CabalCentroData }) {
  return (
    <div className="card">
      <div className="card-header bg-primary text-white"><h5 className="mb-0">Registros CABAL para {data.centro.nombre}</h5></div>
      <div className="card-body">
        {data.results.length ? (
          <>
            <div className="table-responsive">
              <table className="table table-bordered table-hover table-sm">
                <thead className="thead-dark">
                  <tr><th>#</th><th>Nro Comercio</th><th>Razón Social</th><th>Importe</th><th>Fecha Transacción</th><th>Pago</th></tr>
                </thead>
                <tbody>
                  {data.results.map((r) => (
                    <tr key={r.numero}>
                      <td>{r.numero}</td><td>{r.nro_comercio}</td><td>{r.razon_social}</td><td>{r.importe}</td><td>{r.fecha_trx}</td>
                      {r.pago_aceptado
                        ? <td className="text-success font-weight-bold">Pago aceptado</td>
                        : <td className="text-danger font-weight-bold">Pago no aceptado</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3">{data.count} registros encontrados.</div>
            <div className="mt-2">
              {data.has_previous && <><a href={`?page=${data.previous_page}`} className="btn btn-secondary btn-sm">Anterior</a>{" "}</>}
              <span>Página {data.page} de {data.num_pages}</span>
              {data.has_next && <>{" "}<a href={`?page=${data.next_page}`} className="btn btn-secondary btn-sm">Siguiente</a></>}
            </div>
          </>
        ) : <div className="alert alert-info">No hay registros CABAL para este centro.</div>}
      </div>
    </div>
  );
}

// --- Routes -------------------------------------------------------------------------------------

function List() {
  const state = useCdfPage(`web/cdf/informecabal/${window.location.search}`, listValid);
  return renderWithNativeToasts(state, (data) => ({ title: "Informe Cabal - Historial", breadcrumb: null, content: <CabalListContent data={data} /> }));
}
function Archivo({ id }: { id: string }) {
  const state = useCdfPage(`web/cdf/informecabal/${id}/`, archivoValidator);
  return renderWithNativeToasts(state, (data) => ({ title: "Detalle Archivo CABAL", breadcrumb: null, content: <CabalArchivoContent data={data} /> }));
}
function Registro({ id }: { id: string }) {
  const state = useCdfPage(`web/cdf/informecabal/registro/${id}/`, registroValidator);
  return renderWithNativeToasts(state, () => ({ title: "Detalle Registro CABAL", breadcrumb: null, content: <CabalRegistroContent /> }));
}
function PorCentro({ centro, id }: { centro: string; id: string }) {
  const state = useCdfPage(`web/cdf/centros/${centro}/informecabal/${id}/${window.location.search}`, centroValidator);
  return renderWithNativeToasts(state, (data) => ({ title: `Archivos CABAL - ${data.centro.nombre}`, breadcrumb: null, content: <CabalCentroContent data={data} /> }));
}

type Params = { kind: "list" | "archivo" | "registro" | "centro"; id?: string; centro?: string };

// Native URLs of the CDF Informe Cabal screens (CDF01). `preview/`, `process/` and `reprocess/` stay native AJAX.
export const cdfInformeCabalRoute: RouteDefinition<Params> = {
  name: "cdf-informecabal",
  match: (pathname) => {
    if (pathname === "/centrodefamilia/informecabal/") return { kind: "list" };
    const archivo = /^\/centrodefamilia\/informecabal\/([1-9]\d*)\/$/.exec(pathname);
    if (archivo) return { kind: "archivo", id: archivo[1] };
    const registro = /^\/centrodefamilia\/informecabal\/registro\/([1-9]\d*)\/$/.exec(pathname);
    if (registro) return { kind: "registro", id: registro[1] };
    const centro = /^\/centrodefamilia\/centros\/([1-9]\d*)\/informecabal\/([1-9]\d*)\/$/.exec(pathname);
    return centro ? { kind: "centro", centro: centro[1], id: centro[2] } : null;
  },
  render: ({ kind, id, centro }) => {
    if (kind === "list") return <List />;
    if (kind === "archivo") return <Archivo id={id!} />;
    if (kind === "registro") return <Registro id={id!} />;
    return <PorCentro centro={centro!} id={id!} />;
  },
};
