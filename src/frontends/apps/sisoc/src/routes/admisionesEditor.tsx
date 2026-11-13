/* eslint-disable react-refresh/only-export-components -- the editor screen exports its validator and the native-call seam for the unit tests. */
import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeModal, NativeToasts } from "./nativeParity";
import { Crispy, type Field, type Value } from "./admisionesInformeEditor";
import { internal, record, text, webClient } from "./MainFrame";

/**
 * AD03.02 technical admision editor (`admisiones_tecnicos_form.html`,
 * `/comedores/admisiones/tecnicos/editar/<pk>`). Data comes from `/api/web/comedores/admisiones/<pk>/`,
 * which runs the native view; every button of the page posts to
 * `/api/web/comedores/admisiones/<pk>/acciones/<accion>/`, which runs the native `post()` dispatch.
 * The inline edits, the state and GDE edits, the uploads and the resync keep the native AJAX endpoints
 * the page's scripts call. While the native page draws the embedded report and cover form the preview
 * entry serves the native page, so this screen never shows that section.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Boton = { clave: string; texto: string; clase: string; modal: string | null; url: string | null };
type Option = { value: string; label: string; selected: boolean; disabled: boolean };
type EstadoUi = { kind: "badge"; badge: string } | { kind: "text" } | { kind: "select"; requires_observacion: boolean; border: string; options: Option[] };
type Gde = { kind: "plain" } | { kind: "organizacion" } | { kind: "editable"; value: string | null };
export type Doc = {
  id: string; row_id: string; documentacion_id: number | null; archivo_id: number | null; nombre: string; obligatorio: boolean; organizacion: boolean;
  vencimiento: string | null; estado: string; estado_valor: string; estado_ui: EstadoUi; archivo_url: string | null; puede_eliminar: boolean;
  puede_adjuntar: boolean; gde: Gde; numero_gde: string; personalizado: boolean; observaciones: string | null;
};
type Pdf = { archivo: string | null; docx: string | null; docx_editado: string | null };
export type EditorData = {
  id: number; vacio: boolean; banner: string | null;
  comedor: { id: number | null; nombre: string; tipocomedor: string; programa: string; organizacion: string; provincia: string; municipio: string; localidad: string; calle: string; numero: string; piso: string; departamento: string };
  urls: { listar: string; comedor: string | null; pagina: string; localidades: string; agregar_documento: string; resync: string };
  botones: Boton[];
  resync: { desincronizada: boolean; documentacion_desactualizada: boolean; solo_datos_organizacion: boolean; tipo_entidad_actual: string; tipo_entidad_snapshot: string; documentos_modificados: string[]; datos_modificados: string[] } | null;
  complementario_requerido: { observaciones: string } | null;
  informe_a_subsanar: string | null;
  seleccion_convenio: { tipo_entidad: string; tipo_convenio: string; precargado: boolean; tipo: string } | null;
  admision: {
    tipo: string; tipo_convenio: string; convenio_numero: number | null; vigente_pwa: boolean; personas_conveniadas_nomina: number | null; tipo_display: string; estado_proceso: string;
    fecha: string; vencimiento_mandatos: string; num_expediente: string | null; enviado_legales: boolean; informe_estado: string | null; numero_if_tecnico: string | null;
    informe_gde: string | null; estado_legales: string; observaciones: string;
  };
  puede_editar_convenio_numero: boolean; mostrar_personas_conveniadas_nomina: boolean; puede_editar_personas_conveniadas_nomina: boolean; puede_editar_num_expediente: boolean;
  pdf: Pdf | null; complementarios: { pdf: string | null; fecha: string; estado: string }[];
  validaciones: { editable: true; fields: Field[] } | { editable: false; valores: [string, string][] } | null;
  stats: { obligatorios_completos: number | null; obligatorios_total: number | null; aceptados: number | null; a_validar_abogado: number | null; rectificar: number | null; pendientes: number | null };
  documentos: Doc[]; documentos_personalizados: Doc[]; puede_agregar_documento: boolean;
  modales: { if_informe: Field[]; if_informe_archivo: { id: string; label: string }; caratular: Field[]; informe_id: number | null };
  informe_embebido: boolean; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const list = (v: unknown, ok: (x: unknown) => boolean) => Array.isArray(v) && v.every(ok);
const strings = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));
const nullableText = (v: unknown) => v === null || text(v);
const fileUrl = (v: unknown) => v === null || internal(v) || (text(v) && /^https?:\/\//.test(v));
const docOk = (d: unknown) => strings(d, ["id", "row_id", "nombre", "estado", "estado_valor", "numero_gde"]) && record(d) && record(d.estado_ui) && record(d.gde) &&
  typeof d.obligatorio === "boolean" && typeof d.puede_eliminar === "boolean" && typeof d.puede_adjuntar === "boolean" && fileUrl(d.archivo_url);

export function editorValid(v: unknown): v is EditorData {
  if (!record(v) || !record(v.comedor) || !record(v.urls) || !record(v.admision) || !record(v.stats) || !record(v.modales)) return false;
  const a = v.admision, u = v.urls, m = v.modales;
  return typeof v.id === "number" && typeof v.vacio === "boolean" && nullableText(v.banner) &&
    text(v.comedor.nombre) && ["listar", "pagina", "localidades", "agregar_documento", "resync"].every((k) => internal(u[k])) &&
    (u.comedor === null || internal(u.comedor)) &&
    list(v.botones, (b) => strings(b, ["clave", "texto", "clase"]) && nullableText((b as Boton).modal) && (((b as Boton).url === null) || internal((b as Boton).url))) &&
    strings(a, ["tipo_convenio", "tipo_display", "estado_proceso", "fecha", "vencimiento_mandatos", "estado_legales", "observaciones"]) &&
    (a.convenio_numero === null || typeof a.convenio_numero === "number") && (a.personas_conveniadas_nomina === null || typeof a.personas_conveniadas_nomina === "number") &&
    typeof a.vigente_pwa === "boolean" && typeof a.enviado_legales === "boolean" && nullableText(a.num_expediente) && nullableText(a.informe_estado) && nullableText(a.numero_if_tecnico) && fileUrl(a.informe_gde) &&
    ["puede_editar_convenio_numero", "mostrar_personas_conveniadas_nomina", "puede_editar_personas_conveniadas_nomina", "puede_editar_num_expediente", "puede_agregar_documento", "informe_embebido"].every((k) => typeof v[k] === "boolean") &&
    (v.pdf === null || (record(v.pdf) && ["archivo", "docx", "docx_editado"].every((k) => fileUrl((v.pdf as Record<string, unknown>)[k])))) &&
    list(v.complementarios, (c) => strings(c, ["fecha", "estado"]) && fileUrl((c as Record<string, unknown>).pdf)) &&
    (v.validaciones === null || (record(v.validaciones) && typeof v.validaciones.editable === "boolean")) &&
    list(v.documentos, docOk) && list(v.documentos_personalizados, docOk) &&
    list(m.if_informe, record) && list(m.caratular, (f) => record(f) && text(f.name) && text(f.id)) && record(m.if_informe_archivo) && text(m.if_informe_archivo.id) &&
    list(v.messages, (x) => strings(x, ["message"]) && LEVELS.includes((x as Message).level));
}

/** The calls of the page's scripts (`admisionesactualizarestado.js`, `admisionestecnico.js`, `admisionResyncConvenio.js`). */
export const editorNative = {
  post: async (url: string, body: Record<string, string>, extra: Record<string, string> = {}): Promise<{ success?: boolean; error?: string; [k: string]: unknown }> => {
    const response = await fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "X-CSRFToken": leerCookie("csrftoken") ?? "", "Content-Type": "application/x-www-form-urlencoded", ...extra },
      body: new URLSearchParams(body),
    });
    return response.json();
  },
  upload: (url: string, form: FormData, progress: (percent: number) => void): Promise<{ status: number; body: string }> => new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.upload.addEventListener("progress", (e) => { if (e.lengthComputable) progress(Math.round((e.loaded / e.total) * 100)); });
    xhr.addEventListener("load", () => resolve({ status: xhr.status, body: xhr.responseText }));
    xhr.addEventListener("error", () => resolve({ status: 0, body: "" }));
    xhr.open("POST", url, true);
    xhr.setRequestHeader("X-CSRFToken", leerCookie("csrftoken") ?? "");
    xhr.send(form);
  }),
  remove: async (url: string): Promise<{ success?: boolean; error?: string }> => {
    const response = await fetch(url, { method: "DELETE", credentials: "same-origin", headers: { "X-CSRFToken": leerCookie("csrftoken") ?? "" } });
    return response.json();
  },
  navigate: (url: string) => { window.location.href = url; },
  alert: (message: string) => window.alert(message),
};

