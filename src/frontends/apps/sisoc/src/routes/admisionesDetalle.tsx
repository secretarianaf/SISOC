/* eslint-disable react-refresh/only-export-components -- the detail screen exports its validator for the unit tests. */
import { Fragment, useRef, useState, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { Pagination } from "./listControls";
import { NativeModal, NativeToasts } from "./nativeParity";
import { internal, record, text } from "./MainFrame";

/**
 * AD03.01 admision detail (`admisiones_detalle.html`, `/comedores/<id>/admision/<pk>/detalle/`).
 * Data comes from `/api/web/comedores/admisiones/<comedor>/<pk>/detalle/`, which runs the
 * native view; dates and numbers arrive already localized. The «Forzar Cierre» form posts to
 * the native URL (its own rules and flash message decide); the inline edits and the additional
 * file upload are drawn as the template does and are wired in AD03.02.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Doc = { nombre: string; obligatorio: boolean; estado: string; numero_gde: string; archivo_url: string | null };
type Enlace = { label: string; tone: string; me_2: boolean; url: string };
type Page = { is_paginated: boolean; number: number; count: number; has_rows: boolean; previous: number | null; next: number | null; range: (number | "…")[]; param: string; query_without_page: string };
export type DetalleData = {
  id: number; activa: boolean; comedor: { id: number; nombre: string }; urls: { comedores: string; comedor: string; pagina: string };
  puede_forzar_cierre: boolean;
  admision: {
    creado: string; tipo: string; tipo_convenio: string; convenio_numero: number | null; vigente_pwa: boolean; estado_actual: string; fecha_estado: string;
    estado_legales: string; enviado_legales: boolean; enviado_acompaniamiento: boolean; num_expediente: string | null; fecha_cierre: string | null; motivo_cierre: string;
  };
  puede_editar_convenio_numero: boolean; puede_editar_num_expediente: boolean; num_expediente_bloqueo: string;
  dupla: { nombre: string; estado: string; abogado: string; tecnicos: string[] } | null;
  documentos: Doc[]; documentos_personalizados: Doc[];
  informe_tecnico: Record<string, string> | null; informe_enlaces: Enlace[] | null; informe_gde: { numero: string; archivo: string | null } | null;
  complementarios: { fecha: string; estado: string; observaciones: string; pdf: string | null; pdf_final: string | null; word_final: string | null }[];
  historial_estados: { headers: string[]; rows: string[][]; page: Page };
  acompanamiento: {
    expediente: string; disposicion: string; if_relevamiento: string; vencimiento: string; codigo_proyecto: string; if_asociados: string; dias: string[];
    prestaciones_por_dia: { tipo: string; valores: string[] }[]; totales: { tipo: string; cantidad: string }[];
  };
  expedientes_pagos: { expediente: string; convenio: string; if_prestaciones: string; monto: string; orden_pago: string; fecha_banco: string; fecha_acreditacion: string; url: string }[];
  rendiciones_mensuales: { mes: string; anio: string; documento_adjunto: boolean; observaciones: string; url: string }[];
  rendicion_final: { fisicamente_presentada: boolean; documentos: { tipo: string; estado: string; observaciones: string; actualizacion: string; archivo: string | null }[]; historial: { fecha: string; usuario: string; accion: string }[] } | null;
  messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const fileUrl = (v: unknown): v is string => internal(v) || (text(v) && /^https?:\/\//.test(v));
const nullableFile = (v: unknown) => v === null || fileUrl(v);
const strings = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));
const list = (v: unknown, ok: (x: unknown) => boolean) => Array.isArray(v) && v.every(ok);
const docOk = (d: unknown) => strings(d, ["nombre", "estado", "numero_gde"]) && typeof (d as Doc).obligatorio === "boolean" && nullableFile((d as Doc).archivo_url);

export function detalleValid(v: unknown): v is DetalleData {
  if (!record(v) || !record(v.comedor) || !record(v.urls) || !record(v.admision) || !record(v.historial_estados) || !record(v.acompanamiento)) return false;
  const a = v.admision, h = v.historial_estados, p = h.page, ac = v.acompanamiento;
  if (!record(p)) return false;
  return int(v.id) && typeof v.activa === "boolean" && int(v.comedor.id) && text(v.comedor.nombre) &&
    ["comedores", "comedor", "pagina"].every((k) => internal((v.urls as Record<string, unknown>)[k])) &&
    typeof v.puede_forzar_cierre === "boolean" && typeof v.puede_editar_convenio_numero === "boolean" && typeof v.puede_editar_num_expediente === "boolean" && text(v.num_expediente_bloqueo) &&
    strings(a, ["creado", "tipo", "tipo_convenio", "estado_actual", "fecha_estado", "estado_legales", "motivo_cierre"]) &&
    (a.convenio_numero === null || int(a.convenio_numero)) && ["vigente_pwa", "enviado_legales", "enviado_acompaniamiento"].every((k) => typeof a[k] === "boolean") &&
    (a.num_expediente === null || text(a.num_expediente)) && (a.fecha_cierre === null || text(a.fecha_cierre)) &&
    (v.dupla === null || (strings(v.dupla, ["nombre", "estado", "abogado"]) && list((v.dupla as Record<string, unknown>).tecnicos, text))) &&
    list(v.documentos, docOk) && list(v.documentos_personalizados, docOk) &&
    (v.informe_tecnico === null || (record(v.informe_tecnico) && Object.values(v.informe_tecnico).every(text))) &&
    (v.informe_enlaces === null || list(v.informe_enlaces, (e) => strings(e, ["label", "tone"]) && fileUrl((e as Enlace).url) && typeof (e as Enlace).me_2 === "boolean")) &&
    (v.informe_gde === null || (record(v.informe_gde) && text(v.informe_gde.numero) && nullableFile(v.informe_gde.archivo))) &&
    list(v.complementarios, (c) => strings(c, ["fecha", "estado", "observaciones"]) && ["pdf", "pdf_final", "word_final"].every((k) => nullableFile((c as Record<string, unknown>)[k]))) &&
    list(h.headers, text) && list(h.rows, (r) => list(r, text)) &&
    typeof p.is_paginated === "boolean" && typeof p.has_rows === "boolean" && int(p.number) && int(p.count) && (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    list(p.range, (n) => n === "…" || int(n)) && text(p.param) && text(p.query_without_page) &&
    strings(ac, ["expediente", "disposicion", "if_relevamiento", "vencimiento", "codigo_proyecto", "if_asociados"]) && list(ac.dias, text) &&
    list(ac.prestaciones_por_dia, (r) => strings(r, ["tipo"]) && list((r as Record<string, unknown>).valores, text)) && list(ac.totales, (t) => strings(t, ["tipo", "cantidad"])) &&
    list(v.expedientes_pagos, (e) => strings(e, ["expediente", "convenio", "if_prestaciones", "monto", "orden_pago", "fecha_banco", "fecha_acreditacion"]) && internal((e as Record<string, unknown>).url)) &&
    list(v.rendiciones_mensuales, (r) => strings(r, ["mes", "anio", "observaciones"]) && typeof (r as Record<string, unknown>).documento_adjunto === "boolean" && internal((r as Record<string, unknown>).url)) &&
    (v.rendicion_final === null || (record(v.rendicion_final) && typeof v.rendicion_final.fisicamente_presentada === "boolean" &&
      list(v.rendicion_final.documentos, (d) => strings(d, ["tipo", "estado", "observaciones", "actualizacion"]) && nullableFile((d as Record<string, unknown>).archivo)) &&
      list(v.rendicion_final.historial, (i) => strings(i, ["fecha", "usuario", "accion"])))) &&
    list(v.messages, (m) => strings(m, ["message"]) && LEVELS.includes((m as Message).level));
}

/** Native `fetch` of `admisionesactualizarestado.js`: form-encoded POST with the CSRF header. */
export const admisionesNative = {
  post: async (url: string, body: Record<string, string>): Promise<{ success?: boolean; error?: string; [k: string]: unknown }> => {
    const response = await fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "X-CSRFToken": leerCookie("csrftoken") ?? "", "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(body),
    });
    return response.json();
  },
  upload: (url: string, form: FormData): Promise<number> => new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.addEventListener("load", () => resolve(xhr.status));
    xhr.addEventListener("error", () => resolve(0));
    xhr.open("POST", url);
    xhr.send(form);
  }),
  reload: () => window.location.reload(),
  alert: (message: string) => window.alert(message),
};

