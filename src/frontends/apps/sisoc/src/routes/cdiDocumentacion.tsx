/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";
import { client, internal, messagesValid, navigation, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import { NativeModal } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDI06 intervention detail (`centrodeinfancia/intervencion_detail_view.html`) with its attached
 * document. The native view stays the authority through `/api/web/cdi/intervenciones/`. The
 * "Descargar" link points to the authenticated per-object download (CDI-F2): the browser never
 * receives the storage path. "Eliminar" (superusers, as in the native template) asks for
 * confirmation in the native modal, POSTs once and follows the native redirect with its message.
 */
type Centro = { id: number; nombre: string; url: string };
type Documentacion = { name: string; descargar: string; eliminar: string | null };
type Detail = {
  id: number; centro: Centro; fecha: string; tipo_intervencion: string; subintervencion: string; destinatario: string;
  forma_contacto: string; observaciones: string; documentacion: Documentacion | null; messages: CdiMessage[];
};

function detailValid(v: unknown): v is Detail {
  if (!record(v) || !Number.isSafeInteger(v.id) || !record(v.centro) || !messagesValid(v.messages)) return false;
  const c = v.centro;
  const d = v.documentacion;
  const docOk = d === null || (record(d) && text(d.name) && internal(d.descargar) && (d.eliminar === null || internal(d.eliminar)));
  return Number.isSafeInteger(c.id) && text(c.nombre) && internal(c.url) && docOk &&
    ["fecha", "tipo_intervencion", "subintervencion", "destinatario", "forma_contacto", "observaciones"].every((k) => text(v[k]));
}

const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";

function redirectTarget(data: unknown): string | null {
  if (!record(data) || data.ok !== true || typeof data.redirect !== "string") return null;
  return internal(data.redirect) ? data.redirect : null;
}

/** One POST of the native delete; an unconfirmed outcome is reported, never resubmitted. */
function EliminarModal({ url, close }: { url: string; close: () => void }) {
  const busy = useRef(false);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;
  async function confirm(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true);
    try {
      const { data, status } = await client.post(url, new URLSearchParams({ csrfmiddlewaretoken: leerCookie("csrftoken") ?? "" }), {
        validateStatus: (s: number) => (s >= 200 && s < 300) || s === 403,
      });
      if (status === 403) { setForbidden({ prerequisite: prerequisiteFromForbidden(data) }); return; }
      const to = redirectTarget(data);
      if (to) { navigation.assign(to); return; }
      setUncertain(true);
    } catch {
      setUncertain(true);
    }
    busy.current = false; setPending(false);
  }
  return (
    <NativeModal id="confirmDeleteModal" title="Confirmar eliminación" close={close} busy={pending}>
      <div className="modal-content">
        <form method="post" onSubmit={confirm}>
          <div className="modal-header">
            <h5 className="modal-title" id="confirmDeleteModalLabel">Confirmar eliminación</h5>
            <button type="button" className="btn-close" aria-label="Close" onClick={close} />
          </div>
          <div className="modal-body">¿Está seguro de que desea eliminar la documentación adjunta?</div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className="btn btn-danger" id="btn-confirmar-eliminar-documentacion" disabled={pending || uncertain}>Eliminar</button>
          </div>
          {uncertain && <p role="alert" className="px-3 mb-3">{UNCERTAIN}</p>}
        </form>
      </div>
    </NativeModal>
  );
}

function DetailContent({ data }: { data: Detail }) {
  const [confirming, setConfirming] = useState(false);
  const doc = data.documentacion;
  const rows: [string, string][] = [
    ["Fecha y hora", data.fecha], ["Tipo de intervención", data.tipo_intervencion], ["Sub-intervención", data.subintervencion],
    ["Destinatario", data.destinatario], ["Forma de contacto", data.forma_contacto], ["Observaciones", data.observaciones],
  ];
  return <>
    <div className="container mt-4">
      <div className="card card-primary card-outline">
        <div className="card-header">
          <h3 className="card-title">Detalle de Intervención</h3>
        </div>
        <div className="card-body">
          <table className="table table-bordered table-striped">
            <tbody>
              <tr>
                <th scope="row" className="w-25">Centro</th>
                <td><a href={data.centro.url}>{data.centro.nombre}</a></td>
              </tr>
              {rows.map(([label, value]) => <tr key={label}><th scope="row">{label}</th><td>{value}</td></tr>)}
              <tr>
                <th scope="row">Documentación adjunta</th>
                <td>
                  {doc ? (
                    <div className="d-flex align-items-center">
                      <span className="me-3">{doc.name}</span>
                      <a href={doc.descargar} className="btn btn-sm btn-primary me-2" download>Descargar</a>
                      {doc.eliminar && (
                        <form method="post" id="form-eliminar-documentacion" style={{ display: "inline" }} onSubmit={(e) => e.preventDefault()}>
                          <button type="button" className="btn btn-sm btn-danger" onClick={() => setConfirming(true)}>Eliminar</button>
                        </form>
                      )}
                    </div>
                  ) : "No hay documentación adjunta."}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    {confirming && doc?.eliminar && <EliminarModal url={doc.eliminar} close={() => setConfirming(false)} />}
  </>;
}

function DocumentacionPage({ id }: { id: string }) {
  const [state] = useCdiPage(`web/cdi/intervenciones/${id}/`, detailValid);
  return renderCdi(state, (data) => ({
    title: "Detalle de Intervención - Centro de Desarrollo Infantil", heading: "", content: <DetailContent data={data} />,
  }));
}

const OWN = /^\/centrodeinfancia\/intervencion\/detalle\/(\d+)\/$/;

// Native URL of the CDI intervention detail (CDI06); same trailing slash.
export const cdiDocumentacionRoute: RouteDefinition<{ id: string }> = {
  name: "cdi-documentacion",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { id: own[1] } : null;
  },
  render: (params) => <DocumentacionPage id={params.id} />,
};
