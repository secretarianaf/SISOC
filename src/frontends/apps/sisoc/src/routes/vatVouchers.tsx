/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import type { ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { renderMain, record, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import {
  bool, integer, listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, vatNavigation,
  type Message, type Page,
} from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V01.01 vouchers and parametrías: `voucher_list.html`, `voucher_detail.html` and
 * `parametria_list.html`. Data comes from `/api/web/vat/vouchers/`, which runs the native views;
 * dates and labels arrive formatted. The credit actions (recargar, cancelar) stay the native
 * POST forms of the detail, sent to their own URLs.
 */
type Urls = { list: string; create: string };
type Row = {
  id: number; ciudadano: string; documento: string; programa: string; disponible: number; inicial: number;
  vencimiento: string; estado: string; estado_label: string; detail_url: string;
};
export type VoucherListData = { results: Row[]; page: Page; busqueda: string; urls: Urls; messages: Message[] };
type ParametriaRow = {
  id: number; nombre: string; programa: string; cantidad_inicial: number; vencimiento: string; activa: boolean; vouchers: number; detail_url: string;
};
export type ParametriaListData = { results: ParametriaRow[]; page: Page; busqueda: string; urls: Urls; messages: Message[] };
type Campo = { name: string; id: string; label: string; required: boolean; tag: "input" | "select"; min: number | null; choices: { value: string; label: string }[] };
export type VoucherDetailData = {
  id: number; ciudadano: string; documento: string; programa: string; estado: string; estado_label: string; disponible: number; inicial: number;
  porcentaje: string; asignado_por: string; fecha_asignacion: string; vencimiento: string; dias_para_vencer: number;
  usos: { fecha: string; oferta: string; cantidad: number }[];
  recargas: { fecha: string; motivo: string; por: string; cantidad: number }[];
  logs: { tipo_evento: string; fecha: string }[];
  acciones: { recargar: boolean; cancelar: boolean; recargar_url: string; cancelar_url: string; campos: Campo[] };
  messages: Message[];
};

const API = "web/vat/vouchers/";
const ACTIVE = "/vat/vouchers/parametrias/";
const internalPath = (v: unknown) => text(v) && v.startsWith("/") && !v.startsWith("//");

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["ciudadano", "documento", "programa", "vencimiento", "estado", "estado_label"].every((k) => text(r[k])) &&
  integer(r.disponible) && integer(r.inicial) && internalPath(r.detail_url);
const parametriaValid = (r: unknown) => record(r) && integer(r.id) && text(r.nombre) && text(r.programa) && integer(r.cantidad_inicial) && text(r.vencimiento) &&
  bool(r.activa) && integer(r.vouchers) && internalPath(r.detail_url);

export function voucherListValid(v: unknown): v is VoucherListData {
  return record(v) && Array.isArray(v.results) && v.results.every(rowValid) && pageValid(v.page) && text(v.busqueda) && listUrlsValid(v.urls) && messagesValid(v.messages);
}
export function parametriaListValid(v: unknown): v is ParametriaListData {
  return record(v) && Array.isArray(v.results) && v.results.every(parametriaValid) && pageValid(v.page) && text(v.busqueda) && listUrlsValid(v.urls) && messagesValid(v.messages);
}
const campoValid = (c: unknown) => record(c) && text(c.name) && text(c.id) && text(c.label) && bool(c.required) && (c.tag === "input" || c.tag === "select") &&
  (c.min === null || integer(c.min)) && Array.isArray(c.choices) && c.choices.every((o) => record(o) && text(o.value) && text(o.label));
export function voucherDetailValid(v: unknown): v is VoucherDetailData {
  if (!record(v) || !record(v.acciones)) return false;
  const a = v.acciones;
  return integer(v.id) && ["ciudadano", "documento", "programa", "estado", "estado_label", "porcentaje", "asignado_por", "fecha_asignacion", "vencimiento"].every((k) => text(v[k])) &&
    integer(v.disponible) && integer(v.inicial) && integer(v.dias_para_vencer) &&
    Array.isArray(v.usos) && v.usos.every((u) => record(u) && text(u.fecha) && text(u.oferta) && integer(u.cantidad)) &&
    Array.isArray(v.recargas) && v.recargas.every((r) => record(r) && text(r.fecha) && text(r.motivo) && text(r.por) && integer(r.cantidad)) &&
    Array.isArray(v.logs) && v.logs.every((l) => record(l) && text(l.tipo_evento) && text(l.fecha)) &&
    bool(a.recargar) && bool(a.cancelar) && internalPath(a.recargar_url) && internalPath(a.cancelar_url) && Array.isArray(a.campos) && a.campos.every(campoValid) &&
    messagesValid(v.messages);
}

// --- Voucher list (`voucher_list.html`) -------------------------------------

function EstadoBadge({ estado, label }: { estado: string; label: string }) {
  if (estado === "activo") return <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}{label}</span>;
  if (estado === "vencido") return <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}{label}</span>;
  if (estado === "agotado") return <span className="badge-validacion pendiente"><i className="fas fa-exclamation-circle" />{" "}{label}</span>;
  return <span className="badge-validacion" style={{ background: "#4b5563", color: "#e5e7eb", borderColor: "#6b7280" }}><i className="fas fa-minus-circle" />{" "}{label}</span>;
}

