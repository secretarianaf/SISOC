/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen and validator live here with the route. */
import { messagesValid, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import type { RouteDefinition } from "./types";

/**
 * CDI nomina form detail (`centrodeinfancia/nomina_formulario_detail.html`): a striped table of
 * label/value rows. The backend renders each value with the native template expression
 * (`default:"-"`, `yesno`, `date`), so this page only draws the rows.
 */
export type NominaFormularioData = { rows: { label: string; value: string }[]; messages: CdiMessage[] };

export function nominaFormularioValid(v: unknown): v is NominaFormularioData {
  return record(v) && messagesValid(v.messages) && Array.isArray(v.rows) && v.rows.every((r) => record(r) && text(r.label) && text(r.value));
}

export function NominaFormularioContent({ data }: { data: NominaFormularioData }) {
  return (
    <div className="container mt-5">
      <div className="page-header">
        <div className="row align-items-center">
          <div className="col">
            <h1>Detalle del Formulario de Nómina</h1>
          </div>
        </div>
      </div>
      <div className="card mt-4">
        <div className="card-body">
          <h5 className="mb-3">Información General</h5>
          <table className="table table-striped">
            <tbody>
              {data.rows.map((row, n) => (
                <tr key={`${n}:${row.label}`}>
                  <td><strong>{row.label}</strong></td>
                  <td>{row.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function NominaFormularioPage({ id }: { id: string }) {
  const [state] = useCdiPage(`web/cdi/nomina/${id}/formulario/`, nominaFormularioValid);
  return renderCdi(state, (data) => ({ title: "Detalle - Formulario de Nómina", heading: "", content: <NominaFormularioContent data={data} /> }));
}

const OWN = /^\/centrodeinfancia\/([1-9]\d*)\/nomina\/formulario\/$/;

// Native URL of the CDI nomina form detail; same trailing slash. The id is the nomina id.
export const cdiNominaFormularioRoute: RouteDefinition<{ id: string }> = {
  name: "cdi-nomina-formulario",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { id: own[1] } : null;
  },
  render: ({ id }) => <NominaFormularioPage id={id} />,
};
