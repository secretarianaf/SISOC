/* eslint-disable react-refresh/only-export-components -- the module exports each legajo section with its validator. */
import { Fragment } from "react";
import { internal, record, text } from "./MainFrame";

/**
 * O05.01 legajo data blocks delivered as sections: `legajo/region.html`,  `legajo/proyectos.html`, `legajo/comedores.html`.
 * Markup, classes and texts are the native partial's; the API only sends data.
 */
export type RegionSection = {
  kind: "region"; can_manage: boolean; edit_url: string | null; has_data: boolean; region: string; subzona: string; territorials: string[];
};

/** Territorial badges separated by the whitespace the template leaves between them. */
function Territorials({ labels }: { labels: string[] }) {
  return <>{labels.map((label, i) => <Fragment key={`${label}-${i}`}>{i > 0 && " "}<span className="badge-territorial">{label}</span></Fragment>)}</>;
}

export const regionSectionValid = (v: unknown): v is RegionSection =>
  record(v) && v.kind === "region" && typeof v.can_manage === "boolean" && (v.edit_url === null || internal(v.edit_url)) &&
  typeof v.has_data === "boolean" && text(v.region) && text(v.subzona) && Array.isArray(v.territorials) && v.territorials.every(text);

export function RegionSection({ section }: { section: RegionSection }) {
  return (
    <div className="tabla-legajo card-region" style={{ position: "relative" }}>
      {section.edit_url && <a href={section.edit_url} className="btn-edit-card" aria-label="Editar datos de región"><i className="fas fa-pen" /></a>}
      <h5 className="mb-1">Datos de Región</h5>
      <span className="chip-legajo mb-3">Común a Línea Secos y Línea Tradicional</span>
      {section.has_data ? (
        <div className="datos-card p-0 border-0 shadow-none mb-0">
          <div className="info-row"><strong>Región:</strong> <span className="value">{section.region}</span></div>
          <div className="info-row"><strong>Subzona:</strong> <span className="value">{section.subzona}</span></div>
        </div>
      ) : (
        <div className="bloque-vacio">
          <span>Faltan Región y Subzona.</span>{" "}
          <span className="nota-legajo">Se cargan en Editar organización › Datos Abordaje Comunitario.</span>
          {section.edit_url && <>{" "}<a href={section.edit_url} className="btn btn-success btn-sm">+ Completar región</a></>}
        </div>
      )}
      {section.territorials.length > 0 && (
        <>
          <h6 className="titulo-dorado mt-3 mb-1">Territoriales anteriores sin proyecto</h6>
          <div>
            <Territorials labels={section.territorials} />
          </div>
          <p className="nota-legajo mt-2 mb-0">
            Asignados a la organización antes de que los territoriales fueran por proyecto.
            Se ven hasta que se asignen a un proyecto o se quiten en Editar organización.
          </p>
        </>
      )}
    </div>
  );
}

type ProjectRow = { id: number; code: string; territorials: string[] };
export type ProyectosSection = { kind: "proyectos"; title: string; color: string; can_manage: boolean; edit_url: string | null; total: number; rows: ProjectRow[] };

export const proyectosSectionValid = (v: unknown): v is ProyectosSection =>
  record(v) && v.kind === "proyectos" && text(v.title) && text(v.color) && typeof v.can_manage === "boolean" && (v.edit_url === null || internal(v.edit_url)) &&
  typeof v.total === "number" && Array.isArray(v.rows) &&
  v.rows.every((r) => record(r) && typeof r.id === "number" && text(r.code) && Array.isArray(r.territorials) && r.territorials.every(text));

