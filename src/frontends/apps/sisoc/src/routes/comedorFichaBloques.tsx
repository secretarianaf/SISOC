/* eslint-disable react-refresh/only-export-components -- the unit surface is this module: the lower card types, their validation and the cards. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { CapacitacionesCard, capacitacionesValid, type Capacitaciones } from "./comedorFichaCapacitaciones";
import { withChartJs } from "./comedorFichaTablero";
import { NativeToasts } from "./nativeParity";
import { accepted, internal, record, text, webClient } from "./MainFrame";
import { useCardCollapse } from "./relevamientos";

/**
 * CO07.01 ficha, the cards of `comedor_detail.html` under the central block. Data are the
 * top-level keys of `GET /api/web/comedores/comedores/<pk>/`.
 */
export type Certificacion = { id: number; periodo: string; usuario: string; conforme: boolean; creado: string; pdf: string | null };
export type Certificaciones = { historial: string; items: Certificacion[] };
export type Colaborador = {
  id: number; nombre: string; dni: string; cuil: string; sexo: string; genero: string; telefono: string; alta: string; baja: string; actividades: string;
  editar: string | null; eliminar: { url: string; deshabilitado: boolean } | null;
};
export type Colaboradores = { agregar: string | null; items: Colaborador[]; resultados: string };
export type Interacciones = { labels: string[]; values: number[] };
export type Bloques = { certificaciones: Certificaciones; colaboradores: Colaboradores; interacciones: Interacciones; capacitaciones: Capacitaciones | null };

const strs = (v: unknown, keys: string[]) => record(v) && keys.every((k) => typeof v[k] === "string");

export function certificacionesValid(v: unknown): v is Certificaciones {
  return record(v) && internal(v.historial) && Array.isArray(v.items) &&
    v.items.every((c) => strs(c, ["periodo", "usuario", "creado"]) && Number.isSafeInteger((c as Certificacion).id) && typeof (c as Certificacion).conforme === "boolean" &&
      ((c as Certificacion).pdf === null || internal((c as Certificacion).pdf)));
}

export function colaboradoresValid(v: unknown): v is Colaboradores {
  return record(v) && (v.agregar === null || internal(v.agregar)) && text(v.resultados) && Array.isArray(v.items) &&
    v.items.every((c) => strs(c, ["nombre", "dni", "cuil", "sexo", "genero", "telefono", "alta", "baja", "actividades"]) && Number.isSafeInteger((c as Colaborador).id) &&
      ((c as Colaborador).editar === null || internal((c as Colaborador).editar)) &&
      ((c as Colaborador).eliminar === null || (record((c as Colaborador).eliminar) && internal((c as Colaborador).eliminar!.url) && typeof (c as Colaborador).eliminar!.deshabilitado === "boolean")));
}

export const interaccionesValid = (v: unknown): v is Interacciones =>
  record(v) && Array.isArray(v.labels) && v.labels.every(text) && Array.isArray(v.values) && v.values.every((n) => typeof n === "number");

