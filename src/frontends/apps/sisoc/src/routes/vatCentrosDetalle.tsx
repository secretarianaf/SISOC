/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { Fragment, useState, type ReactNode } from "react";
import { accepted, internal, postForm, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { apiPath, cursosPanelEndpoint } from "./vatCentrosDetalleShared";
import { CursosPanelContainer } from "./vatCentrosDetalleCursos";
import { CENTRO_DETALLE_CSS } from "./vatCentrosDetalleStyles";
import { CENTRO_MODALES_CSS } from "./vatCentrosDetalleModalesStyles";
import { TourHelp } from "./vatTour";
import { AsPModal, centroAcciones, fieldsValid, formDataValid } from "./vatCentrosDetalleModales";
import type { Field } from "./vatFormShared";
import { bool, integer, messagesValid, vatNavigation, type Message } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V06.01 detalle de un centro: `vat/centros/centro_detail.html` (information, referente, additional locations and contacts).
 * `/api/web/vat/centros-detalle/<id>/` runs the native detail view (scope, 404/403 and the printed values are the native ones);
 * the courses and commissions panel is the fragment the native page loads by AJAX (`vatCentrosDetalleCursos.tsx`). The side
 * tabs are the page's own JavaScript (`setupCentroInfoTabs`). The buttons and modals that add, edit and delete locations and
 * contacts are the page's own too (`vatCentrosDetalleModales.tsx`); the native page draws no identifier button, so neither
 * does this one. Saving or deleting reloads the page, as the native script does.
 */
type Acciones = { form: string; guardar: string; eliminar: string };
type Ubicacion = { id: number; nombre: string; caracteristica: string; localidad: string; domicilio: string; urls: Acciones };
type Contacto = { id: number; nombre: string; documento: string; rol: string; principal: boolean; telefono: string; urls: Acciones };
type Modales = { contacto: { fields: Field[]; crear: string }; ubicacion: { fields: Field[]; crear: string; localidades: string } } | null;
const PERMISOS = ["editar_centro", "agregar_ubicacion", "editar_ubicacion", "eliminar_ubicacion", "agregar_contacto", "editar_contacto", "eliminar_contacto"] as const;
export type CentroDetalleData = {
  id: number; nombre: string; codigo: string; activo: boolean; mostrar_datos_administrativos: boolean; tipo_gestion: string; domicilio: string;
  telefono: string; celular: string; correo: string | null; mapa: string | null;
  referente: { nombre: string; telefono: string; dni: string; correo: string; usuarios: string[] };
  ubicaciones: Ubicacion[]; contactos: Contacto[]; permisos: Record<(typeof PERMISOS)[number], boolean>; urls: { cursos: string }; modales: Modales; messages: Message[];
};

const accionesValid = (u: unknown): u is Acciones => record(u) && internal(u.form) && internal(u.guardar) && internal(u.eliminar);
const modalesValid = (m: unknown): m is Modales => m === null || (record(m) && record(m.contacto) && fieldsValid(m.contacto.fields) && internal(m.contacto.crear) &&
  record(m.ubicacion) && fieldsValid(m.ubicacion.fields) && internal(m.ubicacion.crear) && internal(m.ubicacion.localidades));

const strings = (v: Record<string, unknown>, keys: string[]) => keys.every((k) => text(v[k]));
const list = (v: unknown, valid: (row: Record<string, unknown>) => boolean) => Array.isArray(v) && v.every((row) => record(row) && valid(row));

export function centroDetalleValid(v: unknown): v is CentroDetalleData {
  return record(v) && integer(v.id) && strings(v, ["nombre", "codigo", "tipo_gestion", "domicilio", "telefono", "celular"]) && bool(v.activo) &&
    bool(v.mostrar_datos_administrativos) && (v.correo === null || text(v.correo)) && (v.mapa === null || text(v.mapa)) &&
    record(v.referente) && strings(v.referente, ["nombre", "telefono", "dni", "correo"]) && Array.isArray(v.referente.usuarios) && v.referente.usuarios.every(text) &&
    list(v.ubicaciones, (u) => integer(u.id) && strings(u, ["nombre", "caracteristica", "localidad", "domicilio"]) && accionesValid(u.urls)) &&
    list(v.contactos, (c) => integer(c.id) && strings(c, ["nombre", "documento", "rol", "telefono"]) && bool(c.principal) && accionesValid(c.urls)) &&
    record(v.permisos) && PERMISOS.every((k) => bool((v.permisos as Record<string, unknown>)[k])) &&
    record(v.urls) && internal(v.urls.cursos) && modalesValid(v.modales) && messagesValid(v.messages);
}

type Panel = "general" | "ubicaciones" | "contactos";
const ORDER: Panel[] = ["general", "ubicaciones", "contactos"];
const LABELS: Record<Panel, string> = { general: "Información general", ubicaciones: "Ubicaciones adicionales", contactos: "Contactos adicionales" };

function Item({ label, children }: { label: string; children: ReactNode }) {
  return <div className="sisoc-data-item"><p className="sisoc-data-label">{label}</p><p className="sisoc-data-value">{children}</p></div>;
}

function Referente({ icon, label, children, plain }: { icon: string; label: string; children: ReactNode; plain?: boolean }) {
  return (
    <li className="sisoc-referente-item">
      <span className="sisoc-referente-icon"><i className={`fas ${icon}`} /></span>
      <div className="sisoc-referente-copy"><span>{label}</span>{plain ? <div>{children}</div> : <strong>{children}</strong>}</div>
    </li>
  );
}

function GeneralPanel({ data, active }: { data: CentroDetalleData; active: boolean }) {
  const { referente } = data;
  return (
    <section className={`sisoc-info-panel${active ? " is-active" : ""}`} data-sisoc-panel="general">
      <div className="sisoc-panel-section">
        <div className="sisoc-general-layout">
          <div className="sisoc-general-main">
            <div className="sisoc-section-header"><h2>Información general sobre el establecimiento</h2></div>
            <hr className="sisoc-section-divider" />
            <div className="sisoc-general-grid">
              <Item label="CUE">#{data.codigo}</Item>
              {data.mostrar_datos_administrativos && <Item label="Sector de gestión">{data.tipo_gestion}</Item>}
              <Item label="Domicilio">{data.domicilio}</Item>
              <Item label="Teléfono">{data.telefono}</Item>
              <Item label="Celular">{data.celular}</Item>
              <Item label="Correo electrónico">{data.correo ? <a href={`mailto:${data.correo}`}>{data.correo}</a> : "-"}</Item>
            </div>
          </div>
          <div className="sisoc-map-preview">
            {data.mapa ? (
              <iframe title="Mapa del centro" frameBorder="0" style={{ border: 0 }} loading="lazy" referrerPolicy="no-referrer-when-downgrade" src={data.mapa} allowFullScreen />
            ) : (
              <div className="sisoc-map-placeholder"><i className="fas fa-map-marker-alt" />{" "}<span>Sin datos suficientes para mostrar el mapa</span></div>
            )}
          </div>
        </div>
        <hr className="sisoc-section-divider" />
        <div className="sisoc-section-header"><h2>Referente del centro</h2></div>
        <ul className="sisoc-referente-list">
          <Referente icon="fa-signature" label="Nombre y apellido">{referente.nombre}</Referente>
          <Referente icon="fa-phone" label="Teléfono">{referente.telefono}</Referente>
          <Referente icon="fa-user-check" label="Usuario del sistema" plain>
            {referente.usuarios.length === 0 ? "-" : referente.usuarios.map((nombre, i) => (
              <Fragment key={i}>{i > 0 && <span className="d-none">,</span>}{" "}{nombre}{i < referente.usuarios.length - 1 && " ,"}</Fragment>
            ))}
          </Referente>
          <Referente icon="fa-id-card" label="DNI">{referente.dni}</Referente>
          <Referente icon="fa-envelope" label="Correo electrónico">{referente.correo}</Referente>
        </ul>
      </div>
    </section>
  );
}

type ModalState = { kind: "contacto" | "ubicacion"; title: string; fields: Field[]; endpoint: string } | null;
type OpenModal = (modal: NonNullable<ModalState>) => void;

/** `editContacto`/`editUbicacion`: the form of the record is fetched, then the modal opens in edit mode. */
async function editar(kind: "contacto" | "ubicacion", urls: Acciones, open: OpenModal) {
  const failure = kind === "contacto" ? "Error al cargar el contacto" : "Error al cargar la ubicación";
  try {
    const { data, status } = await webClient.get(apiPath(urls.form), { validateStatus: accepted });
    if (status !== 200 || !formDataValid(data)) throw new Error(failure);
    open({ kind, title: kind === "contacto" ? "Editar Contacto" : "Editar Ubicación", fields: data.fields, endpoint: apiPath(urls.guardar) });
  } catch {
    centroAcciones.alert(`Error al cargar el formulario de edición: ${failure}`);
  }
}

/** `deleteContacto`/`deleteUbicacion`: confirm, POST the native delete and reload whatever the answer was. */
async function borrar(confirmText: string, url: string) {
  if (!vatNavigation.confirm(confirmText)) return;
  await postForm(url, new URLSearchParams());
  centroAcciones.reload();
}

const Add = ({ label, onClick }: { label: string; onClick: () => void }) => (
  <button type="button" className="sisoc-btn sisoc-btn--add" onClick={onClick}><i className="fas fa-plus" />{" "}<span>{label}</span></button>
);
const RowButton = ({ kind, label, icon, onClick }: { kind: "edit" | "delete"; label: string; icon: string; onClick: () => void }) => (
  <button type="button" className={`sisoc-btn sisoc-btn--${kind}`} onClick={onClick}><i className={`fas ${icon}`} />{" "}<span>{label}</span></button>
);

function UbicacionesPanel({ data, active, open }: { data: CentroDetalleData; active: boolean; open: OpenModal }) {
  const n = data.ubicaciones.length;
  const { permisos, modales } = data;
  const editable = permisos.editar_centro;
  return (
    <section className={`sisoc-info-panel${active ? " is-active" : ""}`} data-sisoc-panel="ubicaciones">
      <div className="sisoc-panel-section">
        <div className="sisoc-section-header">
          <h2>Ubicaciones adicionales</h2>
          {editable && permisos.agregar_ubicacion && modales && (
            <Add label="Agregar sede" onClick={() => open({ kind: "ubicacion", title: "Agregar Ubicacion", fields: modales.ubicacion.fields, endpoint: apiPath(modales.ubicacion.crear) })} />
          )}
        </div>
        <hr className="sisoc-section-divider" />
        {n > 0 ? (
          <>
            <div className="sisoc-table-shell"><div className="sisoc-table-wrap">
              <table className="sisoc-table">
                <thead><tr><th>Nombre</th><th>Característica</th><th>Localidad</th><th>Domicilio</th><th>Acciones</th></tr></thead>
                <tbody>
                  {data.ubicaciones.map((u) => (
                    <tr key={u.id}><td>{u.nombre}</td><td>{u.caracteristica}</td><td>{u.localidad}</td><td>{u.domicilio}</td>
                      <td>
                        <div className="sisoc-table-actions">
                          {editable && permisos.editar_ubicacion && <RowButton kind="edit" icon="fa-pen" label="Editar" onClick={() => void editar("ubicacion", u.urls, open)} />}
                          {editable && permisos.eliminar_ubicacion && <RowButton kind="delete" icon="fa-trash" label="Borrar" onClick={() => void borrar("Eliminar ubicacion?", apiPath(u.urls.eliminar))} />}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div></div>
            <div className="sisoc-table-footer">
              <span>Mostrando 1-{n} de {n}</span>
              <div className="sisoc-pager" aria-hidden="true"><button type="button">&lt;</button><span>1 de 1</span><button type="button">&gt;</button></div>
            </div>
          </>
        ) : <div className="sisoc-empty-state">No hay ubicaciones registradas para este centro.</div>}
      </div>
    </section>
  );
}

function ContactosPanel({ data, active, open }: { data: CentroDetalleData; active: boolean; open: OpenModal }) {
  const { permisos, modales } = data;
  const editable = permisos.editar_centro;
  return (
    <section className={`sisoc-info-panel${active ? " is-active" : ""}`} data-sisoc-panel="contactos">
      <div className="sisoc-panel-section">
        <div className="sisoc-section-header">
          <h2>Contactos adicionales</h2>
          {editable && permisos.agregar_contacto && modales && (
            <Add label="Agregar contacto" onClick={() => open({ kind: "contacto", title: "Agregar Contacto", fields: modales.contacto.fields, endpoint: apiPath(modales.contacto.crear) })} />
          )}
        </div>
        <hr className="sisoc-section-divider" />
        {data.contactos.length > 0 ? (
          <div className="sisoc-table-shell"><div className="sisoc-table-wrap">
            <table className="sisoc-table">
              <thead><tr><th>Nombre y apellido</th><th>Documento</th><th>Rol</th><th>Principal</th><th>Teléfono</th><th>Acciones</th></tr></thead>
              <tbody>
                {data.contactos.map((c) => (
                  <tr key={c.id}>
                    <td>{c.nombre}</td><td>{c.documento}</td><td>{c.rol}</td><td>{c.principal ? "Sí" : "No"}</td><td>{c.telefono}</td>
                    <td>
                      <div className="sisoc-table-actions">
                        {editable && permisos.editar_contacto && <RowButton kind="edit" icon="fa-pen" label="Editar" onClick={() => void editar("contacto", c.urls, open)} />}
                        {editable && permisos.eliminar_contacto && <RowButton kind="delete" icon="fa-trash" label="Borrar" onClick={() => void borrar("¿Eliminar contacto?", apiPath(c.urls.eliminar))} />}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div></div>
        ) : <div className="sisoc-empty-state">No hay contactos adicionales cargados.</div>}
      </div>
    </section>
  );
}

export function CentroDetalleContent({ data }: { data: CentroDetalleData }) {
  const [active, setActive] = useState<Panel>("general");
  const [modal, setModal] = useState<ModalState>(null);
  const at = ORDER.indexOf(active);
  const tab = (panel: Panel, left: boolean) => {
    const idx = ORDER.indexOf(panel);
    const show = left ? idx <= at : idx > at;
    return (
      <button key={panel} type="button" className={`sisoc-side-tab${idx === at && left ? " is-active" : ""}`} data-sisoc-tab-target={panel}
        aria-selected={idx === at && left} hidden={!show} onClick={() => setActive(panel)}>
        <span>{LABELS[panel]}</span>
      </button>
    );
  };
  return (
    <>
      <NativeToasts messages={data.messages} />
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/vat_design.css" />
      <link rel="stylesheet" href="/static/custom/css/centro_detail.css" />
      <style>{CENTRO_DETALLE_CSS}</style>
      <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
      <style>{CENTRO_MODALES_CSS}</style>
      <div className="sisoc-centro-page">
        <div className="ci-hero d-print-none">
          <div className="sisoc-title-row">
            <div className="sisoc-title-block"><h1>{data.nombre}</h1></div>
            <div className="sisoc-title-meta">
              <span className="sisoc-cue-text">CUE {data.codigo}</span>{" "}
              {data.activo ? <span className="sisoc-status-pill">Activo</span> : <span className="sisoc-status-pill is-inactive">Inactivo</span>}
            </div>
          </div>
          <div className="sisoc-info-shell">
            <div className="sisoc-side-tabs sisoc-side-tabs--left" role="tablist" aria-label="Secciones visitadas">{ORDER.map((p) => tab(p, true))}</div>
            <div className="sisoc-info-content">
              <GeneralPanel data={data} active={active === "general"} />
              <UbicacionesPanel data={data} active={active === "ubicaciones"} open={setModal} />
              <ContactosPanel data={data} active={active === "contactos"} open={setModal} />
            </div>
            <div className="sisoc-side-tabs sisoc-side-tabs--right" role="tablist" aria-label="Secciones pendientes">{ORDER.map((p) => tab(p, false))}</div>
          </div>
        </div>
        <CursosPanelContainer endpoint={cursosPanelEndpoint(data.urls.cursos)} />
      </div>
      {modal && data.modales && (
        <AsPModal key={`${modal.kind}:${modal.endpoint}`} id={modal.kind === "contacto" ? "modalContacto" : "modalUbicacion"} formId={modal.kind === "contacto" ? "formContacto" : "formUbicacion"}
          title={modal.title} fields={modal.fields} endpoint={modal.endpoint} close={() => setModal(null)}
          rejection={modal.kind === "contacto" ? "No se pudo guardar el contacto. Revisá los datos e intentá nuevamente." : "No se pudo guardar la ubicación. Revisá los datos e intentá nuevamente."}
          localidades={modal.kind === "ubicacion" ? data.modales.ubicacion.localidades : null} />
      )}
      <TourHelp section="centros_detail" />
    </>
  );
}

function CentroDetallePage({ id }: { id: string }) {
  const [state] = useMainResource(`web/vat/centros-detalle/${id}/`, centroDetalleValid);
  return renderMain(state, "Cargando centro…", (data) => ({ title: data.nombre, breadcrumb: null, content: <CentroDetalleContent data={data} /> }));
}

// Native URL of `VAT/urls.py` (`vat_centro_detail`).
export const vatCentrosDetalleRoute: RouteDefinition<{ id: string }> = {
  name: "vat-centros-detalle",
  match(pathname) {
    const m = pathname.match(/^\/vat\/centros\/([0-9]+)\/$/);
    return m ? { id: m[1] } : null;
  },
  render: ({ id }) => <CentroDetallePage key={id} id={id} />,
};
