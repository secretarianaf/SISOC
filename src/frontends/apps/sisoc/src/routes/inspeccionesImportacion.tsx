import { useRef, useState, type FormEvent } from "react";
import type { ClaroLayout } from "./ClaroFrame";
import { Encabezado as AsignacionesHeader } from "./inspeccionesAsignacionesPage";
import { internal, layoutValid, tabsValid, totalesValid, type Totales } from "./inspeccionesEscuelasApi";
import { Encabezado as EscuelasHeader, Screen } from "./inspeccionesEscuelasPage";
import { AsignacionesImportHelp, EscuelasImportHelp, ImportSteps } from "./inspeccionesImportacionUI";
import { useScreen } from "./inspeccionesScreen";
import type { RouteDefinition } from "./types";

type Kind = "escuelas" | "asignaciones";
type Step = 1 | 2 | 3;
type Entry = { tipo: Kind; paso: Step };
type Base = Entry & {
  titulo: string;
  layout: ClaroLayout;
  tabs: { id: string; label: string; url: string }[];
  totales: Totales | null;
};
type ReviewUrls = { volver: string; subir: string; confirmar: string; cancelar: string; observaciones: string };
type Upload = Base & { paso: 1; errores: string[]; csrf: string; urls: Pick<ReviewUrls, "volver" | "subir"> };
type Summary = {
  total: number; fila_encabezado: number; a_importar: number; rechazadas: number;
  nuevas?: number; restauradas?: number; repetidas?: number; otra_visita?: number;
  nuevas_sin_observaciones?: number; actualizadas_sin_observaciones?: number; a_revisar?: number; sin_cambios?: number;
  columnas: { original: string; campo: string; renombrada: boolean }[];
  motivos?: { etiqueta: string; cantidad: number }[];
  equivalencias?: { desde: string; hacia: string }[];
};
type Observation = { fila: number; cueanexo: string; nombre: string; tipo: string; motivo: string; detalle: string };
type Outcome = Base & { nombre_archivo: string; resumen: Summary; observaciones: Observation[]; total_observaciones: number };
type Review = Outcome & { paso: 2; csrf: string; urls: ReviewUrls };
type Result = Outcome & { paso: 3; urls: Pick<ReviewUrls, "volver"> };
type ImportData = Upload | Review | Result;

const root = /^\/inspecciones\/(escuelas|asignaciones)\/importar\/(?:(?:[0-9a-f]{32})\/(confirmar\/)?)?$/;
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";
const text = (value: unknown): value is string => typeof value === "string";

function validSummary(value: unknown, kind: Kind): value is Summary {
  if (!record(value)) return false;
  const counts = kind === "escuelas"
    ? ["nuevas_sin_observaciones", "actualizadas_sin_observaciones", "a_revisar", "sin_cambios"]
    : ["nuevas", "restauradas", "repetidas", "otra_visita"];
  return ["total", "fila_encabezado", "a_importar", "rechazadas", ...counts].every((key) => Number.isSafeInteger(value[key])) &&
    Array.isArray(value.columnas) && value.columnas.every((c) => record(c) && text(c.original) && text(c.campo) && typeof c.renombrada === "boolean") &&
    (kind !== "escuelas" || (
      Array.isArray(value.motivos) && value.motivos.every((m) => record(m) && text(m.etiqueta) && Number.isSafeInteger(m.cantidad)) &&
      Array.isArray(value.equivalencias) && value.equivalencias.every((e) => record(e) && text(e.desde) && text(e.hacia))
    ));
}

function importValid(value: unknown): value is ImportData {
  if (!record(value) || (value.tipo !== "escuelas" && value.tipo !== "asignaciones") || !record(value.urls) || !internal(value.urls.volver) || !text(value.titulo) ||
      !layoutValid(value.layout) || !tabsValid(value.tabs) ||
      (value.tipo === "escuelas" ? !totalesValid(value.totales) : value.totales !== null)) return false;
  const urls = value.urls;
  if (value.paso === 1) return internal(urls.subir) && text(value.csrf) && Array.isArray(value.errores) && value.errores.every(text);
  if (value.paso !== 2 && value.paso !== 3) return false;
  if (value.paso === 2 && (!["subir", "confirmar", "cancelar", "observaciones"].every((key) => internal(urls[key])) || !text(value.csrf))) return false;
  return validSummary(value.resumen, value.tipo) && text(value.nombre_archivo) && Number.isSafeInteger(value.total_observaciones) &&
    Array.isArray(value.observaciones) && value.observaciones.every((row) => record(row) && Number.isSafeInteger(row.fila) &&
      ["cueanexo", "nombre", "tipo", "motivo", "detalle"].every((key) => text(row[key])));
}

