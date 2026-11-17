import { useCallback, useEffect, useState, type ReactNode } from "react";
import { NativeModal } from "./nativeParity";
import { CsrfInput, type Field } from "./vatFormShared";
import { MODAL_CONTROLS, ModalControl, SubmitButton, useModalClass, useModalForm, type Plan } from "./vatCentrosDetalleModales";

/**
 * `#modalCurso` (with the plan selector `#modalPlanCurricularSelector`) and `#modalComisionCurso` of
 * `vat/centros/partials/centro_cursos_panel.html`, opened from the "Agregar curso" button and the edit buttons of the rows.
 * The values of an edit come from the row (the native `data-*` attributes); the POST goes to the native update views.
 */
export type CursoEdicion = { plan_estudio: string; nombre: string; tipo: string[]; estado: string; inscripcion_libre: boolean; observaciones: string; guardar: string };
export type ComisionEdicion = {
  curso: string; curso_nombre: string; ubicacion: string; cupo_total: string; acepta_lista_espera: boolean; cupo_lista_espera: string;
  fecha_inicio: string; fecha_fin: string; estado: string; observaciones: string; guardar: string;
};

const withValues = (fields: Field[], values: Record<string, string | boolean>): Field[] => fields.map((f) => (f.name in values ? { ...f, value: values[f.name] } : f));
const find = (fields: Field[], name: string) => fields.find((f) => f.name === name) as Field;
const required = (f: Field) => (f as Field & { required?: boolean }).required === true;
const Required = ({ f }: { f: Field }) => (required(f) ? <>{" "}<span className="text-danger">*</span></> : null);
const Feedback = ({ error }: { error?: string }) => (error !== undefined ? <div className="invalid-feedback d-block">{error}</div> : null);
const Close = ({ close, className = "btn-close" }: { close: () => void; className?: string }) => <button type="button" className={className} aria-label="Close" onClick={close} />;