type Toast = { tone: "success" | "danger"; text: string } | null;
type Done = (messages: Message[], rejected: boolean) => void;
type Errors = { fields: Field[]; non_field_errors: string[] } | null;

const CSS = `
        .gde-display {
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        .gde-display:hover {
            background-color: #f8f9fa;
        }
        .gde-edit {
            min-width: 250px;
        }
        .gde-edit .btn {
            width: 32px;
            height: 32px;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
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

const asValue = (f: Field): Value => f.value;

/** `{{ form.<campo>|as_crispy_field }}` over the bound fields of the API, with the values held here. */
function FormFields({ fields, values, set, wrap }: { fields: Field[]; values: Record<string, Value>; set: (name: string, v: Value) => void; wrap?: (f: Field, node: ReactNode) => ReactNode }) {
  return <>{fields.map((f) => {
    const node = <Crispy f={f} value={values[f.name] ?? asValue(f)} onChange={(v) => set(f.name, v)} />;
    return <Fragment key={f.name}>{wrap ? wrap(f, node) : node}</Fragment>;
  })}</>;
}

function useValues(fields: Field[]) {
  const [values, setValues] = useState<Record<string, Value>>(() => Object.fromEntries(fields.map((f) => [f.name, f.value])));
  return [values, (name: string, v: Value) => setValues((prev) => ({ ...prev, [name]: v }))] as const;
}

type Runner = (accion: string, body: FormData | Record<string, string>) => Promise<{ ok: boolean; errors: Errors }>;

function ModalFrame({ id, title, close, size = " modal-dialog-centered", children, footer, formProps, busy, controls }: {
  id: string; title: string; close?: () => void; size?: string; children: ReactNode; footer: ReactNode; busy?: boolean; controls?: string;
  formProps?: { onSubmit: (e: FormEvent<HTMLFormElement>) => void; encType?: string };
}) {
  const body = <>
    <div className="modal-header">
      <h5 className="modal-title" id={`${id}Label`}>{title}</h5>
      {close && <button type="button" className="btn-close" aria-label="Close" onClick={close} />}
    </div>
    {children}
    <div className="modal-footer">{footer}</div>
  </>;
  return (
    <NativeModal id={id} title={title} close={close ?? (() => undefined)} busy={busy ?? !close} size={size} controls={controls}>
      <div className="modal-content">{formProps ? <form method="POST" action="" {...formProps}>{body}</form> : body}</div>
    </NativeModal>
  );
}

function Confirm({ id, title, question, accion, run, close, centered = false }: { id: string; title: string; question: string; accion: string; run: Runner; close: () => void; centered?: boolean }) {
  const [busy, setBusy] = useState(false);
  const send = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    await run(accion, {});
    setBusy(false);
  };
  return (
    <NativeModal id={id} title={title} close={close} busy={busy} size={centered ? " modal-dialog-centered" : ""}>
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id={`${id}Label`}>{title}</h5>
          <button type="button" className="btn-close" aria-label="Close" onClick={close} />
        </div>
        <div className="modal-body mb-2">{question}</div>
        <div className="modal-footer">
          <form method="POST" action="" onSubmit={(e) => void send(e)}>
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}
            <button type="submit" className="btn btn-primary" disabled={busy}>Confirmar</button>
          </form>
        </div>
      </div>
    </NativeModal>
  );
}

function IFInforme({ data, run, close }: { data: EditorData; run: Runner; close: () => void }) {
  const [busy, setBusy] = useState(false);
  const f = data.modales.if_informe[0];
  const archivo = data.modales.if_informe_archivo;
  const send = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    await run("if-informe-tecnico", new FormData(e.currentTarget));
    setBusy(false);
  };
  return (
    <ModalFrame id="modalIFInformeTecnico" title="Cargar Informe Técnico -GDE" close={close} size="" busy={busy} controls="button:not([disabled]),input:not([disabled])"
      formProps={{ onSubmit: (e) => void send(e), encType: "multipart/form-data" }}
      footer={<><button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}<button type="submit" className="btn btn-primary" disabled={busy}>Guardar</button></>}>
      <div className="modal-body">
        {f && <Crispy f={f} value={f.value} onChange={() => undefined} />}
        <div id={`div_${archivo.id}`} className="mb-3">
          <label htmlFor={archivo.id} className="form-label requiredField">{archivo.label}<span className="asteriskField">*</span></label>
          <input type="file" name="archivo_informe_tecnico_GDE" id={archivo.id} className="clearablefileinput form-control" required />
        </div>
      </div>
    </ModalFrame>
  );
}

function Caratular({ data, run, close, errors }: { data: EditorData; run: Runner; close: () => void; errors: Errors }) {
  const [busy, setBusy] = useState(false);
  const fields = errors ? errors.fields : data.modales.caratular;
  const by = (name: string) => fields.find((f) => f.name === name)!;
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(fields.map((f) => [f.name, String(f.value)])));
  const send = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    await run("caratular", Object.fromEntries(fields.map((f) => [f.name, values[f.name] ?? ""])));
    setBusy(false);
  };
  const widget = (f: Field, extra = "") => {
    const { class: cls, maxlength, ...rest } = f.attrs;
    return <input type="text" name={f.name} id={f.id} className={`${String(cls ?? "form-control")}${extra}`} maxLength={maxlength ? Number(maxlength) : undefined} {...rest}
      required={f.required} value={values[f.name] ?? ""} onChange={(e) => setValues((p) => ({ ...p, [f.name]: e.target.value }))} />;
  };
  const err = (f: Field) => f.errors.length > 0 && <ul className="errorlist">{f.errors.map((m, i) => <li key={i}>{m}</li>)}</ul>;
  const a = by("expediente_anio"), n = by("expediente_numero"), r = by("expediente_reparticion"), o = by("expediente_organismo");
  return (
    <ModalFrame id="caratularExpediente" title="Caratular Expediente" close={close} size=" modal-dialog-centered modal-expediente-amplio" busy={busy}
      formProps={{ onSubmit: (e) => void send(e) }}
      footer={<><button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}<button type="submit" className="btn btn-primary" id="btnCaratulacion_id" disabled={busy}>Guardar</button></>}>
      <div className="modal-body">
        <div className="row g-3 expediente-estructurado-grid">
          <div className="col-12 col-md-2">
            <label className="form-label" htmlFor={a.id}>Año</label>
            <div className="input-group"><span className="input-group-text">EX-</span>{widget(a)}</div>
            {err(a)}
          </div>
          <div className="col-12 col-md-3">
            <label className="form-label" htmlFor={n.id}>Número</label>
            {widget(n)}
            {err(n)}
          </div>
          <div className="col-12 col-md-4">
            <label className="form-label" htmlFor={r.id}>Repartición</label>
            <div className="input-group"><span className="input-group-text">APN-</span>{widget(r)}</div>
            {err(r)}
          </div>
          <div className="col-12 col-md-3">
            <label className="form-label" htmlFor={o.id}>Organismo</label>
            <div className="input-group"><span className="input-group-text">#</span>{widget(o)}</div>
            {err(o)}
          </div>
        </div>
        {errors && errors.non_field_errors.length > 0 && <div className="alert alert-danger mt-3 mb-0"><ul className="errorlist nonfield">{errors.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul></div>}
      </div>
    </ModalFrame>
  );
}

function RevisarInforme({ data, close, upload }: { data: EditorData; close: () => void; upload: () => void }) {
  return (
    <ModalFrame id="modalRevisarInformeTecnico" title="Revisar Informe Técnico" close={close} size=""
      footer={<button type="button" className="btn btn-secondary" onClick={close}>Cerrar</button>}>
      <div className="modal-body">
        <div className="d-grid gap-2">
          {data.pdf?.docx ? <a href={data.pdf.docx} className="btn btn-success" download>📄 Descargar DOCX de informe técnico generado</a>
            : <button className="btn btn-secondary" disabled>📄 DOCX no disponible</button>}
          <button type="button" className="btn btn-warning" onClick={upload}>📤 Subir DOCX Informe técnico Final</button>
        </div>
      </div>
    </ModalFrame>
  );
}

function SubirDocx({ data, run, close }: { data: EditorData; run: Runner; close: () => void }) {
  const [busy, setBusy] = useState(false);
  const send = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    await run("subir-docx-final", new FormData(e.currentTarget));
    setBusy(false);
  };
  return (
    <NativeModal id="modalSubirDocxFinal" title="Subir DOCX Informe técnico Final" close={close} busy={busy}>
      <form method="post" encType="multipart/form-data" action="" onSubmit={(e) => void send(e)}>
        {data.modales.informe_id !== null && <input type="hidden" name="informe_id" value={data.modales.informe_id} />}
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="modalSubirDocxFinalLabel">Subir DOCX Informe técnico Final</h5>
            <button type="button" className="btn-close" aria-label="Close" onClick={close} />
          </div>
          <div className="modal-body">
            <div className="mb-3">
              <label htmlFor="docx_final" className="form-label">Archivo DOCX final</label>
              <input type="file" className="form-control" id="docx_final" name="docx_final" accept=".docx" required />
              <div className="form-text">Seleccione el archivo DOCX final que será revisado por el abogado.</div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}
            <button type="submit" className="btn btn-primary" disabled={busy}>Subir Archivo</button>
          </div>
        </div>
      </form>
    </NativeModal>
  );
}

const MENSAJES_RESYNC = {
  datos: "Los datos de la Organización dentro del Informe Técnico se reemplazarán por los del Legajo de la Organización. ¿Está seguro de continuar?",
  actualizar: "La información de la Admisión, incluidos los datos de la Organización dentro del Informe Técnico, se actualizará desde el Legajo de la Organización y se perderá el progreso realizado. ¿Está seguro de continuar?",
  continuar: "Continuará gestionando la Admisión con la información ya procesada, sin las últimas actualizaciones realizadas al Legajo de la Organización correspondiente. ¿Está seguro de continuar?",
};

function Resync({ data }: { data: EditorData }) {
  const r = data.resync!;
  const [accion, setAccion] = useState("");
  const [paso, setPaso] = useState<"seleccion" | "confirmacion">("seleccion");
  const [confirmada, setConfirmada] = useState("");
  const [busy, setBusy] = useState(false);
  const titulo = r.desincronizada ? "El tipo de convenio fue actualizado desde el Legajo de la Organización"
    : r.documentacion_desactualizada ? "La Documentación relacionada a la Organización fue actualizada desde el Legajo de la Organización"
      : "Los datos de la Organización fueron actualizados desde el Legajo de la Organización";
  const mensaje = confirmada === "actualizar" ? (r.solo_datos_organizacion ? MENSAJES_RESYNC.datos : MENSAJES_RESYNC.actualizar) : confirmada === "continuar" ? MENSAJES_RESYNC.continuar : "";
  const confirmar = async () => {
    setBusy(true);
    try {
      const resp = await editorNative.post(data.urls.resync, { accion: confirmada }, { "X-Requested-With": "XMLHttpRequest" });
      if (resp.success === false) { editorNative.alert((resp.error as string) || "No se pudo aplicar la acción."); setBusy(false); return; }
      editorNative.navigate((resp.redirect as string) || window.location.href);
    } catch {
      editorNative.alert("Ocurrió un error al aplicar la acción.");
      setBusy(false);
    }
  };
  return (
    <NativeModal id="modalResyncConvenio" title={titulo} close={() => undefined} busy controls="select,button:not([disabled])" size=" modal-dialog-centered">
      <div className="modal-content">
        <div className="modal-header bg-warning text-dark">
          <h5 className="modal-title" id="modalResyncConvenioLabel"><i className="fas fa-exclamation-triangle me-2" />{" "}{titulo}</h5>
        </div>
        <div className="modal-body">
          {paso === "seleccion" ? (
            <div id="modalResyncStepSeleccion">
              <p className="mb-2">Para continuar con la admisión debe seleccionar una de las siguientes opciones:</p>
              <select id="accionResyncConvenio" className="form-select" required value={accion} onChange={(e) => setAccion(e.target.value)}>
                <option value="" disabled>Seleccione una opción...</option>
                <option value="actualizar">Actualizar Información desde Legajo Organización (incluye datos de la Organización dentro del Informe Técnico)</option>
                <option value="continuar">Continuar operando con la Admisión actual</option>
              </select>
              {r.desincronizada && <div className="small text-muted mt-3">
                Tipo de Entidad actual de la Organización: <strong>{r.tipo_entidad_actual}</strong>.<br />{" "}
                Tipo registrado en esta admisión: <strong>{r.tipo_entidad_snapshot}</strong>.
              </div>}
              {r.documentos_modificados.length > 0 && <div className="mt-3">
                <p className="small fw-bold mb-1">Documentos modificados:</p>
                <ul className="small mb-0">{r.documentos_modificados.map((e, i) => <li key={i}>{e}</li>)}</ul>
              </div>}
              {r.datos_modificados.length > 0 && <div className="mt-3">
                <p className="small fw-bold mb-1">Datos de la Organización modificados:</p>
                <ul className="small mb-0">{r.datos_modificados.map((e, i) => <li key={i}>{e}</li>)}</ul>
              </div>}
            </div>
          ) : (
            <div id="modalResyncStepConfirmacion"><p id="modalConfirmarResyncConvenioMensaje" className="mb-0">{mensaje}</p></div>
          )}
        </div>
        <div className="modal-footer">
          {paso === "seleccion"
            ? <button type="button" className="btn btn-warning" id="btnAplicarResyncConvenio" disabled={!accion} onClick={() => { setConfirmada(accion); setPaso("confirmacion"); }}>Aplicar</button>
            : <>
              <button type="button" className="btn btn-secondary" id="btnVolverResyncConvenio" onClick={() => setPaso("seleccion")}>Volver</button>{" "}
              <button type="button" className="btn btn-primary" id="btnConfirmarResyncConvenio" disabled={busy} onClick={() => void confirmar()}>Confirmar</button>
            </>}
        </div>
      </div>
    </NativeModal>
  );
}

function SeleccionConvenio({ data, run }: { data: EditorData; run: Runner }) {
  const s = data.seleccion_convenio!;
  const [v, setV] = useState({ es_ex_pnud: "", estado_convenio_pnud: "", tipo_renovacion: "", estado_financiamiento: "", informe_complementario_modifica_prestaciones: "" });
  const [busy, setBusy] = useState(false);
  const set = (name: keyof typeof v, value: string) => setV((p) => ({ ...p, [name]: value, ...(name === "es_ex_pnud" && value !== "si" ? { estado_convenio_pnud: "" } : {}) }));
  const aplicaPnud = v.es_ex_pnud === "si";
  const send = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    const body: Record<string, string> = s.tipo === "incorporacion"
      ? { es_ex_pnud: v.es_ex_pnud, estado_convenio_pnud: v.estado_convenio_pnud }
      : { tipo_renovacion: v.tipo_renovacion, estado_financiamiento: v.estado_financiamiento, informe_complementario_modifica_prestaciones: v.informe_complementario_modifica_prestaciones };
    await run("confirmar-tipo-convenio", body);
    setBusy(false);
  };
  const select = (id: string, name: keyof typeof v, label: string, opts: [string, string][], required = true) => (
    <>
      <label htmlFor={id} className="form-label fw-bold">{label}</label>
      <select className="form-select" id={id} name={name} required={required} value={v[name]} onChange={(e) => set(name, e.target.value)}>
        <option value="" disabled>Seleccione una opción</option>
        {opts.map(([value, text_]) => <option key={value} value={value}>{text_}</option>)}
      </select>
    </>
  );
  return (
    <NativeModal id="seleccionModal" title="Selección de Convenio" close={() => undefined} busy size=" modal-dialog-centered">
      <div className="modal-content">
        <form method="POST" onSubmit={(e) => void send(e)}>
          <div className="modal-header"><h5 className="modal-title">Selección de Convenio</h5></div>
          <div className="modal-body">
            <div className="mb-3">
              <label className="form-label fw-bold">Tipo de Entidad</label>
              <input type="text" className="form-control" value={s.tipo_entidad} readOnly />
              <div className="form-text">Esta información debe editarse desde el legajo de la Organización</div>
            </div>
            <div>
              <label className="form-label fw-bold">Tipo de Convenio</label>
              <input type="text" className="form-control" value={s.tipo_convenio} readOnly />
            </div>
            {s.tipo === "incorporacion" && <>
              <div className="mt-3">{select("esExPnudInicial", "es_ex_pnud", "¿Es Ex PNUD?", [["si", "Sí"], ["no", "No"]])}</div>
              {aplicaPnud && <div className="mt-3" id="estadoConvenioPnudInicialContainer">{select("estadoConvenioPnudInicial", "estado_convenio_pnud", "Estado del convenio PNUD", [["vigente", "Vigente"], ["finalizado", "Finalizado"]], true)}</div>}
            </>}
            {s.tipo === "renovacion" && <>
              <div className="mt-3">{select("tipoRenovacionInicial", "tipo_renovacion", "¿Qué renovación tramita?", [["primera", "Primera renovación"], ["segunda_o_posterior", "Segunda renovación o posterior"]])}</div>
              <div className="mt-3">{select("estadoFinanciamientoInicial", "estado_financiamiento", "Estado del financiamiento", [["vigente", "Financiamiento vigente"], ["finalizado", "Financiamiento finalizado"]])}</div>
              <div className="mt-3">{select("informeComplementarioPrestacionesInicial", "informe_complementario_modifica_prestaciones", "¿Se realizó Informe Complementario para modificar prestaciones?", [["si", "Sí"], ["no", "No"]])}</div>
            </>}
          </div>
          <div className="modal-footer">
            <a href={data.urls.listar} className="btn btn-secondary">Cancelar</a>{" "}
            <button type="submit" className="btn btn-primary" id="confirmarSeleccion" disabled={!s.precargado || busy}>Continuar</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

function ObservacionRectificar({ confirm, close }: { confirm: (observacion: string) => void; close: () => void }) {
  const [valor, setValor] = useState("");
  const [error, setError] = useState("");
  const guardar = () => {
    if (!valor.trim()) { setError("Debe completar las observaciones."); return; }
    confirm(valor.trim());
  };
  return (
    <NativeModal id="modalObservacionRectificar" title="Observaciones obligatorias" close={close} busy size=" modal-dialog-centered" controls="button:not([disabled]),textarea:not([disabled])">
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id="modalObservacionRectificarLabel">Observaciones obligatorias</h5>
          <button type="button" className="btn-close" aria-label="Close" onClick={close} />
        </div>
        <div className="modal-body">
          <div className="mb-3">
            <label htmlFor="observacionRectificar" className="form-label">Detalle el motivo de la rectificacion</label>
            <textarea className="form-control" id="observacionRectificar" rows={4} maxLength={2000} value={valor} onChange={(e) => setValor(e.target.value)} autoFocus />
            <div className="text-danger small mt-2" id="observacionRectificarError">{error}</div>
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}
          <button type="button" className="btn btn-primary" id="btnConfirmarRectificar" onClick={guardar}>Guardar observaciones</button>
        </div>
      </div>
    </NativeModal>
  );
}

function EliminarArchivo({ doc, run, close }: { doc: Doc; run: () => Promise<void>; close: () => void }) {
  return (
    <NativeModal id="modalConfirmarEliminar" title="Eliminar Archivo" close={close} size=" modal-dialog-centered">
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id="modalConfirmarEliminarLabel">Eliminar Archivo</h5>
          <button type="button" className="btn-close" aria-label="Close" onClick={close} />
        </div>
        <div className="modal-body" id="modalConfirmarEliminarBody">
          <p>¿Seguro que quiere eliminar el siguiente archivo?</p>
          <p className="mb-0"><strong>{doc.nombre}</strong></p>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}
          <button type="button" className="btn btn-danger" id="btnConfirmarEliminar" onClick={() => void run()}>Eliminar</button>
        </div>
      </div>
    </NativeModal>
  );
}

function EditorEnLinea({ valor, id, vacio, agregar, editar, toast, endpoint, field, exito, falla, error }: {
  valor: number | null; id: number; vacio: string; agregar: string; editar: string; toast: (t: Toast) => void; endpoint: string; field: string;
  exito: string; falla: string; error: string;
}) {
  const [editando, setEditando] = useState(false);
  const [borrador, setBorrador] = useState(valor === null ? "" : String(valor));
  const [actual, setActual] = useState(valor);
  const base = field === "convenio_numero" ? "convenio-numero" : "personas-conveniadas-nomina";
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => { if (editando) { input.current?.focus(); input.current?.select(); } }, [editando]);
  const guardar = async () => {
    try {
      const r = await editorNative.post(endpoint, { admision_id: String(id), [field]: borrador.trim() });
      if (!r.success) {
        if (field === "convenio_numero") toast({ tone: "danger", text: (r.error as string) || falla });
        else editorNative.alert("Error: " + ((r.error as string) || falla));
        return;
      }
      const n = (r[field] as number | null | undefined) ?? null;
      setActual(n); setBorrador(n === null ? "" : String(n)); setEditando(false);
      toast({ tone: "success", text: exito });
    } catch {
      if (field === "convenio_numero") toast({ tone: "danger", text: error });
      else editorNative.alert(error);
    }
  };
  const cancelar = () => { setBorrador(actual === null ? "" : String(actual)); setEditando(false); };
  return (
    <div className="d-inline-flex align-items-center gap-2">
      <div id={`${base}-display`} className={`convenio-numero-display${editando ? " d-none" : ""}`} onClick={() => setEditando(true)}>
        {actual !== null ? <><span className="text-success fw-bold">{actual}</span>{" "}<i className="bi bi-pencil-square ms-2 text-muted" title={editar} /></>
          : <><span className="text-muted">{vacio}</span>{" "}<i className="bi bi-plus-circle ms-2 text-primary" title={agregar} /></>}
      </div>
      <div id={`${base}-edit`} className={`convenio-numero-edit${editando ? "" : " d-none"}`}>
        <input type="number" id={`${base}-input`} className="form-control form-control-sm" value={borrador} min="0" step="1" onChange={(e) => setBorrador(e.target.value)} ref={input} />
        <button type="button" className="btn btn-success btn-sm convenio-numero-btn" title="Guardar" onClick={() => void guardar()}><i className="bi bi-check-lg" /></button>{" "}
        <button type="button" className="btn btn-danger btn-sm convenio-numero-btn" title="Cancelar" onClick={cancelar}><i className="bi bi-x-lg" /></button>
      </div>
    </div>
  );
}

function ExpedienteModal({ data, toast, close, onSaved }: { data: EditorData; toast: (t: Toast) => void; close: () => void; onSaved: (n: string) => void }) {
  const match = (data.admision.num_expediente ?? "").trim().match(/^EX-(\d{4})-(\d{9})- -APN-([A-Z0-9]+)#([A-Z0-9]+)$/i);
  const inicial = match ? match.slice(1) : ["", "", "", "MCH"];
  const [anio, setAnio] = useState(inicial[0]);
  const [numero, setNumero] = useState(inicial[1]);
  const [reparticion, setReparticion] = useState(inicial[2]);
  const [organismo, setOrganismo] = useState(inicial[3]);
  const fallo = (message: string) => toast({ tone: "danger", text: message || "No se pudo actualizar el número de expediente." });
  const guardar = async () => {
    const a = anio.trim(), n = numero.trim(), r = reparticion.trim().toUpperCase(), o = organismo.trim().toUpperCase();
    if (!/^\d{4}$/.test(a) || !/^\d{9}$/.test(n) || !/^[A-Z0-9]+$/.test(r) || !/^[A-Z0-9]+$/.test(o)) {
      fallo("Complete el año (4 dígitos), número (9 dígitos), repartición y organismo.");
      return;
    }
    try {
      const resp = await editorNative.post("/ajax/actualizar-num-expediente/", { admision_id: String(data.id), num_expediente: `EX-${a}-${n}- -APN-${r}#${o}` });
      if (!resp.success) { fallo((resp.error as string) || ""); return; }
      onSaved(((resp.num_expediente as string) || "").trim());
      toast({ tone: "success", text: "Número de expediente actualizado con éxito." });
      close();
    } catch {
      fallo("Ocurrió un error al actualizar el número de expediente.");
    }
  };
  return (
    <NativeModal id="editarExpedienteModal" title="Editar número de expediente" close={close} size=" modal-dialog-centered modal-expediente-amplio">
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id="editarExpedienteModalLabel">Editar número de expediente</h5>
          <button type="button" className="btn-close" aria-label="Cerrar" onClick={close} />
        </div>
        <div className="modal-body">
          <div className="row g-3 expediente-estructurado-grid">
            <div className="col-12 col-md-2">
              <label className="form-label" htmlFor="num-expediente-anio">Año</label>
              <div className="input-group"><span className="input-group-text">EX-</span>
                <input id="num-expediente-anio" className="form-control" inputMode="numeric" maxLength={4} placeholder="2025" required value={anio} onChange={(e) => setAnio(e.target.value)} /></div>
            </div>
            <div className="col-12 col-md-3">
              <label className="form-label" htmlFor="num-expediente-numero">Número</label>
              <input id="num-expediente-numero" className="form-control" inputMode="numeric" maxLength={9} placeholder="112100154" required value={numero} onChange={(e) => setNumero(e.target.value)} />
            </div>
            <div className="col-12 col-md-4">
              <label className="form-label" htmlFor="num-expediente-reparticion">Repartición</label>
              <div className="input-group"><span className="input-group-text">APN-</span>
                <input id="num-expediente-reparticion" className="form-control text-uppercase" maxLength={50} placeholder="DDNAYF" required value={reparticion} onChange={(e) => setReparticion(e.target.value)} /></div>
            </div>
            <div className="col-12 col-md-3">
              <label className="form-label" htmlFor="num-expediente-organismo">Organismo</label>
              <div className="input-group"><span className="input-group-text">#</span>
                <input id="num-expediente-organismo" className="form-control text-uppercase" maxLength={50} required value={organismo} onChange={(e) => setOrganismo(e.target.value)} /></div>
            </div>
          </div>
          <small className="text-muted">
            Tené en cuenta que, si modificás el número de expediente, este cambio no se reflejará en el informe técnico en caso de que ya esté finalizado.
          </small>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}
          <button type="button" className="btn btn-primary" onClick={() => void guardar()}>Guardar</button>
        </div>
      </div>
    </NativeModal>
  );
}