function bootstrap({ tipo, paso }: Entry): ImportData | null {
  try {
    const data: unknown = JSON.parse(document.getElementById("inspecciones-importacion-data")?.textContent ?? "");
    return importValid(data) && data.tipo === tipo && data.paso === paso ? data : null;
  } catch {
    return null;
  }
}

function SummaryPanel({ data }: { data: Review | Result }) {
  const { resumen: info, observaciones: rows, total_observaciones: total, tipo, paso } = data;
  const metrics = [
    ...tipo === "escuelas" ? [
      ["Nuevas", info.nuevas_sin_observaciones, "insp-kpi-teal"],
      ["Actualizadas", info.actualizadas_sin_observaciones],
      [paso === 3 ? "Importadas a revisar" : "Se importan a revisar", info.a_revisar, "insp-kpi-ambar"],
      ...info.sin_cambios ? [["Sin cambios", info.sin_cambios]] : [],
    ] : [
      ["Nuevas", info.nuevas, "insp-kpi-teal"],
      ...info.restauradas ? [["Se vuelven a asignar", info.restauradas]] : [],
      ["Ya estaban asignadas", info.repetidas],
      ["Otra visita el mismo día", info.otra_visita, "insp-kpi-ambar"],
    ],
    ["Rechazadas", info.rechazadas, info.rechazadas ? "insp-kpi-rojo" : ""],
  ];
  return <>
    <div className="insp-columnas">
      <span>Columnas reconocidas:</span>
      {info.columnas.map(({ original, campo, renombrada }, index) =>
        <span key={`${campo}-${index}`} className="insp-columna">{renombrada ? `${original} → ${campo}` : original}</span>)}
    </div>
    <div className="insp-totales">
      {metrics.map(([label, value, className]) => <div key={label} className={`insp-kpi${className ? ` ${className}` : ""}`}>
        <div className="insp-kpi-titulo">{label}</div><div className="insp-kpi-valor">{value}</div>
      </div>)}
    </div>
    {(!!info.motivos?.length || !!info.equivalencias?.length) && <div className="insp-totales insp-totales-2">
      {!!info.motivos?.length && <div className="insp-aviso insp-aviso-ambar">
        <strong>A revisar: se importan igual y quedan marcadas</strong>
        <ul>{info.motivos.map((m) => <li key={m.etiqueta}>{m.cantidad} · {m.etiqueta.toLowerCase()}</li>)}</ul>
      </div>}
      {!!info.equivalencias?.length && <div className="insp-aviso insp-aviso-celeste">
        <strong>Equivalencias de provincia aplicadas</strong>
        <ul>{info.equivalencias.map((e) => <li key={e.desde}>{e.desde} → {e.hacia}</li>)}</ul>
      </div>}
    </div>}
    {!!rows.length && <div className="insp-seccion">
      <div className="insp-seccion-cabecera">
        <h3>Primeras filas a revisar</h3>
        {total > rows.length && <span className="insp-seccion-nota">{rows.length} de {total}</span>}
      </div>
      <div className="table-responsive"><table className="table insp-tabla">
        <thead><tr>{["Fila", "Cueanexo", tipo === "escuelas" ? "Escuela" : "Inspector", "Observación"].map((label) => <th key={label} scope="col">{label}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) => <tr key={`${row.fila}-${index}`}>
          <td>{row.fila}</td><td className="insp-mono">{row.cueanexo || "—"}</td><td>{row.nombre || "—"}</td>
          <td><span className={`insp-badge ${row.tipo === "rechazada" ? "insp-badge-error" : "insp-badge-alerta"}`}>{row.motivo}</span>{" "}{row.detalle}</td>
        </tr>)}</tbody>
      </table></div>
    </div>}
  </>;
}

const Csrf = ({ token }: { token: string }) => <input type="hidden" name="csrfmiddlewaretoken" value={token} />;

