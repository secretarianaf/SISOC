/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { DetailHead } from "./cdfDataTable";
import {
  client, csrfToken, integer, internal, messagesValid, navigation, record, renderCdf, text, useCdfPage, type CdfMessage, type CdfPage, type CdfState,
} from "./cdfFrame";
import { NativeModal, NativeToasts } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDF-C: `centros/actividadcentro_detail.html` (ficha with the enrolled and the waitlist, the
 * promotion forms and the `promo_error` modal). The API runs the native view; "Dar de baja" and
 * "Agregar Participante" are native links, "Promover" posts once and the native redirect is followed
 * (a POST is never retried: another promotion may take another participant).
 */
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

export type Persona = {
  id: number; apellido: string; nombre: string; documento: string; sexo: string; fecha_registro: string;
  urls: { ciudadano: string; delete?: string; promover?: string };
};
export type ActividadDetailData = {
  actividad: {
    id: number; nombre: string; categoria: string; estado_display: string; horariosdesde: string; horarioshasta: string;
    cantidad_personas: string; sexos: string[]; dias: string[]; precio_total: string;
  };
  centro: { id: number; nombre: string };
  participantes: Persona[]; lista_espera: Persona[]; promo_error: boolean; puede_tomar_asistencia: boolean;
  urls: { centro_list: string; centro_detail: string; edit: string; create_participante: string; asistencia: string };
  messages: CdfMessage[];
};

const personaValid = (p: unknown): p is Persona => record(p) && integer(p.id) && ["apellido", "nombre", "documento", "sexo", "fecha_registro"].every((k) => text(p[k])) &&
  record(p.urls) && internal(p.urls.ciudadano) && (p.urls.delete === undefined || internal(p.urls.delete)) && (p.urls.promover === undefined || internal(p.urls.promover));

export function detailValid(v: unknown): v is ActividadDetailData {
  if (!record(v) || !record(v.actividad) || !record(v.centro) || !record(v.urls)) return false;
  const a = v.actividad, u = v.urls;
  return integer(a.id) && ["nombre", "categoria", "estado_display", "horariosdesde", "horarioshasta", "cantidad_personas", "precio_total"].every((k) => text(a[k])) &&
    Array.isArray(a.sexos) && a.sexos.every(text) && Array.isArray(a.dias) && a.dias.every(text) && integer(v.centro.id) && text(v.centro.nombre) &&
    Array.isArray(v.participantes) && v.participantes.every(personaValid) && Array.isArray(v.lista_espera) && v.lista_espera.every(personaValid) &&
    typeof v.promo_error === "boolean" && typeof v.puede_tomar_asistencia === "boolean" &&
    ["centro_list", "centro_detail", "edit", "create_participante", "asistencia"].every((k) => internal(u[k])) && messagesValid(v.messages);
}

/** The flash messages stay a toast at the end of `<body>` (toastr), not inside the page content. */
export function renderWithNativeToasts<T extends { messages: CdfMessage[] }>(state: CdfState<T>, render: (data: T) => CdfPage) {
  if (state.status !== "ready") return renderCdf(state, render);
  const original = state.data;
  return renderCdf({ ...state, data: { ...original, messages: [] } }, () => {
    const page = render(original);
    return { ...page, content: <><NativeToasts messages={original.messages} />{page.content}</> };
  });
}

