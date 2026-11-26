/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { bool, messagesValid, vatNavigation, type Message } from "./vatShared";
import { Control, CsrfInput, Err, FORM_CSS, fieldValid, Select2Links, UNCERTAIN, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import type { RouteDefinition } from "./types";

/**
 * V05.02 course forms: `curso/curso_form.html` and `curso_confirm_delete.html` (`vat_curso_{create,update,delete}`). Data comes from
 * `/api/web/vat/cursos-formularios/`, which runs the native ModelForm and views; the POST persists through their `form_valid` /
 * `post` (message queued, native soft delete). The create URL needs `?centro=<id>` (the native `dispatch` guard answers 403 without
 * it) and React forwards it to the API.
 *
 * Kept native behaviors: the template draws only five fields, so saving resets `tipo`; «Usa voucher», the voucher parametrías and the
 * credit cost are hidden and locked by the form (a posted value is ignored) and the template prints its multi-line `{# #}` note as text; the «Guía de carga» progress counts the four key fields as
 * the template script does and its accordion opens one item at a time. The embedded variant (`?modal=1`, loaded by the native centers
 * panel in an iframe) is not a React page: the preview entry serves it natively.
 */
type Campo = Field & { required?: boolean };
export type CursoFormData = { editing: boolean; fields: Campo[]; non_field_errors: string[]; urls: { cancel: string }; messages: Message[] };
export type CursoDeleteData = { titulo: string; urls: { detail: string } };

const API = "web/vat/cursos-formularios/";
const NAMES = ["plan_estudio", "nombre", "estado", "inscripcion_libre", "observaciones"];
const KEY_FIELDS = ["plan_estudio", "nombre", "estado", "observaciones"];

export const cursoFormValid = (v: unknown): v is CursoFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) && v.fields.every(fieldValid) &&
  NAMES.join() === (v.fields as Field[]).map((f) => f.name).join() && (v.fields as { required?: unknown }[]).every((f) => bool(f.required)) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.cancel) && messagesValid(v.messages);
export const cursoDeleteValid = (v: unknown): v is CursoDeleteData => record(v) && text(v.titulo) && record(v.urls) && internal(v.urls.detail);

// The native template wraps this note in `{# ... #}`, which Django only treats as a comment on one line: it prints as text inside the form.
const NATIVE_NOTE = `{# REQ 2026-09-23: "Usa voucher" se oculta del alta y la edición
                       (docs/registro/analisis/2026-09-23-inet-quitar-usa-voucher-alta-curso.md).
                       Los campos quedan disabled+HiddenInput en el form (ver
                       _hide_and_lock_fields en VAT/forms.py) para conservar su valor
                       en la edición de un curso existente. #}`;

const GUIDE = [
  { id: "guiaNombre", title: "Nombre del curso", body: "Máximo 150 caracteres. Ejemplo recomendado: \"Programación Web Full Stack 2026\"." },
  { id: "guiaPlan", title: "Plan curricular", body: "Define modalidad, estructura pedagógica y criterios de certificación del curso." },
  { id: "guiaEstado", title: "Estado del curso", body: "Activo: visible y operativo. Planificado: pendiente de inicio. Finalizado/Cancelado: sin nuevas altas." },
];

/** «Guía de carga del curso»: the progress of the template script and the accordion of Bootstrap (one item open at a time). */
function Guide({ done }: { done: number }) {
  const [open, setOpen] = useState<string | null>(null);
  const percent = Math.round((done / KEY_FIELDS.length) * 100);
  return <div className="row mb-4"><div className="col-12"><div className="border rounded-3 p-3 bg-light-subtle">
    <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
      <h2 className="h6 mb-0">Guía de carga del curso</h2>
      <span className="small text-muted" id="cursoProgressLabel">{done} de {KEY_FIELDS.length} campos clave completados</span>
    </div>
    <div className="progress" role="progressbar" aria-label="Progreso de carga" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
      <div className="progress-bar" id="cursoProgressBar" style={{ width: `${percent}%` }} aria-valuenow={percent} />
    </div>
    <div className="accordion accordion-flush mt-3" id="cursoFormGuide">
      {GUIDE.map((g) => <div className="accordion-item" key={g.id}>
        <h3 className="accordion-header">
          <button className={`accordion-button${open === g.id ? "" : " collapsed"}`} type="button" aria-expanded={open === g.id} aria-controls={g.id}
            onClick={() => setOpen(open === g.id ? null : g.id)}>{g.title}</button>
        </h3>
        <div id={g.id} className={`accordion-collapse collapse${open === g.id ? " show" : ""}`}>
          <div className="accordion-body small text-muted">{g.body}</div>
        </div>
      </div>)}
    </div>
  </div></div></div>;
}