const INFO_EXPEDIENTE = "Tené en cuenta que, si modificás el número de expediente, este cambio no se reflejará en el informe técnico en caso de que ya esté finalizado.";

function InformeIcono({ estado }: { estado: string | null }) {
  if (estado === null) return <i className="bi bi-x-circle-fill text-danger" />;
  if (estado === "Validado") return <i className="bi bi-check-circle-fill text-success" />;
  if (estado === "Para revision" || estado === "Iniciado") return <i className="bi bi-check-circle-fill text-warning" />;
  if (estado === "A subsanar") return <i className="bi bi-exclamation-circle-fill text-danger" />;
  return null;
}

function AdmisionCard({ data, toast, editarExpediente }: { data: EditorData; toast: (t: Toast) => void; editarExpediente: () => void }) {
  const a = data.admision;
  const [pwa, setPwa] = useState(a.vigente_pwa);
  const expediente = a.num_expediente;
  const cambiarPwa = async (checked: boolean) => {
    setPwa(checked);
    try {
      const r = await editorNative.post("/ajax/actualizar-vigente-pwa/", { admision_id: String(data.id), vigente_pwa: checked ? "1" : "0" });
      if (!r.success) { setPwa(!checked); editorNative.alert("Error: " + ((r.error as string) || "No se pudo actualizar la vigencia PWA.")); }
    } catch {
      setPwa(!checked); editorNative.alert("Ocurrio un error al actualizar la vigencia PWA.");
    }
  };
  const informe = a.informe_estado;
  const pdf = data.pdf;
  const docxIcon = (url: string, tone: string) => <span className="fw-bold"><a href={url} target="_blank"><i className={`bi bi-filetype-docx text-${tone} h4 ms-3 text-bold`} /></a></span>;
  return (
    <div className="col-6">
      <div className="card card-primary card-outline h-100">
        <div className="card-header"><h2 className="card-title fw-bold fs-3">Admisión</h2></div>
        <div className="card-body card-comments">
          <ul className="nav nav-pills flex-column">
            <li className="nav-item"><div className="comment-text">Tipo Convenio:{" "}<span className="fw-bold">{a.tipo_convenio}</span></div></li>
            <li className="nav-item"><div className="comment-text">Número de convenio:{" "}
              {data.puede_editar_convenio_numero
                ? <EditorEnLinea valor={a.convenio_numero} id={data.id} vacio="Sin numero de convenio" agregar="Agregar numero de convenio" editar="Editar numero de convenio" toast={toast}
                  endpoint="/ajax/actualizar-convenio-numero/" field="convenio_numero" exito="Numero de convenio actualizado con exito." falla="No se pudo actualizar el numero de convenio."
                  error="Ocurrio un error al actualizar el numero de convenio." />
                : <span className="fw-bold">{a.convenio_numero ?? "-"}</span>}
            </div></li>
            <li className="nav-item"><div className="comment-text">Vigente PWA:{" "}
              {data.puede_editar_convenio_numero
                ? <div className="form-check form-switch d-inline-block ms-2">
                  <input className="form-check-input" type="checkbox" role="switch" id="vigente-pwa-input" checked={pwa} onChange={(e) => void cambiarPwa(e.target.checked)} />{" "}
                  <label className="form-check-label" htmlFor="vigente-pwa-input">Admisión vigente</label>
                </div>
                : pwa ? <span className="badge bg-success">Vigente</span> : <span className="badge bg-secondary">No vigente</span>}
            </div></li>
            {data.mostrar_personas_conveniadas_nomina && <li className="nav-item"><div className="comment-text">Personas conveniadas nómina:{" "}
              {data.puede_editar_personas_conveniadas_nomina
                ? <EditorEnLinea valor={a.personas_conveniadas_nomina} id={data.id} vacio="Sin personas conveniadas nómina" agregar="Agregar personas conveniadas nómina" editar="Editar personas conveniadas nómina" toast={toast}
                  endpoint="/ajax/actualizar-personas-conveniadas-nomina/" field="personas_conveniadas_nomina" exito="Personas conveniadas nómina actualizadas con éxito."
                  falla="No se pudo actualizar personas conveniadas nomina." error="Ocurrio un error al actualizar personas conveniadas nomina." />
                : <span className="fw-bold">{a.personas_conveniadas_nomina ?? "-"}</span>}
            </div></li>}
            <li className="nav-item"><div className="comment-text">Tipo:{" "}<span className="fw-bold">{a.tipo_display}</span></div></li>
            <li className="nav-item"><div className="comment-text">Estado del Proceso:{" "}<span className="fw-bold">{a.estado_proceso}</span></div></li>
            <li className="nav-item"><div className="comment-text">Fecha:{" "}<span className="fw-bold">{a.fecha}</span></div></li>
            <li className="nav-item"><div className="comment-text">Fecha de vencimiento de mandatos:{" "}<span className="fw-bold">{a.vencimiento_mandatos}</span></div></li>
            <li className="nav-item"><div className="comment-text">Número de Expediente:{" "}
              <span id="num-expediente-display" className="fw-bold">{expediente || "Sin información"}{" "}</span>{" "}
              {expediente ? <i id="num-expediente-status-icon" className="bi bi-check-circle-fill text-success" /> : <i id="num-expediente-status-icon" className="bi bi-x-circle-fill text-danger" />}
              {expediente && data.puede_editar_num_expediente
                ? <>{" "}<button type="button" id="btn-editar-num-expediente" className="btn btn-outline-primary btn-sm ms-2" onClick={editarExpediente}>Editar</button></>
                : a.enviado_legales ? <>{" "}<small className="text-muted ms-1">No editable después de enviar a legales.</small></> : null}
              {expediente && <>{" "}<i id="num-expediente-info-icon" className="fas fa-info-circle ms-1" data-bs-toggle="tooltip" data-bs-placement="top" title={INFO_EXPEDIENTE} /></>}
            </div></li>
            <li className="nav-item"><div className="comment-text">Informe Técnico:{" "}<span className="fw-bold">{informe ?? ""}</span>{" "}<InformeIcono estado={informe} /></div></li>
            {pdf && <li className="nav-item"><div className="comment-text">Informe Técnico SISOC:{" "}
              {informe === "Validado"
                ? pdf.docx_editado ? docxIcon(pdf.docx_editado, "success") : pdf.docx ? docxIcon(pdf.docx, "info") : null
                : <>
                  {pdf.archivo && <span className="fw-bold"><a href={pdf.archivo} target="_blank"><i className="bi bi-filetype-pdf text-info h4 ms-3 text-bold" /></a></span>}
                  {pdf.docx && docxIcon(pdf.docx, "info")}
                </>}
            </div></li>}
            {a.numero_if_tecnico && <li className="nav-item"><div className="comment-text">Informe Técnico GDE:{" "}<span className="fw-bold">{a.numero_if_tecnico}</span>{" "}<i className="bi bi-check-circle-fill text-success" />
              {a.informe_gde && <>{" "}<span className="fw-bold"><a href={a.informe_gde} target="_blank"><i className="bi bi-file-earmark-check text-info h4 ms-1 text-bold" /></a></span></>}
            </div></li>}
            {data.complementarios.length > 0 && <li className="nav-item"><div className="comment-text">PDF Informes Complementarios:{" "}
              {data.complementarios.map((c, i) => <Fragment key={i}>
                {c.pdf ? <span className="fw-bold"><a href={c.pdf} target="_blank"><i className="bi bi-filetype-pdf text-info h4 ms-3 text-bold" />{c.fecha}</a></span>
                  : <span className="fw-bold">{c.fecha} - {c.estado}</span>}
                <br />
              </Fragment>)}
            </div></li>}
          </ul>
        </div>
      </div>
    </div>
  );
}

