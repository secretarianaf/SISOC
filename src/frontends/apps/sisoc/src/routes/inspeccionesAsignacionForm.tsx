import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import InspSelect2 from "./InspSelect2";
import { apiPath, client } from "./inspeccionesEscuelasApi";
import { verificarAsignacion, type AsignacionFormData, type Field } from "./inspeccionesAsignacionesApi";

/**
 * Assignment form of `inspecciones/partials/asignacion_form.html` (IN02), the same
 * in the modal and as a page. Values and errors come from the vertical's web API,
 * which runs the native `AsignacionCrearView`. The «otra visita» notice follows
 * `panel.js` (`data-insp-verificar`): it is asked on load and when the day, the
 * inspector or the school change.
 */
function Errors({ errors }: { errors: string[] }) {
  return <>{errors.map((error, index) => <div key={index} className="invalid-feedback d-block">{error}</div>)}</>;
}

function Required({ htmlFor, children }: { htmlFor: string; children: string }) {
  return <label className="form-label" htmlFor={htmlFor}>{children}{" "}<span className="text-danger">*</span></label>;
}

const cls = (base: string, field: Field) => `${base}${field.errors.length ? " is-invalid" : ""}`;

export default function AsignacionForm({ data, action, modal, success, pending, onSubmit, autoFocus }: {
  data: AsignacionFormData;
  /** API endpoint the form posts to. */
  action: string;
  modal: { parent: () => HTMLElement | null; close: () => void } | null;
  /** Success notice of «Asignar y cargar otra» (`[data-insp-mensaje]`). */
  success: string;
  pending: boolean;
  onSubmit: (body: URLSearchParams) => void;
  autoFocus: boolean;
}) {
  const form = useRef<HTMLFormElement>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const f = data.fields;
  // `panel.js` focuses the first input or select after painting the form.
  useEffect(() => {
    if (autoFocus) form.current?.querySelector<HTMLElement>("input:not([type=hidden]), select")?.focus();
  }, [autoFocus, data]);
  const verify = useCallback(() => {
    const element = form.current;
    if (!element) return;
    const value = (name: string) => element.querySelector<HTMLInputElement | HTMLSelectElement>(`[name=${name}]`)?.value ?? "";
    const values = { fecha: value("fecha"), inspector: value("inspector"), escuela: value("escuela") };
    if (!values.escuela || !values.fecha) { setNotice(null); return; }
    void verificarAsignacion(data.options.verificar_url, values).then((result) => { if (result !== undefined) setNotice(result); });
  }, [data.options.verificar_url]);
  useEffect(() => {
    const element = form.current;
    if (!element) return undefined;
    const change = (event: Event) => { if ((event.target as HTMLElement).hasAttribute?.("data-insp-verifica")) verify(); };
    element.addEventListener("change", change);
    verify();
    return () => element.removeEventListener("change", change);
  }, [verify]);
  const searchInspector = useCallback((term: string, signal: AbortSignal) =>
    client.get(`${apiPath(data.options.inspectores_url)}?q=${encodeURIComponent(term)}`, { signal }).then(({ data: body }: { data: unknown }) => body),
  [data.options.inspectores_url]);
  const searchEscuela = useCallback((term: string, signal: AbortSignal) =>
    client.get(`${apiPath(data.options.escuelas_url)}?q=${encodeURIComponent(term)}`, { signal }).then(({ data: body }: { data: unknown }) => body),
  [data.options.escuelas_url]);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) return;
    const body = new URLSearchParams(new FormData(event.currentTarget) as unknown as Record<string, string>);
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    if (submitter?.name) body.append(submitter.name, submitter.value);
    onSubmit(body);
  };
  return (
    <form ref={form} method="post" action={action} noValidate data-insp-form-modal="" data-insp-verificar={data.options.verificar_url} aria-labelledby="insp-modal-form-titulo" onSubmit={submit}>
      <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
      <div className="modal-header">
        <h2 className="modal-title h5" id="insp-modal-form-titulo">Nueva asignación</h2>
        <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Cerrar" onClick={modal ? () => modal.close() : undefined} />
      </div>
      <div className="modal-body">
        <div data-insp-mensaje="">{success && <div className="alert alert-success" role="status">{success}</div>}</div>
        {data.non_field_errors.map((error, index) => <div key={index} className="alert alert-danger">{error}</div>)}
        <div className="mb-3">
          <Required htmlFor="id_fecha">Jornada</Required>
          <input id="id_fecha" name="fecha" type="date" className={cls("form-control", f.fecha)} defaultValue={f.fecha.value} data-insp-verifica="" required />
          <Errors errors={f.fecha.errors} />
        </div>
        <div className="mb-3">
          <Required htmlFor="id_inspector">Inspector</Required>
          <InspSelect2 id="id_inspector" name="inspector" placeholder="Usuario, nombre, apellido o DNI" minimum={3} initial={data.inspector_inicial} search={searchInspector}
            width="100%" dropdownParent={modal?.parent} autoSubmit={false} describedBy="ayuda-inspector" required verifica selectClass={cls("form-select", f.inspector)} />
          <div id="ayuda-inspector" className="form-text">
            Solo usuarios con la sección Inspecciones escolares y rol Inspector. Escribí al menos 3 letras.
          </div>
          <Errors errors={f.inspector.errors} />
        </div>
        <div className="mb-3">
          <Required htmlFor="id_escuela">Escuela</Required>
          <InspSelect2 id="id_escuela" name="escuela" placeholder="Nombre, Cueanexo o domicilio" minimum={3} initial={data.escuela_inicial} search={searchEscuela}
            width="100%" dropdownParent={modal?.parent} autoSubmit={false} describedBy="ayuda-escuela" required verifica selectClass={cls("form-select", f.escuela)} />
          <div id="ayuda-escuela" className="form-text">
            Busca por nombre, Cueanexo o domicilio desde 3 letras · 20 resultados como máximo.
          </div>
          <Errors errors={f.escuela.errors} />
        </div>
        <div className={`insp-aviso insp-aviso-ambar${notice ? "" : " d-none"}`} role="status" data-insp-aviso-duplicada="">{notice ?? ""}</div>
      </div>
      <div className="modal-footer">
        <button type="button" className="btn btn-link" data-bs-dismiss="modal" onClick={modal ? () => modal.close() : undefined}>Cancelar</button>
        <button type="submit" name="otra" value="1" className="btn btn-outline-primary" disabled={pending}>Asignar y cargar otra</button>
        <button type="submit" className="btn btn-primary" disabled={pending}>Asignar</button>
      </div>
    </form>
  );
}
