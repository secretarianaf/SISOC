/* eslint-disable react-refresh/only-export-components -- unit surface: provider, hook, cards and validators travel together for the tests. */
import { createContext, Fragment, useContext, useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { webClient, internal, record, text } from "./MainFrame";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";

/**
 * C04.02: the cards the verticals add to Ciudadano 360 (`ciudadanos/ciudadano_detail.html`), drawn from the JSON of
 * `/api/web/<backend>/ciudadanos/<pk>/aportes/<aporte>/` (`ciudadanos.web_aportes`). The list of aportes and their
 * URLs come from the server (`GET /api/web/ciudadanos/<pk>/`), never from the client. Every aporte loads on its own, so
 * a slow or failed provider only affects its own cards (C2: those show "No disponible", never partial data).
 */
export type Aporte = { aporte: string; secciones: string[]; url: string };
export type AporteState =
  | { status: "loading" }
  | { status: "ok"; secciones: Record<string, unknown> }
  | { status: "unavailable" }
  | { status: "forbidden"; prerequisite: WebPrerequisite };

type Comedor = { id: number; nombre: string; url: string };
type ComedorActual = Comedor & { tipo_texto: string; provincia_texto: string; municipio_texto: string };
type Nomina = { estado: string; comedor: Comedor | null; fecha_texto: string };
export type ComedoresData = { nomina_actual: (Omit<Nomina, "comedor"> & { comedor: ComedorActual | null }) | null; historial: Nomina[] };
export type Colaboracion = { comedor: Comedor | null; fecha_alta_texto: string; fecha_baja_texto: string; actividades: string[] };
export type PwaData = { pertenece_comunidad_indigena: boolean; situacion_calle: boolean; persona_con_celiaquia: boolean };
type Legajo = { estado_expediente: string; estado_legajo: string; resultado_cruce: string; estado_cupo: string; es_titular_activo: boolean; revision_tecnica: string };
export type CeliaquiaData = { legajo_actual: Legajo | null; historial: { estado_legajo: string; estado_cupo: string; creado_en_texto: string }[] };
type Inscripcion = {
  curso_texto: string; comision: { id: number; codigo: string; url: string }; estado_display: string;
  asistencias_presentes: number; asistencias_registradas: number; asistencia_porcentaje: number; url: string;
};
type InscripcionOferta = { curso_texto: string; comision: { id: number; codigo: string; url: string }; estado_display: string; url: string };
export type VatPrograma = {
  nombre: string; voucher_badge: { tipo: "activo" | "referencia" | "sin_voucher"; estado_display: string };
  voucher: { id: number; url: string; estado_display: string } | null;
  creditos_totales: number; creditos_actuales: number; cursos_asignados: number; asistencias_presentes: number; asistencias_registradas: number;
  inscripciones: Inscripcion[]; inscripciones_oferta: InscripcionOferta[];
};
export type CdfFila = { centro_nombre: string; actividad_nombre: string; estado: string; fecha_registro_texto: string };
export type CdfMontoData = { total: string; total_texto: string };

const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const bool = (v: unknown): v is boolean => typeof v === "boolean";
const list = (v: unknown, each: (item: unknown) => boolean): v is unknown[] => Array.isArray(v) && v.every(each);
const comedorBasic = (v: unknown): boolean => record(v) && integer(v.id) && text(v.nombre) && internal(v.url);
const comedorOrNull = (v: unknown) => v === null || comedorBasic(v);
const comision = (v: unknown) => record(v) && integer(v.id) && text(v.codigo) && internal(v.url);

const comedoresValid = (v: unknown) => {
  if (!record(v) || !list(v.historial, (n) => record(n) && text(n.estado) && comedorOrNull(n.comedor) && text(n.fecha_texto))) return false;
  const a = v.nomina_actual;
  if (a === null) return true;
  return record(a) && text(a.estado) && text(a.fecha_texto) && (a.comedor === null || (comedorBasic(a.comedor) && record(a.comedor) &&
    text(a.comedor.tipo_texto) && text(a.comedor.provincia_texto) && text(a.comedor.municipio_texto)));
};
const colaboracionesValid = (v: unknown) => list(v, (c) => record(c) && comedorOrNull(c.comedor) && text(c.fecha_alta_texto) &&
  text(c.fecha_baja_texto) && list(c.actividades, text));
const pwaValid = (v: unknown) => record(v) && bool(v.pertenece_comunidad_indigena) && bool(v.situacion_calle) && bool(v.persona_con_celiaquia);
const celiaquiaValid = (v: unknown) => {
  if (!record(v) || !list(v.historial, (h) => record(h) && text(h.estado_legajo) && text(h.estado_cupo) && text(h.creado_en_texto))) return false;
  const l = v.legajo_actual;
  return l === null || (record(l) && ["estado_expediente", "estado_legajo", "resultado_cruce", "estado_cupo", "revision_tecnica"].every((k) => text(l[k])) && bool(l.es_titular_activo));
};
const vatValid = (v: unknown) => record(v) && list(v.programas, (p) => record(p) && text(p.nombre) && record(p.voucher_badge) &&
  ["activo", "referencia", "sin_voucher"].includes(p.voucher_badge.tipo as string) && text(p.voucher_badge.estado_display) &&
  (p.voucher === null || (record(p.voucher) && integer(p.voucher.id) && internal(p.voucher.url) && text(p.voucher.estado_display))) &&
  ["creditos_totales", "creditos_actuales", "cursos_asignados", "asistencias_presentes", "asistencias_registradas"].every((k) => integer(p[k])) &&
  list(p.inscripciones, (i) => record(i) && text(i.curso_texto) && comision(i.comision) && text(i.estado_display) && integer(i.asistencias_presentes) &&
    integer(i.asistencias_registradas) && integer(i.asistencia_porcentaje) && internal(i.url)) &&
  list(p.inscripciones_oferta, (i) => record(i) && text(i.curso_texto) && comision(i.comision) && text(i.estado_display) && internal(i.url)));
const cdfValid = (v: unknown) => list(v, (f) => record(f) && text(f.centro_nombre) && text(f.actividad_nombre) && text(f.estado) && text(f.fecha_registro_texto));
const cdfMontoValid = (v: unknown) => record(v) && text(v.total) && text(v.total_texto);

/** Sections each aporte must bring; a response without them (or malformed) is "No disponible". */
const SECTIONS: Record<string, Record<string, (v: unknown) => boolean>> = {
  comedores: { comedores: comedoresValid, comedores_colaboraciones: colaboracionesValid },
  pwa: { pwa: pwaValid },
  celiaquia: { celiaquia: celiaquiaValid },
  vat: { vat: vatValid },
  centrodefamilia: { centrodefamilia: cdfValid, centrodefamilia_monto: cdfMontoValid },
};

export function aporteResult(aporte: string, status: number, data: unknown): AporteState {
  if (status === 403) {
    const prerequisite = prerequisiteFromForbidden(data);
    return prerequisite ? { status: "forbidden", prerequisite } : { status: "unavailable" };
  }
  const expected = SECTIONS[aporte];
  if (status !== 200 || !expected || !record(data) || data.aporte !== aporte || !record(data.secciones)) return { status: "unavailable" };
  const secciones = data.secciones;
  return Object.entries(expected).every(([name, valid]) => valid(secciones[name])) ? { status: "ok", secciones } : { status: "unavailable" };
}

type Registry = Record<string, AporteState>;
const AportesContext = createContext<Registry>({});

/** Requests every aporte in parallel on mount; each one settles on its own (there is no automatic retry). */
export function AportesProvider({ aportes, children }: { aportes: Aporte[]; children: ReactNode }) {
  const [registry, setRegistry] = useState<Registry>({});
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const settle = (aporte: string, state: AporteState) => { if (active) setRegistry((current) => ({ ...current, [aporte]: state })); };
    for (const { aporte, url } of aportes) {
      const relative = url.replace(/^\/api\//, "");
      // 401 is left to the client (login redirect); the rest is classified here.
      webClient.get(relative, { signal: controller.signal, validateStatus: (s) => s !== 401 })
        .then((r) => settle(aporte, aporteResult(aporte, r.status, r.data)))
        .catch((error: { response?: { status?: number } }) => { if (error?.response?.status !== 401) settle(aporte, { status: "unavailable" }); });
    }
    return () => { active = false; controller.abort(); };
  }, [aportes]);
  return <AportesContext.Provider value={registry}>{children}</AportesContext.Provider>;
}