function ComedorCard({ data }: { data: EditorData }) {
  const c = data.comedor;
  return (
    <div className="col-6">
      <div className="card card-primary card-outline">
        <div className="card-header"><h2 className="card-title fw-bold fs-3">Comedor</h2></div>
        <div className="card-body card-comments p-3">
          <ul className="nav nav-pills flex-column">
            <li className="nav-item"><div className="comment-text ">Nombre:{" "}
              {c.id !== null && data.urls.comedor ? <a href={data.urls.comedor}><span className="fw-bold">{c.nombre}</span></a> : <span className="fw-bold">{c.nombre || "-"}</span>}
            </div></li>
            <li className="nav-item"><div className="comment-text">Tipo Comedor:{" "}<span className="fw-bold">{c.tipocomedor}</span></div></li>
            <li className="nav-item"><div className="comment-text">Programa:{" "}<span className="fw-bold">{c.programa}</span></div></li>
            <li className="nav-item"><div className="comment-text">Organización:{" "}<span className="fw-bold">{c.organizacion}</span></div></li>
            <li className="nav-item"><div className="comment-text">Provincia:{" "}<span className="fw-bold">{c.provincia} - {c.municipio} - {c.localidad}</span></div></li>
            <li className="nav-item"><div className="comment-text">Calle:{" "}<span className="fw-bold">{c.calle} {c.numero} - Piso: {c.piso} {c.departamento}</span></div></li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function Validaciones({ data, run }: { data: EditorData; run: Runner }) {
  const v = data.validaciones!;
  const fields = v.editable ? v.fields : [];
  const [values, set] = useValues(fields);
  const [busy, setBusy] = useState(false);
  if (!v.editable) {
    return <dl className="row mb-0">{v.valores.map(([label, valor]) => <Fragment key={label}><dt className="col-sm-4">{label}</dt><dd className="col-sm-8">{valor}</dd></Fragment>)}</dl>;
  }
  const incorporacion = data.admision.tipo === "incorporacion";
  const aplicaPnud = values.es_ex_pnud === "si";
  const send = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    const body: Record<string, string> = {};
    for (const f of fields) body[f.name] = String(f.name === "estado_convenio_pnud" && incorporacion && !aplicaPnud ? "" : values[f.name] ?? "");
    await run("validaciones-template", body);
    setBusy(false);
  };
  return (
    <form method="post" onSubmit={(e) => void send(e)}>
      <div className="row">
        <FormFields fields={fields} values={values} set={set} wrap={(f, node) => {
          if (f.name === "estado_convenio_pnud") return <div className={`col-md-6${aplicaPnud ? "" : " d-none"}`} id="estadoConvenioPnudEdicionContainer">{node}</div>;
          return <div className="col-md-6">{node}</div>;
        }} />
      </div>
      <button type="submit" className="btn btn-primary" disabled={busy}>Guardar validaciones</button>
    </form>
  );
}

function BarraGde({ doc, toast, reload }: { doc: Doc; toast: (t: Toast) => void; reload: () => void }) {
  const g = doc.gde as { kind: "editable"; value: string | null };
  const [editando, setEditando] = useState(false);
  const [valor, setValor] = useState(g.value ?? "");
  const gdeInput = useRef<HTMLInputElement>(null);
  useEffect(() => { if (editando) gdeInput.current?.focus(); }, [editando]);
  const guardar = async () => {
    try {
      const r = await editorNative.post("/ajax/actualizar-numero-gde/", { documento_id: doc.id, numero_gde: valor.trim() });
      if (!r.success) { editorNative.alert("Error: " + r.error); setValor((r.valor_anterior as string) || ""); return; }
      toast({ tone: "success", text: "Número GDE actualizado con éxito." });
      setEditando(false);
      reload();
    } catch {
      editorNative.alert("Ocurrió un error al actualizar el número GDE.");
    }
  };
  return (
    <>
      <div id={`gde-display-${doc.id}`} className={`gde-display${editando ? " d-none" : ""}`} onClick={() => setEditando(true)}>
        {g.value ? <><span className="text-success fw-bold">{g.value}</span>{" "}<i className="bi bi-pencil-square ms-2 text-muted" style={{ cursor: "pointer" }} title="Editar número GDE" /></>
          : <><span className="text-muted">Sin número GDE</span>{" "}<i className="bi bi-plus-circle ms-2 text-primary" style={{ cursor: "pointer" }} title="Agregar número GDE" /></>}
      </div>
      <div id={`gde-edit-${doc.id}`} className={`gde-edit${editando ? "" : " d-none"}`}>
        <div className="d-flex align-items-center">
          <input type="text" className="form-control form-control-sm me-2" id={`gde-input-${doc.id}`} value={valor} placeholder="Ingrese número GDE" maxLength={50} style={{ maxWidth: "150px" }} ref={gdeInput} onChange={(e) => setValor(e.target.value)} />
          <button className="btn btn-success btn-sm me-1" title="Guardar" onClick={() => void guardar()}><i className="bi bi-check" /></button>{" "}
          <button className="btn btn-secondary btn-sm" title="Cancelar" onClick={() => { setValor(g.value ?? ""); setEditando(false); }}><i className="bi bi-x" /></button>
        </div>
      </div>
    </>
  );
}

function Fila({ doc, admisionId, toast, reload, pedirObservacion, pedirEliminar }: {
  doc: Doc; admisionId: number; toast: (t: Toast) => void; reload: () => void; pedirObservacion: (doc: Doc) => void; pedirEliminar: (doc: Doc) => void;
}) {
  const [progreso, setProgreso] = useState<number | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const ui = doc.estado_ui;
  const cambiarEstado = async (estado: string, observacion?: string) => {
    const body: Record<string, string> = { estado, documento_id: String(doc.archivo_id), admision_id: String(admisionId) };
    if (observacion) body.observacion = observacion;
    try {
      const r = await editorNative.post("/ajax/actualizar-estado/", body);
      if (!r.success) { editorNative.alert("Error: " + ((r.error as string) || "No se pudo actualizar el estado.")); return; }
      toast({ tone: "success", text: "Estado actualizado con éxito." });
      reload();
    } catch {
      editorNative.alert("Ocurrio un error al actualizar el estado.");
    }
  };
  const subir = async (file: File | undefined) => {
    if (!file) { editorNative.alert("Por favor, selecciona un archivo antes de adjuntar."); return; }
    setProgreso(0);
    const form = new FormData();
    form.append("archivo", file);
    const r = await editorNative.upload(`/admision/${admisionId}/documentacion/${doc.documentacion_id}/subir/`, form, setProgreso);
    if (r.status === 200) {
      const data = JSON.parse(r.body) as { success?: boolean; error?: string };
      if (data.success) reload(); else editorNative.alert("Error al subir el archivo: " + (data.error || ""));
    } else editorNative.alert("Error al subir el archivo");
    setProgreso(null);
  };
  const rowKey = doc.archivo_id ?? doc.row_id;
  const selected = ui.kind === "select" ? ui.options.find((o) => o.selected)?.value ?? "" : "";
  const badgeClass = ui.kind === "badge" ? `badge ${ui.badge}` : "";
  return (
    <>
      <tr id={`fila-${doc.row_id}`} data-personalizado={doc.personalizado ? "1" : "0"} data-documentacion-id={doc.documentacion_id ?? ""} data-archivo-id={doc.archivo_id ?? ""}>
        <td className="ps-3">
          {doc.estado_valor === "Rectificar" && <><i className="bi bi-x-circle text-danger fs-4 fw-bold me-1" />{" "}</>}
          {doc.nombre}{" "}
          {doc.obligatorio && <span className="text-danger fs-5 ms-1">*</span>}
          {doc.organizacion && <div className="small text-muted">
            Documento de la organizacion
            {doc.vencimiento && <>{" "}<span className="ms-2">Vencimiento: {doc.vencimiento}</span></>}
          </div>}
        </td>
        <td id={`estado-${rowKey}`} className="ps-1 text-center" style={{ minWidth: "8rem" }}>
          {ui.kind === "select" ? (
            <select className={`form-control form-control-sm mb-2${ui.border ? ` ${ui.border}` : ""}`} value={selected}
              onChange={(e) => {
                const estado = e.target.value;
                if (estado === "Rectificar" && ui.requires_observacion) pedirObservacion(doc); else void cambiarEstado(estado);
              }}>
              {ui.options.map((o) => <option key={o.value} value={o.value} disabled={o.disabled}>{o.label}</option>)}
            </select>
          ) : ui.kind === "badge" ? <span className={badgeClass}>{doc.estado}</span> : <>{doc.estado}</>}
        </td>
        <td>
          {doc.archivo_url ? <>
            <a href={doc.archivo_url} target="_blank" className="btn btn-primary btn-sm">Ver Archivo</a>
            {doc.puede_eliminar && <>{" "}<button className="btn btn-sm btn-danger px-3 ms-2" onClick={() => pedirEliminar(doc)}>Eliminar</button></>}
          </> : doc.puede_adjuntar && <>
            <input type="file" id={`file-${doc.documentacion_id}`} className="d-none" ref={input} onChange={(e) => void subir(e.target.files?.[0])} />
            <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => input.current?.click()}>Adjuntar</button>
            <div className="progress mt-2" id={`progress-container-${doc.documentacion_id}`} style={{ display: progreso === null ? "none" : "block", height: "3px" }}>
              <div className="progress-bar  progress-bar-striped" role="progressbar" id={`progress-bar-${doc.documentacion_id}`} style={{ width: `${progreso ?? 0}%` }}>{progreso ?? 0}%</div>
            </div>
          </>}
        </td>
        <td id={`gde-${doc.id}`}>
          {doc.gde.kind === "organizacion" ? <>
            {doc.numero_gde ? <span className="text-success fw-bold">{doc.numero_gde}</span> : <span className="text-muted">Sin número GDE</span>}{" "}
            <i className="bi bi-info-circle ms-1 text-muted" title="El número de GDE se gestiona desde el Legajo de la Organización" />
          </> : doc.gde.kind === "editable" ? <BarraGde doc={doc} toast={toast} reload={reload} />
            : doc.numero_gde ? <span className="text-success fw-bold">{doc.numero_gde}</span> : <span className="text-muted">-</span>}
        </td>
      </tr>
      {doc.observaciones && <tr id={`fila-obs-${rowKey}`} className={doc.estado !== "Rectificar" ? "d-none" : ""}>
        <td colSpan={4} className="bg-danger-subtle small ps-4">
          <strong><i className="bi bi-arrow-return-right fs-6" />{" "}Observaciones:</strong>{" "}
          <span>{doc.observaciones.split(/\r?\n/).map((l, i) => <Fragment key={i}>{i > 0 && <br />}{l}</Fragment>)}</span>
        </td>
      </tr>}
    </>
  );
}

