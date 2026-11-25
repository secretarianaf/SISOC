/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { safeInternalPath } from "../webAccess";
import { DestinatariosPanel, type FilterConfig, type Selected } from "./comunicadosDestinatarios";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { resetAfterRejectedPost } from "./nativeParity";

/**
 * CM02.02 create and edit form: `comunicado_form.html` with `comunicadosForm.js`.
 * GET `/api/web/comedores/comunicados/crear/` or `<id>/editar/` returns what the native form renders;
 * the POST is multipart with the native field names (`comedores` and `organizaciones` as one CSV, the
 * attachments formset management form) and runs the native view. A 400 returns the bound form.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Choice = { value: string; label: string };
type Field = { value: string | boolean | string[]; required: boolean; hidden: boolean; errors: string[]; choices?: Choice[]; max_length?: number };
type Existing = { nombre_original: string; url: string; hidden: { name: string; value: string }[]; delete: { name: string; id: string; checked: boolean } };
export type ComunicadoFormData = {
  title: string; is_edit: boolean; es_tecnico: boolean;
  fields: Record<"tipo" | "subtipo" | "fecha_vencimiento" | "destacado" | "para_todos_comedores" | "comedores" | "organizaciones" | "titulo" | "cuerpo", Field>;
  formset: { prefix: string; has_forms: boolean; management: Record<string, string>; existing: Existing[] };
  info: { estado: string; estado_label: string; fecha_creacion: string; creador: string } | null;
  filters_config: Record<string, FilterConfig>; seleccionados: Record<string, Selected[]>;
  max_adjunto_bytes: number; extensiones: string[]; messages?: Message[];
};

const API = "web/comedores/comunicados/";
const GESTION = "/comunicados/gestion/";
const FIELD_NAMES = ["tipo", "subtipo", "fecha_vencimiento", "destacado", "para_todos_comedores", "comedores", "organizaciones", "titulo", "cuerpo"] as const;
const MANAGEMENT = ["TOTAL_FORMS", "INITIAL_FORMS", "MIN_NUM_FORMS", "MAX_NUM_FORMS"];
const UNCERTAIN = "No se pudo confirmar el resultado. Revise la gestión de comunicados antes de volver a guardar.";
const LEVELS = ["success", "error", "warning", "info"];

const fieldValid = (f: unknown) => record(f) && (text(f.value) || typeof f.value === "boolean" || (Array.isArray(f.value) && f.value.every(text))) &&
  typeof f.required === "boolean" && typeof f.hidden === "boolean" && Array.isArray(f.errors) && f.errors.every(text) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));

export function formValid(v: unknown): v is ComunicadoFormData {
  if (!record(v) || !record(v.fields) || !record(v.formset) || !record(v.filters_config) || !record(v.seleccionados)) return false;
  const set = v.formset;
  return text(v.title) && typeof v.is_edit === "boolean" && typeof v.es_tecnico === "boolean" &&
    FIELD_NAMES.every((n) => fieldValid((v.fields as Record<string, unknown>)[n])) &&
    text(set.prefix) && typeof set.has_forms === "boolean" && record(set.management) && MANAGEMENT.every((n) => text(set.management && (set.management as Record<string, unknown>)[n])) &&
    Array.isArray(set.existing) && set.existing.every((e) => record(e) && text(e.nombre_original) && text(e.url) && Array.isArray(e.hidden) &&
      e.hidden.every((h) => record(h) && text(h.name) && text(h.value)) && record(e.delete) && text(e.delete.name) && text(e.delete.id) && typeof e.delete.checked === "boolean") &&
    (v.info === null || (record(v.info) && text(v.info.estado) && text(v.info.estado_label) && text(v.info.fecha_creacion) && text(v.info.creador))) &&
    ["comedores", "organizaciones"].every((u) => Array.isArray((v.seleccionados as Record<string, unknown>)[u])) &&
    (v.messages === undefined || (Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string))));
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const comunicadosFormNavigation = { assign: (to: string) => window.location.assign(to) };

type Values = Record<(typeof FIELD_NAMES)[number], string | boolean>;
const first = (f: Field) => f.errors[0];
const FieldError = ({ field }: { field: Field }) => (first(field) ? <div className="invalid-feedback d-block">{first(field)}</div> : null);

function formatSize(bytes: number) {
  if (bytes === 0) return "0 B";
  const sizes = ["B", "KB", "MB", "GB"], i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${parseFloat((bytes / 1024 ** i).toFixed(1))} ${sizes[i]}`;
}

function fileIcon(file: File) {
  if (file.type.startsWith("image/")) return "fas fa-file-image";
  if (file.type.includes("pdf")) return "fas fa-file-pdf";
  if (file.type.includes("word") || file.name.endsWith(".doc") || file.name.endsWith(".docx")) return "fas fa-file-word";
  if (file.type.includes("excel") || file.name.endsWith(".xls") || file.name.endsWith(".xlsx")) return "fas fa-file-excel";
  return "fas fa-file";
}

const initialValues = (data: ComunicadoFormData): Values => {
  const f = data.fields;
  const tipo = String(f.tipo.value);
  return {
    tipo, subtipo: tipo === "externo" ? String(f.subtipo.value) : "", fecha_vencimiento: String(f.fecha_vencimiento.value),
    destacado: f.destacado.hidden ? String(f.destacado.value) : Boolean(f.destacado.value), para_todos_comedores: Boolean(f.para_todos_comedores.value),
    comedores: "", organizaciones: "", titulo: String(f.titulo.value), cuerpo: String(f.cuerpo.value),
  };
};

const Panel = ({ icon, label, id, hidden, children }: { icon: string; label: string; id?: string; hidden?: boolean; children: ReactNode }) => (
  <div id={id} className={`editor-panel${hidden ? " d-none" : ""}`}>
    <div className="panel-label"><i className={icon} />{" "}{label}</div>
    <div className="panel-body">{children}</div>
  </div>
);

export function ComunicadoFormContent({ initial, endpoint, onMessages }: { initial: ComunicadoFormData; endpoint: string; onMessages?: (m: Message[]) => void }) {
  const [data, setData] = useState(initial);
  const [revision, setRevision] = useState(0);
  const [values, setValues] = useState(() => initialValues(initial));
  const [files, setFiles] = useState<File[]>([]);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const picker = useRef<HTMLInputElement>(null);
  const f = data.fields;
  const externo = values.tipo === "externo";
  const subtipo = String(values.subtipo);
  const set = (name: keyof Values, value: string | boolean) => setValues((v) => ({ ...v, [name]: value }));
  const tipoField = f.tipo, subtipoField = f.subtipo;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new FormData(event.currentTarget);
    body.delete("archivos_adjuntos");
    files.forEach((file) => body.append("archivos_adjuntos", file));
    let outcome: { kind: "redirect"; to: string } | { kind: "invalid"; data: unknown } | { kind: "uncertain" } = { kind: "uncertain" };
    try {
      const { data: response, status } = await webClient.post(endpoint, body, { validateStatus: (s) => (s >= 200 && s < 300) || s === 400 || s === 403 });
      if (status === 403) { onMessages?.([{ message: record(response) && text(response.detail) ? response.detail : UNCERTAIN, level: "error" }]); busy.current = false; setPending(false); return; }
      if (status === 400) outcome = { kind: "invalid", data: response };
      else if (record(response) && response.ok === true && internal(response.redirect) && safeInternalPath(response.redirect) === response.redirect) outcome = { kind: "redirect", to: response.redirect };
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    if (outcome.kind === "redirect") { comunicadosFormNavigation.assign(outcome.to); return; }
    if (outcome.kind === "invalid" && formValid(outcome.data)) {
      setData(outcome.data); setValues(initialValues(outcome.data)); setRevision((r) => r + 1);
      resetAfterRejectedPost();
    } else setUncertain(true);
    busy.current = false; setPending(false);
  }

  const switchField = (name: "destacado" | "para_todos_comedores") => (
    <input type="checkbox" name={name} className="form-check-input" role="switch" id={`id_${name}`} checked={Boolean(values[name])} onChange={(e) => set(name, e.target.checked)} />
  );

  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comunicadoForm.css" />
      <div className="comunicado-editor">
        <form method="post" encType="multipart/form-data" onSubmit={submit} key={revision}>
          <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
          <Panel icon="fas fa-sliders-h" label="Configuración">
            <div className="options-row">
              <div className="option-item">
                <label htmlFor="id_tipo">Tipo de Comunicado</label>
                <select name="tipo" className="form-select" id="id_tipo" required={tipoField.required} value={String(values.tipo)}
                  onChange={(e) => setValues((v) => ({ ...v, tipo: e.target.value, subtipo: e.target.value === "externo" ? v.subtipo : "" }))}>
                  {(tipoField.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <FieldError field={tipoField} />
                <small className="form-text">Interna: SISOC &middot; Externa: App móvil (PWA)</small>
              </div>
              <div id="subtipo-options" className={`option-item${externo ? "" : " d-none"}`}>
                <label htmlFor="id_subtipo">Subtipo</label>
                <select name="subtipo" className="form-select" id="id_subtipo" required={subtipoField.required} value={subtipo} onChange={(e) => set("subtipo", e.target.value)}>
                  {(subtipoField.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <FieldError field={subtipoField} />
                <small className="form-text">Institucional: broadcast &middot; Comedores: dirigido</small>
              </div>
              <div className="option-item">
                <label htmlFor="id_fecha_vencimiento">Vencimiento</label>
                <input type="datetime-local" name="fecha_vencimiento" className="form-control" id="id_fecha_vencimiento" value={String(values.fecha_vencimiento)} onChange={(e) => set("fecha_vencimiento", e.target.value)} />
                <FieldError field={f.fecha_vencimiento} />
                <small className="form-text">Opcional. Deja de mostrarse en esa fecha.</small>
              </div>
            </div>
            <div id="destacado-option" className={`mt-3${externo ? " d-none" : ""}`}>
              <div className="form-check form-switch" style={{ display: "flex", alignItems: "center" }}>
                {f.destacado.hidden ? <input type="hidden" name="destacado" id="id_destacado" value={String(values.destacado)} /> : switchField("destacado")}
                <label className="form-check-label" htmlFor="id_destacado" style={{ marginBottom: 0 }}><i className="fas fa-star text-warning" />{" "}Marcar como Destacado</label>
              </div>
              <small className="form-text">Aparece fijado arriba de la lista.</small>
            </div>
          </Panel>
          <Panel icon="fas fa-utensils" label="Destinatarios" id="comedores-options" hidden={!(externo && subtipo === "comedores")}>
            <div className="mb-3">
              <div className="form-check form-switch" style={{ display: "flex", alignItems: "center" }}>
                {switchField("para_todos_comedores")}
                <label className="form-check-label" htmlFor="id_para_todos_comedores" style={{ marginBottom: 0 }}>Enviar a todos los comedores</label>
              </div>
              <small className="form-text">Se enviará a todos los comedores que tiene asignados.</small>
            </div>
            <div id="comedores-selector" className={values.para_todos_comedores ? "d-none" : ""}>
              <DestinatariosPanel key={`c${revision}`} universo="comedores" config={data.filters_config.comedores ?? {}} initial={data.seleccionados.comedores} errors={f.comedores.errors} />
            </div>
          </Panel>
          <Panel icon="fas fa-building" label="Destinatarios" id="organizaciones-options" hidden={!(externo && subtipo === "organizaciones")}>
            <DestinatariosPanel key={`o${revision}`} universo="organizaciones" config={data.filters_config.organizaciones ?? {}} initial={data.seleccionados.organizaciones} errors={f.organizaciones.errors} />
          </Panel>
          <Panel icon="fas fa-pen" label="Redacción">
            <div className="mb-3">
              <label htmlFor="id_titulo">Título{" "}<span className="text-danger">*</span></label>
              <input type="text" name="titulo" maxLength={f.titulo.max_length} className="form-control" required={f.titulo.required} id="id_titulo" value={String(values.titulo)} onChange={(e) => set("titulo", e.target.value)} />
              <FieldError field={f.titulo} />
            </div>
            <div className="mb-0">
              <label htmlFor="id_cuerpo">Contenido{" "}<span className="text-danger">*</span></label>
              <textarea name="cuerpo" cols={40} rows={6} className="form-control" required={f.cuerpo.required} id="id_cuerpo" value={String(values.cuerpo)} onChange={(e) => set("cuerpo", e.target.value)} />
              <FieldError field={f.cuerpo} />
            </div>
          </Panel>
          <Panel icon="fas fa-paperclip" label="Archivos Adjuntos">
            <input type="file" name="archivos_adjuntos" id="archivosInput" className="d-none" accept={data.extensiones.join(",")} multiple ref={picker}
              onChange={(e) => { setFiles((all) => [...all, ...Array.from(e.target.files ?? [])]); e.target.value = ""; }} />
            <div className="d-flex align-items-center gap-3">
              <button type="button" id="addFilesBtn" className="btn-add-files" onClick={() => picker.current?.click()}><i className="fas fa-plus me-1" />{" "}Agregar archivos</button>
              <div id="selectedFilesInfo" className={files.length ? "" : "d-none"}><span className="badge files-badge"><span id="fileCount">{files.length}</span>{" "}archivo(s)</span></div>
            </div>
            <small className="form-text d-block mt-2">Puedes agregar múltiples archivos haciendo clic varias veces.</small>
            <div id="filePreviewContainer" className="mt-3">
              {files.map((file, index) => (
                <div key={`${file.name}-${index}`} className="archivo-preview-item d-flex align-items-center justify-content-between p-2 mb-2 rounded">
                  <div className="d-flex align-items-center">
                    <i className={`${fileIcon(file)} me-2`} style={{ color: "#f39c12" }} />
                    <div><div className="fw-bold small">{file.name}</div><div className="small" style={{ color: "#6b7280" }}>{formatSize(file.size)}</div></div>
                  </div>
                  <button type="button" className="btn btn-sm btn-outline-danger btn-remove-file" onClick={() => setFiles((all) => all.filter((_, i) => i !== index))}><i className="fas fa-times" /></button>
                </div>
              ))}
            </div>
            {MANAGEMENT.map((n) => <input key={n} type="hidden" name={`${data.formset.prefix}-${n}`} value={data.formset.management[n]} id={`id_${data.formset.prefix}-${n}`} readOnly />)}
            {data.is_edit && data.formset.has_forms && <>
              <hr style={{ borderColor: "#374151", marginTop: "16px" }} />
              <label className="mb-2"><i className="fas fa-folder-open me-1" />{" "}Archivos actuales</label>
              <div id="adjuntos-container">
                {data.formset.existing.map((a) => (
                  <div className="adjunto-row mb-2 p-2 d-flex justify-content-between align-items-center" key={a.delete.name}>
                    <div>
                      <i className="fas fa-file me-2" style={{ color: "#f39c12" }} />{" "}
                      <a href={a.url} target="_blank">{a.nombre_original}</a>
                      {a.hidden.map((h) => <input key={h.name} type="hidden" name={h.name} value={h.value} readOnly />)}
                    </div>
                    <div className="form-check">
                      <input type="checkbox" name={a.delete.name} id={a.delete.id} defaultChecked={a.delete.checked} />{" "}
                      <label className="form-check-label" htmlFor={a.delete.id} style={{ color: "#e74c3c" }}>Eliminar</label>
                    </div>
                  </div>
                ))}
              </div>
            </>}
          </Panel>
          {data.is_edit && data.info && (
            <Panel icon="fas fa-info-circle" label="Información">
              <div className="comunicado-info">
                <div className="info-item"><strong>Estado:</strong>{" "}<EstadoBadge estado={data.info.estado} label={data.info.estado_label} /></div>
                <div className="info-item"><strong>Creado:</strong> {data.info.fecha_creacion}</div>
                <div className="info-item"><strong>Por:</strong> {data.info.creador}</div>
              </div>
            </Panel>
          )}
          {uncertain && <p role="alert" className="text-danger">{UNCERTAIN}</p>}
          <div className="editor-actions">
            <a href={GESTION} className="btn btn-cancel"><i className="fas fa-arrow-left me-1" />{" "}Cancelar</a>
            <button type="submit" className="btn btn-save" disabled={pending || uncertain}><i className="fas fa-save me-1" />{" "}Guardar Comunicado</button>
          </div>
        </form>
      </div>
    </>
  );
}

const BADGE_STYLES: Record<string, { background: string; color: string }> = {
  borrador: { background: "rgba(156,163,175,0.15)", color: "#9ca3af" },
  publicado: { background: "rgba(16,185,129,0.15)", color: "#10b981" },
  archivado: { background: "rgba(107,114,128,0.15)", color: "#6b7280" },
};
const EstadoBadge = ({ estado, label }: { estado: string; label: string }) => (BADGE_STYLES[estado] ? <span className="badge" style={BADGE_STYLES[estado]}>{label}</span> : null);

export function ComunicadoFormPage({ id }: { id?: string }) {
  const endpoint = id ? `${API}${id}/editar/` : `${API}crear/`;
  const [state] = useMainResource(endpoint, formValid);
  const [messages, setMessages] = useState<Message[]>([]);
  return renderMain(state, "Cargando comunicado…", (data) => ({
    title: data.title,
    heading: data.title,
    breadcrumb: null,
    content: <>
      <InsumosToastList messages={[...(data.messages ?? []), ...messages]} />
      <ComunicadoFormContent initial={data} endpoint={endpoint} onMessages={setMessages} />
    </>,
  }));
}