export function ProyectosSection({ section }: { section: ProyectosSection }) {
  return (
    <div className={`tabla-legajo card-programa card-${section.color}`} style={{ position: "relative" }}>
      {section.edit_url && <a href={section.edit_url} className="btn-edit-card" aria-label="Editar proyectos"><i className="fas fa-pen" /></a>}
      <h5 className="mb-3">
        {section.title} <span className="badge badge-gold ms-2">{section.total} Total</span>
      </h5>
      {section.rows.length > 0 ? (
        <div className="table-responsive">
          <table className="table table-sm align-middle">
            <thead>
              <tr><th>Código de Proyecto</th><th>Territoriales</th><th>Estado</th></tr>
            </thead>
            <tbody>
              {section.rows.map((row) => (
                <tr key={row.id}>
                  <td><span className="badge rounded-pill bg-primary px-3 py-2">{row.code}</span></td>
                  <td>{row.territorials.length > 0 ? <Territorials labels={row.territorials} /> : <span className="badge badge-pendiente">Sin territorial</span>}</td>
                  <td><span className="badge-status vigente"><i className="fas fa-check-circle" /> Activo</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="texto-vacio mb-0">No hay proyectos activos.</p>}
      <p className="nota-legajo mt-2 mb-0">Cada proyecto pertenece a una sola línea y tiene sus propios territoriales.</p>
    </div>
  );
}

type SpaceRow = {
  id: number; name: string; url: string; caritas: boolean; type: string; code: string | null; program: string; province: string; municipality: string;
  locality: string; address: string; referent: string | null; validation: "ok" | "no" | "pending";
};
export type ComedoresSection = { kind: "comedores"; title: string; color: string; show_code: boolean; show_program: boolean; total: number; rows: SpaceRow[] };

export const comedoresSectionValid = (v: unknown): v is ComedoresSection =>
  record(v) && v.kind === "comedores" && text(v.title) && text(v.color) && typeof v.show_code === "boolean" && typeof v.show_program === "boolean" &&
  typeof v.total === "number" && Array.isArray(v.rows) &&
  v.rows.every((r) => record(r) && typeof r.id === "number" && text(r.name) && internal(r.url) && typeof r.caritas === "boolean" && text(r.type) &&
    (r.code === null || text(r.code)) && text(r.program) && text(r.province) && text(r.municipality) && text(r.locality) && text(r.address) &&
    (r.referent === null || text(r.referent)) && ["ok", "no", "pending"].includes(r.validation as string));

function Validation({ state }: { state: SpaceRow["validation"] }) {
  if (state === "ok") return <span className="badge badge-ok"><i className="fas fa-check-circle" /> Validado</span>;
  if (state === "no") return <span className="badge badge-no"><i className="fas fa-times-circle" /> No Validado</span>;
  return <span className="badge badge-pendiente"><i className="fas fa-clock" /> Pendiente</span>;
}

export function ComedoresSection({ section }: { section: ComedoresSection }) {
  return (
    <div className={`tabla-legajo card-programa card-${section.color}`}>
      <h5 className="mb-3">
        <span>{section.title}</span> <span className="badge badge-gold ms-2">{section.total} Total</span>
      </h5>
      {section.rows.length > 0 ? (
        <div className="table-responsive">
          <table className="table table-sm">
            <thead>
              <tr>
                <th>Nombre</th><th>Tipo</th>
                {section.show_code && <th>Código de Proyecto</th>}
                {section.show_program && <th>Programa</th>}
                <th>Ubicación</th><th>Dirección</th><th>Referente</th><th>¿Fue Validado?</th><th className="text-end">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {section.rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <a href={row.url} className="enlace-dorado">{row.name}</a>
                    {row.caritas && <>{" "}<span className="badge ms-1 badge-caritas"><i className="fas fa-heart" /> CARITAS</span></>}
                  </td>
                  <td>{row.type}</td>
                  {section.show_code && <td>{row.code ? <span className="badge rounded-pill bg-primary px-3 py-2">{row.code}</span> : "-"}</td>}
                  {section.show_program && <td>{row.program}</td>}
                  <td>
                    <div className="small-ubicacion">{row.province}</div>
                    <div className="small-ubicacion-sub">{row.municipality} / {row.locality}</div>
                  </td>
                  <td>{row.address}</td>
                  <td>{row.referent ?? "-"}</td>
                  <td><Validation state={row.validation} /></td>
                  <td className="text-end"><a href={row.url} className="btn btn-sm accion-ver"><i className="fas fa-eye" /> Ver</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="texto-vacio mb-0">No hay comedores asociados en este programa.</p>}
    </div>
  );
}
