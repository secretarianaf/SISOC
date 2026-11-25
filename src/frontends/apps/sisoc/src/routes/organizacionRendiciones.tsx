/* eslint-disable react-refresh/only-export-components -- the module exports its validators, seams and the legajo sections next to the route. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * O04 `organizacion_rendicion_detail.html` (detalle de rendición of an
 * organization) and the rendiciones table and project filter of the legajo
 * (`legajo/rendiciones_tabla.html`, `legajo/filtro_proyecto.html`). The API runs
 * the native `OrganizacionRendicionDetailView`. The PDF download (O04.02) is the
 * job of `rendicioncuentasmensual`: this page calls its endpoints as the native
 * script does (one POST, no retry, 3 s polling up to 15 min).
 */
export type RendicionData = {
  id: number; number: string | number; organization: { id: number; name: string }; project_code: string; convenio: string; number_text: string; period: string;
  process: string; territorial: string; territorial_date: string; audit: string; audit_date: string; validated: string; validated_date: string;
  audited: string; audited_date: string; audit_record_url: string | null; regularized: string; regularized_date: string; complementary_record_url: string | null;
  can_view_rendicion: boolean; can_download_pdf: boolean; urls: { rendicion: string; pdf_request: string; pdf_status: string };
};

const KEYS = ["project_code", "convenio", "number_text", "period", "process", "territorial", "territorial_date", "audit", "audit_date", "validated", "validated_date",
  "audited", "audited_date", "regularized", "regularized_date"];

export function rendicionValid(v: unknown): v is RendicionData {
  return record(v) && typeof v.id === "number" && record(v.organization) && text(v.organization.name) && KEYS.every((k) => text(v[k])) &&
    (v.audit_record_url === null || text(v.audit_record_url)) && (v.complementary_record_url === null || text(v.complementary_record_url)) &&
    record(v.urls) && internal(v.urls.rendicion) && internal(v.urls.pdf_request) && internal(v.urls.pdf_status);
}

/** Navigation seam of the finished download (`window.location.href` in the native script). */
export const pdfNavigation = { assign: (to: string) => window.location.assign(to) };
const POLL_MS = 3000;
const MAX_WAIT_MS = 15 * 60 * 1000;
/** Wall clock outside the component: the wait limit is measured from the click. */
const now = () => Date.now();
const waited = (since: number) => now() - since;
const GENERIC = "No se pudo generar el PDF.";

async function readJson(response: Response): Promise<Record<string, unknown>> {
  const data = await response.json().catch(() => ({})) as Record<string, unknown>;
  if (!response.ok) throw new Error(text(data.mensaje) && data.mensaje ? data.mensaje : GENERIC);
  return data;
}

function PdfAction({ requestUrl, statusUrl }: { requestUrl: string; statusUrl: string }) {
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const started = useRef(0);
  useEffect(() => () => clearTimeout(timer.current), []);

  function process(data: Record<string, unknown>) {
    if (data.estado === "listo" && text(data.url_descarga) && data.url_descarga) {
      setGenerating(false);
      setMessage({ text: "PDF listo. La descarga comienza en unos segundos.", error: false });
      pdfNavigation.assign(data.url_descarga);
      return;
    }
    if (data.estado === "pendiente" || data.estado === "procesando") {
      if (waited(started.current) > MAX_WAIT_MS) throw new Error("La generación del PDF tardó demasiado. Intentá nuevamente.");
      setMessage({ text: "Generando el PDF. Puede tardar unos minutos.", error: false });
      timer.current = setTimeout(poll, POLL_MS);
      return;
    }
    throw new Error(text(data.mensaje) && data.mensaje ? data.mensaje : GENERIC);
  }
  const fail = (error: unknown) => { setGenerating(false); setMessage({ text: error instanceof Error ? error.message : GENERIC, error: true }); };
  function poll() {
    fetch(statusUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } }).then(readJson).then(process).catch(fail);
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    started.current = now();
    setGenerating(true);
    setMessage(null);
    const body = new FormData();
    const csrf = leerCookie("csrftoken");
    if (csrf) body.append("csrfmiddlewaretoken", csrf);
    fetch(requestUrl, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest", ...(csrf ? { "X-CSRFToken": csrf } : {}) }, body })
      .then(readJson).then(process).catch(fail);
  }
  return (
    <form className="d-inline js-pdf-descarga-form" method="post" action={requestUrl} onSubmit={submit}>
      <button type="submit" className="btn btn-sm btn-outline-success" disabled={generating}>
        <span className={`js-submit-idle${generating ? " d-none" : ""}`}><i className="fas fa-file-pdf" /> Descargar</span>
        <span className={`js-submit-spinner${generating ? "" : " d-none"}`}><span className="spinner-border spinner-border-sm" aria-hidden="true" /> Generando PDF…</span>
      </button>
      <div className={`small mt-1 js-pdf-descarga-mensaje ${message ? (message.error ? "text-danger" : "text-muted") : ""}`} role="status" aria-live="polite">{message?.text ?? ""}</div>
    </form>
  );
}

