/* eslint-disable react-refresh/only-export-components -- the field pieces, their validators and the form rules of the Dispositivos form live together. */
import { useState, type ReactNode } from "react";
import { internal, record, text } from "./cdfFrame";

/**
 * Pieces of `dispositivos_form.html`: the crispy field (`as_crispy_field`), the check-box groups, the
 * document slots and the rules of `dispositivoFormModerno.js` that do not touch the DOM.
 */
export type Choice = { value: string; label: string };
export type FieldError = { message: string; code: string };
export type Campo = {
  name: string; label: string; required: boolean; help_text: string; attrs: Record<string, string>; errors: FieldError[];
  widget: string; value: string; choices?: Choice[];
};
export type Grupo = {
  name: string; label: string; required: boolean; help_text: string; errors: string[];
  options: { id: string; value: string; label: string; checked: boolean }[];
};
export type Archivo = { name: string; accept: string; saved: null | { full_name: string; label: string; url: string; pdf: boolean } };

const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
export const campoValid = (f: unknown): f is Campo => record(f) && ["name", "label", "help_text", "widget", "value"].every((k) => text(f[k])) &&
  typeof f.required === "boolean" && record(f.attrs) && Object.values(f.attrs).every(text) &&
  Array.isArray(f.errors) && f.errors.every((e) => record(e) && text(e.message) && text(e.code)) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));
export const grupoValid = (g: unknown): g is Grupo => record(g) && ["name", "label", "help_text"].every((k) => text(g[k])) && typeof g.required === "boolean" &&
  strings(g.errors) && Array.isArray(g.options) && g.options.every((o) => record(o) && text(o.id) && text(o.value) && text(o.label) && typeof o.checked === "boolean");
export const archivoValid = (a: unknown): a is Archivo => record(a) && text(a.name) && text(a.accept) &&
  (a.saved === null || (record(a.saved) && text(a.saved.full_name) && text(a.saved.label) && internal(a.saved.url) && typeof a.saved.pdf === "boolean"));

/** The HTML attributes the server projects are lower case; React names them in camel case. */
const REACT_ATTR: Record<string, string> = { maxlength: "maxLength", minlength: "minLength", inputmode: "inputMode" };
const reactAttrs = (attrs: Record<string, string>) => Object.fromEntries(Object.entries(attrs).map(([k, v]) => [REACT_ATTR[k] ?? k, v]));
const INPUT_CLASS: Record<string, string> = { text: "textinput", email: "emailinput", number: "numberinput" };

function Feedback({ id, errors, help }: { id: string; errors: FieldError[]; help: string }) {
  return (
    <>
      {errors.length > 0 && (
        <div id={`${id}_error`} className="invalid-feedback">
          {errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e.message}</strong></p>)}
        </div>
      )}
      {help && <div id={`${id}_helptext`} className="form-text">{help}</div>}
    </>
  );
}

