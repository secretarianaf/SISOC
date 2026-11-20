/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { INSCRIPCION_DETAIL_CSS } from "./vatInscripcionStyles";
import { bool, listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, integer, type Message, type Page } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V03.02 inscripciones: `persona/inscripcion_list.html` and `persona/inscripcion_detail.html`. Data comes from
 * `/api/web/vat/inscripciones-persona/`, which runs the native views; alta, edición and baja are `vatInscripcionForm`.
 */
type Row = {
  id: number; ciudadano: string; comision: string; programa: string; canal: string; fecha: string; estado: string; estado_label: string;
  detail_url: string; update_url: string; delete_url: string;
};
export type InscripcionListData = {
  results: Row[]; page: Page; busqueda: string; permisos: { editar: boolean; eliminar: boolean }; urls: { list: string; create: string }; messages: Message[];
};
export type InscripcionDetailData = {
  id: number; ciudadano: string; dni: string; comision_codigo: string; comision_label: string; programa: string; estado: string; estado_label: string;
  canal: string; fecha_inscripcion: string; fecha_validacion: string; observaciones: string; fecha_creacion: string; fecha_modificacion: string;
  permisos: { editar: boolean; eliminar: boolean }; urls: { comision: string; update: string; delete: string }; messages: Message[];
};

const API = "web/vat/inscripciones-persona/";

const rowValid = (r: unknown) => record(r) && integer(r.id) &&
  ["ciudadano", "comision", "programa", "canal", "fecha", "estado", "estado_label"].every((k) => text(r[k])) &&
  internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export function inscripcionListValid(v: unknown): v is InscripcionListData {
  return record(v) && Array.isArray(v.results) && v.results.every(rowValid) && pageValid(v.page) && text(v.busqueda) &&
    record(v.permisos) && bool(v.permisos.editar) && bool(v.permisos.eliminar) && listUrlsValid(v.urls) && messagesValid(v.messages);
}

export function inscripcionDetailValid(v: unknown): v is InscripcionDetailData {
  return record(v) && integer(v.id) &&
    ["ciudadano", "dni", "comision_codigo", "comision_label", "programa", "estado", "estado_label", "canal", "fecha_inscripcion", "fecha_validacion", "observaciones", "fecha_creacion", "fecha_modificacion"].every((k) => text(v[k])) &&
    record(v.permisos) && bool(v.permisos.editar) && bool(v.permisos.eliminar) &&
    record(v.urls) && internal(v.urls.comision) && internal(v.urls.update) && internal(v.urls.delete) && messagesValid(v.messages);
}

/** The state badge of the list (`badge-validacion`), one branch per state as the template has them. */
function EstadoBadge({ estado, label }: { estado: string; label: string }) {
  if (estado === "completada") {
    return <span className="badge-validacion" style={{ background: "#4b5563", color: "#e5e7eb", borderColor: "#6b7280" }}>
      <i className="fas fa-flag-checkered" />{" "}{label}</span>;
  }
  const [klass, icon] = estado === "inscripta" ? ["validado", "fa-check-circle"]
    : estado === "validada_presencial" ? ["validado", "fa-user-check"]
    : estado === "abandonada" || estado === "rechazada" ? ["no-validado", "fa-times-circle"]
    : ["pendiente", "fa-clock"];
  return <span className={`badge-validacion ${klass}`}><i className={`fas ${icon}`} />{" "}{label}</span>;
}