function PlanSelector({ planes, selected, choose, back }: { planes: Plan[]; selected: string; choose: (id: string) => void; back: () => void }) {
  const [search, setSearch] = useState("");
  useModalClass("modalPlanCurricularSelector", "vat-ui-modal");
  // `shown.bs.modal` focuses the search field; the curso modal hid at the same time, so Bootstrap's late cleanup leaves `<body>` without `modal-open`.
  useEffect(() => {
    document.body.classList.remove("modal-open");
    document.getElementById("planCurricularSelectorSearch")?.focus();
  }, []);
  const normal = (v: string) => v.toString().trim().toLowerCase();
  const shown = planes.filter((p) => !normal(search) || [p.etiqueta, p.normativa].some((v) => normal(v).includes(normal(search))));
  return (
    <NativeModal id="modalPlanCurricularSelector" title="Seleccionar Plan Curricular" close={back} size=" modal-xl modal-dialog-scrollable" controls={MODAL_CONTROLS}>
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id="modalPlanCurricularSelectorLabel">Seleccionar Plan Curricular</h5>
          <Close close={back} />
        </div>
        <div className="modal-body">
          <div className="row g-2 align-items-end mb-3">
            <div className="col-lg-6">
              <label htmlFor="planCurricularSelectorSearch" className="form-label small fw-semibold text-uppercase mb-1" style={{ letterSpacing: ".05em" }}>Buscar</label>
              <input type="search" id="planCurricularSelectorSearch" className="form-control form-control-sm" placeholder="Buscar por plan o normativa" autoComplete="off"
                value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
          </div>
          <div className="table-responsive border rounded">
            <table className="table table-hover align-middle mb-0" id="tablaPlanCurricularSelector">
              <thead className="table-light"><tr><th>Plan Curricular</th><th>Normativa</th><th className="text-end">Acción</th></tr></thead>
              <tbody>
                {planes.length === 0 && <tr><td colSpan={3} className="text-center py-4 text-muted">No hay planes curriculares activos disponibles para este centro.</td></tr>}
                {planes.map((p) => (
                  <tr key={p.id} className={`${String(p.id) === selected ? "table-primary" : ""}${shown.includes(p) ? "" : " d-none"}`.trim() || undefined}
                    aria-selected={String(p.id) === selected} onClick={() => choose(String(p.id))}>
                    <td className="fw-semibold">{p.etiqueta}</td>
                    <td>{p.normativa || "-"}</td>
                    <td className="text-end">
                      <button type="button" className="btn btn-sm btn-outline-primary" onClick={(e) => { e.stopPropagation(); choose(String(p.id)); }}>Seleccionar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div id="planCurricularSelectorEmpty" className={`text-center py-4 text-muted${planes.length > 0 && shown.length === 0 ? "" : " d-none"}`}>
            <i className="fas fa-filter fa-2x mb-2 opacity-50" />
            <p className="mb-0">No hay planes curriculares que coincidan con los filtros.</p>
          </div>
        </div>
        <div className="modal-footer"><button type="button" className="btn btn-secondary" onClick={back}>Cerrar</button></div>
      </div>
    </NativeModal>
  );
}

/** `#modalCurso`: create (`Nuevo Curso`) or edit (`Editar Curso`) with the plan selector, the tipo counter and the course fields. */
export function CursoModal({ fields, planes, edicion, endpoint, close, onSaved }: {
  fields: Field[]; planes: Plan[]; edicion: CursoEdicion | null; endpoint: string; close: () => void; onSaved: () => void;
}) {
  const initial = edicion
    ? withValues(fields, { plan_estudio: edicion.plan_estudio, nombre: edicion.nombre, tipo: edicion.tipo.join(","), estado: edicion.estado, inscripcion_libre: edicion.inscripcion_libre, observaciones: edicion.observaciones })
    : fields;
  const form = useModalForm({ fields: initial, endpoint, rejection: edicion ? "No se pudo actualizar el curso. Revisa los datos e intenta nuevamente." : "No se pudo guardar el curso. Revisa los datos e intenta nuevamente.", onSaved: () => { close(); onSaved(); } });
  const [choosing, setChoosing] = useState(false);
  const [dropdownParent, setDropdownParent] = useState<HTMLElement | null>(null);
  // `data-dropdown-parent="#modalCurso"`: the tipo results list lives inside the modal element.
  const backToCurso = useCallback(() => setChoosing(false), [setChoosing]);
  const hostModal = useCallback((node: HTMLElement | null) => setDropdownParent(node?.closest<HTMLElement>(".modal") ?? null), [setDropdownParent]);
  const [plan, nombre, tipo, estado, libre, observaciones] = ["plan_estudio", "nombre", "tipo", "estado", "inscripcion_libre", "observaciones"].map((n) => find(initial, n));
  const planValue = String(form.state.plan_estudio ?? "");
  const planLabel = plan.choices.find((c) => c.value && c.value === planValue)?.label.trim() ?? "";
  const selectedCount = String(form.state.tipo ?? "").split(",").filter(Boolean).length;
  const title = edicion ? "Editar Curso" : "Nuevo Curso";
  if (choosing) return <PlanSelector planes={planes} selected={planValue} choose={(id) => { form.set("plan_estudio", id); setChoosing(false); }} back={backToCurso} />;
  const row = (children: ReactNode, className = "col-12 mb-3") => <div className={className}>{children}</div>;
  return (
    <NativeModal id="modalCurso" title={title} close={close} busy={form.busy} size=" sisoc-curso-modal-dialog modal-dialog-centered" controls={MODAL_CONTROLS}>
      <div className="modal-content sisoc-curso-modal-content" ref={hostModal}>
        <div className="modal-header sisoc-curso-modal-header">
          <h5 className="modal-title" id="modalCursoLabel"><i className="fas fa-book" /><span id="modalCursoLabelText">{title}</span></h5>
          <Close close={close} className="btn-close sisoc-curso-close" />
        </div>
        <form id="formCurso" method="post" onSubmit={(e) => void form.submit(e)}>
          <CsrfInput />
          <div className="modal-body sisoc-curso-modal-body">
            <div id="planEstudioSeleccionadoInfo" className={`alert alert-info${planLabel ? "" : " d-none"}`} role="status" aria-live="polite">
              {planLabel ? `Plan curricular seleccionado: ${planLabel}` : ""}
            </div>
            <div className="row">
              {row(<>
                <label htmlFor="openPlanCurricularSelector" className="form-label sisoc-curso-label">Plan curricular<Required f={plan} /></label>
                <div className="d-none">
                  <select name={plan.name} id={plan.id} className={plan.attrs.class} required={required(plan)} value={planValue} onChange={(e) => form.set("plan_estudio", e.target.value)}>
                    {plan.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                  <Feedback error={form.errors.plan_estudio} />
                </div>
                <button type="button" id="openPlanCurricularSelector" className="sisoc-curso-select-trigger" onClick={() => setChoosing(true)}>
                  <span id="planCurricularSelectorButtonLabel">{planLabel ? "Cambiar plan curricular" : "Seleccionar plan curricular"}</span>
                  <i className="fas fa-chevron-down" />
                </button>
                <div id="planCurricularSelectorSummary" className={`sisoc-curso-summary${planLabel ? "" : " text-muted"}`}>{planLabel || "No hay plan curricular seleccionado."}</div>
                {plan.help_text ? <div className="form-text sisoc-curso-help">{plan.help_text}</div> : null}
              </>)}
              {row(<>
                <label htmlFor={nombre.id} className="form-label sisoc-curso-label">Nombre del curso<Required f={nombre} /></label>
                <ModalControl f={nombre} state={form.state} set={form.set} invalid={form.errors.nombre !== undefined} />
                <Feedback error={form.errors.nombre} />
              </>)}
              {row(<>
                <div className="sisoc-curso-vouchers-head">
                  <label htmlFor={tipo.id} className="form-label sisoc-curso-label mb-0">{tipo.label}<Required f={tipo} /></label>
                  <span className={`sisoc-curso-voucher-counter${selectedCount > 0 ? " is-active" : ""}`} data-voucher-counter="tipo">
                    <i className="fas fa-ticket-alt" />{" "}<span data-voucher-counter-value="tipo">{selectedCount}</span>{" "}<span className="sisoc-curso-voucher-counter-label">seleccionados</span>
                  </span>
                </div>
                <ModalControl f={tipo} state={form.state} set={form.set} invalid={form.errors.tipo !== undefined} dropdownParent={dropdownParent} />
                <Feedback error={form.errors.tipo} />
                {tipo.help_text ? <div className="form-text sisoc-curso-help">{tipo.help_text}</div> : null}
              </>, "col-12 mb-3 sisoc-curso-vouchers sisoc-curso-tipo")}
              {row(<>
                <label htmlFor={estado.id} className="form-label sisoc-curso-label">Estado<Required f={estado} /></label>
                <ModalControl f={estado} state={form.state} set={form.set} invalid={form.errors.estado !== undefined} />
                <Feedback error={form.errors.estado} />
              </>)}
              {row(<label className="sisoc-curso-check" htmlFor={libre.id}>
                <ModalControl f={libre} state={form.state} set={form.set} invalid={form.errors.inscripcion_libre !== undefined} />{" "}<span>Inscripcion libre</span>
                <Feedback error={form.errors.inscripcion_libre} />
              </label>, "col-12 mb-3 sisoc-curso-check-row")}
              {row(<>
                <label htmlFor={observaciones.id} className="form-label sisoc-curso-label">{observaciones.label}<Required f={observaciones} /></label>
                <ModalControl f={observaciones} state={form.state} set={form.set} invalid={form.errors.observaciones !== undefined} />
                <Feedback error={form.errors.observaciones} />
              </>)}
            </div>
          </div>
          <div className="modal-footer sisoc-curso-modal-footer">
            <button type="button" className="sisoc-curso-submit sisoc-curso-submit--secondary" onClick={close}>Cancelar</button>
            <SubmitButton busy={form.busy} className="sisoc-curso-submit sisoc-curso-submit--primary" id="cursoPrimarySubmitBtn">{edicion ? "Actualizar" : "Guardar"}</SubmitButton>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

/** `#modalComisionCurso` in edit mode: the course is shown as a note, the waitlist capacity follows its toggle and the dates validate. */
export function ComisionCursoModal({ fields, edicion, close, onSaved }: { fields: Field[]; edicion: ComisionEdicion; close: () => void; onSaved: () => void }) {
  const initial = withValues(fields, {
    curso: edicion.curso, ubicacion: edicion.ubicacion, cupo_total: edicion.cupo_total, acepta_lista_espera: edicion.acepta_lista_espera, cupo_lista_espera: edicion.cupo_lista_espera,
    fecha_inicio: edicion.fecha_inicio, fecha_fin: edicion.fecha_fin, estado: edicion.estado, observaciones: edicion.observaciones,
  });
  const form = useModalForm({ fields: initial, endpoint: edicion.guardar, rejection: "No se pudo actualizar la comision. Revisa los datos e intenta nuevamente.", onSaved: () => { close(); onSaved(); } });
  useModalClass("modalComisionCurso", "vat-ui-modal");
  const waitlist = form.state.acepta_lista_espera === true;
  const inicio = String(form.state.fecha_inicio ?? "");
  const fin = String(form.state.fecha_fin ?? "");
  // `updateComisionCursoDateValidation`: the end date cannot precede the start date.
  useEffect(() => {
    const input = document.getElementById("id_fecha_fin") as HTMLInputElement | null;
    input?.setCustomValidity(inicio && fin && fin < inicio ? "La fecha de fin debe ser mayor o igual a la fecha de inicio." : "");
  }, [inicio, fin]);
  // `syncWaitlistCapacity`: the capacity is cleared when the waitlist is off.
  const { set } = form;
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const setValue = (name: string, value: string | boolean) => {
    setTouched((t) => new Set(t).add(name));
    set(name, value);
    if (name === "acepta_lista_espera" && value !== true) set("cupo_lista_espera", "");
  };
  const control = (f: Field) => {
    const props = f.name === "fecha_fin" ? { ...f, attrs: { ...f.attrs, min: inicio } } : f.name === "cupo_lista_espera" ? { ...f, attrs: { ...f.attrs, ...(waitlist ? { required: "required" } : {}) } } : f;
    // `setFormValue` assigns `select.value` without refreshing the select2 box: curso and ubicación show their placeholder until they are changed.
    // The ubicación select is never turned into a select2 by the native script: it stays a plain select showing the value.
    const stale = f.name === "curso" && !touched.has(f.name);
    return <ModalControl f={props} state={form.state} set={setValue} invalid={form.errors[f.name] !== undefined} placeholderOnly={stale} plainSelect={f.name === "ubicacion"} />;
  };
  const help = (f: Field) => (f.help_text ? <div className="form-text">{f.help_text}</div> : null);
  return (
    <NativeModal id="modalComisionCurso" title="Editar Comision de Curso" close={close} busy={form.busy} size=" modal-lg" controls={MODAL_CONTROLS}>
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id="modalComisionCursoLabel">Editar Comision de Curso</h5>
          <Close close={close} />
        </div>
        <form id="formComisionCurso" method="post" onSubmit={(e) => void form.submit(e)}>
          <CsrfInput />
          <div className="modal-body">
            <div className="alert alert-light border small mb-3" id="cursoSeleccionadoInfo">Curso seleccionado: {edicion.curso_nombre}</div>
            <div className="row">
              {initial.map((f) => {
                const error = form.errors[f.name];
                if (f.name === "acepta_lista_espera") {
                  return (
                    <div key={f.name} className="col-md-6 mb-3">
                      <div className="form-check mt-4 pt-2">
                        {control(f)}{" "}<label htmlFor={f.id} className="form-check-label fw-bold">{f.label}</label>
                      </div>
                      <Feedback error={error} />{help(f)}
                    </div>
                  );
                }
                if (f.name === "cupo_lista_espera") {
                  return (
                    <div key={f.name} className={`col-md-6 mb-3${waitlist || f.value ? "" : " d-none"}`} data-waitlist-capacity-wrapper>
                      <label htmlFor={f.id} className="form-label fw-bold">{f.label}{" "}<span className={`text-danger${waitlist ? "" : " d-none"}`} data-waitlist-required-mark>*</span></label>
                      {control(f)}<Feedback error={error} />{help(f)}
                    </div>
                  );
                }
                return (
                  <div key={f.name} className="col-md-6 mb-3">
                    <label htmlFor={f.id} className="form-label fw-bold">{f.label}<Required f={f} /></label>
                    {control(f)}<Feedback error={error} />{help(f)}
                  </div>
                );
              })}
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <SubmitButton busy={form.busy} className="btn btn-primary">Actualizar</SubmitButton>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}
