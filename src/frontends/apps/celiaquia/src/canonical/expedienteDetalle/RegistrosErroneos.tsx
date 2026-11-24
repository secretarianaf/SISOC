import { Fragment, useState, type FormEvent } from "react";
import { postNative, postNativeJson } from "./native";
import type { Run } from "./Dialogs";
import type { Catalogos, Opcion, Registro } from "./types";

type Field = { name: string; label: string; required?: boolean; type?: string; options?: "sexos" | "nacionalidades" | "municipios" | "localidades" };

const TITULAR: Field[] = [
  { name: "apellido", label: "Apellido", required: true }, { name: "nombre", label: "Nombre", required: true },
  { name: "documento", label: "CUIL", required: true }, { name: "fecha_nacimiento", label: "Fecha Nacimiento", required: true },
  { name: "sexo", label: "Sexo", required: true, options: "sexos" }, { name: "nacionalidad", label: "Nacionalidad", required: true, options: "nacionalidades" },
  { name: "municipio", label: "Municipio", required: true, options: "municipios" }, { name: "localidad", label: "Localidad", required: true, options: "localidades" },
  { name: "telefono", label: "Teléfono" }, { name: "email", label: "Email", type: "email" },
  { name: "calle", label: "Calle", required: true }, { name: "altura", label: "Altura", required: true }, { name: "codigo_postal", label: "Código Postal", required: true },
];
const RESPONSABLE: Field[] = [
  { name: "apellido_responsable", label: "Apellido Responsable" }, { name: "nombre_responsable", label: "Nombre Responsable" },
  { name: "documento_responsable", label: "CUIL Responsable" }, { name: "fecha_nacimiento_responsable", label: "Fecha Nac. Responsable" },
  { name: "sexo_responsable", label: "Sexo Responsable", options: "sexos" }, { name: "telefono_responsable", label: "Teléfono Responsable" },
  { name: "email_responsable", label: "Email Responsable", type: "email" }, { name: "domicilio_responsable", label: "Domicilio Responsable" },
  { name: "localidad_responsable", label: "Localidad Responsable", options: "localidades" },
];

/** Initial select value with the same matching rules as the native template. */
function initial(registro: Registro, field: Field, options: Opcion[]) {
  const raw = registro.datos_raw[field.name] ?? "";
  if (field.name === "nacionalidad") return registro.nacionalidad_id;
  if (field.name === "municipio") return registro.municipio_id;
  if (!field.options) return raw;
  const lower = raw.toLowerCase();
  const found = options.find((o) => String(o.id) === raw || o.label.toLowerCase() === lower
    || (field.options === "sexos" && ((raw.toUpperCase() === "M" && o.label.toLowerCase() === "masculino") || (raw.toUpperCase() === "F" && o.label.toLowerCase() === "femenino"))));
  return found ? String(found.id) : "";
}

function RegistroForm({ registro, catalogos, run, disabled }: { registro: Registro; catalogos: Catalogos | null; run: Run; disabled: boolean }) {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body: Record<string, string> = {};
    new FormData(event.currentTarget).forEach((value, key) => { body[key] = String(value).trim(); });
    void run(() => postNativeJson(registro.actualizar_url, body), (r) => String(r.message ?? "Cambios guardados. Usá \"Reprocesar Todos\" para crear los legajos."));
  };
  const input = (field: Field, required: boolean) => {
    const options = field.options ? (catalogos?.[field.options] ?? []) as (Opcion & { municipio?: string })[] : [];
    const invalid = registro.invalid_fields.includes(field.name);
    const common = { name: field.name, required, "aria-invalid": invalid || undefined, defaultValue: initial(registro, field, options) };
    return <label key={field.name} className={invalid ? "ed-invalid" : undefined}>{field.label}{required && " *"}
      {field.options ? <select {...common}><option value="">Seleccionar...</option>{options.map((o) => <option key={o.id} value={o.id}>{o.label}{o.municipio ? ` (${o.municipio})` : ""}</option>)}</select>
        : <input type={field.type ?? "text"} {...common} />}
    </label>;
  };
  return <form className="ed-form-grid" onSubmit={submit} aria-label={`Editar datos de la fila ${registro.fila}`}>
    <h4>Editar Datos - Fila {registro.fila}</h4>
    {TITULAR.map((field) => input(field, Boolean(field.required)))}
    <h4>Datos del responsable</h4>
    {RESPONSABLE.map((field) => input(field, registro.responsable_requerido))}
    <button type="submit" disabled={disabled}>Guardar cambios</button>
  </form>;
}