export function useAporte(aporte: string): AporteState {
  return useContext(AportesContext)[aporte] ?? { status: "loading" };
}

/** The first prerequisite a provider asked for (the standard shell flow shows it instead of the page). */
export function pendingPrerequisite(registry: Registry): WebPrerequisite | null {
  for (const state of Object.values(registry)) if (state.status === "forbidden") return state.prerequisite;
  return null;
}
export function useAportesPrerequisite(): WebPrerequisite | null {
  return pendingPrerequisite(useContext(AportesContext));
}

// --- Cards (`ciudadano_seccion.html` and the other fragments) ---------------

const LABEL: CSSProperties = { color: "rgba(255,255,255,0.7)" };
const VALUE: CSSProperties = { fontSize: "0.95rem", color: "rgba(255,255,255,0.95)", marginTop: "0.25rem" };
const GRID: CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" };
const LINK: CSSProperties = { color: "#E7BA61", textDecoration: "underline" };
const EMPTY: CSSProperties = { color: "rgba(255,255,255,0.5)" };
const TITLE_BADGE: CSSProperties = { background: "rgba(46, 125, 51, 0.6)", color: "white", padding: "0.35rem 0.75rem", fontSize: "0.75rem", marginLeft: "0.5rem" };
const SUBTITLE: CSSProperties = { marginTop: "1.5rem", marginBottom: "1rem", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "1rem" };
const BORDER_GOLD: CSSProperties = { border: "2px solid var(--gold)" };