const Item = ({ label, children }: { label: string; children: ReactNode }) => (
  <div className="col-md-4"><small className="text-muted d-block">{label}</small>{children}</div>
);
const Value = ({ children }: { children: ReactNode }) => <strong>{children}</strong>;
const FileLink = ({ url }: { url: string | null }) => (url ? <a href={url} target="_blank" rel="noreferrer">Ver archivo</a> : <strong>-</strong>);

function Detalle({ data }: { data: RendicionData }) {
  return (
    <div className="container-fluid py-4">
      <div className="card shadow-sm">
        <div className="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div>
            <h4 className="mb-1">Rendición {data.number}</h4>
            <small>{data.organization.name}</small>
          </div>
          <div className="d-flex gap-2">
            {data.can_view_rendicion && <a className="btn btn-primary" href={data.urls.rendicion}>Ir a Rendición</a>}
          </div>
        </div>
        <div className="card-body">
          <div className="row g-4">
            <Item label="Código de Proyecto"><Value>{data.project_code}</Value></Item>
            <Item label="Convenio"><Value>{data.convenio}</Value></Item>
            <Item label="Número de Rendición"><Value>{data.number_text}</Value></Item>
            <Item label="Período"><Value>{data.period}</Value></Item>
            <Item label="Estado del proceso"><Value>{data.process}</Value></Item>
            <Item label="Validación Territorial"><Value>{data.territorial}</Value></Item>
            <Item label="Fecha de Validación Territorial"><Value>{data.territorial_date}</Value></Item>
            <Item label="Validación Auditoría"><Value>{data.audit}</Value></Item>
            <Item label="Fecha de Validación Auditoría"><Value>{data.audit_date}</Value></Item>
            <Item label="Validación"><Value>{data.validated}</Value></Item>
            <Item label="Fecha de Validación"><Value>{data.validated_date}</Value></Item>
            <Item label="PDF Rendición">{data.can_download_pdf ? <PdfAction requestUrl={data.urls.pdf_request} statusUrl={data.urls.pdf_status} /> : <Value>-</Value>}</Item>
            <Item label="Auditada"><Value>{data.audited}</Value></Item>
            <Item label="Fecha de Auditada"><Value>{data.audited_date}</Value></Item>
            <Item label="PDF Acta de Auditoría"><FileLink url={data.audit_record_url} /></Item>
            <Item label="Regularización de Rendición"><Value>{data.regularized}</Value></Item>
            <Item label="Fecha de Regularización"><Value>{data.regularized_date}</Value></Item>
            <Item label="Acta Complementaria"><FileLink url={data.complementary_record_url} /></Item>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function OrganizacionRendicion({ id, rendicionId }: { id: number; rendicionId: number }) {
  const [state] = useMainResource(`web/comedores/organizaciones/${id}/rendiciones/${rendicionId}/`, rendicionValid);
  return renderMain(state, "Cargando rendición…", (data) => ({ title: "Detalle de Rendición", breadcrumb: <></>, content: <Detalle data={data} /> }));
}

// --- legajo sections ---------------------------------------------------------------------------

type TableRow = {
  id: number; line: string | null; line_label: string | null; project: string; convenio: string; number: string; period: string;
  territorial: boolean; audit: boolean; validated: boolean; audited: boolean; url: string;
};
export type RendicionesSection = { kind: "rendiciones"; show_line: boolean; rows: TableRow[] };
export type RendicionesFiltroSection = { kind: "rendiciones_filtro"; codes: string[]; selected: string; program_id: number | null };

export const rendicionesSectionValid = (v: unknown): v is RendicionesSection =>
  record(v) && v.kind === "rendiciones" && Array.isArray(v.rows) && v.rows.every((r) => record(r) && text(r.convenio) && text(r.period) && internal(r.url));
export const rendicionesFiltroValid = (v: unknown): v is RendicionesFiltroSection =>
  record(v) && v.kind === "rendiciones_filtro" && Array.isArray(v.codes) && v.codes.every(text) && text(v.selected);

const mark = (on: boolean) => (on ? "✔" : "-");

export function RendicionesTable({ section }: { section: RendicionesSection }) {
  return (
    <div className="table-responsive">
      <table className="table table-sm align-middle">
        <thead>
          <tr>
            {section.show_line && <><th>Línea</th><th>Proyecto</th></>}
            <th>Conv.</th><th>N° de Rend.</th><th>Período</th><th>Validación Territorial</th><th>Revisión para Carga</th><th>Validación</th><th>Auditada</th><th>Detalle</th>
          </tr>
        </thead>
        <tbody>
          {section.rows.map((row) => (
            <tr key={row.id}>
              {section.show_line && (
                <>
                  <td>{row.line ? <span className={`badge badge-linea-${row.line}`}>{row.line_label}</span> : <span className="badge badge-pendiente">Sin línea</span>}</td>
                  <td>{row.project}</td>
                </>
              )}
              <td>{row.convenio}</td><td>{row.number}</td><td>{row.period}</td>
              <td>{mark(row.territorial)}</td><td>{mark(row.audit)}</td><td>{mark(row.validated)}</td><td>{mark(row.audited)}</td>
              <td><a className="btn btn-sm btn-outline-light" href={row.url}>Ver</a></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The filter is a real GET form: the legajo reloads with `proyecto=` exactly as the native page does. */
export function RendicionesFiltro({ section }: { section: RendicionesFiltroSection }) {
  if (section.codes.length > 1) {
    return (
      <form method="get" className="d-flex align-items-end gap-2">
        {section.program_id !== null && <input type="hidden" name="programa" value={section.program_id} />}
        <input type="hidden" name="seccion" value="rendiciones" />
        <div>
          <label htmlFor="proyecto-rendiciones" className="form-label mb-1">Código de Proyecto</label>
          <select id="proyecto-rendiciones" name="proyecto" className="form-select form-select-sm" defaultValue={section.selected}>
            <option value="">Todos los proyectos</option>
            {section.codes.map((code) => <option key={code} value={code}>{code}</option>)}
          </select>
        </div>
        <button type="submit" className="btn btn-sm btn-outline-light">Filtrar</button>
      </form>
    );
  }
  if (section.codes.length === 1) return <div><small className="d-block text-white-50">Código de Proyecto</small><strong>{section.codes[0]}</strong></div>;
  return null;
}

// Native URL (trailing slash, as `urls.py` declares it).
export const organizacionRendicionesRoute: RouteDefinition<{ id: number; rendicionId: number }> = {
  name: "comedores-organizaciones-rendiciones",
  match(pathname) {
    const found = /^\/organizaciones\/([1-9]\d{0,14})\/rendiciones\/([1-9]\d{0,14})\/detalle\/$/.exec(pathname);
    return found ? { id: Number(found[1]), rendicionId: Number(found[2]) } : null;
  },
  render: ({ id, rendicionId }) => <OrganizacionRendicion id={id} rendicionId={rendicionId} />,
};