export function InscripcionListContent({ data }: { data: InscripcionListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Inscripción" placeholder="Buscar por ciudadano, comisión o programa" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
    <VatTable
      headers={[{ title: "Ciudadano", sortable: { column: "ciudadano" } }, { title: "Comisión" }, { title: "Programa" }, { title: "Canal" }, { title: "Fecha" }, { title: "Estado" }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={7} sortValue={(r) => r.ciudadano}
      empty={{ title: "No se encontraron inscripciones", text: "No hay inscripciones que coincidan con los criterios de búsqueda." }}
      renderRow={(i) => <tr key={i.id}>
        <td data-ciudadano={i.ciudadano}><a href={i.detail_url} className="link-handler" title="Ver detalles">{i.ciudadano}</a></td>
        <td>{i.comision}</td>
        <td>{i.programa}</td>
        <td>{i.canal}</td>
        <td>{i.fecha}</td>
        <td><EstadoBadge estado={i.estado} label={i.estado_label} /></td>
        <td><div className="action-buttons" role="group">
          <a href={i.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
          {data.permisos.editar && <>{" "}<a href={i.update_url} className="btn btn-editar link-handler" title="Editar inscripción"><i className="fas fa-edit" />{" "}Editar</a></>}
          {data.permisos.eliminar && <>{" "}<a href={i.delete_url} className="btn btn-eliminar link-handler" title="Eliminar inscripción"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
        </div></td>
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, inscripcionListValid);
  return renderMain(state, "Cargando inscripciones…", (data) => ({ title: "Inscripciones", breadcrumb: null, content: <InscripcionListContent data={data} /> }));
}

const PILL: Record<string, string> = {
  inscripta: "ci-pill-green", pre_inscripta: "ci-pill-yellow", validada_presencial: "ci-pill-blue", completada: "ci-pill-teal", abandonada: "ci-pill-gray", rechazada: "ci-pill-red",
};
const STAT = { flex: 1, padding: ".25rem .5rem" };
const STAT_BORDER = { ...STAT, borderLeft: "1px solid rgba(255,255,255,.12)" };
const STAT_LABEL = { display: "block", marginBottom: ".2rem" };

export function InscripcionDetailContent({ data }: { data: InscripcionDetailData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <style>{INSCRIPCION_DETAIL_CSS}</style>
    <div className="ci-hero">
      <div className="d-flex align-items-start justify-content-between flex-wrap gap-3 mb-3">
        <div className="d-flex align-items-center gap-3">
          <a href={data.urls.comision} className="ci-back"><i className="bi bi-arrow-left" /></a>
          <div>
            <div className="ci-hero-title" style={{ marginTop: 0 }}>{data.ciudadano}</div>
            <div className="ci-hero-sub" style={{ opacity: 0.75, fontSize: ".88rem" }}>
              <i className="bi bi-clipboard-check me-1" />Inscripción a {data.comision_codigo}
            </div>
          </div>
        </div>
        <div className="d-flex align-items-center gap-2 flex-wrap">
          <span className="ci-state-badge">{data.estado_label}</span>
          <span className="ci-state-badge">{data.canal}</span>
          {data.permisos.editar && <a href={data.urls.update} className="ci-edit-btn"><i className="bi bi-pencil me-1" />Editar</a>}
        </div>
      </div>
      <div style={{ background: "rgba(255,255,255,.08)", borderRadius: 8, padding: ".85rem 1.15rem", display: "flex", flexWrap: "wrap", gap: 0 }}>
        <div style={{ ...STAT, minWidth: 100 }}>
          <span className="ci-stat-lbl" style={STAT_LABEL}>Ciudadano</span>
          <span className="ci-stat-val">{data.ciudadano}</span>
        </div>
        <div style={{ ...STAT_BORDER, minWidth: 80 }}>
          <span className="ci-stat-lbl" style={STAT_LABEL}>DNI</span>
          <span className="ci-stat-val" style={{ fontFamily: "monospace" }}>{data.dni}</span>
        </div>
        <div style={{ ...STAT_BORDER, minWidth: 100 }}>
          <span className="ci-stat-lbl" style={STAT_LABEL}>Comisión</span>
          <span className="ci-stat-val">{data.comision_codigo}</span>
        </div>
        <div style={{ ...STAT_BORDER, minWidth: 100 }}>
          <span className="ci-stat-lbl" style={STAT_LABEL}>Fecha inscripción</span>
          <span className="ci-stat-val"><i className="bi bi-calendar3 me-1" style={{ fontSize: ".8rem", opacity: 0.6 }} />{data.fecha_inscripcion}</span>
        </div>
      </div>
    </div>
    <div className="row g-3 align-items-start">
      <div className="col-xl-8">
        <div className="ci-panel">
          <div className="ci-info-grid">
            <div className="ci-info-item"><span className="ci-lbl">Ciudadano</span><span className="ci-val">{data.ciudadano}</span></div>
            <div className="ci-info-item"><span className="ci-lbl">DNI</span><span className="ci-val" style={{ fontFamily: "monospace" }}>{data.dni}</span></div>
            <div className="ci-info-item"><span className="ci-lbl">Comisión</span><span className="ci-val">{data.comision_label}</span></div>
            <div className="ci-info-item"><span className="ci-lbl">Programa</span><span className="ci-val">{data.programa}</span></div>
            <div className="ci-info-item">
              <span className="ci-lbl">Estado</span>
              <span className="ci-val"><span className={`ci-pill ${PILL[data.estado] ?? "ci-pill-gray"}`}>{data.estado_label}</span></span>
            </div>
            <div className="ci-info-item"><span className="ci-lbl">Canal de origen</span><span className="ci-val">{data.canal}</span></div>
            <div className="ci-info-item"><span className="ci-lbl">Fecha inscripción</span><span className="ci-val">{data.fecha_inscripcion}</span></div>
            <div className="ci-info-item"><span className="ci-lbl">Validación presencial</span><span className="ci-val">{data.fecha_validacion}</span></div>
          </div>
          {data.observaciones && <div style={{ margin: "0 1.25rem", padding: ".75rem 1rem", background: "var(--bs-tertiary-bg)", border: "1px solid var(--bs-border-color)", borderRadius: 8, marginBottom: ".5rem" }}>
            <span className="ci-lbl">Observaciones</span>
            <p className="mb-0 small" style={{ color: "var(--bs-body-color)" }}>{data.observaciones}</p>
          </div>}
          <div className="ci-audit">
            <span><i className="bi bi-clock me-1" />Creado {data.fecha_creacion}</span>
            <span><i className="bi bi-pencil me-1" />Modificado {data.fecha_modificacion}</span>
            <span className="ms-auto">#{data.id}</span>
          </div>
        </div>
      </div>
      <div className="col-xl-4">
        <div style={{ position: "sticky", top: "1rem" }}>
          <div className="ci-scard">
            <p className="ci-sc-title">Acciones rápidas</p>
            <div className="d-grid gap-2">
              {data.permisos.editar && <a href={data.urls.update} className="btn btn-primary rounded-3"><i className="bi bi-pencil me-2" />Editar inscripción</a>}
              {data.permisos.eliminar && <a href={data.urls.delete} className="btn btn-outline-danger rounded-3"><i className="bi bi-trash me-2" />Eliminar</a>}
            </div>
          </div>
          <div className="ci-scard">
            <p className="ci-sc-title">Comisión asociada</p>
            <p className="mb-2" style={{ fontSize: ".86rem", fontWeight: 600, color: "var(--bs-body-color)" }}>{data.comision_label}</p>
            <a href={data.urls.comision} className="btn btn-outline-secondary btn-sm rounded-3 w-100"><i className="bi bi-box-arrow-up-right me-1" />Ver comisión</a>
          </div>
        </div>
      </div>
    </div>
  </>;
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, inscripcionDetailValid);
  return renderMain(state, "Cargando inscripción…", (data) => ({ title: `Inscripción — ${data.ciudadano}`, breadcrumb: null, content: <InscripcionDetailContent data={data} /> }));
}

type Params = { id?: string };

// Native URLs of `VAT/urls.py`; `nueva/`, `<id>/editar/` and `<id>/eliminar/` are `vatInscripcionForm`.
const PATH = /^\/vat\/inscripciones\/(?:([0-9]+)\/)?$/;

export const vatInscripcionRoute: RouteDefinition<Params> = {
  name: "vat-inscripcion",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage key={id} id={id} /> : <ListPage />;
  },
};