export function RegistrosErroneos({ registros, catalogos, reprocesarUrl, run, disabled }: { registros: Registro[]; catalogos: Catalogos | null; reprocesarUrl: string | null; run: Run; disabled: boolean }) {
  const [open, setOpen] = useState<number | null>(null);
  const eliminar = (registro: Registro) => run(async () => {
    let message = "¿Está seguro de realizar la baja lógica de este registro?";
    try {
      const preview = await postNative(registro.eliminar_url, new URLSearchParams({ preview: "1" }));
      const data = preview.preview as { total_afectados: number; desglose_por_modelo?: { modelo: string; cantidad: number }[] } | undefined;
      if (data) message = `Se aplicará una baja lógica en cascada.\nTotal afectados: ${data.total_afectados}\n${(data.desglose_por_modelo ?? []).map((i) => `- ${i.modelo}: ${i.cantidad}`).join("\n")}`;
    } catch { /* the native flow also falls back to the generic question */ }
    if (!window.confirm(message)) return;
    return postNative(registro.eliminar_url);
  }, (r) => String(r.message ?? "Registro eliminado."));
  const reprocesar = () => {
    if (!reprocesarUrl || !window.confirm("¿Está seguro de reprocesar todos los registros erróneos? Esta acción intentará crear los legajos con los datos corregidos.")) return;
    void run(() => postNativeJson(reprocesarUrl, {}), (r) => String(r.alerta_resumen ?? r.message ?? "Registros reprocesados."));
  };
  return <section className="ed-panel" aria-labelledby="ed-registros">
    <div className="ed-row"><h2 id="ed-registros">Registros con Errores ({registros.length})</h2>{reprocesarUrl && <button type="button" disabled={disabled} onClick={reprocesar}>Reprocesar Todos</button>}</div>
    <div className="ed-scroll" tabIndex={0} role="region" aria-label="Registros con errores"><table><thead><tr><th scope="col">Fila</th><th scope="col">Datos</th><th scope="col">Error</th><th scope="col">Acciones</th></tr></thead>
      <tbody>{registros.map((registro) => <Fragment key={registro.id}>
        <tr>
          <td>{registro.fila}</td>
          <td><small>{registro.datos_raw.apellido && <div><strong>Apellido:</strong> {registro.datos_raw.apellido}</div>}{registro.datos_raw.nombre && <div><strong>Nombre:</strong> {registro.datos_raw.nombre}</div>}
            {registro.datos_raw.documento && <div><strong>CUIL:</strong> {registro.datos_raw.documento}</div>}{registro.datos_raw.fecha_nacimiento && <div><strong>F.Nac:</strong> {registro.datos_raw.fecha_nacimiento}</div>}
            {(registro.datos_raw.apellido_responsable || registro.datos_raw.nombre_responsable) && <span className="ed-chip">Con Responsable</span>}</small></td>
          <td><small className="ed-error">{registro.mensaje_error}</small></td>
          <td><button type="button" aria-expanded={open === registro.id} onClick={() => setOpen(open === registro.id ? null : registro.id)}>Editar</button>
            <button type="button" disabled={disabled} onClick={() => void eliminar(registro)} aria-label={`Eliminar registro de la fila ${registro.fila}`}>Eliminar</button></td>
        </tr>
        {open === registro.id && <tr key={`${registro.id}-form`}><td colSpan={4}><RegistroForm registro={registro} catalogos={catalogos} run={run} disabled={disabled} /></td></tr>}
      </Fragment>)}</tbody></table></div>
  </section>;
}
