/* eslint-disable react-refresh/only-export-components -- route registry entry. */
import { Breadcrumb, internal, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

type Row = {
  id: number;
  mes: number;
  anio: number;
  observaciones: string;
  detail_url: string;
  edit_url: string | null;
  delete_url: string | null;
};

type ListData = {
  comedor: string;
  back_url: string;
  new_url: string | null;
  rows: Row[];
};

const integer = (value: unknown): value is number => typeof value === "number" && Number.isSafeInteger(value);
const optionalLink = (value: unknown) => value === null || internal(value);

function valid(value: unknown): value is ListData {
  return record(value) && text(value.comedor) && internal(value.back_url) && optionalLink(value.new_url) &&
    Array.isArray(value.rows) && value.rows.every((row) => record(row) &&
      integer(row.id) && integer(row.mes) && integer(row.anio) && text(row.observaciones) &&
      internal(row.detail_url) && optionalLink(row.edit_url) && optionalLink(row.delete_url));
}

function RendicionMensualPorComedor({ comedorId }: { comedorId: string }) {
  // Django's QueryDict reads the last value if a deep link repeats a key.
  const page = new URLSearchParams(window.location.search).getAll("page").at(-1);
  const query = page === undefined ? "" : `?${new URLSearchParams({ page })}`;
  const [state] = useMainResource(`web/comedores/rendicioncuentasmensual/por-comedor/${comedorId}/${query}`, valid);
  return renderMain(state, "Cargando seguimientos mensuales…", (data) => ({
    title: "Acciones",
    breadcrumb: <Breadcrumb items={[
      { text: "Rendición de cuenta mensual", url: null },
      { text: "Volver al acompañamiento", url: data.back_url },
      { text: "Lista", url: null },
    ]} />,
    content: (
      <div className="container mt-4">
        <h1 className="mb-3">Seguimiento mensual - {data.comedor}</h1>
        {data.new_url && <div className="d-flex justify-content-end mb-4">
          <a className="btn btn-success" href={data.new_url}>Nuevo seguimiento mensual</a>
        </div>}
        <div className="card shadow-sm">
          <div className="card-body">
            <div className="table-responsive" role="region" aria-label="Seguimientos mensuales" tabIndex={0}>
              <table className="table table-bordered table-hover mb-0">
                <thead className="table-dark">
                  <tr>{["#", "Mes", "Año", "Observaciones", "Acciones"].map((label) => <th key={label} scope="col">{label}</th>)}</tr>
                </thead>
                <tbody>
                  {data.rows.length === 0 && <tr><td colSpan={5}>No hay seguimientos mensuales.</td></tr>}
                  {data.rows.map((row, index) => (
                    <tr key={row.id}>
                      <td>{index + 1}</td>
                      <td>{row.mes}</td>
                      <td>{row.anio}</td>
                      <td>{row.observaciones}</td>
                      <td className="w-25">
                        <div className="d-flex flex-wrap gap-1">
                          <a className="btn btn-info btn-sm" href={row.detail_url}>Ver Detalle</a>
                          {row.edit_url && <a className="btn btn-warning btn-sm" href={row.edit_url}>Editar</a>}
                          {row.delete_url && <a className="btn btn-danger btn-sm" href={row.delete_url}>Dar de baja</a>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    ),
  }));
}

const LIST = /^\/rendicioncuentasmensual\/rendicioncuentasmensual\/([0-9]+)\/$/;

export const rendicionMensualPorComedorRoute: RouteDefinition<{ comedorId: string }> = {
  name: "comedores-rendicion-mensual-por-comedor",
  match(pathname) {
    const found = LIST.exec(pathname);
    return found ? { comedorId: found[1] } : null;
  },
  render({ comedorId }) {
    return <RendicionMensualPorComedor key={comedorId} comedorId={comedorId} />;
  },
};
