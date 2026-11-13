/* eslint-disable react-refresh/only-export-components -- the unit surface is this module: the lower card types, their validation and the cards. */
import type { ReactNode } from "react";
import { internal, record } from "./MainFrame";
import { useCardCollapse } from "./relevamientos";

/**
 * CO07.01 ficha, the cards of `comedor_detail.html` under the central block. Data are the
 * top-level keys of `GET /api/web/comedores/comedores/<pk>/`.
 */
export type Certificacion = { id: number; periodo: string; usuario: string; conforme: boolean; creado: string; pdf: string | null };
export type Certificaciones = { historial: string; items: Certificacion[] };
export type Bloques = { certificaciones: Certificaciones };

const strs = (v: unknown, keys: string[]) => record(v) && keys.every((k) => typeof v[k] === "string");

export function certificacionesValid(v: unknown): v is Certificaciones {
  return record(v) && internal(v.historial) && Array.isArray(v.items) &&
    v.items.every((c) => strs(c, ["periodo", "usuario", "creado"]) && Number.isSafeInteger((c as Certificacion).id) && typeof (c as Certificacion).conforme === "boolean" &&
      ((c as Certificacion).pdf === null || internal((c as Certificacion).pdf)));
}

export function bloquesValid(v: Record<string, unknown>): boolean {
  return certificacionesValid(v.certificaciones);
}

/** The collapsible card every lower block uses (`card bg-card` with `card-tools`). */
function Tarjeta({ titulo, tools, children, headerClass }: { titulo: string; tools: ReactNode; children: ReactNode; headerClass?: string }) {
  return (
    <div className="card bg-card">
      <div className={headerClass ?? "card-header"}>
        <h3 className="card-title font-weight-bold me-3 pt-1">{titulo}</h3>
        <div className="card-tools">{tools}</div>
      </div>
      <div className="card-body">{children}</div>
    </div>
  );
}

const Colapsar = () => <button type="button" className="btn btn-tool" data-card-widget="collapse"><i className="fas fa-minus" /></button>;

export function CertificacionesCard({ data }: { data: Certificaciones }) {
  useCardCollapse();
  return (
    <div className="row relevamiento-container mb-3">
      <div className="col-12">
        <Tarjeta titulo="Certificaciones Mensuales de Prestaciones" tools={<><a href={data.historial} className="btn btn-primary me-2 btn-sm">Ver historial completo</a>{" "}<Colapsar /></>}>
          <div className="table-responsive">
            <table className="table table-sm table-bordered table-striped mb-0">
              <thead><tr><th>Período</th><th>Usuario generador</th><th>Estado Conformidad</th><th>Fecha de certificación</th><th>Ver PDF</th></tr></thead>
              <tbody>
                {data.items.length ? data.items.map((c) => (
                  <tr key={c.id}>
                    <td>{c.periodo}</td>
                    <td>{c.usuario}</td>
                    <td>{c.conforme ? <span className="badge bg-success">Conforme</span> : <span className="badge bg-danger">No conforme</span>}</td>
                    <td>{c.creado}</td>
                    <td>{c.pdf ? <a href={c.pdf} className="btn btn-sm btn-primary" target="_blank" rel="noopener">Ver PDF</a> : <span className="text-muted">No disponible</span>}</td>
                  </tr>
                )) : <tr><td colSpan={5} className="text-center text-muted py-3">No hay certificaciones mensuales registradas.</td></tr>}
              </tbody>
            </table>
          </div>
        </Tarjeta>
      </div>
    </div>
  );
}

/** The lower cards in the order of the template. */
export function FichaBloques({ data }: { data: Bloques }) {
  return <CertificacionesCard data={data.certificaciones} />;
}
