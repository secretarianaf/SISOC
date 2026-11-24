/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useState, type ReactNode } from "react";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import Select2 from "./select2";
import { bool, messagesValid, type Message } from "./vatShared";
import { ConfirmDelete, Control, CsrfInput, Err, FORM_CSS, fieldValid, Select2Links, UNCERTAIN, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import { TourHelpInline } from "./vatTourInline";
import type { RouteDefinition } from "./types";

/**
 * V05.02 institutional offer forms: `oferta_institucional/oferta_form.html` and `oferta_confirm_delete.html`
 * (`vat_oferta_institucional_{create,update,delete}`). Data comes from `/api/web/vat/ofertas-institucionales/`, which runs the
 * native ModelForm and views; the POST persists through their `form_valid` / `post` (message queued, native soft delete).
 *
 * The inline script of the native template is reproduced: the voucher and cost columns show only with «Usa Voucher» on; turning it
 * off (and the page load with it off) resets the cost to `0` and clears the vouchers; with it on, the vouchers that belong to
 * another program than the chosen one are dropped. Kept native quirks: the title of the create form says «Nueva Oferta Materia»;
 * the native list keeps the other-program vouchers in the open dropdown as disabled rows, here they are not listed; the help
 * tour is drawn in place (the include sits inside `{% block content %}`).
 */
type Campo = Field & { required?: boolean };
export type Voucher = {
  name: string; id: string; label: string; help_text: string; attrs: Record<string, string>; errors: string[]; values: string[];
  choices: { value: string; label: string; programa_id: string }[];
};
export type OfertaFormData = {
  editing: boolean; fields: Campo[]; vouchers: Voucher; non_field_errors: string[]; urls: { list: string }; messages: Message[];
};
export type OfertaDeleteData = { titulo: string; subtitulo: string; urls: { detail: string } };

const API = "web/vat/ofertas-institucionales/";
const NAMES = ["plan_curricular", "centro", "titulo_referencia", "programa", "ciclo_lectivo", "nombre_local", "estado", "usa_voucher", "costo", "fecha_publicacion", "observaciones"];

const voucherValid = (v: unknown) => record(v) && text(v.name) && text(v.id) && text(v.label) && text(v.help_text) && record(v.attrs) && Object.values(v.attrs).every(text) &&
  Array.isArray(v.errors) && v.errors.every(text) && Array.isArray(v.values) && v.values.every(text) &&
  Array.isArray(v.choices) && v.choices.every((c) => record(c) && text(c.value) && text(c.label) && text(c.programa_id));

export const ofertaFormValid = (v: unknown): v is OfertaFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) && v.fields.every(fieldValid) &&
  NAMES.join() === (v.fields as Field[]).map((f) => f.name).join() && (v.fields as { required?: unknown }[]).every((f) => bool(f.required)) && voucherValid(v.vouchers) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.list) && messagesValid(v.messages);
export const ofertaDeleteValid = (v: unknown): v is OfertaDeleteData => record(v) && text(v.titulo) && text(v.subtitulo) && record(v.urls) && internal(v.urls.detail);

/** A select2 field of the template; the locked fields of the provincial role (`disabled`) keep their value and cannot be changed. */
function Selector({ f, state, set }: { f: Field; state: Record<string, string | boolean>; set: (name: string, value: string | boolean) => void }) {
  if (f.attrs.disabled === undefined) return <Control f={f} state={state} set={set} />;
  return <Select2 id={f.id} name={f.name} choices={f.choices} value={[String(state[f.name] ?? "")]} onChange={() => undefined} disabled
    placeholder={f.attrs["data-placeholder"]} selectClassName={f.attrs.class ?? ""} selectProps={{ required: f.attrs.required !== undefined ? true : undefined, "data-width": f.attrs["data-width"] }}
    hideEmptyChoice noResults="No results found" clearTrigger="none" focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown" />;
}

