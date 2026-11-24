import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import InspSelect2 from "./InspSelect2";
import { apiPath, client, type EscuelaFormData, type Field } from "./inspeccionesEscuelasApi";

/**
 * School form of `inspecciones/partials/escuela_form.html` (IN05), the same in
 * the modal and as a page. Values and errors come from the vertical's web API,
 * which runs the native `EscuelaCrearView` / `EscuelaEditarView`.
 */
function Errors({ errors }: { errors: string[] }) {
  return <>{errors.map((error, index) => <div key={index} className="invalid-feedback d-block">{error}</div>)}</>;
}

function Required({ htmlFor, children }: { htmlFor: string; children: string }) {
  return <label className="form-label" htmlFor={htmlFor}>{children}{" "}<span className="text-danger">*</span></label>;
}

const cls = (base: string, field: Field) => `${base}${field.errors.length ? " is-invalid" : ""}`;

export default function EscuelaForm({ data, action, modal, success, pending, onSubmit, autoFocus }: {
  data: EscuelaFormData;
  /** API endpoint the form posts to. */
  action: string;
  modal: { parent: () => HTMLElement | null; close: () => void } | null;
  /** Success notice of «Guardar y cargar otra» (`[data-insp-mensaje]`). */
  success: string;
  pending: boolean;
  onSubmit: (body: URLSearchParams) => void;
  autoFocus: boolean;
}) {
  const form = useRef<HTMLFormElement>(null);
  const f = data.fields;
  const [provincia, setProvincia] = useState(f.provincia.value);
  const [clear, setClear] = useState(0);
  const [localidadDisabled, setLocalidadDisabled] = useState(false);
  // `panel.js` focuses the first input or select after painting the form.
  useEffect(() => {
    if (autoFocus) form.current?.querySelector<HTMLElement>("input:not([type=hidden]), select")?.focus();
  }, [autoFocus, data]);
  const search = useCallback((term: string, signal: AbortSignal) => {
    const value = (form.current?.querySelector<HTMLSelectElement>("#id_provincia")?.value) ?? "";
    const url = `${apiPath(data.options.localidades_url)}?q=${encodeURIComponent(term)}&provincia=${encodeURIComponent(value)}`;
    return client.get(url, { signal }).then(({ data: body }: { data: unknown }) => body);
  }, [data.options.localidades_url]);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) return;
    const body = new URLSearchParams(new FormData(event.currentTarget) as unknown as Record<string, string>);
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    if (submitter?.name) body.append(submitter.name, submitter.value);
    onSubmit(body);
  };
  const input = (name: "cueanexo" | "cp" | "nombre" | "domicilio" | "telefono" | "mail", extra: Record<string, unknown>, className = "form-control") => (
    <input id={`id_${name}`} name={name} className={cls(className, f[name])} defaultValue={f[name].value} {...extra} />
  );
  return (
    <form ref={form} method="post" action={action} noValidate data-insp-form-modal="" aria-labelledby="insp-modal-form-titulo" onSubmit={submit}>
      <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
      <div className="modal-header">
        <h2 className="modal-title h5" id="insp-modal-form-titulo">{data.editar ? "Editar escuela" : "Nueva escuela"}</h2>
        <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Cerrar" onClick={modal ? () => modal.close() : undefined} />
      </div>
      <div className="modal-body">
        <div data-insp-mensaje="">{success && <div className="alert alert-success" role="status">{success}</div>}</div>
        {data.aviso && (
          <div className="insp-aviso insp-aviso-ambar" role="status">
            <strong>Datos a revisar:</strong>{` ${data.aviso.motivos}.`}
            {data.aviso.localidad_original && <>{" Localidad del archivo: "}<em>{data.aviso.localidad_original}</em>{"."}</>}
            {" Al guardar con una localidad de la lista y un mail válido se quita la marca."}
          </div>
        )}
        {data.non_field_errors.map((error, index) => <div key={index} className="alert alert-danger">{error}</div>)}
        <div className="row g-3">
          <div className="col-md-6">
            <Required htmlFor="id_provincia">Provincia</Required>
            <select id="id_provincia" name="provincia" className={cls("form-select", f.provincia)} data-insp-limpia="#id_localidad" required
              value={provincia} onChange={(event) => { setProvincia(event.target.value); setClear((n) => n + 1); setLocalidadDisabled(!event.target.value); }}>
              <option value="">Elegí la provincia</option>
              {data.options.provincias.map((p) => <option key={p.id} value={String(p.id)}>{p.nombre}</option>)}
            </select>
            <Errors errors={f.provincia.errors} />
          </div>
          <div className="col-md-6">
            <Required htmlFor="id_localidad">Localidad</Required>
            <InspSelect2 id="id_localidad" name="localidad" placeholder="Buscá la localidad" minimum={0} initial={data.localidad_inicial} search={search}
              width="100%" dropdownParent={modal?.parent} autoSubmit={false} describedBy="ayuda-localidad" required clearSignal={clear} disabled={localidadDisabled}
              selectClass={cls("form-select", f.localidad)} />
            <div id="ayuda-localidad" className="form-text">
              Busca dentro de la provincia elegida y muestra el municipio para distinguir nombres repetidos.
            </div>
            <Errors errors={f.localidad.errors} />
          </div>
          <div className="col-md-6">
            <Required htmlFor="id_cueanexo">Cueanexo</Required>
            {input("cueanexo", { type: "text", inputMode: "numeric", maxLength: 9, pattern: "\\d{9}", "aria-describedby": "ayuda-cueanexo", "aria-invalid": f.cueanexo.errors.length ? "true" : undefined, required: true }, "form-control insp-mono")}
            <div id="ayuda-cueanexo" className="form-text">9 dígitos, con los ceros iniciales.</div>
            {f.cueanexo.errors.map((error, index) => (
              <div key={index} className="invalid-feedback d-block">
                {error}
                {data.duplicada_url && <>{" "}<a href={data.duplicada_url}>Abrir para editar</a></>}
              </div>
            ))}
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="id_cp">C. P.</label>
            {input("cp", { type: "text", maxLength: 20, "aria-describedby": "ayuda-cp" })}
            <div id="ayuda-cp" className="form-text">Admite el formato CPA, por ejemplo B1754ABC.</div>
            <Errors errors={f.cp.errors} />
          </div>
          <div className="col-12">
            <Required htmlFor="id_nombre">Nombre</Required>
            {input("nombre", { type: "text", maxLength: 255, required: true })}
            <Errors errors={f.nombre.errors} />
          </div>
          <div className="col-12">
            <Required htmlFor="id_domicilio">Domicilio</Required>
            {input("domicilio", { type: "text", maxLength: 255, required: true })}
            <Errors errors={f.domicilio.errors} />
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="id_telefono">Teléfono</label>
            {input("telefono", { type: "tel", maxLength: 255, "aria-describedby": "ayuda-telefono" })}
            <div id="ayuda-telefono" className="form-text">Admite característica, internos y varios números.</div>
            <Errors errors={f.telefono.errors} />
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="id_mail">Mail</label>
            {input("mail", { type: "email", maxLength: 255 })}
            <Errors errors={f.mail.errors} />
          </div>
        </div>
      </div>
      <div className="modal-footer">
        <button type="button" className="btn btn-link" data-bs-dismiss="modal" onClick={modal ? () => modal.close() : undefined}>Cancelar</button>
        {!data.editar && <button type="submit" name="otra" value="1" className="btn btn-outline-primary" disabled={pending}>Guardar y cargar otra</button>}
        <button type="submit" className="btn btn-primary" disabled={pending}>Guardar escuela</button>
      </div>
    </form>
  );
}
