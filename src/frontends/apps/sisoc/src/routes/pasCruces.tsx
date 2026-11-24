/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators and helpers are exported for the tests. */
import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { InsumosToastList } from "../InsumosToast";
import { prerequisiteFromForbidden } from "../webAccess";
import { record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import {
  BuscadorButton, EmptyState, ModuleHeader, PAS_API, PAS_STYLESHEET, SourceChip, WorkflowNav,
  bool, integer, list, nullable, shape, workflowValid, type WorkflowCard,
} from "./pasFrame";
import type { RouteDefinition } from "./types";

/**
 * PAS03.01 and PAS03.02: «Cruces y Novedades» on the native URL `pas/cruces`
 * (`pas/area.html`, branch `cruces`). The data comes from `/api/web/pas/cruces/`
 * and every action posts to the sibling routes (`exportar-sintys/`,
 * `importar-sintys/`, `actualizar-renaper/`). After each action the page asks
 * the GET again, as the native page reloads; messages are toasts. SINTyS and
 * RENAPER are never called from here: no automatic retry, a result that cannot
 * be confirmed is reported and the page is read again.
 */
type Etapa = { numero: number; nombre: string; fecha: string | null; fecha_texto: string; completada: boolean; integracion_pendiente: boolean };
type Incompatibilidad = { titular: string; dni: number; categoria: string; detalle: string; fecha_deteccion: string; periodo_impacto: string; estado: string };
export type CrucesData = {
  can_change: boolean; total_padron: number;
  circuito: { periodo: string; periodo_texto: string; existe: boolean };
  etapas: Etapa[];
  renaper: { fecha: string | null; total: number; fallecidas: number; errores: number };
  incompatibilidades: Incompatibilidad[];
  areas: WorkflowCard[];
};
type Notice = { message: string; level: "success" | "error" };

const etapaValid = (v: unknown): v is Etapa => shape(v, {
  numero: integer, nombre: text, fecha: nullable(text), fecha_texto: text, completada: bool, integracion_pendiente: bool,
});
const incompatibilidadValid = (v: unknown): v is Incompatibilidad => shape(v, {
  titular: text, dni: integer, categoria: text, detalle: text, fecha_deteccion: text, periodo_impacto: text, estado: text,
});
export const crucesValid = (v: unknown): v is CrucesData => shape(v, {
  can_change: bool, total_padron: integer,
  circuito: (c) => shape(c, { periodo: text, periodo_texto: text, existe: bool }),
  etapas: list(etapaValid),
  renaper: (r) => shape(r, { fecha: nullable(text), total: integer, fallecidas: integer, errores: integer }),
  incompatibilidades: list(incompatibilidadValid),
  areas: workflowValid,
});

const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const EXPORT_FAILED = "No se pudo generar la nómina.";
const RENAPER_CONFIRM = "Se consultará todo el padrón PAS contra RENAPER. ¿Continuar?";
const ENDPOINT = `${PAS_API}cruces/`;
const ANY = { validateStatus: () => true };

type Outcome = { kind: "done"; notice: Notice | null } | { kind: "forbidden"; data: unknown };

const isBuffer = (data: unknown): data is ArrayBuffer => Object.prototype.toString.call(data) === "[object ArrayBuffer]";
const messageOf = (data: unknown) => (record(data) && text(data.message) ? data.message : null);

/** `area.html` script: the blob is saved with the name of `Content-Disposition`, then the page reloads. */
function saveBlob(data: ArrayBuffer, headers: Record<string, string | undefined>) {
  const name = /filename="([^"]+)"/.exec(headers["content-disposition"] ?? "")?.[1] ?? "nomina_pas_sintys.xlsx";
  const url = URL.createObjectURL(new Blob([data], { type: headers["content-type"] ?? "" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function exportSintys(): Promise<Outcome & { alert?: string }> {
  try {
    const response = await webClient.post(`${ENDPOINT}exportar-sintys/`, null, { responseType: "arraybuffer", ...ANY });
    if (response.status === 403) {
      const body = isBuffer(response.data) ? (() => { try { return JSON.parse(new TextDecoder().decode(response.data)); } catch { return null; } })() : response.data;
      return { kind: "forbidden", data: body };
    }
    if (response.status === 200 && isBuffer(response.data)) {
      saveBlob(response.data, response.headers as Record<string, string | undefined>);
      return { kind: "done", notice: null };
    }
    return { kind: "done", notice: null, alert: response.status === 504 ? UNCERTAIN : EXPORT_FAILED };
  } catch {
    return { kind: "done", notice: null, alert: EXPORT_FAILED };
  }
}

async function importSintys(file: File): Promise<Outcome> {
  const body = new FormData();
  body.append("archivo", file);
  try {
    const { data, status } = await webClient.post(`${ENDPOINT}importar-sintys/`, body, ANY);
    if (status === 403) return { kind: "forbidden", data };
    const message = messageOf(data);
    if (status === 200 && message) return { kind: "done", notice: { message, level: "success" } };
    if (status === 400 && message) return { kind: "done", notice: { message, level: "error" } };
  } catch {
    // Reported as unconfirmed below.
  }
  return { kind: "done", notice: { message: UNCERTAIN, level: "error" } };
}

async function updateRenaper(): Promise<Outcome> {
  try {
    const { data, status } = await webClient.post(`${ENDPOINT}actualizar-renaper/`, null, ANY);
    if (status === 403) return { kind: "forbidden", data };
    const message = messageOf(data);
    if (status === 200 && message) return { kind: "done", notice: { message, level: "success" } };
  } catch {
    // Reported as unconfirmed below.
  }
  return { kind: "done", notice: { message: UNCERTAIN, level: "error" } };
}

/** `pluralize:"es"`. */
const controles = (total: number) => `${total} control${total === 1 ? "" : "es"}`;

export function CrucesHeading({ data, onDone }: { data: CrucesData; onDone: (outcome: Outcome) => void }) {
  const [exporting, setExporting] = useState(false);
  const busy = useRef(false);
  const input = useRef<HTMLInputElement>(null);

  async function guarded(task: () => Promise<Outcome & { alert?: string }>, release?: () => void) {
    if (busy.current) return;
    busy.current = true;
    const outcome = await task();
    busy.current = false;
    if (outcome.kind === "done" && outcome.alert) {
      release?.();
      window.alert(outcome.alert);
      return;
    }
    onDone(outcome);
  }
  const submitExport = (event: FormEvent) => {
    event.preventDefault();
    if (busy.current) return;
    setExporting(true);
    void guarded(exportSintys, () => setExporting(false));
  };
  const submitImport = (event: FormEvent) => {
    event.preventDefault();
    const file = input.current?.files?.[0];
    if (file) void guarded(() => importSintys(file));
  };
  const changed = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files?.length) void guarded(() => importSintys(event.target.files![0]));
  };
  return <div className="pas-circuit-heading">
    <div>
      <h2>Circuito administrativo mensual</h2>
      <span>Período {data.circuito.periodo_texto} · {data.total_padron} titulares incluidos</span>
    </div>
    {data.can_change && <div className="pas-circuit-actions">
      <form method="post" id="pas-export-sintys-form" onSubmit={submitExport}>
        <button type="submit" className="btn pas-primary-action" disabled={exporting}>
          <i className="bi bi-arrow-up" aria-hidden="true" />{" "}Exportar a SINTyS (VIAS)
        </button>
      </form>
      <form method="post" encType="multipart/form-data" className="pas-import-form" id="pas-import-sintys-form" onSubmit={submitImport}>
        <label className="btn pas-secondary-action" htmlFor="id_archivo">
          <i className="bi bi-arrow-down" aria-hidden="true" />{" "}Importar retorno
        </label>{" "}
        <input ref={input} type="file" name="archivo" accept=".xlsx,.xls,.csv" className="form-control" required id="id_archivo" onChange={changed} />{" "}
        <button type="submit" className="visually-hidden">Confirmar importación</button>
      </form>
    </div>}
  </div>;
}

function Steps({ etapas }: { etapas: Etapa[] }) {
  return <ol className="pas-circuit-steps">
    {etapas.map((etapa) => <li key={etapa.numero} className={etapa.completada ? "is-complete" : "is-pending"}>
      <span className="pas-stage-marker">{etapa.completada ? <i className="bi bi-check-lg" aria-hidden="true" /> : etapa.numero}</span>
      <strong>{etapa.nombre}</strong>
      {etapa.completada
        ? <time dateTime={etapa.fecha ?? undefined}>{etapa.fecha_texto}</time>
        : <>
          <span className="pas-stage-status">Pendiente</span>
          {etapa.integracion_pendiente && <small>Integración no disponible</small>}
        </>}
    </li>)}
  </ol>;
}

const FIXED_SOURCES: [string, string][] = [
  ["Ingresos (AFIP / Empleo)", "Pendiente de API"],
  ["Patrimonio (DNRPA / CNPB)", "Pendiente de API"],
  ["Situación penal (M. Justicia)", "Pendiente de FTP"],
  ["Cuentas BNA sin movimiento", "Pendiente de API"],
  ["Migraciones — traslados ext.", "Pendiente de API"],
];

function Sources({ data, onDone }: { data: CrucesData; onDone: (outcome: Outcome) => void }) {
  const [updating, setUpdating] = useState(false);
  const busy = useRef(false);
  const { renaper } = data;
  async function update(event: FormEvent) {
    event.preventDefault();
    if (busy.current || !window.confirm(RENAPER_CONFIRM)) return;
    busy.current = true;
    setUpdating(true);
    const outcome = await updateRenaper();
    busy.current = false;
    onDone(outcome);
  }
  return <section className="pas-cross-source-grid" aria-label="Estado de fuentes externas">
    <div className="pas-source-renaper">
      <span>Supervivencia (RENAPER)</span>
      <div className="pas-renaper-actions">
        {renaper.fecha
          ? <strong className={renaper.errores ? "has-errors" : "is-synced"}>Actualizado {renaper.fecha} · {controles(renaper.total)}</strong>
          : <strong>Sin ejecución registrada</strong>}
        {data.can_change && <form method="post" id="pas-renaper-update-form" onSubmit={(e) => void update(e)}>
          <button type="submit" className="pas-renaper-update-button" disabled={updating}>
            {updating
              ? <><span className="spinner-border spinner-border-sm" aria-hidden="true" />{" "}Actualizando</>
              : <><i className="bi bi-arrow-clockwise" aria-hidden="true" />{" "}Actualizar</>}
          </button>
        </form>}
      </div>
    </div>
    {FIXED_SOURCES.map(([label, status]) => <div key={label}><span>{label}</span><strong>{status}</strong></div>)}
  </section>;
}

function Alerts({ rows }: { rows: Incompatibilidad[] }) {
  return <section className="pas-panel pas-alerts-panel">
    <div className="pas-section-heading">
      <div>
        <span className="pas-eyebrow">Incompatibilidades detectadas</span>
        <h2>Bandeja de alertas</h2>
      </div>
      <span className="pas-source-chip is-pending">{rows.length} pendiente{rows.length === 1 ? "" : "s"}</span>
    </div>
    {rows.length
      ? <div className="pas-table-wrap">
        <table className="pas-table pas-incompatibility-table">
          <thead><tr><th>Titular</th><th>DNI</th><th>Categoría</th><th>Detalle</th><th>Detección</th><th>Impacta en</th><th>Estado</th></tr></thead>
          <tbody>{rows.map((row, i) => <tr key={i}>
            <td><strong>{row.titular}</strong></td>
            <td className="pas-monospace">{row.dni}</td>
            <td><span className="pas-training-status is-suspendida">{row.categoria}</span></td>
            <td>{row.detalle}</td>
            <td>{row.fecha_deteccion}</td>
            <td>{row.periodo_impacto}</td>
            <td><span className="pas-stage-status">{row.estado}</span></td>
          </tr>)}</tbody>
        </table>
      </div>
      : <EmptyState large icon="bi-shield-check" title="Sin incompatibilidades de supervivencia"
        detail="Los resultados RENAPER fallecidos impactarán aquí para el período siguiente." />}
  </section>;
}

function CrucesPage({ notices, onNotices, onReload }: { notices: Notice[]; onNotices: (n: Notice[]) => void; onReload: () => void }) {
  const [state, setState] = useMainResource<CrucesData>(ENDPOINT, crucesValid);
  const done = (outcome: Outcome) => {
    if (outcome.kind === "forbidden") {
      setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(outcome.data) });
      return;
    }
    onNotices(outcome.notice ? [outcome.notice] : []);
    onReload();
  };
  return renderMain(state, "Cargando área…", (data) => ({
    title: "Cruces y Novedades · PAS",
    breadcrumb: null,
    appHeader: <div className="pas-top-actions"><BuscadorButton /></div>,
    content: <>
      {PAS_STYLESHEET}
      <main className="pas-workspace">
        <ModuleHeader title="Cruces y Novedades" aside={<SourceChip pending={false} icon="bi-arrow-repeat">RENAPER · control diario</SourceChip>} />
        <WorkflowNav cards={data.areas} />
        <section className="pas-circuit-card">
          <CrucesHeading data={data} onDone={done} />
          <Steps etapas={data.etapas} />
        </section>
        <Sources data={data} onDone={done} />
        <Alerts rows={data.incompatibilidades} />
      </main>
      {createPortal(<InsumosToastList messages={notices} />, document.body)}
    </>,
  }));
}

/** Rereading the GET is the reload of the native page; the toast outlives the remount. */
function CrucesRoute() {
  const [generation, setGeneration] = useState(0);
  const [notices, setNotices] = useState<Notice[]>([]);
  return <CrucesPage key={generation} notices={notices} onNotices={setNotices} onReload={() => setGeneration((n) => n + 1)} />;
}

export const pasCrucesRoute: RouteDefinition<{ page: "cruces" }> = {
  name: "pas-cruces",
  match: (pathname) => (pathname === "/pas/cruces" ? { page: "cruces" } : null),
  render: () => <CrucesRoute />,
};
