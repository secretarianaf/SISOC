/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { bool, integer, messagesValid, type Message } from "./vatShared";
import { CURSO_DETALLE_CSS } from "./vatCursoDetalleStyles";
import type { RouteDefinition } from "./types";

/**
 * V05.01 course detail: `curso/curso_detail.html` (read only). Data comes from `/api/web/vat/cursos-detalle/<id>/`, which runs the
 * native `CursoDetailView`; «Editar curso» is drawn only when the view says the user can edit it. The create, edit and delete
 * forms live in `vatCursoForm.tsx`; `/vat/cursos/<id>/` is the only URL this module owns.
 */
export type CursoDetailData = {
  id: number; nombre: string; centro: string; plan_titulo: string; plan: string; estado: string; estado_label: string; tipo: string;
  prioritario: string; inscripcion_libre: string; observaciones: string; usa_voucher: string; costo_creditos: string; vouchers: string[];
  comisiones_count: number; puede_editar: boolean; urls: { update: string }; messages: Message[];
};

const API = "web/vat/cursos-detalle/";

export const cursoDetailValid = (v: unknown): v is CursoDetailData => record(v) && integer(v.id) &&
  ["nombre", "centro", "plan_titulo", "plan", "estado", "estado_label", "tipo", "prioritario", "inscripcion_libre", "observaciones", "usa_voucher", "costo_creditos"].every((k) => text(v[k])) &&
  Array.isArray(v.vouchers) && v.vouchers.every(text) && integer(v.comisiones_count) && bool(v.puede_editar) && record(v.urls) && internal(v.urls.update) && messagesValid(v.messages);

export function CursoDetailContent({ data }: { data: CursoDetailData }) {
  const item = (label: string, value: string, full = false) => <div className={`sisoc-data-item${full ? " sisoc-data-item--full" : ""}`}>
    <p className="sisoc-data-label">{label}</p><p className="sisoc-data-value">{value}</p>
  </div>;
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
    <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>{CURSO_DETALLE_CSS}</style>
    <div className="sisoc-curso-page">
      <div className="sisoc-title-row">
        <div className="sisoc-title-block">
          <p className="sisoc-title-kicker">Curso</p>
          <h1>{data.nombre}</h1>
          <p className="sisoc-title-sub">{data.plan_titulo} · {data.centro}</p>
        </div>
        <div className="sisoc-title-actions">
          <span className={`sisoc-status-pill sisoc-status-pill--${data.estado}`}>{data.estado_label}</span>
          {data.puede_editar && <a href={data.urls.update} className="sisoc-edit-btn"><i className="fas fa-pen" />{" "}Editar curso</a>}
        </div>
      </div>
      <div className="sisoc-panels-grid">
        <div>
          <section className="sisoc-panel">
            <div className="sisoc-panel-header"><h2>Datos del curso</h2></div>
            <div className="sisoc-panel-body"><div className="sisoc-data-grid">
              {item("Plan de estudio", data.plan)}
              {item("Estado", data.estado_label)}
              {item("Tipo", data.tipo)}
              {item("Prioritario", data.prioritario)}
              {item("Inscripción libre", data.inscripcion_libre)}
              {item("Observaciones", data.observaciones, true)}
            </div></div>
          </section>
        </div>
        <div>
          <section className="sisoc-panel">
            <div className="sisoc-panel-header"><h2>Parametría de voucher</h2></div>
            <div className="sisoc-panel-body"><div className="sisoc-data-grid">
              {item("Usa voucher", data.usa_voucher)}
              {item("Costo en créditos", data.costo_creditos)}
              <div className="sisoc-data-item sisoc-data-item--full">
                <p className="sisoc-data-label">Vouchers habilitados</p>
                {data.vouchers.length
                  ? <ul className="sisoc-voucher-list">{data.vouchers.map((nombre, n) => <li key={n}><i className="fas fa-ticket-alt" />{nombre}</li>)}</ul>
                  : <p className="sisoc-data-value">-</p>}
              </div>
            </div></div>
          </section>
          <section className="sisoc-panel">
            <div className="sisoc-panel-header"><h2>Comisiones</h2></div>
            <div className="sisoc-panel-body">
              <p className="sisoc-data-label">Comisiones vinculadas</p>
              <p className="sisoc-metric-value">{data.comisiones_count}</p>
            </div>
          </section>
        </div>
      </div>
    </div>
  </>;
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, cursoDetailValid);
  return renderMain(state, "Cargando curso…", (data) => ({ title: `${data.nombre} - Curso`, breadcrumb: null, content: <CursoDetailContent data={data} /> }));
}

type Params = { id: string };

// Native URL `vat_curso_detail`; `nuevo/`, `<id>/editar/` and `<id>/eliminar/` belong to the form module.
const PATH = /^\/vat\/cursos\/([0-9]+)\/$/;

export const vatCursoDetalleRoute: RouteDefinition<Params> = {
  name: "vat-curso-detalle",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return <DetailPage key={id} id={id} />;
  },
};