function ImportDialog({ data }: { data: ImportData }) {
  const { paso, tipo, titulo, urls } = data;
  const pendingRef = useRef(false);
  const [processing, setProcessing] = useState(false);
  const submitOnce = (event: FormEvent<HTMLFormElement>) => {
    if (pendingRef.current) { event.preventDefault(); return; }
    pendingRef.current = true;
    setProcessing(true);
  };
  const uploadPending = "Leyendo el archivo… puede tardar unos segundos.";
  const confirmPending = "Guardando… puede tardar unos segundos.";
  return <section className="insp-dialogo" aria-labelledby="insp-importar-titulo">
    <div className="insp-dialogo-cabecera">
      <h2 id="insp-importar-titulo">{titulo}</h2>
      {paso === 2 ? <form method="post" action={data.urls.cancelar} onSubmit={submitOnce}>
        <Csrf token={data.csrf} />
        <button type="submit" className="insp-dialogo-cerrar" aria-label="Cerrar y descartar el archivo" disabled={processing}>×</button>
      </form> : <a className="insp-dialogo-cerrar" href={urls.volver} aria-label="Cerrar">×</a>}
    </div>
    {paso === 1 ? <form method="post" encType="multipart/form-data" action={data.urls.subir} onSubmit={submitOnce}>
      <Csrf token={data.csrf} />
      <div className="insp-dialogo-cuerpo">
        <ImportSteps step={paso} />
        {tipo === "escuelas" ? <EscuelasImportHelp /> : <AsignacionesImportHelp />}
        <div>
          <label className="form-label" htmlFor="id_archivo">Archivo Excel (.xlsx) o CSV</label>
          <input id="id_archivo" className={`form-control${data.errores.length ? " is-invalid" : ""}`} type="file" name="archivo" accept=".xlsx,.csv" required
            aria-invalid={data.errores.length ? true : undefined} aria-describedby={data.errores.length ? "insp-archivo-errores" : undefined} />
          {!!data.errores.length && <div id="insp-archivo-errores">
            {data.errores.map((error, index) => <div key={index} className="invalid-feedback d-block">{error}</div>)}
          </div>}
        </div>
      </div>
      <div className="insp-dialogo-pie"><div className="insp-acciones">
        <a className="btn btn-link" href={urls.volver}>Cancelar</a>
        <button type="submit" className="btn btn-primary" disabled={processing}>Revisar el archivo</button>
      </div></div>
      {processing && <p className="small text-muted px-3" role="status">{uploadPending}</p>}
    </form> : <>
      <div className="insp-dialogo-cuerpo">
        <ImportSteps step={paso} />
        {paso === 2 ? <div className="insp-archivo">
          <i className="fas fa-file-alt" aria-hidden="true" />
          <div className="insp-espacio"><strong>{data.nombre_archivo}</strong> · {data.resumen.total} filas · encabezado en la fila {data.resumen.fila_encabezado}</div>
          <a href={data.urls.subir}>Cambiar archivo</a>
        </div> : <div className="insp-aviso insp-aviso-ok" role="status">
          <strong>Importación terminada.</strong>{" "}Se guardaron {data.resumen.a_importar} de {data.resumen.total} filas de {data.nombre_archivo}.
        </div>}
        <SummaryPanel data={data} />
      </div>
      <div className="insp-dialogo-pie">
        {paso === 2 ? <>
          <div>{data.total_observaciones > 0 && <a href={data.urls.observaciones}>
            <i className="fas fa-download" aria-hidden="true" />{" "}Descargar las {data.total_observaciones} observaciones (CSV)
          </a>}</div>
          <div className="insp-acciones">
            <form method="post" action={data.urls.cancelar} onSubmit={submitOnce}>
              <Csrf token={data.csrf} />
              <button type="submit" className="btn btn-link" disabled={processing}>Cancelar</button>
            </form>
            <form method="post" action={data.urls.confirmar} onSubmit={submitOnce}>
              <Csrf token={data.csrf} />
              <button type="submit" className="btn btn-primary" disabled={processing || !data.resumen.a_importar}>Importar {data.resumen.a_importar} {tipo}</button>
            </form>
          </div>
        </> : <div className="insp-acciones"><a className="btn btn-primary" href={urls.volver}>Volver al listado</a></div>}
      </div>
      {processing && <p className="small text-muted px-3" role="status">{confirmPending}</p>}
    </>}
  </section>;
}

function ImportPage(entry: Entry) {
  const [data] = useState(() => bootstrap(entry));
  const { state } = useScreen(null, importValid, data);
  return <Screen state={state} noun="importaciones">{(payload) => <>
    {payload.totales ? <EscuelasHeader tabs={payload.tabs} totales={payload.totales} /> : <AsignacionesHeader tabs={payload.tabs} />}
    <ImportDialog data={payload} />
  </>}</Screen>;
}

export const inspeccionesImportacionRoute: RouteDefinition<Entry> = {
  name: "inspecciones-importacion",
  match(pathname) {
    const match = root.exec(pathname);
    if (!match) return null;
    return { tipo: match[1] as Kind, paso: match[2] ? 3 : /\/[0-9a-f]{32}\/$/.test(pathname) ? 2 : 1 };
  },
  render: (entry) => <ImportPage {...entry} />,
};