function CursoForm({ initial, endpoint, forbidden }: { initial: CursoFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: cursoFormValid });
  const byName = Object.fromEntries(data.fields.map((f) => [f.name, f])) as Record<string, Campo>;
  // `hasValue` of the template script: a non-empty value (text is trimmed).
  const done = KEY_FIELDS.filter((name) => String(state[name] ?? "").trim() !== "").length;
  const label = (f: Campo, star: boolean): ReactNode => <label htmlFor={f.id} className="form-label fw-600">{f.label}{star && <>{" "}<span className="text-danger">*</span></>}</label>;
  const help = (f: Campo): ReactNode => !!f.help_text && <div className="form-text text-muted mt-1">{f.help_text}</div>;
  const plan = byName.plan_estudio, nombre = byName.nombre, estado = byName.estado, libre = byName.inscripcion_libre, obs = byName.observaciones;
  return <>
    <NativeToasts messages={data.messages} />
    <Select2Links />
    <div className="container-fluid py-4">
      <div className="d-flex align-items-center gap-2 mb-4">
        <a href={data.urls.cancel} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
        <h1 className="h3 mb-0" style={{ color: "#1f3a93" }}>{data.editing ? "Editar Curso" : <><i className="bi bi-plus-circle me-2" />Nuevo Curso</>}</h1>
      </div>
      <div className="card border-0 shadow-sm"><div className="card-body p-4">
        <form method="post" noValidate onSubmit={(e) => void submit(e)}>
          <CsrfInput />
          {uncertain && <p role="alert">{UNCERTAIN}</p>}
          <Guide done={done} />
          <div className="row mb-4"><div className="col-md-6">{label(plan, false)}<Control f={plan} state={state} set={set} />{help(plan)}<Err f={plan} /></div></div>
          <div className="row mb-4"><div className="col-md-6">{label(nombre, true)}<Control f={nombre} state={state} set={set} />{help(nombre)}<Err f={nombre} /></div></div>
          <div className="row mb-4"><div className="col-md-6">{label(estado, true)}<Control f={estado} state={state} set={set} /><Err f={estado} /></div></div>
          <div className="row mb-4"><div className="col-md-3 d-flex align-items-center pt-3"><div>
            <div className="form-check form-switch">
              <Control f={libre} state={state} set={set} />{" "}
              <label className="form-check-label fw-600" htmlFor={libre.id}>{libre.label}</label>
            </div>
            {libre.help_text && <div className="form-text text-muted">{libre.help_text}</div>}
            <Err f={libre} />
          </div></div></div>
          {NATIVE_NOTE}
          <div className="row mb-4"><div className="col-md-12">
            <div className="form-text text-muted mb-2">La modalidad se toma automáticamente del plan de estudio seleccionado.</div>
            {label(obs, false)}<Control f={obs} state={state} set={set} />{help(obs)}<Err f={obs} />
          </div></div>
          <div className="d-flex justify-content-end gap-2 mt-4">
            <a href={data.urls.cancel} className="btn btn-outline-secondary">Cancelar</a>
            <button type="submit" className="btn btn-primary">{data.editing ? "Actualizar" : "Crear"}</button>
          </div>
        </form>
      </div></div>
    </div>
    <style>{FORM_CSS}</style>
  </>;
}

function FormPage({ id }: { id?: string }) {
  const endpoint = `${API}${id ? `${id}/editar/` : "nuevo/"}`;
  // The create guard reads `?centro=` from the URL, also on the POST.
  const target = id ? endpoint : `${endpoint}${window.location.search}`;
  const [state, setState] = useMainResource(target, cursoFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: data.editing ? "Editar Curso" : "Nuevo Curso", breadcrumb: null,
    content: <CursoForm initial={data} endpoint={target} forbidden={forbidden} />,
  }));
}

/** `curso/curso_confirm_delete.html`: the plain card. */
function CursoDelete({ data, endpoint, forbidden }: { data: CursoDeleteData; endpoint: string; forbidden: (d: unknown) => void }) {
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const result = await postForm(endpoint, new URLSearchParams());
    busy.current = false;
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else setUncertain(true);
  }
  return <div className="container-fluid py-4"><div className="card border-0 shadow-sm"><div className="card-body p-4">
    <h1 className="h4 mb-3">Eliminar curso</h1>
    <p>¿Seguro que querés eliminar el curso{" "}<strong>{data.titulo}</strong>?</p>
    <form method="post" onSubmit={(e) => void submit(e)}>
      <CsrfInput />
      {uncertain && <p role="alert">{UNCERTAIN}</p>}
      <div className="d-flex gap-2 justify-content-end">
        <a href={data.urls.detail} className="btn btn-outline-secondary">Cancelar</a>
        <button type="submit" className="btn btn-danger">Eliminar</button>
      </div>
    </form>
  </div></div></div>;
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, cursoDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar Curso", breadcrumb: null, content: <CursoDelete data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { mode: "nuevo" | "editar" | "eliminar"; id?: string };

// Native URLs `vat_curso_{create,update,delete}`; the detail belongs to `vatCursoDetalle.tsx` and the course commissions keep their own module.
const PATH = /^\/vat\/cursos\/(?:(nuevo)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatCursoFormRoute: RouteDefinition<Params> = {
  name: "vat-curso-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[1] ? { mode: "nuevo" } : { mode: m[3] as "editar" | "eliminar", id: m[2] };
  },
  render({ mode, id }) {
    if (mode === "eliminar") return <DeletePage key={id} id={id!} />;
    return <FormPage key={`${mode}:${id ?? ""}`} id={id} />;
  },
};