function OfertaForm({ initial, endpoint, forbidden }: { initial: OfertaFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const [vouchers, setVouchers] = useState(initial.vouchers.values);
  // `send` is read when the form is submitted: the chosen vouchers go as the repeated `voucher_parametrias` of the multiple select.
  const send = (to: string, body: URLSearchParams) => {
    for (const v of vouchers) body.append("voucher_parametrias", v);
    return postForm(to, body);
  };
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: ofertaFormValid, send });
  const byName = Object.fromEntries(data.fields.map((f) => [f.name, f])) as Record<string, Campo>;
  const usa = state.usa_voucher === true;
  const programa = String(state.programa ?? "");
  // The template script (`actualizarCosto` / `filtrarVouchersPorPrograma`) runs on load, after a rejected POST (the page reload, with the vouchers the server bound)
  // and on every toggle or program change. It is applied while rendering, so a stale value never flashes.
  const [applied, setApplied] = useState<{ usa: boolean; programa: string; data: OfertaFormData | null }>({ usa: false, programa: "", data: null });
  if (applied.data !== data || applied.usa !== usa || applied.programa !== programa) {
    setApplied({ usa, programa, data });
    const base = applied.data !== data ? data.vouchers.values : vouchers;
    const next = usa ? base.filter((id) => !programa || data.vouchers.choices.find((c) => c.value === id)?.programa_id === programa) : [];
    if (next.length !== vouchers.length || next.some((v, n) => v !== vouchers[n])) setVouchers(next);
    if (!usa && state.costo !== "0") set("costo", "0");
  }
  const required = (f: Campo): ReactNode => f.required ? <>{" "}<span className="text-danger">*</span></> : null;
  const group = (name: string, icon: string, labelRequired: boolean) => {
    const f = byName[name];
    return <>
      <label htmlFor={f.id} className="form-label fw-600">{f.label}{labelRequired && required({ ...f, required: true })}</label>
      <div className="input-group">
        <span className="input-group-text bg-light border-0"><i className={icon} style={{ color: "#1f3a93" }} /></span>
        {name === "centro" || name === "titulo_referencia" || name === "programa" ? <Selector f={f} state={state} set={set} /> : <Control f={f} state={state} set={set} />}
      </div>
      <Err f={f} />
    </>;
  };
  const switchField = byName.usa_voucher;
  const costo = byName.costo;
  const fecha = byName.fecha_publicacion;
  const obs = byName.observaciones;
  const attrs = data.vouchers.attrs;
  const visible = data.vouchers.choices.filter((c) => !programa || c.programa_id === programa);
  return <>
    <NativeToasts messages={data.messages} />
    <Select2Links />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-12">
        <div className="d-flex align-items-center gap-2 mb-4">
          <a href={data.urls.list} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
          <div>
            <h1 className="h2 mb-0" style={{ color: "#1f3a93" }}>
              {data.editing ? <><i className="bi bi-pencil-square me-2" />Editar Oferta Institucional</> : <><i className="bi bi-plus-circle me-2" />Nueva Oferta Materia</>}
            </h1>
          </div>
        </div>
      </div></div>
      <div className="row">
        <div className="col-lg-8"><div className="card border-0 shadow-sm">
          <div className="card-header bg-light border-bottom"><h5 className="mb-0"><i className="bi bi-file-earmark-text me-2" style={{ color: "#1f3a93" }} />Información General</h5></div>
          <div className="card-body p-4">
            <form method="post" noValidate onSubmit={(e) => void submit(e)}>
              <CsrfInput />
              <input type="hidden" name="plan_curricular" id={byName.plan_curricular.id} value={String(state.plan_curricular ?? "")} readOnly />
              {uncertain && <p role="alert">{UNCERTAIN}</p>}
              <div className="row mb-4">
                <div className="col-md-6">{group("centro", "bi-building", true)}</div>
                <div className="col-md-6">{group("titulo_referencia", "bi-journal-bookmark", true)}</div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{group("programa", "bi-folder", true)}</div>
                <div className="col-md-6">{group("ciclo_lectivo", "bi-calendar3", true)}</div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{group("nombre_local", "bi-type", false)}</div>
                <div className="col-md-6">{group("estado", "bi-flag", true)}</div>
              </div>
              <div className="row mb-4">
                <div className="col-md-3 d-flex align-items-center pt-3"><div>
                  <div className="form-check form-switch">
                    <Control f={switchField} state={state} set={set} />{" "}
                    <label className="form-check-label fw-600" htmlFor={switchField.id}>{switchField.label}</label>
                  </div>
                  {switchField.help_text && <div className="form-text text-muted">{switchField.help_text}</div>}
                </div></div>
                <div className="col-md-5" id="campo-vouchers" style={{ display: usa ? "block" : "none" }}>
                  <label htmlFor={data.vouchers.id} className="form-label fw-600">{data.vouchers.label}</label>
                  <Select2 id={data.vouchers.id} name={data.vouchers.name} multiple choices={visible.map((c) => ({ value: c.value, label: c.label }))} value={vouchers} onChange={setVouchers}
                    placeholder={attrs["data-placeholder"]} selectClassName={attrs.class ?? ""} selectProps={{ "data-width": attrs["data-width"], size: attrs.size ? Number(attrs.size) : undefined, style: { minHeight: "170px" } }}
                    noResults="No results found" clearTrigger="none" focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown" />
                  {data.vouchers.help_text && <div className="form-text text-muted">{data.vouchers.help_text}</div>}
                  {data.vouchers.errors.length > 0 && <div className="text-danger small mt-1">{data.vouchers.errors[0]}</div>}
                </div>
                <div className="col-md-3" id="campo-costo" style={{ display: usa ? "block" : "none" }}>
                  <label htmlFor={costo.id} className="form-label fw-600">{costo.label}</label>
                  <div className="input-group"><span className="input-group-text bg-light border-0">$</span><Control f={costo} state={state} set={set} /></div>
                  {costo.help_text && <div className="form-text text-muted">{costo.help_text}</div>}
                  <Err f={costo} />
                </div>
                <div className="col-md-4">
                  <label htmlFor={fecha.id} className="form-label fw-600">{fecha.label}</label>
                  <div className="input-group"><span className="input-group-text bg-light border-0"><i className="bi-calendar-event" style={{ color: "#1f3a93" }} /></span><Control f={fecha} state={state} set={set} /></div>
                  <Err f={fecha} />
                </div>
              </div>
              <div className="row mb-4"><div className="col-md-12">
                <label htmlFor={obs.id} className="form-label fw-600">{obs.label}</label>
                <Control f={obs} state={state} set={set} />
                <Err f={obs} />
              </div></div>
              <hr className="my-4" />
              <div className="d-flex gap-2 justify-content-end">
                <a href={data.urls.list} className="btn btn-outline-secondary"><i className="bi bi-x-lg me-2" />Cancelar</a>
                <button type="submit" className="btn btn-primary"><i className="bi bi-check-lg me-2" />{" "}{data.editing ? "Actualizar" : "Crear"}</button>
              </div>
            </form>
          </div>
        </div></div>
        <div className="col-lg-4"><div className="card border-0 shadow-sm bg-light"><div className="card-body">
          <h6 className="card-title fw-600" style={{ color: "#1f3a93" }}><i className="bi bi-info-circle me-2" />Información</h6>
          <div className="small text-muted"><p>Oferta educativa basada en un plan de estudio para un ciclo lectivo.</p></div>
        </div></div></div>
      </div>
    </div>
    <style>{FORM_CSS}</style>
    <TourHelpInline section="oferta_form" />
  </>;
}