const yesno = (v: boolean) => (v ? "Si" : "No");

function Dl({ cols, rows }: { cols: [string, string]; rows: [string, ReactNode][] }) {
  return <dl className="row mb-0">{rows.map(([label, value]) => <Fragment key={label}><dt className={`col-sm-${cols[0]}`}>{label}</dt><dd className={`col-sm-${cols[1]}`}>{value}</dd></Fragment>)}</dl>;
}

function Download({ url }: { url: string | null }) {
  return url ? <a href={url} className="btn btn-outline-primary btn-sm" target="_blank" rel="noopener">Descargar</a> : <>-</>;
}

function Card({ tone, title, children, bodyClass = "" }: { tone: string; title: string; children: ReactNode; bodyClass?: string }) {
  return <div className={`card card-outline ${tone} mb-4`}>
    <div className="card-header"><h3 className="card-title">{title}</h3></div>
    <div className={`card-body${bodyClass}`}>{children}</div>
  </div>;
}

function ForzarCierre({ data, close }: { data: DetalleData; close: () => void }) {
  return (
    <NativeModal id="forzarCierreModal" title="Forzar Cierre de Admisión" close={close} controls="button:not([disabled]),textarea:not([disabled])">
      <div className="modal-content">
        <form method="post" action={data.urls.pagina}>
          <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
          <div className="modal-header">
            <h5 className="modal-title" id="forzarCierreModalLabel">Forzar Cierre de Admisión</h5>
            <button type="button" className="btn-close" aria-label="Close" onClick={close} />
          </div>
          <div className="modal-body">
            <div className="alert alert-warning">
              <i className="fas fa-exclamation-triangle me-2" />{" "}
              <strong>Atención:</strong> Esta acción marcará la admisión como inactiva y no se podrá revertir.
            </div>
            <div className="mb-3">
              <label htmlFor="motivo_forzar_cierre" className="form-label">Motivo del cierre forzado <span className="text-danger">*</span></label>
              <textarea className="form-control" id="motivo_forzar_cierre" name="motivo_forzar_cierre" rows={4} required
                placeholder="Ingrese el motivo por el cual se fuerza el cierre de esta admisión..." />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" name="forzar_cierre" className="btn btn-danger">Confirmar Cierre</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

type Toast = { tone: "success" | "danger"; text: string } | null;

function AdmisionCard({ data, toast }: { data: DetalleData; toast: (t: Toast) => void }) {
  const a = data.admision, d = data.dupla;
  const [convenio, setConvenio] = useState(a.convenio_numero);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(a.convenio_numero === null ? "" : String(a.convenio_numero));
  const [pwa, setPwa] = useState(a.vigente_pwa);
  const guardarConvenio = async () => {
    try {
      const r = await admisionesNative.post("/ajax/actualizar-convenio-numero/", { admision_id: String(data.id), convenio_numero: draft.trim() });
      if (!r.success) { toast({ tone: "danger", text: (r.error as string) || "No se pudo actualizar el numero de convenio." }); return; }
      const n = (r.convenio_numero as number | null | undefined) ?? null;
      setConvenio(n); setDraft(n === null ? "" : String(n)); setEditing(false);
      toast({ tone: "success", text: "Numero de convenio actualizado con exito." });
    } catch {
      toast({ tone: "danger", text: "Ocurrio un error al actualizar el numero de convenio." });
    }
  };
  const cancelarConvenio = () => { setDraft(convenio === null ? "" : String(convenio)); setEditing(false); };
  const cambiarPwa = async (checked: boolean) => {
    setPwa(checked);
    try {
      const r = await admisionesNative.post("/ajax/actualizar-vigente-pwa/", { admision_id: String(data.id), vigente_pwa: checked ? "1" : "0" });
      if (!r.success) { setPwa(!checked); admisionesNative.alert("Error: " + ((r.error as string) || "No se pudo actualizar la vigencia PWA.")); }
    } catch {
      setPwa(!checked); admisionesNative.alert("Ocurrio un error al actualizar la vigencia PWA.");
    }
  };
  return (
    <div className="card card-primary card-outline mb-4">
      <div className="card-header"><h3 className="card-title">Admision</h3></div>
      <div className="card-body">
        <div className="row">
          <div className="col-lg-6">
            <Dl cols={["5", "7"]} rows={[
              ["Fecha de creacion", a.creado],
              ["Tipo", a.tipo],
              ["Tipo de convenio", a.tipo_convenio],
              ["Numero de convenio", data.puede_editar_convenio_numero ? (
                <div className="d-inline-flex align-items-center gap-2">
                  <div id="convenio-numero-display" className={`convenio-numero-display${editing ? " d-none" : ""}`} onClick={() => setEditing(true)}>
                    {convenio !== null ? <><span className="text-success fw-bold">{convenio}</span>{" "}<i className="bi bi-pencil-square ms-2 text-muted" title="Editar numero de convenio" /></>
                      : <><span className="text-muted">Sin numero de convenio</span>{" "}<i className="bi bi-plus-circle ms-2 text-primary" title="Agregar numero de convenio" /></>}
                  </div>
                  {editing && <div id="convenio-numero-edit" className="convenio-numero-edit">
                    <input type="number" id="convenio-numero-input" className="form-control form-control-sm" value={draft} min="0" step="1" autoFocus
                      onChange={(e) => setDraft(e.target.value)} />
                    <button type="button" className="btn btn-success btn-sm convenio-numero-btn" title="Guardar" onClick={() => void guardarConvenio()}><i className="bi bi-check-lg" /></button>
                    <button type="button" className="btn btn-danger btn-sm convenio-numero-btn" title="Cancelar" onClick={cancelarConvenio}><i className="bi bi-x-lg" /></button>
                  </div>}
                </div>
              ) : <span className="fw-bold">{convenio ?? "-"}</span>],
              ["Vigente PWA", data.puede_editar_convenio_numero ? (
                <div className="form-check form-switch mb-0">
                  <input className="form-check-input" type="checkbox" role="switch" id="vigente-pwa-input" checked={pwa} onChange={(e) => void cambiarPwa(e.target.checked)} />{" "}
                  <label className="form-check-label" htmlFor="vigente-pwa-input">Admisión vigente para PWA</label>
                </div>
              ) : pwa ? <span className="badge bg-success">Vigente</span> : <span className="badge bg-secondary">No vigente</span>],
              ["Estado Actual", a.estado_actual],
              ["Fecha Estado", a.fecha_estado],
              ["Estado legales", a.estado_legales],
            ]} />
          </div>
          <div className="col-lg-6">
            <Dl cols={["5", "7"]} rows={[
              ["Enviado a legales", yesno(a.enviado_legales)],
              ["Enviado a acompañamiento", yesno(a.enviado_acompaniamiento)],
              ["Número de expediente", (
                <div className="d-inline-flex align-items-center gap-2 flex-wrap">
                  <span id="num-expediente-display" className="fw-bold">{a.num_expediente || "-"}</span>
                  {a.num_expediente ? <i className="bi bi-check-circle-fill text-success" /> : <i className="bi bi-x-circle-fill text-danger" />}
                  {a.num_expediente && <i className="fas fa-info-circle" data-bs-toggle="tooltip" data-bs-placement="top"
                    title="Tené en cuenta que, si modificás el número de expediente, este cambio no se reflejará en el informe técnico en caso de que ya esté finalizado." />}
                </div>
              )],
              ...(a.fecha_cierre !== null ? [["Fecha de cierre", a.fecha_cierre] as [string, ReactNode], ["Motivo de cierre", a.motivo_cierre] as [string, ReactNode]] : []),
            ]} />
          </div>
        </div>
        <hr className="my-4" />
        <h5 className="mb-3">Dupla asignada</h5>
        {d ? (
          <div className="row">
            <div className="col-md-6">
              <p className="mb-1"><strong>Nombre:</strong> {d.nombre}</p>
              <p className="mb-1"><strong>Estado:</strong> {d.estado}</p>
            </div>
            <div className="col-md-6">
              <p className="mb-1"><strong>Abogado/a:</strong> {d.abogado}</p>
              <p className="mb-0"><strong>Integrantes tecnicos:</strong> {d.tecnicos.length ? d.tecnicos.join(", ") : "-"}</p>
            </div>
          </div>
        ) : <p className="text-muted">No hay dupla asignada actualmente.</p>}
      </div>
    </div>
  );
}

function Documentos({ data }: { data: DetalleData }) {
  const [nombre, setNombre] = useState("");
  const [progress, setProgress] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const subir = async (file: File | undefined) => {
    if (!file) return;
    if (!nombre.trim()) { admisionesNative.alert("Por favor ingrese un nombre para el archivo"); return; }
    setProgress(true);
    const form = new FormData();
    form.append("archivo", file); form.append("nombre", nombre.trim()); form.append("csrfmiddlewaretoken", leerCookie("csrftoken") ?? "");
    const status = await admisionesNative.upload(data.urls.pagina, form);
    if (status === 200) admisionesNative.reload();
    else { admisionesNative.alert("Error al subir el archivo"); setProgress(false); }
  };
  const todos = data.documentos.length > 0 || data.documentos_personalizados.length > 0;
  const fila = (doc: Doc, obligatorio: boolean, key: string) => <tr key={key}>
    <td>{doc.nombre}</td><td>{yesno(obligatorio)}</td><td>{doc.estado}</td><td>{doc.numero_gde}</td>
    <td className="text-center">{doc.archivo_url ? <a href={doc.archivo_url} className="btn btn-outline-primary btn-sm" target="_blank" rel="noopener">Descargar</a> : <>-</>}</td>
  </tr>;
  return <>
    <div className="card card-outline card-secondary mb-4">
      <div className="card-header"><h3 className="card-title">Documentacion de admision</h3></div>
      <div className="card-body table-responsive">
        {todos ? (
          <table className="table table-striped table-bordered align-middle">
            <thead><tr><th>Documento</th><th>Obligatorio</th><th>Estado</th><th>Numero IF / GDE</th><th>Archivo</th></tr></thead>
            <tbody>
              {data.documentos.map((doc, i) => fila(doc, doc.obligatorio, `d${i}`))}
              {data.documentos_personalizados.map((doc, i) => fila(doc, false, `p${i}`))}
            </tbody>
          </table>
        ) : <p className="text-muted mb-0">No hay documentos cargados para esta admision.</p>}
      </div>
    </div>
    <div className="card card-outline card-secondary mb-4">
      <div className="card-header"><h3 className="card-title">Archivos adicionales</h3></div>
      <div className="card-body">
        <div className="table-responsive">
          <table className="table table-striped table-bordered table-hover table-sm" id="tablaArchivosAdicionales">
            <thead><tr><th>Documento</th><th>Archivo</th><th>Número de GDE</th></tr></thead>
            <tbody id="tablaArchivosAdicionalesBody">
              {data.documentos_personalizados.map((doc, i) => <tr key={i}>
                <td>{doc.nombre}</td>
                <td className="text-center">{doc.archivo_url ? <a href={doc.archivo_url} className="btn btn-outline-primary btn-sm" target="_blank" rel="noopener">Descargar</a> : <>-</>}</td>
                <td>{doc.numero_gde}</td>
              </tr>)}
              {data.activa && <tr id="fila-agregar-archivo-adicional">
                <td className="ps-1"><input type="text" className="form-control form-control-sm" id="nuevoArchivoNombre" placeholder="Nombre del archivo adicional" value={nombre} onChange={(e) => setNombre(e.target.value)} /></td>
                <td>
                  <input type="file" id="nuevoArchivoFile" className="d-none" ref={fileInput} onChange={(e) => void subir(e.target.files?.[0])} />
                  <button type="button" className="btn btn-sm btn-outline-primary" id="btnAbrirArchivoFile" onClick={() => fileInput.current?.click()}>Adjuntar</button>
                  <div className="progress mt-2" id="progress-container-archivo" style={{ display: progress ? "block" : "none", height: "3px" }}>
                    <div className="progress-bar progress-bar-striped" role="progressbar" id="progress-bar-archivo" style={{ width: "100%" }}>100%</div>
                  </div>
                </td>
                <td><span className="text-muted">-</span></td>
              </tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </>;
}

function Informes({ data }: { data: DetalleData }) {
  const i = data.informe_tecnico, gde = data.informe_gde;
  return (
    <div className="card card-outline card-secondary mb-4">
      <div className="card-header"><h3 className="card-title">Informes tecnicos</h3></div>
      <div className="card-body">
        <h5>Informe tecnico principal</h5>
        {i ? <>
          <div className="row">
            <div className="col-lg-6"><Dl cols={["5", "7"]} rows={[["Expediente", i.expediente], ["Nota GDE IF", i.nota_gde_if], ["IF relevamiento", i.if_relevamiento], ["Vencimiento mandatos", i.vencimiento_mandatos]]} /></div>
            <div className="col-lg-6"><Dl cols={["5", "7"]} rows={[["Estado formulario", i.estado_formulario], ["Tipo", i.tipo], ["Responsable tarjeta", i.responsable_nombre], ["CUIT responsable", i.responsable_cuit]]} /></div>
          </div>
          <div className="mt-3">
            {data.informe_enlaces ? data.informe_enlaces.map((e, n) => <Fragment key={e.label}>{n > 0 && " "}<a href={e.url} className={`btn btn-${e.tone} btn-sm${e.me_2 ? " me-2" : ""}`} target="_blank" rel="noopener">{e.label}</a></Fragment>)
              : <p className="text-muted mb-0">No hay archivos generados para el informe tecnico.</p>}
          </div>
        </> : <p className="text-muted">No se registran informes tecnicos cargados.</p>}
        <hr className="my-4" />
        {gde && <div className="mt-2">
          <span className="fw-bold">Informe Técnico GDE:</span>{" "}
          <span>{gde.numero}</span>
          {gde.archivo && <>{" "}<a href={gde.archivo} className="btn btn-success btn-sm me-2 ms-3" target="_blank" rel="noopener">Descargar Informe Técnico GDE</a></>}
        </div>}
        <hr className="my-4" />
        <h5>Informes tecnicos complementarios</h5>
        {data.complementarios.length ? (
          <div className="table-responsive">
            <table className="table table-striped table-bordered align-middle">
              <thead><tr><th>Fecha</th><th>Estado</th><th>Observaciones</th><th>PDF</th><th>PDF final</th><th>Word final</th></tr></thead>
              <tbody>{data.complementarios.map((c, n) => <tr key={n}>
                <td>{c.fecha}</td><td>{c.estado}</td><td>{c.observaciones}</td>
                <td className="text-center"><Download url={c.pdf} /></td>
                <td className="text-center"><Download url={c.pdf_final} /></td>
                <td className="text-center"><Download url={c.word_final} /></td>
              </tr>)}</tbody>
            </table>
          </div>
        ) : <p className="text-muted mb-0">No se registran informes complementarios.</p>}
      </div>
    </div>
  );
}

function Historial({ data }: { data: DetalleData }) {
  const h = data.historial_estados, p = h.page;
  return (
    <Card tone="card-secondary" title="Historial de estados">
      <div className="row mt-5 max-width-100"><div className="col-12"><div className="card"><div className="card-body">
        <div className="table-responsive-lg">
          <table className="table table-bordered table-striped projects ">
            <thead><tr>{h.headers.map((t) => <th key={t}>{t}</th>)}</tr></thead>
            <tbody>
              {h.rows.length ? h.rows.map((row, r) => <tr key={r}>{row.map((c, i) => <td key={i}>{c}</td>)}</tr>)
                : <tr><td colSpan={h.headers.length} className="text-center text-muted py-4">No se registran cambios de estado.</td></tr>}
            </tbody>
          </table>
        </div>
        <Pagination paginated={p.is_paginated} number={p.number} previous={p.previous} next={p.next} range={p.range}
          href={(n) => `?${p.query_without_page}${p.param}=${n}`} count={p.has_rows ? p.count : null} />
      </div></div></div></div>
    </Card>
  );
}

function Acompanamiento({ data }: { data: DetalleData }) {
  const a = data.acompanamiento;
  return (
    <Card tone="card-success" title="Acompañamiento">
      <h5>Informacion relevante</h5>
      <div className="row">
        <div className="col-lg-6"><Dl cols={["6", "6"]} rows={[["Número de expediente", a.expediente], ["Numero de disposicion", a.disposicion], ["IF de relevamiento", a.if_relevamiento]]} /></div>
        <div className="col-lg-6"><Dl cols={["6", "6"]} rows={[["Vencimiento de mandato", a.vencimiento], ["Codigo de proyecto", a.codigo_proyecto], ["IF asociados", a.if_asociados]]} /></div>
      </div>
      {a.prestaciones_por_dia.length > 0 && <>
        <hr className="my-4" />
        <h5>Prestaciones registradas</h5>
        <div className="table-responsive mb-3">
          <table className="table table-sm table-bordered text-center align-middle">
            <thead className="table-dark"><tr><th>Tipo de comida</th>{a.dias.map((d) => <th key={d}>{d}</th>)}</tr></thead>
            <tbody>{a.prestaciones_por_dia.map((f, n) => <tr key={n}><td className="text-start">{f.tipo}</td>{f.valores.map((v, i) => <td key={i}>{v}</td>)}</tr>)}</tbody>
          </table>
        </div>
        <div className="table-responsive">
          <table className="table table-sm table-bordered align-middle">
            <thead className="table-dark"><tr><th>Tipo de comida</th><th>Total semanal</th></tr></thead>
            <tbody>{a.totales.map((t, n) => <tr key={n}><td>{t.tipo}</td><td>{t.cantidad}</td></tr>)}</tbody>
          </table>
        </div>
      </>}
      <hr className="my-4" />
      <h5>Expedientes de pago</h5>
      {data.expedientes_pagos.length ? (
        <div className="table-responsive mb-3">
          <table className="table table-striped table-bordered align-middle">
            <thead><tr><th>Expediente</th><th>Expediente del convenio</th><th>IF prestaciones</th><th>Monto</th><th>Orden de pago</th><th>Fecha banco</th><th>Fecha acreditacion</th><th>Detalle</th></tr></thead>
            <tbody>{data.expedientes_pagos.map((e, n) => <tr key={n}>
              <td>{e.expediente}</td><td>{e.convenio}</td><td>{e.if_prestaciones}</td><td>{e.monto}</td><td>{e.orden_pago}</td><td>{e.fecha_banco}</td><td>{e.fecha_acreditacion}</td>
              <td className="text-center"><a href={e.url} className="btn btn-outline-primary btn-sm">Ver</a></td>
            </tr>)}</tbody>
          </table>
        </div>
      ) : <p className="text-muted">No se registran expedientes de pago.</p>}
      <h5 className="mt-4">Seguimientos mensuales</h5>
      {data.rendiciones_mensuales.length ? (
        <div className="table-responsive">
          <table className="table table-striped table-bordered align-middle">
            <thead><tr><th>Mes</th><th>Ano</th><th>Documento adjunto</th><th>Observaciones</th><th>Detalle</th></tr></thead>
            <tbody>{data.rendiciones_mensuales.map((r, n) => <tr key={n}>
              <td>{r.mes}</td><td>{r.anio}</td><td>{yesno(r.documento_adjunto)}</td><td>{r.observaciones}</td>
              <td className="text-center"><a href={r.url} className="btn btn-outline-primary btn-sm">Ver</a></td>
            </tr>)}</tbody>
          </table>
        </div>
      ) : <p className="text-muted mb-0">No se registran seguimientos mensuales.</p>}
    </Card>
  );
}

function RendicionFinal({ data }: { data: DetalleData }) {
  const r = data.rendicion_final;
  return (
    <Card tone="card-info" title="Rendicion de cuenta final">
      {r ? <>
        <p className="mb-3"><strong>Fisicamente presentada:</strong> {yesno(r.fisicamente_presentada)}</p>
        <h5>Documentos asociados</h5>
        {r.documentos.length ? (
          <div className="table-responsive mb-3">
            <table className="table table-striped table-bordered align-middle">
              <thead><tr><th>Tipo</th><th>Estado</th><th>Observaciones</th><th>Ultima actualizacion</th><th>Archivo</th></tr></thead>
              <tbody>{r.documentos.map((d, n) => <tr key={n}>
                <td>{d.tipo}</td><td>{d.estado}</td><td>{d.observaciones}</td><td>{d.actualizacion}</td>
                <td className="text-center"><Download url={d.archivo} /></td>
              </tr>)}</tbody>
            </table>
          </div>
        ) : <p className="text-muted">No hay documentos en la rendicion final.</p>}
        <h5>Historial de rendicion</h5>
        {r.historial.length ? (
          <div className="table-responsive">
            <table className="table table-striped table-bordered align-middle">
              <thead><tr><th>Fecha</th><th>Usuario</th><th>Accion</th></tr></thead>
              <tbody>{r.historial.map((i, n) => <tr key={n}><td>{i.fecha}</td><td>{i.usuario}</td><td>{i.accion}</td></tr>)}</tbody>
            </table>
          </div>
        ) : <p className="text-muted mb-0">No hay movimientos registrados en la rendicion final.</p>}
      </> : <p className="text-muted mb-0">Todavia no se genero una rendicion de cuenta final para este comedor.</p>}
    </Card>
  );
}

/** The `titulo-pagina` block: the title and the active/closed badge. */
export function DetalleHeading({ activa }: { activa: boolean }) {
  return <>Detalle de Admision{" "}{activa ? <span className="badge bg-success">Activa</span> : <span className="badge bg-danger">Cerrada</span>}</>;
}

export function DetalleBreadcrumb({ data }: { data: DetalleData }) {
  return <ol className="breadcrumb float-sm-right">
    <li className="breadcrumb-item"><a href={data.urls.comedores}>Comedores</a></li>
    <li className="breadcrumb-item"><a href={data.urls.comedor}>{data.comedor.nombre}</a></li>
    <li className="breadcrumb-item active">Admision</li>
  </ol>;
}

/** The inline `<style>` of the template's `customJS` block. */
const CONVENIO_CSS = `
        .convenio-numero-display {
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        .convenio-numero-display:hover {
            background-color: #f8f9fa;
        }
        .convenio-numero-edit {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            min-width: 220px;
        }
        .convenio-numero-edit .btn {
            width: 32px;
            height: 32px;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .convenio-numero-btn {
            width: 28px;
            height: 28px;
        }
        #convenio-numero-input {
            max-width: 140px;
        }
`;

export function DetalleContent({ data }: { data: DetalleData }) {
  const [closing, setClosing] = useState(false);
  const [toast, setToast] = useState<Toast>(null);
  return (
    <>
      <style>{CONVENIO_CSS}</style>
      {toast && <div className="position-fixed bottom-0 end-0 p-3" style={{ zIndex: 1100 }}>
        <div className={`toast show align-items-center text-bg-${toast.tone} border-0`} role="alert" aria-live="assertive" aria-atomic="true">
          <div className="d-flex">
            <div className="toast-body"><h6>{toast.text}</h6></div>
            <button type="button" className="btn-close btn-close-white me-2 m-auto" aria-label="Cerrar" onClick={() => setToast(null)} />
          </div>
        </div>
      </div>}
      <NativeToasts messages={data.messages} />
      <div className="row mb-3">
        <div className="col-12 d-flex justify-content-between flex-wrap gap-2">
          {data.puede_forzar_cierre && <button type="button" className="btn btn-danger" data-bs-toggle="modal" data-bs-target="#forzarCierreModal" onClick={() => setClosing(true)}>
            <i className="fas fa-times-circle me-2" />Forzar Cierre
          </button>}
        </div>
      </div>
      <AdmisionCard data={data} toast={setToast} />
      <Documentos data={data} />
      <Informes data={data} />
      <Historial data={data} />
      <Acompanamiento data={data} />
      <RendicionFinal data={data} />
      {closing && <ForzarCierre data={data} close={() => setClosing(false)} />}
    </>
  );
}