function ViewButton({ url }: { url: string }) {
  return <td><div className="action-buttons" role="group">
    <a href={url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
  </div></td>;
}

export function VoucherListContent({ data }: { data: VoucherListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Voucher" placeholder="Buscar por nombre o DNI" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Asignar" }} />
    <VatTable
      headers={[{ title: "Ciudadano", sortable: { column: "ciudadano" } }, { title: "DNI" }, { title: "Programa" }, { title: "Créditos" }, { title: "Vencimiento" }, { title: "Estado" }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={7} sortValue={(r) => r.ciudadano}
      empty={{ title: "No se encontraron vouchers", text: "No hay vouchers registrados." }}
      renderRow={(v) => <tr key={v.id}>
        <td data-ciudadano={v.ciudadano}>{v.ciudadano}</td>
        <td>{v.documento}</td>
        <td>{v.programa}</td>
        <td><strong>{v.disponible}</strong>{" "}<span style={{ opacity: 0.6 }}>/ {v.inicial}</span></td>
        <td>{v.vencimiento}</td>
        <td><EstadoBadge estado={v.estado} label={v.estado_label} /></td>
        <ViewButton url={v.detail_url} />
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, voucherListValid);
  return renderMain(state, "Cargando vouchers…", (data) => ({ title: "Vouchers", breadcrumb: null, activePath: ACTIVE, content: <VoucherListContent data={data} /> }));
}

// --- Parametría list (`parametria_list.html`) --------------------------------

export function ParametriaListContent({ data }: { data: ParametriaListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Parametría" placeholder="Buscar por nombre o programa" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
    <VatTable
      headers={[{ title: "Nombre", sortable: { column: "nombre" } }, { title: "Programa" }, { title: "Créditos" }, { title: "Vencimiento" }, { title: "Estado" }, { title: "Vouchers" }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={7} sortValue={(r) => r.nombre}
      empty={{ title: "No se encontraron parametrías", text: "No hay parametrías registradas." }}
      renderRow={(p) => <tr key={p.id}>
        <td data-nombre={p.nombre}><a href={p.detail_url} className="link-handler" title="Ver detalles">{p.nombre}</a></td>
        <td>{p.programa}</td>
        <td>{p.cantidad_inicial}</td>
        <td>{p.vencimiento}</td>
        <td>{p.activa
          ? <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}Activa</span>
          : <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}Inactiva</span>}</td>
        <td>{p.vouchers}</td>
        <ViewButton url={p.detail_url} />
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
  </>;
}

function ParametriaListPage() {
  const [state] = useMainResource(`${API}parametrias/${window.location.search}`, parametriaListValid);
  return renderMain(state, "Cargando parametrías…", (data) => ({ title: "Parametrías de Voucher", breadcrumb: null, activePath: ACTIVE, content: <ParametriaListContent data={data} /> }));
}

// --- Voucher detail (`voucher_detail.html`) ----------------------------------

const CARD_HEADER = "card-header d-flex justify-content-between align-items-center";

function Counter({ children }: { children: ReactNode }) {
  return <span className="badge bg-secondary">{children}</span>;
}

function CsrfToken() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

function RecargaForm({ data }: { data: VoucherDetailData }) {
  const { acciones } = data;
  return (
    <div className="card mb-3">
      <div className="card-header"><h3 className="card-title mb-0"><i className="bi bi-plus-circle me-2" />Recarga manual</h3></div>
      <div className="card-body">
        <form method="post" action={acciones.recargar_url}>
          <CsrfToken />
          {acciones.campos.map((c) => <div key={c.name} className="mb-2">
            <label className="form-label fw-semibold small">{c.label}</label>
            {c.tag === "select"
              ? <select name={c.name} className="form-control" required={c.required} id={c.id}>{c.choices.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
              : <input type="number" name={c.name} className="form-control" min={c.min ?? undefined} required={c.required} id={c.id} />}
          </div>)}
          <button type="submit" className="btn btn-sm btn-success w-100"><i className="bi bi-battery-charging me-1" />Recargar</button>
        </form>
      </div>
    </div>
  );
}

function CancelarForm({ data }: { data: VoucherDetailData }) {
  return (
    <div className="card mb-3 border-danger-subtle">
      <div className="card-header bg-danger-subtle"><h3 className="card-title mb-0 text-danger"><i className="bi bi-x-circle me-2" />Cancelar voucher</h3></div>
      <div className="card-body">
        <p className="small text-muted mb-2">Esta acción cancela el voucher. No se pueden deshacer los usos ya realizados.</p>
        <form method="post" action={data.acciones.cancelar_url} onSubmit={(e) => { if (!vatNavigation.confirm("¿Cancelar este voucher?")) e.preventDefault(); }}>
          <CsrfToken />
          <button type="submit" className="btn btn-sm btn-outline-danger w-100"><i className="bi bi-x-lg me-1" />Cancelar voucher</button>
        </form>
      </div>
    </div>
  );
}

function estadoBadgeClass(estado: string) {
  return estado === "activo" ? "bg-success" : estado === "vencido" ? "bg-danger" : estado === "agotado" ? "bg-warning text-dark" : "bg-secondary";
}

export function VoucherDetailContent({ data }: { data: VoucherDetailData }) {
  const { disponible, inicial, estado } = data;
  const creditsClass = disponible === 0 ? "text-danger" : estado === "activo" ? "text-success" : "text-secondary";
  const barClass = disponible === 0 ? "bg-danger" : disponible < inicial ? "bg-warning" : "bg-success";
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/cardsDetail.css" />
    <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
      <div>
        <h4 className="mb-1 fw-semibold">{data.ciudadano}</h4>
        <span className="text-muted small">DNI {data.documento} · {data.programa}</span>
      </div>
      <div className="d-flex gap-2 align-items-center">
        <span className={`badge fs-6 ${estadoBadgeClass(estado)}`}>{data.estado_label}</span>
      </div>
    </div>

    <div className="row g-3 mb-3">
      <div className="col-md-4"><div className="card h-100"><div className="card-body text-center">
        <div className="text-muted small mb-1">Créditos disponibles</div>
        <div className={`display-5 fw-bold ${creditsClass}`}>{disponible}</div>
        <div className="text-muted small">de {inicial} iniciales</div>
        <div className="progress mt-2" style={{ height: "8px" }}><div className={`progress-bar ${barClass}`} style={{ width: `${data.porcentaje}%` }} /></div>
      </div></div></div>
      <div className="col-md-8"><div className="card h-100"><div className="card-body">
        <dl className="row mb-0 small">
          <dt className="col-sm-4 text-muted">Programa</dt>
          <dd className="col-sm-8">{data.programa}</dd>
          <dt className="col-sm-4 text-muted">Asignado por</dt>
          <dd className="col-sm-8">{data.asignado_por}</dd>
          <dt className="col-sm-4 text-muted">Fecha asignación</dt>
          <dd className="col-sm-8">{data.fecha_asignacion}</dd>
          <dt className="col-sm-4 text-muted">Vencimiento</dt>
          <dd className={`col-sm-8 ${estado === "vencido" ? "text-danger fw-semibold" : ""}`}>{data.vencimiento}</dd>
          <dt className="col-sm-4 text-muted">Días restantes</dt>
          <dd className="col-sm-8">{data.dias_para_vencer > 0
            ? <span className="text-success">{data.dias_para_vencer} días</span>
            : <span className="text-danger">Vencido</span>}</dd>
        </dl>
      </div></div></div>
    </div>

    <div className="row g-3">
      <div className="col-md-7">
        <div className="card">
          <div className={CARD_HEADER}><h3 className="card-title mb-0"><i className="bi bi-receipt me-2" />Usos</h3><Counter>{data.usos.length}</Counter></div>
          <div className="card-body p-0">
            {data.usos.length ? (
              <table className="table table-sm table-hover mb-0">
                <thead className="table-light"><tr><th>Fecha</th><th>Oferta</th><th className="text-end">Créditos</th></tr></thead>
                <tbody>{data.usos.map((u, i) => <tr key={i}>
                  <td className="text-muted small">{u.fecha}</td><td>{u.oferta}</td><td className="text-end fw-semibold text-danger">-{u.cantidad}</td>
                </tr>)}</tbody>
              </table>
            ) : <p className="text-muted small text-center py-3 mb-0">Sin usos registrados.</p>}
          </div>
        </div>
        <div className="card mt-3">
          <div className={CARD_HEADER}><h3 className="card-title mb-0"><i className="bi bi-battery-charging me-2" />Recargas</h3><Counter>{data.recargas.length}</Counter></div>
          <div className="card-body p-0">
            {data.recargas.length ? (
              <table className="table table-sm table-hover mb-0">
                <thead className="table-light"><tr><th>Fecha</th><th>Motivo</th><th>Por</th><th className="text-end">Créditos</th></tr></thead>
                <tbody>{data.recargas.map((r, i) => <tr key={i}>
                  <td className="text-muted small">{r.fecha}</td><td>{r.motivo}</td><td className="text-muted small">{r.por}</td>
                  <td className="text-end fw-semibold text-success">+{r.cantidad}</td>
                </tr>)}</tbody>
              </table>
            ) : <p className="text-muted small text-center py-3 mb-0">Sin recargas registradas.</p>}
          </div>
        </div>
      </div>
      <div className="col-md-5">
        {data.acciones.recargar && <RecargaForm data={data} />}
        {data.acciones.cancelar && <CancelarForm data={data} />}
        <div className="card">
          <div className={CARD_HEADER}><h3 className="card-title mb-0"><i className="bi bi-clock-history me-2" />Historial</h3><Counter>{data.logs.length}</Counter></div>
          <div className="card-body p-0">
            {data.logs.length ? (
              <ul className="list-group list-group-flush">{data.logs.map((log, i) => <li key={i} className="list-group-item py-2 px-3">
                <div className="d-flex justify-content-between">
                  <span className="badge bg-light text-dark border small">{log.tipo_evento}</span>
                  <span className="text-muted small">{log.fecha}</span>
                </div>
              </li>)}</ul>
            ) : <p className="text-muted small text-center py-3 mb-0">Sin eventos registrados.</p>}
          </div>
        </div>
      </div>
    </div>
  </>;
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, voucherDetailValid);
  return renderMain(state, "Cargando voucher…", (data) => ({
    title: `Voucher — ${data.ciudadano}`, heading: "Detalle de Voucher", breadcrumb: null, activePath: ACTIVE, content: <VoucherDetailContent data={data} />,
  }));
}

type Params = { mode: "list" | "parametrias" | "detail"; id?: string };

// Native URLs of `VAT/urls.py`; `asignar/`, `asignar-masivo/`, `parametrias/<id>/` and the POST routes are not mine.
const PATH = /^\/vat\/vouchers\/(?:(parametrias\/)|([0-9]+)\/)?$/;

export const vatVouchersRoute: RouteDefinition<Params> = {
  name: "vat-vouchers",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    if (m[1]) return { mode: "parametrias" };
    return m[2] ? { mode: "detail", id: m[2] } : { mode: "list" };
  },
  render({ mode, id }) {
    if (mode === "parametrias") return <ParametriaListPage />;
    if (mode === "detail") return <DetailPage key={id} id={id!} />;
    return <ListPage />;
  },
};