export const NO_DISPONIBLE = "No disponible";
const Loading = () => <div role="status">Cargando…</div>;

function ComedorLink({ comedor }: { comedor: Comedor | null }) {
  return comedor ? <a href={comedor.url} style={LINK}>{comedor.nombre}</a> : <>-</>;
}

/** The state badge of a nómina / participación. */
function EstadoBadge({ estado, activo, espera, labels }: { estado: string; activo: string; espera: string; labels: [string, string, string] }) {
  if (estado === activo) return <span className="badge" style={{ background: "var(--green)" }}>{labels[0]}</span>;
  if (estado === espera) return <span className="badge" style={{ background: "#FFB84D", color: "var(--navy-dark)" }}>{labels[1]}</span>;
  return <span className="badge" style={{ background: "rgba(255,255,255,0.2)" }}>{labels[2]}</span>;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <div><small style={LABEL}>{label}</small><div style={VALUE}>{children}</div></div>;
}

export function ComedoresCard({ state }: { state: AporteState }) {
  if (state.status === "loading") return <Loading />;
  if (state.status !== "ok") return state.status === "unavailable" ? <div className="tabla-legajo" style={BORDER_GOLD}><h5 className="mb-3"><span>Comedores</span></h5><p style={EMPTY}>{NO_DISPONIBLE}</p></div> : null;
  const data = state.secciones.comedores as ComedoresData;
  const actual = data.nomina_actual;
  const comedor = actual?.comedor ?? null;
  return (
    <div className="tabla-legajo" style={BORDER_GOLD}>
      <h5 className="mb-3">
        <span>Comedores</span>
        {actual?.estado === "activo" && <>{" "}<span className="badge" style={{ background: "rgba(46, 125, 51, 0.6)", color: "white", padding: "0.35rem 0.75rem", fontSize: "0.75rem", marginLeft: "0.5rem" }}>Activo</span></>}
      </h5>
      {actual ? <>
        <div style={GRID}>
          <Field label="Comedor"><ComedorLink comedor={comedor} /></Field>
          <Field label="Tipo">{comedor?.tipo_texto ?? "-"}</Field>
          <Field label="Provincia">{comedor?.provincia_texto ?? "-"}</Field>
          <Field label="Municipio">{comedor?.municipio_texto ?? "-"}</Field>
          <Field label="Estado"><EstadoBadge estado={actual.estado} activo="activo" espera="espera" labels={["Activo", "En espera", "Baja"]} /></Field>
          <Field label="Fecha Registro">{actual.fecha_texto}</Field>
        </div>
        {data.historial.length > 1 && <>
          <h6 style={SUBTITLE}>Historial de Comedores</h6>
          <table className="table table-sm">
            <thead><tr><th>Comedor</th><th>Estado</th><th>Fecha</th></tr></thead>
            <tbody>
              {data.historial.map((n, i) => (
                <tr key={i}>
                  <td><ComedorLink comedor={n.comedor} /></td>
                  <td><EstadoBadge estado={n.estado} activo="activo" espera="espera" labels={["Activo", "En espera", "Baja"]} /></td>
                  <td>{n.fecha_texto}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>}
      </> : <p style={EMPTY}>No hay registros de comedores.</p>}
    </div>
  );
}

/** `ciudadano_colaboraciones.html`: no empty text in the source, so a failure hides the block like the native page. */
export function ColaboracionesCard({ state }: { state: AporteState }) {
  if (state.status !== "ok") return null;
  const items = state.secciones.comedores_colaboraciones as Colaboracion[];
  if (items.length === 0) return null;
  return (
    <div className="row px-4 mt-3"><div className="col-12"><div className="tabla-legajo">
      <h5 className="mb-3">Colaboraciones en comedores</h5>
      <table className="table table-sm">
        <thead><tr><th>Comedor</th><th>Fecha alta</th><th>Fecha baja</th><th>Actividades</th></tr></thead>
        <tbody>
          {items.map((c, i) => (
            <tr key={i}>
              <td><ComedorLink comedor={c.comedor} /></td>
              <td>{c.fecha_alta_texto}</td>
              <td>{c.fecha_baja_texto}</td>
              <td>{c.actividades.length ? c.actividades.map((a, j) => <Fragment key={j}>{j > 0 && " "}{a}{j < c.actividades.length - 1 && " ,"}</Fragment>) : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div></div></div>
  );
}

const PWA_ROWS: [keyof PwaData, string][] = [
  ["pertenece_comunidad_indigena", "Pueblo originario:"], ["situacion_calle", "Situación de calle:"], ["persona_con_celiaquia", "Persona con Celiaquía:"],
];

/** `ciudadano_flags.html`: the three info rows; if the provider is down they never say "No". */
export function PwaFilas({ state }: { state: AporteState }) {
  if (state.status === "loading") return <Loading />;
  if (state.status === "forbidden") return null;
  const data = state.status === "ok" ? (state.secciones.pwa as PwaData) : null;
  return <>{PWA_ROWS.map(([key, label]) => (
    <div className="info-row" key={key}><strong>{label}</strong><span className="value">{data ? (data[key] ? "Sí" : "No") : NO_DISPONIBLE}</span></div>
  ))}</>;
}

/** `ciudadano_badges.html` (in the page's `h1`): only the `true` ones, none when the provider fails. */
export function PwaBadges({ state }: { state: AporteState }) {
  if (state.status !== "ok") return null;
  const data = state.secciones.pwa as PwaData;
  return <>
    {data.situacion_calle && <>{" "}<span className="badge bg-danger ms-2 align-middle" style={{ fontSize: "0.75rem" }}>Situación de calle</span></>}
    {data.persona_con_celiaquia && <>{" "}<span className="badge bg-warning text-dark ms-2 align-middle" style={{ fontSize: "0.75rem" }}>Persona con Celiaquía</span></>}
  </>;
}

export function CeliaquiaCard({ state }: { state: AporteState }) {
  if (state.status === "loading") return <Loading />;
  if (state.status === "forbidden") return null;
  if (state.status === "unavailable") return <div className="tabla-legajo" style={BORDER_GOLD}><h5 className="mb-3"><span>Celiaquía</span></h5><p style={EMPTY}>{NO_DISPONIBLE}</p></div>;
  const data = state.secciones.celiaquia as CeliaquiaData;
  const l = data.legajo_actual;
  return (
    <div className="tabla-legajo" style={BORDER_GOLD}>
      {/* The native card always shows the "Activo" badge, even without a legajo. */}
      <h5 className="mb-3"><span>Celiaquía</span>{" "}<span className="badge" style={TITLE_BADGE}>Activo</span></h5>
      {l ? <>
        <div style={GRID}>
          <Field label="Estado Expediente">{l.estado_expediente}</Field>
          <Field label="Estado Legajo">{l.estado_legajo}</Field>
          <Field label="Resultado Cruce">{l.resultado_cruce}</Field>
          <Field label="Estado Cupo">{l.estado_cupo}</Field>
          <Field label="Titular Activo">{l.es_titular_activo ? "Si" : "No"}</Field>
          <Field label="Revision Tecnico">{l.revision_tecnica}</Field>
        </div>
        {data.historial.length > 1 && <>
          <h6 style={SUBTITLE}>Historial de Expedientes</h6>
          <table className="table table-sm">
            <thead><tr><th>Estado</th><th>Cupo</th><th>Fecha</th></tr></thead>
            <tbody>{data.historial.map((h, i) => <tr key={i}><td>{h.estado_legajo}</td><td>{h.estado_cupo}</td><td>{h.creado_en_texto}</td></tr>)}</tbody>
          </table>
        </>}
      </> : <p style={EMPTY}>No hay expedientes de celiaquía registrados.</p>}
    </div>
  );
}

const VAT_PROGRAM: CSSProperties = { border: "1px solid rgba(255,255,255,0.12)", borderRadius: "12px", padding: "1rem", background: "rgba(255,255,255,0.03)" };
const VAT_HEAD: CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" };
const VAT_METRICS: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "1rem" };
const VAT_H6: CSSProperties = { marginTop: "1rem", marginBottom: "0.75rem", color: "rgba(255,255,255,0.92)" };

function VatVoucherBadge({ badge }: { badge: VatPrograma["voucher_badge"] }) {
  if (badge.tipo === "activo") return <span className="badge" style={{ background: "var(--green)" }}>Voucher activo</span>;
  if (badge.tipo === "referencia") return <span className="badge" style={{ background: "rgba(255,255,255,0.2)" }}>Voucher {badge.estado_display.toLowerCase()}</span>;
  return <span className="badge" style={{ background: "rgba(255,255,255,0.2)" }}>Sin voucher</span>;
}

function VatPrograma({ p }: { p: VatPrograma }) {
  return (
    <div style={VAT_PROGRAM}>
      <div style={VAT_HEAD}>
        <div><h6 style={{ margin: 0, color: "white" }}>{p.nombre}</h6><small style={{ color: "rgba(255,255,255,0.65)" }}>Detalle del legajo dentro del programa</small></div>
        <div><VatVoucherBadge badge={p.voucher_badge} /></div>
      </div>
      <div style={VAT_METRICS}>
        <Field label="Voucher asignado">
          {p.voucher ? <><a href={p.voucher.url} style={LINK}>#{p.voucher.id}</a>{" "}<span style={{ color: "rgba(255,255,255,0.7)" }}>({p.voucher.estado_display})</span></> : "-"}
        </Field>
        <Field label="Créditos totales">{p.creditos_totales}</Field>
        <Field label="Créditos actuales">{p.creditos_actuales}</Field>
        <Field label="Cursos asignados">{p.cursos_asignados}</Field>
        <Field label="Asistencia">{p.asistencias_presentes}/{p.asistencias_registradas} sesiones</Field>
      </div>
      {p.inscripciones.length > 0 && <>
        <h6 style={VAT_H6}>Cursos asignados</h6>
        <table className="table table-sm">
          <thead><tr><th>Curso</th><th>Comisión</th><th>Estado</th><th>Asistencia</th><th>Detalle</th></tr></thead>
          <tbody>
            {p.inscripciones.map((i, k) => (
              <tr key={k}>
                <td>{i.curso_texto}</td>
                <td><a href={i.comision.url} style={LINK}>{i.comision.codigo}</a></td>
                <td>{i.estado_display}</td>
                <td>{i.asistencias_presentes}/{i.asistencias_registradas}{i.asistencias_registradas > 0 && <>{" "}<span style={{ color: "rgba(255,255,255,0.65)" }}>({i.asistencia_porcentaje}%)</span></>}</td>
                <td><a href={i.url} style={LINK}>Ver inscripción</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </>}
      {p.inscripciones_oferta.length > 0 && <>
        <h6 style={VAT_H6}>Inscripciones de oferta</h6>
        <table className="table table-sm">
          <thead><tr><th>Curso</th><th>Comisión</th><th>Estado</th><th>Detalle</th></tr></thead>
          <tbody>
            {p.inscripciones_oferta.map((i, k) => (
              <tr key={k}>
                <td>{i.curso_texto}</td>
                <td><a href={i.comision.url} style={LINK}>{i.comision.codigo}</a></td>
                <td>{i.estado_display}</td>
                <td><a href={i.url} style={LINK}>Ver inscripción</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </>}
    </div>
  );
}

export function VatCard({ state }: { state: AporteState }) {
  if (state.status === "loading") return <Loading />;
  if (state.status === "forbidden") return null;
  if (state.status === "unavailable") return <div className="tabla-legajo" style={BORDER_GOLD}><h5 className="mb-3"><span>Programa VAT</span></h5><p style={EMPTY}>{NO_DISPONIBLE}</p></div>;
  const programas = (state.secciones.vat as { programas: VatPrograma[] }).programas;
  return (
    <div className="tabla-legajo" style={BORDER_GOLD}>
      <h5 className="mb-3">
        <span>Programa VAT</span>
        {programas.length > 0 && <>{" "}<span className="badge" style={TITLE_BADGE}>{programas.length} programa{programas.length === 1 ? "" : "s"}</span></>}
      </h5>
      {programas.length > 0
        ? <div style={{ display: "grid", gap: "1rem" }}>{programas.map((p, i) => <VatPrograma key={i} p={p} />)}</div>
        : <p style={EMPTY}>No hay registros VAT para este ciudadano.</p>}
    </div>
  );
}

export function CdfCard({ state }: { state: AporteState }) {
  if (state.status === "loading") return <Loading />;
  if (state.status === "forbidden") return null;
  if (state.status === "unavailable") return <div className="tabla-legajo" style={BORDER_GOLD}><h5 className="mb-3">Centro de Familia</h5><p style={EMPTY}>{NO_DISPONIBLE}</p></div>;
  const filas = state.secciones.centrodefamilia as CdfFila[];
  return (
    <div className="tabla-legajo" style={BORDER_GOLD}>
      <h5 className="mb-3">Centro de Familia</h5>
      {filas.length > 0 ? (
        <table className="table table-sm">
          <thead><tr><th>Centro</th><th>Actividad</th><th>Estado</th><th>Fecha Registro</th></tr></thead>
          <tbody>
            {filas.map((f, i) => (
              <tr key={i}>
                <td>{f.centro_nombre}</td>
                <td>{f.actividad_nombre}</td>
                <td><EstadoBadge estado={f.estado} activo="inscrito" espera="lista_espera" labels={["Inscrito", "Lista Espera", "Dado de Baja"]} /></td>
                <td>{f.fecha_registro_texto}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p style={EMPTY}>No hay participaciones registradas.</p>}
    </div>
  );
}

/** The text of the Centro de Familia amount card: the server's `total_texto` (a successful zero is data), or "No disponible". */
export function CdfMonto({ state }: { state: AporteState }) {
  if (state.status === "loading") return <Loading />;
  if (state.status !== "ok") return <>{state.status === "unavailable" ? NO_DISPONIBLE : null}</>;
  return <>{(state.secciones.centrodefamilia_monto as CdfMontoData).total_texto}</>;
}