function Tabla({ filas, accion }: { filas: Persona[]; accion: (p: Persona) => ReactNode }) {
  return (
    <div className="cdf-tbl-scroll">
      <table className="cdf-table">
        <thead>
          <tr><th>Participante</th><th>DNI</th><th>Género</th><th>Fecha de Registro</th><th className="text-end">Acciones</th></tr>
        </thead>
        <tbody>
          {filas.map((p) => (
            <tr key={p.id}>
              <td><a href={p.urls.ciudadano}>{p.apellido}, {p.nombre}</a></td>
              <td>{p.documento}</td>
              <td>{p.sexo}</td>
              <td>{p.fecha_registro}</td>
              <td className="text-end">{accion(p)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Info({ icon, label, children }: { icon: string; label: string; children: ReactNode }) {
  return (
    <div className="cdf-info-item">
      <i className={`fas ${icon}`} />
      <div><div className="cdf-info-label">{label}</div><div className="cdf-info-value">{children}</div></div>
    </div>
  );
}

function PromoErrorModal({ close }: { close: () => void }) {
  return (
    <NativeModal id="promoErrorModal" title="Cupo Máximo Alcanzado" close={close} size=" modal-dialog-centered modal-sm">
      <div className="modal-content">
        <div className="modal-header bg-warning text-white">
          <h5 className="modal-title" id="promoErrorLabel">Cupo Máximo Alcanzado</h5>
          <button type="button" className="btn-close btn-close-white" aria-label="Cerrar" onClick={close} />
        </div>
        <div className="modal-body">No hay cupo disponible para promover a un participante de la lista de espera.</div>
        <div className="modal-footer"><button type="button" className="btn btn-outline-secondary" onClick={close}>Cerrar</button></div>
      </div>
    </NativeModal>
  );
}

export function ActividadDetailContent({ data }: { data: ActividadDetailData }) {
  const { actividad: a, centro, urls } = data;
  const [modal, setModal] = useState(data.promo_error);
  const [uncertain, setUncertain] = useState(false);
  const sending = useRef(false);
  // The native `#lista-espera` anchor (the history URL redirects there) scrolls once the page exists.
  useEffect(() => {
    const id = window.location.hash.slice(1);
    if (id) document.getElementById(id)?.scrollIntoView();
  }, []);

  async function promover(event: FormEvent<HTMLFormElement>, p: Persona) {
    event.preventDefault();
    if (sending.current) return;
    sending.current = true;
    try {
      const { data: body } = await client.post(`web/cdf/centros/${centro.id}/actividades/${a.id}/lista-espera/${p.id}/promover/`, new FormData(event.currentTarget));
      if (record(body) && internal(body.url)) { navigation.assign(body.url); return; }
      setUncertain(true);
    } catch {
      setUncertain(true);
    }
    sending.current = false;
  }

  return (
    <>
      <DetailHead />
      <div className="cdf-page">
        <div className="cdf-hero">
          <div className="cdf-hero-block">
            <h1>{a.nombre}</h1>
            <p className="cdf-hero-sub">
              <span><i className="fas fa-house-chimney" />{centro.nombre}</span>{" "}
              <span><i className="fas fa-layer-group" />{a.categoria}</span>{" "}
              <span><i className="fas fa-clock" />{a.horariosdesde} - {a.horarioshasta}</span>
            </p>
          </div>
          <span className="cdf-pill cdf-pill--teal">{a.estado_display}</span>
        </div>
        {uncertain && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
        <div className="cdf-actions mb-4">
          <a href={urls.edit} className="cdf-btn"><i className="fas fa-pen" />Editar</a>{" "}
          <a href={urls.create_participante} className="cdf-btn cdf-btn--primary"><i className="fas fa-user-plus" />Agregar Participante</a>
          {data.puede_tomar_asistencia && <>{" "}<a href={urls.asistencia} className="cdf-btn cdf-btn--gold"><i className="fas fa-clipboard-check" />Tomar Asistencia</a></>}
        </div>
        <div className="cdf-card">
          <div className="cdf-card-head"><i className="fas fa-circle-info" /><span>Información de la actividad</span></div>
          <div className="cdf-card-body">
            <div className="cdf-info-grid">
              <Info icon="fa-house-chimney" label="Centro">{centro.nombre}</Info>
              <Info icon="fa-layer-group" label="Categoría">{a.categoria}</Info>
              <Info icon="fa-users" label="Cupo">{a.cantidad_personas}</Info>
              <Info icon="fa-venus-mars" label="Dirigido a">{a.sexos.length ? a.sexos.join(" , ") : "Todos los sexos"}</Info>
              <Info icon="fa-calendar-days" label="Días">{a.dias.length ? a.dias.join(" , ") : "No asignado"}</Info>
              <Info icon="fa-clock" label="Horario">{a.horariosdesde} - {a.horarioshasta}</Info>
              <Info icon="fa-dollar-sign" label="Costo total">${a.precio_total}</Info>
            </div>
          </div>
        </div>
        <div className="cdf-card">
          <div className="cdf-card-head"><i className="fas fa-user-check" /><span>Nómina de Participantes</span></div>
          <div className="cdf-card-body cdf-card-body--flush">
            {data.participantes.length ? (
              <Tabla filas={data.participantes} accion={(p) => <a href={p.urls.delete} className="cdf-btn cdf-btn--danger">Dar de baja</a>} />
            ) : (
              <div className="cdf-empty">
                <i className="fas fa-user-plus" />
                <p className="cdf-empty-t">No hay participantes inscritos aún</p>
                <p className="cdf-empty-s">Sumá el primero desde "Agregar Participante".</p>
              </div>
            )}
          </div>
        </div>
        <div className="cdf-card" id="lista-espera">
          <div className="cdf-card-head"><i className="fas fa-hourglass-half" /><span>Lista de Espera</span></div>
          <div className="cdf-card-body cdf-card-body--flush">
            {data.lista_espera.length ? (
              <Tabla filas={data.lista_espera} accion={(p) => (
                <form method="post" action={p.urls.promover} style={{ display: "inline" }} onSubmit={(e) => void promover(e, p)}>
                  <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
                  <button type="submit" className="cdf-btn cdf-btn--primary">Promover</button>
                </form>
              )} />
            ) : (
              <div className="cdf-empty">
                <i className="fas fa-hourglass-half" />
                <p className="cdf-empty-t">Sin lista de espera</p>
                <p className="cdf-empty-s">Cuando la actividad se quede sin cupo, los nuevos inscriptos van a aparecer acá.</p>
              </div>
            )}
          </div>
        </div>
      </div>
      {modal && <PromoErrorModal close={() => setModal(false)} />}
    </>
  );
}

export const breadcrumb = (items: [string, string | null][]) => (
  <ol className="breadcrumb float-sm-right">
    {items.map(([label, href]) => (href
      ? <li key={label} className="breadcrumb-item"><a href={href}>{label}</a></li>
      : <li key={label} className="breadcrumb-item active">{label}</li>))}
  </ol>
);

function ActividadDetail({ id }: { id: string }) {
  const state = useCdfPage(`web/cdf/actividades/${id}/${window.location.search}`, detailValid);
  return renderWithNativeToasts(state, (data) => ({
    title: "Detalle Actividad",
    breadcrumb: breadcrumb([["Centro de Familia", data.urls.centro_list], ["Actividades", data.urls.centro_detail], ["Detalle", null]]),
    content: <ActividadDetailContent data={data} />,
  }));
}

// Native URL of the CDF activity ficha (CDF-C).
export const cdfActividadRoute: RouteDefinition<{ id: string }> = {
  name: "cdf-actividad",
  match: (pathname) => {
    const m = /^\/centrodefamilia\/centros\/actividades\/([1-9]\d*)\/detalle\/$/.exec(pathname);
    return m ? { id: m[1] } : null;
  },
  render: ({ id }) => <ActividadDetail id={id} />,
};