/** One `{{ form.x|as_crispy_field }}`; `options`/`value`/`onChange` make a select controlled (the geography lists). */
export function Field({ f, tooltip, options, value, onChange }: {
  f: Campo; tooltip?: ReactNode; options?: Choice[]; value?: string; onChange?: (value: string) => void;
}) {
  const id = `id_${f.name}`;
  const bad = f.errors.length > 0;
  const common = {
    name: f.name, id, required: f.required || undefined, "aria-invalid": bad ? ("true" as const) : undefined,
    "aria-describedby": [f.help_text && `${id}_helptext`, bad && `${id}_error`].filter(Boolean).join(" ") || undefined,
  };
  const invalid = bad ? " is-invalid" : "";
  let control: ReactNode;
  if (f.widget === "select") {
    const choices = options ?? f.choices ?? [];
    const own = onChange ? { value: value ?? "", onChange: (e: { target: { value: string } }) => onChange(e.target.value) } : { defaultValue: f.value };
    control = <select {...common} {...own} className={`form-select${invalid}`}>{choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select>;
  } else if (f.widget === "textarea") {
    control = <textarea {...common} cols={40} rows={10} className={`form-control textarea${invalid}`} defaultValue={f.value} />;
  } else {
    control = <input type={f.widget} {...common} {...reactAttrs(f.attrs)} className={`form-control ${INPUT_CLASS[f.widget] ?? "textinput"}${invalid}`} defaultValue={f.value} />;
  }
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${f.required ? " requiredField" : ""}`}>
        {f.label}{f.required && <span className="asteriskField">*</span>}{tooltip}
      </label>
      {control}
      <Feedback id={id} errors={f.errors} help={f.help_text} />
    </div>
  );
}

/** A `CheckboxSelectMultiple` as crispy draws it: fieldset, legend and one `form-check` per option. */
export function Multi({ g }: { g: Grupo }) {
  const id = `id_${g.name}`;
  const bad = g.errors.length > 0;
  return (
    <div id={`div_${id}`} className="mb-3">
      <fieldset aria-describedby={g.help_text ? `${id}_helptext` : undefined}>
        <legend className={`form-label${g.required ? " requiredField" : ""} fs-6`}>{g.label}{g.required && <span className="asteriskField">*</span>}</legend>
        <div>
          {g.options.map((o) => (
            <div className="form-check" key={o.id}>
              <input type="checkbox" className={`form-check-input${bad ? " is-invalid" : ""}`} name={g.name} value={o.value} id={o.id} defaultChecked={o.checked} />{" "}
              <label htmlFor={o.id} className="form-check-label">{o.label}</label>
            </div>
          ))}
        </div>
        {bad && <div id={`${id}_error`} className="invalid-feedback d-block">{g.errors.map((e, i) => <p key={i}><strong>{e}</strong></p>)}</div>}
        {g.help_text && <div id={`${id}_helptext`} className="form-text">{g.help_text}</div>}
      </fieldset>
    </div>
  );
}

export const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

/** `doc-slot`: the saved file, the hidden Django widget, the upload label and the pending preview. */
export function DocSlot({ file, title, icon, hidden, onChanged }: { file: Archivo; title: string; icon: string; hidden: boolean; onChanged: () => void }) {
  const [cleared, setCleared] = useState(false);
  const [preview, setPreview] = useState<{ name: string; size: string; icon: string } | null>(null);
  const id = `id_${file.name}`;
  const toggle = () => setCleared((c) => !c);
  function chosen(input: HTMLInputElement) {
    const picked = input.files?.[0];
    if (!picked) { setPreview(null); return; }
    const ext = picked.name.split(".").pop()?.toLowerCase() ?? "";
    const kind = ext === "pdf" ? "fas fa-file-pdf doc-icon-pdf" : ["jpg", "jpeg", "png"].includes(ext) ? "fas fa-file-image doc-icon-img" : "fas fa-file-alt doc-icon-other";
    setPreview({ name: picked.name, size: formatFileSize(picked.size), icon: kind });
  }
  return (
    <div className={`doc-slot${hidden ? " d-none" : ""}`} data-field={file.name}>
      <div className="doc-slot-header"><i className={icon} /> {title}</div>
      <div className="doc-widget-hidden">
        {file.saved && (
          <>
            Actualmente: <a href={file.saved.url}>{file.saved.full_name}</a>{" "}
            <input type="checkbox" name={`${file.name}-clear`} id={`${file.name}-clear_id`} checked={cleared} onChange={toggle} />{" "}
            <label htmlFor={`${file.name}-clear_id`}>Eliminar</label><br />
            Modificar:{" "}
          </>
        )}
        <input type="file" name={file.name} accept={file.accept} className="form-control" aria-describedby={`${id}_helptext`} id={id}
          onChange={(e) => { chosen(e.target); onChanged(); }} />
      </div>
      {file.saved && (
        <div className="doc-existente">
          <div className="doc-file-icon"><i className={`fas ${file.saved.pdf ? "fa-file-pdf doc-icon-pdf" : "fa-file-image doc-icon-img"}`} /></div>
          <div className="doc-file-info">
            <div className="doc-file-name">{file.saved.label}</div>
            <div className="doc-file-status"><i className="fas fa-check-circle" /> Guardado</div>
          </div>
          <div className="doc-file-actions">
            <a href={file.saved.url} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-outline-secondary"><i className="fas fa-eye" /></a>{" "}
            <button type="button" className="btn btn-sm btn-outline-danger btn-eliminar-doc" data-field={file.name} onClick={toggle}><i className="fas fa-trash-alt" /></button>
          </div>
          <div className={`doc-eliminar-overlay${cleared ? "" : " d-none"}`} onClick={toggle}><i className="fas fa-trash-alt" /> Marcado para eliminar</div>
        </div>
      )}
      <div className="doc-upload-area">
        <label className="btn-subir-doc" htmlFor={id}><i className="fas fa-upload" /> {file.saved ? "Cambiar" : "Subir documento"}</label>
        <small className="doc-hint">PDF, JPG o PNG — máx. 10 MB</small>
      </div>
      <div className={`doc-preview${preview ? "" : " d-none"}`} id={`preview-${file.name}`}>
        <div className="doc-preview-icon"><i className={preview?.icon ?? "fas fa-file-alt"} /></div>
        <div className="doc-preview-info">
          <div className="doc-preview-name">{preview?.name}</div>
          <div className="doc-preview-size">{preview?.size}</div>
          <div className="doc-preview-status"><i className="fas fa-clock" /> Pendiente de guardar</div>
        </div>
        <button type="button" className="btn-quitar-preview" data-field={file.name}
          onClick={(e) => {
            const input = e.currentTarget.closest(".doc-slot")?.querySelector<HTMLInputElement>("input[type='file']");
            if (input) input.value = "";
            setPreview(null);
            onChanged();
          }}><i className="fas fa-times" /></button>
      </div>
    </div>
  );
}

// --- Progress (`updateProgress` and the `checkSection*` functions) -----------------------------------------

export const SECCIONES = ["identificacion", "caracteristicas", "poblacion", "ingreso", "servicios", "registro", "infraestructura", "articulaciones", "final"] as const;
export type SeccionId = (typeof SECCIONES)[number];
export type Estado = "complete" | "incomplete" | "empty";

const checkedCount = (name: string) => document.querySelectorAll(`[name="${name}"]:checked`).length;
const hasValue = (id: string) => {
  const el = document.getElementById(id) as HTMLInputElement | null;
  return !!(el && el.value && el.value.trim() !== "");
};
const COMPLETAS: Record<SeccionId, () => boolean> = {
  identificacion: () => hasValue("id_nombre_institucion") && hasValue("id_tipo_gestion") && hasValue("id_provincia"),
  caracteristicas: () => hasValue("id_tipo_dispositivo") && hasValue("id_modalidad_funcionamiento"),
  poblacion: () => checkedCount("poblacion_destinataria") > 0 && checkedCount("franja_etaria_destinataria") > 0,
  ingreso: () => checkedCount("modalidad_ingreso") > 0,
  servicios: () => checkedCount("servicios_brindados") > 0,
  registro: () => hasValue("id_registra_informacion_personas"),
  infraestructura: () => checkedCount("infraestructura_disponible") > 0,
  articulaciones: () => checkedCount("articulaciones_institucionales") > 0,
  final: () => hasValue("id_observaciones_adicionales"),
};

function hasSectionData(id: SeccionId): boolean {
  const section = document.getElementById(`section-${id}`);
  if (!section) return false;
  if (Array.from(section.querySelectorAll<HTMLInputElement>("input[type='checkbox']")).some((c) => c.checked)) return true;
  const inputs = section.querySelectorAll<HTMLInputElement>("input:not([type='hidden']):not([type='checkbox']), select, textarea");
  return Array.from(inputs).some((el) => el.value && el.value.trim() !== "");
}

export function readProgress(): Record<SeccionId, Estado> {
  return Object.fromEntries(SECCIONES.map((id) => [id, COMPLETAS[id]() ? "complete" : hasSectionData(id) ? "incomplete" : "empty"])) as Record<SeccionId, Estado>;
}

export const ESTADO_ICONO: Record<Estado, { icon: string; label: string }> = {
  complete: { icon: "fa-check-circle", label: "Completada" },
  incomplete: { icon: "fa-exclamation-circle", label: "Incompleta" },
  empty: { icon: "fa-circle", label: "Sin completar" },
};

// --- Conditional fields (`OTRO_MULTI_PAIRS`, `OTRO_SELECT_PAIRS`, `bindConditional`) ---------------------------

export const OTRO_MULTI: [string, string][] = [
  ["poblacion_destinataria", "poblacion_destinataria_otro"], ["modalidad_ingreso", "modalidad_ingreso_otro"],
  ["documentacion_ingreso", "documentacion_ingreso_otro"], ["requisitos_ingreso", "requisitos_ingreso_otro"],
  ["servicios_brindados", "servicios_brindados_otro"], ["tipos_actividades_formativas", "tipos_actividades_formativas_otro"],
  ["tipo_informacion_registrada", "tipo_informacion_registrada_otro"], ["infraestructura_disponible", "infraestructura_disponible_otro"],
  ["infraestructura_accesibilidad", "infraestructura_accesibilidad_otro"], ["articulaciones_institucionales", "articulaciones_institucionales_otro"],
];
export const OTRO_SELECT: [string, string, string][] = [
  ["tipo_gestion", "tipo_gestion_otra", "otra"], ["tipo_dispositivo", "tipo_dispositivo_otro", "otro"],
  ["tiempo_permanencia_promedio", "tiempo_permanencia_otro", "otro"], ["modo_registro", "modo_registro_otro", "otro"],
];
const SELECTS = [...OTRO_SELECT.map(([name]) => name), "ofrece_actividades_formativas", "registra_informacion_personas"];

/** What decides every wrapper: the value of six selects and the "otro" check of ten groups. */
export type Condicion = { selects: Record<string, string>; otro: Record<string, boolean> };

export function leerCondicion(form: HTMLFormElement): Condicion {
  const get = (name: string) => (form.elements.namedItem(name) as HTMLSelectElement | null)?.value ?? "";
  return {
    selects: Object.fromEntries(SELECTS.map((name) => [name, get(name)])),
    otro: Object.fromEntries(OTRO_MULTI.map(([lista]) => [lista, !!form.querySelector(`input[name="${lista}"][value="otro"]:checked`)])),
  };
}

/** The "otro" detail loses its text when its trigger stops showing it (`apply(true)`). */
export function limpiarOtro(target: HTMLElement, condicion: Condicion) {
  const pares: [string, string, boolean][] = [
    ...OTRO_MULTI.map(([lista, otro]) => [lista, otro, condicion.otro[lista]] as [string, string, boolean]),
    ...OTRO_SELECT.map(([select, otro, valor]) => [select, otro, condicion.selects[select] === valor] as [string, string, boolean]),
  ];
  for (const [disparador, otro, visible] of pares) {
    if (visible || (target as HTMLInputElement).name !== disparador) continue;
    const input = document.getElementById(`wrapper-${otro}`)?.querySelector<HTMLInputElement>("input[type='text'], input:not([type]), textarea");
    if (input) input.value = "";
  }
}

// --- Required-field feedback (`initializeRealTimeValidation`) -----------------------------------------------

const ENVOLTURAS = [".col-md-2", ".col-md-3", ".col-md-4", ".col-md-6", ".col-md-8", ".col-md-12", ".col-12", ".form-group"];
const envoltura = (field: HTMLElement) => ENVOLTURAS.map((s) => field.closest(s)).find(Boolean) as HTMLElement | undefined;
export function validarCampo(field: HTMLInputElement) {
  const wrapper = envoltura(field);
  if (!wrapper || !field.hasAttribute("required") || field.disabled) return;
  wrapper.classList.remove("field-validated", "valid", "invalid");
  wrapper.classList.add("field-validated", field.value && field.value.trim() ? "valid" : "invalid");
}
export const esValidado = (field: HTMLElement) => !!envoltura(field)?.classList.contains("field-validated");

export const SOLO_NUMEROS = ["id_cuit_institucion", "id_responsable_dni", "id_telefono_prefijo", "id_telefono_numero"];
