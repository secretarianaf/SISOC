/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validator and content are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { integer, messagesValid, type Message } from "./vatShared";
import { CsrfInput, useForbidden } from "./vatFormShared";
import { UncertainNotice, usePostDelete } from "./vatCentrosListaShared";
import type { RouteDefinition } from "./types";

/**
 * V06.02 baja de un centro: `vat/centros/centro_confirm_delete.html` (`components/delete_confirm.html` with the cascade
 * preview of the soft delete). The preview comes from `/api/web/vat/centros-lista/<id>/eliminar/`, which runs
 * `CentroDeleteView`; the POST of the form goes to the same endpoint.
 */
type Breakdown = { modelo: string; cantidad: number; modo: string; ejemplos: string[] };
type Preview = { total_afectados: number; total_baja_logica?: number; total_borrado_fisico?: number; desglose_por_modelo: Breakdown[] };
export type CentroBajaData = {
  id: number; nombre: string; preview: Preview | null; confirm_text: string; cancel_text: string; urls: { detail: string }; messages: Message[];
};

const API = "web/vat/centros-lista/";

export function centroBajaValid(v: unknown): v is CentroBajaData {
  if (!record(v) || !record(v.urls)) return false;
  const p = v.preview;
  return integer(v.id) && text(v.nombre) && text(v.confirm_text) && text(v.cancel_text) && internal(v.urls.detail) && messagesValid(v.messages) &&
    (p === null || (record(p) && integer(p.total_afectados) && Array.isArray(p.desglose_por_modelo) &&
      p.desglose_por_modelo.every((d) => record(d) && text(d.modelo) && integer(d.cantidad) && text(d.modo) && Array.isArray(d.ejemplos) && d.ejemplos.every(text))));
}

export function CentroBajaContent({ data, forbidden }: { data: CentroBajaData; forbidden: (d: unknown) => void }) {
  const { uncertain, submit } = usePostDelete(`${API}${data.id}/eliminar/`, forbidden);
  const p = data.preview;
  return <>
    <NativeToasts messages={data.messages} />
    <div className="error-page mt-5 px-3"><div className="error-content">
      <h3><i className="fas fa-exclamation-triangle text-danger px-2" />{" "}Atención!</h3>
      <p>
        ¿Estás seguro que deseas realizar una baja lógica en cascada del registro{" "}
        <span className="font-weight-bold">{data.nombre.toUpperCase()}</span>?
      </p>
      {p && <>
        <div className="alert alert-info">
          <div><strong>Total de registros afectados:</strong> {p.total_afectados}</div>
          {!!p.total_baja_logica && <div>Bajas lógicas: {p.total_baja_logica}</div>}
          {!!p.total_borrado_fisico && <div>Borrados físicos técnicos: {p.total_borrado_fisico}</div>}
        </div>
        <div className="table-responsive mb-3"><table className="table table-sm table-striped mb-0">
          <thead><tr><th>Modelo</th><th>Cantidad</th><th>Acción</th><th>Ejemplos</th></tr></thead>
          <tbody>
            {p.desglose_por_modelo.map((d) => <tr key={d.modelo}>
              <td>{d.modelo}</td>
              <td>{d.cantidad}</td>
              <td>{d.modo === "baja_logica" ? "Baja lógica" : "Borrado físico técnico"}</td>
              <td>{d.ejemplos.length ? d.ejemplos.join(", ") : "-"}</td>
            </tr>)}
          </tbody>
        </table></div>
      </>}
      <div className="text-left">
        <form method="post" action="" onSubmit={submit}>
          <CsrfInput />
          <UncertainNotice show={uncertain} />
          <button type="submit" className="btn btn-danger btn-sm">{data.confirm_text}</button>{" "}
          <a href={data.urls.detail} className="btn btn-secondary btn-sm">{data.cancel_text}</a>
        </form>
      </div>
    </div></div>
  </>;
}

function BajaPage({ id }: { id: string }) {
  const [state, setState] = useMainResource(`${API}${id}/eliminar/`, centroBajaValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Confirmar Eliminación", breadcrumb: null, content: <CentroBajaContent data={data} forbidden={forbidden} />,
  }));
}

// Native URL of `VAT/urls.py`.
const PATH = /^\/vat\/centros\/([0-9]+)\/eliminar\/$/;

export const vatCentrosBajaRoute: RouteDefinition<{ id: string }> = {
  name: "vat-centros-baja",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render: ({ id }) => <BajaPage key={id} id={id} />,
};