function FilaAgregar({ data, reload }: { data: EditorData; reload: () => void }) {
  const [nombre, setNombre] = useState("");
  const [progreso, setProgreso] = useState<number | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const subir = async (file: File | undefined) => {
    if (!file) return;
    const form = new FormData();
    form.append("nombre", nombre.trim());
    form.append("archivo", file);
    setProgreso(0);
    const r = await editorNative.upload(data.urls.agregar_documento, form, setProgreso);
    const body = ((): { success?: boolean; error?: string } | null => { try { return JSON.parse(r.body); } catch { return null; } })();
    if (r.status === 0) editorNative.alert("Error de red al subir el documento.");
    else if (!body) editorNative.alert("Error inesperado en la respuesta del servidor.");
    else if (r.status >= 200 && r.status < 300 && body.success) { setNombre(""); if (input.current) input.current.value = ""; reload(); }
    else editorNative.alert(body.error || "No se pudo cargar el documento.");
    setProgreso(null);
  };
  return (
    <tr id="fila-agregar-documento" data-documentacion-id="" data-archivo-id="">
      <td className="ps-1"><input type="text" className="form-control form-control-sm" id="nuevoDocumentoNombre" placeholder="Nombre del documento adicional" value={nombre} onChange={(e) => setNombre(e.target.value)} /></td>
      <td className="ps-1"><span className="badge bg-secondary" /></td>
      <td>
        <input type="file" id="nuevoDocumentoArchivo" className="d-none" ref={input} onChange={(e) => void subir(e.target.files?.[0])} />
        <button type="button" className="btn btn-sm btn-outline-primary" id="btnAbrirFile"
          onClick={() => { if (!nombre.trim()) { editorNative.alert("Por favor, escriba un nombre antes de adjuntar un archivo."); return; } input.current?.click(); }}>Adjuntar</button>
        <div className="progress mt-2" id="progress-container-nuevo" style={{ display: progreso === null ? "none" : "block", height: "3px" }}>
          <div className="progress-bar progress-bar-striped" role="progressbar" id="progress-bar-nuevo" style={{ width: `${progreso ?? 0}%` }}>{progreso ?? 0}%</div>
        </div>
      </td>
      <td><span className="text-muted">-</span></td>
    </tr>
  );
}