const TITLE = (editing: boolean) => `${editing ? "Editar" : "Nueva"} Oferta Institucional`;

function FormPage({ id }: { id?: string }) {
  const endpoint = `${API}${id ? `${id}/editar/` : "nueva/"}`;
  const [state, setState] = useMainResource(id ? endpoint : `${endpoint}${window.location.search}`, ofertaFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: TITLE(data.editing), breadcrumb: null,
    content: <OfertaForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, ofertaDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar Oferta Institucional", breadcrumb: null,
    content: <ConfirmDelete title={data.titulo} subtitle={data.subtitulo} cancel={data.urls.detail} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { mode: "nueva" | "editar" | "eliminar"; id?: string };

// Native URLs `vat_oferta_institucional_{create,update,delete}`; the list and the detail belong to `vatOferta.tsx`.
const PATH = /^\/vat\/ofertas-institucionales\/(?:(nueva)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatOfertaFormRoute: RouteDefinition<Params> = {
  name: "vat-oferta-institucional-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[1] ? { mode: "nueva" } : { mode: m[3] as "editar" | "eliminar", id: m[2] };
  },
  render({ mode, id }) {
    if (mode === "eliminar") return <DeletePage key={id} id={id!} />;
    return <FormPage key={`${mode}:${id ?? ""}`} id={id} />;
  },
};
