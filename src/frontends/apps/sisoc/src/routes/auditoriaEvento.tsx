import { Breadcrumb, internal, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * Audit event detail: `audittrail/log_detail.html`. GET `/api/web/auditoria/evento/<id>/` (+ the page query, whose
 * `next` the native view validates into `volver_url`) runs `AuditLogDetailView` (403 without `auditlog.view_logentry`,
 * 404 for an unknown event). Values arrive formatted; only "No cargado" is emphasised. Values whose text without tags
 * passes 180 characters carry the `preview` the template shows in `<summary>`. Read only.
 */
type Valor = { empty: boolean; text: string; preview: string | null };
export type EventoData = {
  id: number; inicio_url: string; volver_url: string; fecha_texto: string; actor_texto: string; actor_fallback: boolean;
  actor_secundario: string; modelo_texto: string; instancia_texto: string; evento_texto: string; evento_clase: string;
  con_diffs: boolean; aviso_masivo: string; origen_texto: string; batch_key: string; ip_texto: string; es_eliminacion: boolean;
  cambios: { campo: string; old: Valor; new: Valor }[];
};

const flag = (v: unknown) => typeof v === "boolean";
const valor = (v: unknown) => record(v) && flag(v.empty) && text(v.text) && (v.preview === null || text(v.preview));

export function eventoValid(v: unknown): v is EventoData {
  return record(v) && Number.isSafeInteger(v.id) && internal(v.inicio_url) && internal(v.volver_url) &&
    ["fecha_texto", "actor_texto", "actor_secundario", "modelo_texto", "instancia_texto", "evento_texto", "evento_clase", "aviso_masivo", "origen_texto", "batch_key", "ip_texto"]
      .every((k) => text(v[k])) && flag(v.actor_fallback) && flag(v.con_diffs) && flag(v.es_eliminacion) &&
    Array.isArray(v.cambios) && v.cambios.every((c) => record(c) && text(c.campo) && valor(c.old) && valor(c.new));
}

function Contenido({ v }: { v: Valor }) {
  return v.empty ? <em>No cargado</em> : <>{v.text}</>;
}

function Celda({ v }: { v: Valor }) {
  const style = { whiteSpace: "pre-wrap" as const };
  return (
    <td className="align-top">
      {v.preview !== null ? (
        <details>
          <summary className="text-muted">{v.preview}</summary>
          <div className="mt-2 text-break" style={style}><Contenido v={v} /></div>
        </details>
      ) : <div className="text-break" style={style}><Contenido v={v} /></div>}
    </td>
  );
}

export function EventoContent({ data }: { data: EventoData }) {
  return (
    <>
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header"><h3 className="card-title">Evento #{data.id}</h3></div>
            <div className="card-body">
              <dl className="row mb-0">
                <dt className="col-sm-3">Fecha</dt>
                <dd className="col-sm-9">{data.fecha_texto}</dd>
                <dt className="col-sm-3">Usuario</dt>
                <dd className="col-sm-9">
                  <div className={data.actor_fallback ? "text-muted" : ""}>{data.actor_texto}</div>
                  {data.actor_secundario && <small className="text-muted d-block">{data.actor_secundario}</small>}
                </dd>
                <dt className="col-sm-3">Modelo</dt>
                <dd className="col-sm-9">{data.modelo_texto}</dd>
                <dt className="col-sm-3">ID de instancia</dt>
                <dd className="col-sm-9">{data.instancia_texto}</dd>
                <dt className="col-sm-3">Evento</dt>
                <dd className="col-sm-9">
                  <span className={`badge ${data.evento_clase}`}>{data.evento_texto}</span>
                  {!data.con_diffs && <>{" "}<span className="badge bg-warning text-dark ms-1">Sin diffs</span></>}
                  {data.aviso_masivo && <>{" "}<small className="text-muted d-block mt-1">{data.aviso_masivo}</small></>}
                </dd>
                <dt className="col-sm-3">Origen</dt>
                <dd className="col-sm-9">
                  {data.origen_texto}
                  {data.batch_key && <>{" "}<small className="text-muted d-block">Batch key: {data.batch_key}</small></>}
                </dd>
                <dt className="col-sm-3">IP</dt>
                <dd className="col-sm-9">{data.ip_texto}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                Cambios{" "}
                {data.cambios.length > 0 ? <span className="badge bg-secondary">{data.cambios.length}</span> : <span className="badge bg-warning text-dark">Sin diffs</span>}
              </h3>
            </div>
            <div className="card-body">
              {data.cambios.length > 0 ? (
                <div className="table-responsive">
                  <table className="table table-striped">
                    <thead><tr><th>Campo</th><th>Valor anterior</th><th>Valor nuevo</th></tr></thead>
                    <tbody>
                      {data.cambios.map((c) => (
                        <tr key={c.campo}>
                          <td className="align-top"><strong>{c.campo}</strong></td>
                          <Celda v={c.old} />
                          <Celda v={c.new} />
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="alert alert-light mb-0" role="status">
                  <div className="fw-semibold">Sin diffs registrados para este evento.</div>
                  <div className="small text-muted mt-1">
                    {data.es_eliminacion ? "Las eliminaciones o eventos automáticos pueden no incluir detalle de cambios." : "El backend no expuso diferencias para este evento."}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function EventoPage({ id }: { id: string }) {
  const [state] = useMainResource(`web/auditoria/evento/${id}/${window.location.search}`, eventoValid);
  return renderMain(state, "Cargando evento…", (data) => ({
    title: "Detalle auditoría", activePath: "/auditoria/",
    heading: "Detalle de auditoría",
    breadcrumb: <Breadcrumb items={[{ text: "Inicio", url: data.inicio_url }, { text: "Auditoría", url: data.volver_url }, { text: `Evento ${data.id}`, url: null }]} />,
    content: <EventoContent data={data} />,
  }));
}

export const auditoriaEventoRoute: RouteDefinition<{ id: string }> = {
  name: "auditoria-evento",
  match(pathname) {
    const found = /^\/auditoria\/evento\/([0-9]+)\/$/.exec(pathname);
    return found ? { id: found[1] } : null;
  },
  render: ({ id }) => <EventoPage id={id} />,
};