function Documentos({ data, toast, reload }: { data: EditorData; toast: (t: Toast) => void; reload: () => void }) {
  const s = data.stats;
  const [rectificar, setRectificar] = useState<Doc | null>(null);
  const [eliminar, setEliminar] = useState<Doc | null>(null);
  const confirmarRectificacion = async (observacion: string) => {
    const doc = rectificar!;
    setRectificar(null);
    try {
      const r = await editorNative.post("/ajax/actualizar-estado/", { estado: "Rectificar", documento_id: String(doc.archivo_id), admision_id: String(data.id), observacion });
      if (!r.success) { editorNative.alert("Error: " + ((r.error as string) || "No se pudo actualizar el estado.")); return; }
      toast({ tone: "success", text: "Estado actualizado con éxito." });
      reload();
    } catch {
      editorNative.alert("Ocurrio un error al actualizar el estado.");
    }
  };
  const quitar = async () => {
    const doc = eliminar!;
    const identifier = doc.documentacion_id !== null ? doc.documentacion_id : doc.archivo_id;
    if (identifier === null) return;
    let url = `/admision/${data.id}/documentacion/${identifier}/eliminar/`;
    if (doc.archivo_id !== null) url += `?archivo_id=${doc.archivo_id}`;
    try {
      const r = await editorNative.remove(url);
      if (r.success) { setEliminar(null); reload(); } else editorNative.alert("Error al eliminar el archivo: " + (r.error || ""));
    } catch {
      /* the native script only logs the failure */
    }
  };
  const fila = (doc: Doc) => <Fila key={doc.row_id} doc={doc} admisionId={data.id} toast={toast} reload={reload} pedirObservacion={setRectificar} pedirEliminar={setEliminar} />;
  const completos = s.obligatorios_completos === s.obligatorios_total;
  return (
    <>
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header d-flex align-items-center">
              <h2 className="card-title fw-bold fs-3 mb-0">
                Documentos requeridos{" "}
                <span className="fs-5 ms-3"><small>{s.obligatorios_completos}/{s.obligatorios_total}</small>{" "}
                  {completos ? <i className="bi bi-check-circle-fill text-success" /> : <i className="bi bi-x-circle-fill text-danger" />}
                </span>
              </h2>
              <div className="d-flex align-items-center gap-2 ms-auto">
                <span className="badge bg-success" title="Aceptados">Aceptados: {s.aceptados}</span>{" "}
                <span className="badge bg-primary" title="A Validar Abogado">Validar Abogado: {s.a_validar_abogado}</span>{" "}
                <span className="badge bg-danger" title="Rectificar">Rectificar: {s.rectificar}</span>{" "}
                <span className="badge bg-secondary" title="Pendientes">Pendientes: {s.pendientes}</span>
              </div>
            </div>
            <div className="card-body card-comments p-0 pb-1">
              <div className="container mt-2 table-responsive">
                <table className="table table-striped table-bordered table-hover table-sm" id="tablaDocumentos">
                  <thead><tr><th>Documento</th><th style={{ width: "1%", whiteSpace: "nowrap" }}>Estado</th><th>Archivo</th><th>Número de GDE</th></tr></thead>
                  <tbody id="tablaDocumentosBody">
                    {data.documentos.map(fila)}
                    <tr><td colSpan={4} className="p-3" /></tr>
                    <tr className="table-secondary"><td colSpan={4} className="fw-bold text-center py-2">Documentación adicional</td></tr>
                    {data.documentos_personalizados.map(fila)}
                    {data.puede_agregar_documento && <FilaAgregar data={data} reload={reload} />}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
      {rectificar && <ObservacionRectificar confirm={(o) => void confirmarRectificacion(o)} close={() => setRectificar(null)} />}
      {eliminar && <EliminarArchivo doc={eliminar} run={quitar} close={() => setEliminar(null)} />}
    </>
  );
}