export function bloquesValid(v: Record<string, unknown>): boolean {
  return certificacionesValid(v.certificaciones) && colaboradoresValid(v.colaboradores) && interaccionesValid(v.interacciones) && capacitacionesValid(v.capacitaciones);
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

// --- Colaboradores ------------------------------------------------------------------------------

/** Navigation seam of the baja (the native form POST ends in a redirect to the ficha). */
export const colaboradoresNavigation = { assign: (to: string) => window.location.assign(to), confirm: (message: string) => window.confirm(message) };
const UNCERTAIN = { message: "No se pudo confirmar el resultado. Revisá los colaboradores del espacio antes de volver a intentar.", level: "error" as const };

function EliminarForm({ c }: { c: NonNullable<Colaborador["eliminar"]> }) {
  const [toasts, setToasts] = useState<{ message: string; level: "error" }[]>([]);
  const inFlight = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || !colaboradoresNavigation.confirm("¿Desea dar de baja a este colaborador?")) return;
    inFlight.current = true; setToasts([]);
    try {
      const { data, status } = await webClient.post(c.url.replace(/^\/api\//, ""), new URLSearchParams(), { validateStatus: accepted });
      if (status === 403) setToasts([{ message: record(data) && text(data.detail) ? data.detail : UNCERTAIN.message, level: "error" }]);
      else if (record(data) && data.ok === true && internal(data.redirect)) colaboradoresNavigation.assign(data.redirect);
      else setToasts([UNCERTAIN]);
    } catch { setToasts([UNCERTAIN]); } finally { inFlight.current = false; }
  }
  return (
    <form method="post" className="d-inline" onSubmit={(e) => void submit(e)}>
      {toasts.length > 0 && <NativeToasts messages={toasts} />}
      <button type="submit" className="btn btn-sm btn-danger" disabled={c.deshabilitado}>Eliminar</button>
    </form>
  );
}

export function ColaboradoresCard({ data }: { data: Colaboradores }) {
  useCardCollapse();
  return (
    <div className="row relevamiento-container mb-3">
      <div className="col-12">
        <div className="card bg-card">
          <div className="card-header">
            <h3 className="card-title font-weight-bold me-3 pt-1">Colaboradores del espacio</h3>
            <div className="card-tools">
              {data.agregar && <><a href={data.agregar} className="btn btn-primary me-2 btn-sm">Agregar</a>{" "}</>}
              <Colapsar />
            </div>
          </div>
          <div className="card-body">
            <div className="table-responsive">
              <table className="table table-sm table-bordered table-striped mb-0">
                <thead>
                  <tr>{["Apellido y nombre", "DNI", "CUIL", "Sexo", "Género", "Teléfono", "Fecha alta", "Fecha baja", "Actividades", "Acciones"].map((h) => <th key={h}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {data.items.length ? data.items.map((c) => (
                    <tr key={c.id}>
                      <td>{c.nombre}</td><td>{c.dni}</td><td>{c.cuil}</td><td>{c.sexo}</td><td>{c.genero}</td><td>{c.telefono}</td><td>{c.alta}</td><td>{c.baja}</td><td>{c.actividades}</td>
                      <td className="text-nowrap">
                        {c.editar && <><a href={c.editar} className="btn btn-sm btn-primary me-1">Editar</a>{" "}</>}
                        {c.eliminar && <EliminarForm c={c.eliminar} />}
                      </td>
                    </tr>
                  )) : <tr><td colSpan={10} className="text-center text-muted py-3">No hay colaboradores registrados para este espacio.</td></tr>}
                </tbody>
              </table>
            </div>
            <p className="text-muted small mt-2 mb-0">{data.resultados}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Historial de interacciones (Chart.js line chart, as the native page) -----------------------------

/** The native script: a filled line, integer ticks from zero. */
export function interaccionesChartConfig(d: Interacciones) {
  return {
    type: "line",
    data: { labels: d.labels, datasets: [{ data: d.values, borderColor: "#f2a000", backgroundColor: "rgba(84, 164, 180, 0.35)", pointBackgroundColor: "#f2a000", pointBorderColor: "#f2a000", pointRadius: 4, pointHoverRadius: 5, tension: 0.35, fill: true }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c: { parsed: { y?: number } }) => ` ${c.parsed.y || 0}` } } },
      scales: { x: { grid: { display: false }, ticks: { color: "#ffffff" } }, y: { beginAtZero: true, ticks: { color: "#ffffff", precision: 0 }, grid: { color: "rgba(255,255,255,0.08)" } } },
    },
  };
}

export function InteraccionesCard({ data }: { data: Interacciones }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    let instance: { destroy: () => void } | null = null;
    const stop = withChartJs((Chart) => {
      const context = canvas.current?.getContext("2d");
      if (context) instance = new Chart(context, interaccionesChartConfig(data));
    });
    return () => { stop(); instance?.destroy(); };
  }, [data]);
  return (
    <div className="row mb-3">
      <div className="col-12">
        <div className="card bg-card">
          <div className="card-header py-1"><h4 className="fw-bold my-1">Historial de interacciones</h4></div>
          <div className="card-body"><div className="w-100 comedor-chart-h220"><canvas id="interaccionesChart" ref={canvas} /></div></div>
        </div>
      </div>
    </div>
  );
}

/** The lower cards in the order of the template; `intervenciones` is the slot of the tabs card. */
export function FichaBloques({ data, intervenciones }: { data: Bloques; intervenciones?: ReactNode }) {
  return (
    <>
      <CertificacionesCard data={data.certificaciones} />
      <ColaboradoresCard data={data.colaboradores} />
      {intervenciones}
      <InteraccionesCard data={data.interacciones} />
      {data.capacitaciones && <CapacitacionesCard data={data.capacitaciones} />}
    </>
  );
}
