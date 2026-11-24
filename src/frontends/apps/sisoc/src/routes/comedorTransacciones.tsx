/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, validator and route live here. */
import { InsumosToastList } from "../InsumosToast";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * CO07.01 DW transactions history of a comedor (`comedor_transacciones_detalle`):
 * `comedor/comedor_transacciones_detail.html`, a read-only table with the period, the movements and the
 * amounts the native page shows (Transferido is the DW debit total and Gastado the credit total). Data comes
 * from `/api/web/comedores/comedores/<id>/transacciones/`, which runs the native view and its DW service.
 * No filter, export or write exists, and a DW failure shows the same «Sin información» message as no data.
 */
type Transaccion = { periodo: string; movimientos: string; transferido: string; gastado: string; saldo: string };
export type ComedorTransaccionesData = {
  comedor: { id: number; nombre: string };
  transacciones: Transaccion[];
  urls: { comedores: string; comedor: string };
  messages: { message: string; level: "success" | "error" | "warning" | "info" }[];
};

const LEVELS = ["success", "error", "warning", "info"];

export function transaccionesValid(v: unknown): v is ComedorTransaccionesData {
  if (!record(v) || !record(v.comedor) || !record(v.urls)) return false;
  return Number.isSafeInteger(v.comedor.id) && text(v.comedor.nombre) &&
    Array.isArray(v.transacciones) && v.transacciones.every((t) => record(t) &&
      ["periodo", "movimientos", "transferido", "gastado", "saldo"].every((k) => text(t[k]))) &&
    internal(v.urls.comedores) && internal(v.urls.comedor) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

const TABLE_STYLE = `table.transacciones-table > :not(caption) > * > * { padding-bottom: .5rem; padding-top: .5rem; }
table.transacciones-table thead th { background-color: #3d4f63 !important; border-bottom: 2px solid #e7ba61 !important; }`;

export function ComedorTransaccionesContent({ data }: { data: ComedorTransaccionesData }) {
  return (
    <div className="container-fluid">
      <InsumosToastList messages={data.messages} />
      <style>{TABLE_STYLE}</style>
      <div className="card mb-3">
        <div className="card-header">
          <h3 className="card-title">Transacciones - Nación Servicios</h3>
        </div>
        <div className="card-body p-0">
          {data.transacciones.length ? (
            <div className="table-responsive">
              <table className="table table-bordered table-sm mb-0 transacciones-table">
                <thead>
                  <tr>
                    <th scope="col">Período</th>
                    <th scope="col" className="text-end">Movimientos</th>
                    <th scope="col" className="text-end">Transferido</th>
                    <th scope="col" className="text-end">Gastado</th>
                    <th scope="col" className="text-end">Saldo Cereado</th>
                  </tr>
                </thead>
                <tbody>
                  {data.transacciones.map((t, index) => (
                    <tr key={index}>
                      <td>{t.periodo}</td>
                      <td className="text-end">{t.movimientos}</td>
                      <td className="text-end">{t.transferido}</td>
                      <td className="text-end">{t.gastado}</td>
                      <td className="text-end">{t.saldo}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="alert alert-info m-3">
              <i className="bi bi-info-circle me-2" />{" "}
              <strong>Sin información</strong> - No hay registros de transacciones disponibles para este comedor.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TransaccionesPage({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(`${endpoint}${window.location.search}`, transaccionesValid);
  return renderMain(state, "Cargando transacciones…", (data) => ({
    title: `Transacciones - ${data.comedor.nombre}`,
    breadcrumb: null,
    appHeader: (
      <div className="row g-2 align-items-center">
        <div className="col-12 col-lg d-flex justify-content-lg-end">
          <h4 className="m-0">Transacciones - Nación Servicios</h4>
        </div>
      </div>
    ),
    content: <ComedorTransaccionesContent data={data} />,
  }));
}

const API = "web/comedores/comedores/";
const TRANSACCIONES = /^\/comedores\/([1-9]\d*)\/transacciones$/;

// Native URL `comedor_transacciones_detalle` (no trailing slash, like the Django route).
export const comedorTransaccionesRoute: RouteDefinition<{ endpoint: string }> = {
  name: "comedor-transacciones",
  match(pathname) {
    const m = TRANSACCIONES.exec(pathname);
    return m ? { endpoint: `${API}${m[1]}/transacciones/` } : null;
  },
  render: ({ endpoint }) => <TransaccionesPage key={endpoint} endpoint={endpoint} />,
};