/** The `titulo-pagina` block. */
export function EditorHeading({ data }: { data: EditorData }) {
  return <>{data.comedor.nombre}{data.banner && <>{" "}<span className="ms-3 fs-5 bg-danger text-white px-2 py-1 rounded">{data.banner}</span></>}</>;
}

export function EditorBreadcrumb({ data }: { data: EditorData }) {
  return <ol className="breadcrumb float-sm-right">
    <div className="breadcrumb-item"><a href={data.urls.listar}>Técnicos - Admisiones</a></div>
    <div className="breadcrumb-item active">{data.comedor.nombre}</div>
  </ol>;
}

export function EditorContent({ data, onDone }: { data: EditorData; onDone: Done }) {
  const [modal, setModal] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast>(null);
  const [flash, setFlash] = useState<Message[]>(data.messages);
  const [errors, setErrors] = useState<Errors>(null);
  const [expediente, setExpediente] = useState(false);
  const reload = () => onDone([], false);
  const run: Runner = async (accion, body) => {
    try {
      const { data: d, status } = await webClient.post(`web/comedores/admisiones/${data.id}/acciones/${accion}/`, body, { validateStatus: (s: number) => s >= 200 && s < 500 });
      const messages = (record(d) && Array.isArray(d.messages) ? d.messages : []) as Message[];
      if (status === 400 && record(d) && Array.isArray(d.fields)) {
        // An invalid form re-renders the page with the modal open and the errors in the fields.
        setErrors({ fields: d.fields as Field[], non_field_errors: (d.non_field_errors as string[]) ?? [] });
        return { ok: false, errors: { fields: d.fields as Field[], non_field_errors: (d.non_field_errors as string[]) ?? [] } };
      }
      setErrors(null);
      setModal(null);
      setFlash(messages);
      onDone(messages, status >= 400);
      return { ok: status < 400, errors: null };
    } catch {
      setFlash([{ message: "Error inesperado.", level: "error" }]);
      return { ok: false, errors: null };
    }
  };
  const abrir = (b: Boton) => { if (b.modal) setModal(b.modal); };
  const close = () => { setModal(null); setErrors(null); };
  const confirmaciones: Record<string, { title: string; question: string; accion: string }> = {
    confirmarLegalesModal: { title: "Confirmar derivar a Legales", question: "¿Estás seguro que queres derivar a Legales", accion: "derivar-legales" },
    modalDisponibilizarAcomp: { title: "Confirmar disponibilizar a acompañamiento", question: "¿Esta seguro que quiere hacer esta acción", accion: "comenzar-acompanamiento" },
    modalRectificarDocumetacion: { title: "Confirmar rectificar documentación", question: "¿Estás seguro que queres rectificar documentación", accion: "rectificar-documentacion" },
    modalFinalizarCargaDocumentacion: { title: "Confirmar finalizar carga de documentación", question: "¿Estás seguro que querés finalizar la carga de documentación", accion: "finalizar-carga-documentacion" },
  };
  const conf = modal ? confirmaciones[modal] : undefined;
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/numeroExpedienteModal.css" />
      <link rel="stylesheet" href="/static/custom/css/informeTecnicoSecciones.css" />
      <style>{CSS}</style>
      <NativeToasts messages={flash} />
      {toast && <div className="position-fixed bottom-0 end-0 p-3" style={{ zIndex: 1100 }}>
        <div className={`toast show align-items-center text-bg-${toast.tone} border-0`} role="alert" aria-live="assertive" aria-atomic="true">
          <div className="d-flex">
            <div className="toast-body"><h6>{toast.text}</h6></div>
            <button type="button" className="btn-close btn-close-white me-2 m-auto" aria-label="Cerrar" onClick={() => setToast(null)} />
          </div>
        </div>
      </div>}
      <div className="row justify-content-between d-print-none mx-1 mb-3">
        <div className="col-auto">
          {data.botones.map((b) => <Fragment key={b.clave}>{b.url
            ? <a href={b.url} className={`btn ${b.clase} mr-1`}>{b.texto}</a>
            : <button type="button" className={`btn ${b.clase} mr-1`} onClick={() => abrir(b)}>{b.texto}</button>}{" "}</Fragment>)}
        </div>
      </div>
      {data.resync && <Resync data={data} />}
      {data.complementario_requerido && <div className="row mb-3"><div className="col-12">
        <div className="alert alert-warning" role="alert">
          <h5 className="alert-heading"><i className="fas fa-exclamation-triangle" />{" "}Informe Técnico Complementario Requerido</h5>
          {data.complementario_requerido.observaciones
            ? <><p className="mb-0"><strong>Observaciones de Legales:</strong></p><p className="mb-0">{data.complementario_requerido.observaciones}</p></>
            : <p className="mb-0">Se requiere completar un informe técnico complementario.</p>}
        </div>
      </div></div>}
      {data.informe_a_subsanar && <div className="row mb-3"><div className="col-12">
        <div className="alert alert-danger" role="alert">
          <h5 className="alert-heading"><i className="fas fa-exclamation-triangle" />{" "}Informe Técnico a Subsanar</h5>
          <p className="mb-0"><strong>Observaciones del Abogado:</strong></p>
          <p className="mb-0">{data.informe_a_subsanar}</p>
        </div>
      </div></div>}
      {data.seleccion_convenio && <SeleccionConvenio data={data} run={run} />}
      <div className="row mb-3">
        <AdmisionCard data={data} toast={setToast} editarExpediente={() => setExpediente(true)} />
        <ComedorCard data={data} />
      </div>
      {data.validaciones && <div className="row mb-3"><div className="col-12">
        <div className="card card-primary card-outline">
          <div className="card-header"><h2 className="card-title fw-bold">Validaciones para templates</h2></div>
          <div className="card-body">
            <p className="text-muted">Estas validaciones no modifican la documentación requerida por el tipo de convenio.</p>
            <Validaciones data={data} run={run} />
          </div>
        </div>
      </div></div>}
      {data.admision.estado_legales === "A Rectificar" && <div className="row mb-3"><div className="col-12">
        <div className="card card-danger card-outline h-100">
          <div className="card-header"><h2 className="card-title fw-bold fs-3">A Rectificar</h2></div>
          <div className="card-body card-comments"><h6>{data.admision.observaciones}</h6></div>
        </div>
      </div></div>}
      <Documentos data={data} toast={setToast} reload={reload} />
      {conf && <Confirm id={modal!} title={conf.title} question={conf.question} accion={conf.accion} run={run} close={close} centered={modal === "confirmarLegalesModal"} />}
      {modal === "modalIFInformeTecnico" && <IFInforme data={data} run={run} close={close} />}
      {modal === "modalRevisarInformeTecnico" && <RevisarInforme data={data} close={close} upload={() => setModal("modalSubirDocxFinal")} />}
      {modal === "modalSubirDocxFinal" && <SubirDocx data={data} run={run} close={close} />}
      {modal === "caratularExpediente" && <Caratular data={data} run={run} close={close} errors={errors} />}
      {expediente && <ExpedienteModal data={data} toast={setToast} close={() => setExpediente(false)} onSaved={() => reload()} />}
    </>
  );
}
