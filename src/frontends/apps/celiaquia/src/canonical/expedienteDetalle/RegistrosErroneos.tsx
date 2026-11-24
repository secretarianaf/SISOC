import { Fragment, useEffect, useRef, useState, type FormEvent } from "react";
import { NativeError, postNative, postNativeJson, type NativeResult } from "./native";
import { expedienteIdFromPath, queueTimedAlert } from "./timedAlert";
import type { Run } from "./Dialogs";
import type { Catalogos, Notice, Opcion, Registro } from "./types";

type Field = { name: string; label: string; required?: boolean; type?: string; options?: "sexos" | "nacionalidades" | "municipios" | "localidades" };
type Values = Record<string, string>;

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
/** Native autosave delay (`programarGuardado` in static/custom/js/registros_erroneos.js). */
const AUTOSAVE_DELAY_MS = 500;

const optionsFor = (field: Field, catalogos: Catalogos | null) => (field.options ? (catalogos?.[field.options] ?? []) : []) as (Opcion & { municipio?: string })[];

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

/** The body the native form would post for an untouched record (every field, trimmed). */
function initialValues(registro: Registro, catalogos: Catalogos | null): Values {
  return Object.fromEntries([...TITULAR, ...RESPONSABLE].map((field) => [field.name, (initial(registro, field, optionsFor(field, catalogos)) ?? "").trim()]));
}

const readForm = (form: HTMLFormElement): Values => {
  const values: Values = {};
  new FormData(form).forEach((value, key) => { values[key] = String(value).trim(); });
  return values;
};

/** Same wording and tone as `buildReprocesarRegistrosFeedback` in the native script. */
function reprocesarFeedback(data: NativeResult): Notice & { queue: boolean } {
  const creados = Number(data.creados || 0);
  const errores = Number(data.errores || 0);
  const excluidos = Number(data.excluidos || 0);
  const partes: string[] = [];
  if (creados > 0) partes.push(`Se ${creados === 1 ? "creó" : "crearon"} ${creados} ${creados === 1 ? "legajo" : "legajos"} correctamente.`);
  else partes.push("No se crearon legajos nuevos.");
  if (excluidos > 0) partes.push(`${excluidos} ${excluidos === 1 ? "legajo" : "legajos"} ${excluidos === 1 ? "no se creó" : "no se crearon"} porque ya ${excluidos === 1 ? "existe" : "existen"} en otro expediente activo.`);
  if (errores > 0) partes.push(`${errores} ${errores === 1 ? "registro" : "registros"} aún tienen errores.`);
  const tone = errores > 0 || creados === 0 ? "warning" : "success";
  return { tone, text: partes.join(" "), queue: tone === "success" && creados > 0 && Boolean(data.alerta_resumen) };
}

function RegistroForm({ registro, catalogos, values, invalid, status, disabled, onEdit, onRetry }: {
  registro: Registro; catalogos: Catalogos | null; values: Values | undefined; invalid: string[]; status: Notice | undefined;
  disabled: boolean; onEdit: (values: Values, field: string) => void; onRetry: () => void;
}) {
  const input = (field: Field, required: boolean) => {
    const options = optionsFor(field, catalogos);
    const isInvalid = invalid.includes(field.name);
    const common = { name: field.name, required, "aria-invalid": isInvalid || undefined, defaultValue: values?.[field.name] ?? initial(registro, field, options) };
    return <label key={field.name} className={isInvalid ? "ed-invalid" : undefined}>{field.label}{required && " *"}
      {field.options ? <select {...common}><option value="">Seleccionar...</option>{options.map((o) => <option key={o.id} value={o.id}>{o.label}{o.municipio ? ` (${o.municipio})` : ""}</option>)}</select>
        : <input type={field.type ?? "text"} {...common} />}
    </label>;
  };
  // Edits autosave like the native form, so Enter must not submit anything.
  const onSubmit = (event: FormEvent<HTMLFormElement>) => event.preventDefault();
  return <form className="ed-form-grid" onSubmit={onSubmit} aria-label={`Editar datos de la fila ${registro.fila}`}
    onChange={(event) => onEdit(readForm(event.currentTarget), (event.target as HTMLInputElement).name)}>
    <h4>Editar Datos - Fila {registro.fila}</h4>
    <fieldset disabled={disabled} style={{ display: "contents" }}>
      {TITULAR.map((field) => input(field, Boolean(field.required)))}
      <h4>Datos del responsable</h4>
      {RESPONSABLE.map((field) => input(field, registro.responsable_requerido))}
    </fieldset>
    <p><small><strong>Nota:</strong> Los campos se guardan automáticamente al cambiar. Luego usa &quot;Reprocesar Todos&quot; para crear los legajos.</small></p>
    {status && <p className={`ed-alert ed-${status.tone}`} role={status.tone === "danger" ? "alert" : "status"}>{status.text}</p>}
    {status?.tone === "danger" && <button type="button" disabled={disabled} onClick={onRetry}>Reintentar guardado</button>}
  </form>;
}

export function RegistrosErroneos({ registros, catalogos, reprocesarUrl, run, disabled }: { registros: Registro[]; catalogos: Catalogos | null; reprocesarUrl: string | null; run: Run; disabled: boolean }) {
  const [open, setOpen] = useState<number | null>(null);
  // Edits outlive the collapsible form so closing it never drops unsaved values.
  const [edits, setEdits] = useState<Record<number, Values>>({});
  const [invalid, setInvalid] = useState<Record<number, string[]>>({});
  const [status, setStatus] = useState<Record<number, Notice | undefined>>({});
  const timers = useRef<Record<number, ReturnType<typeof setTimeout>>>({});
  const queue = useRef<Record<number, Promise<boolean>>>({});

  useEffect(() => {
    const pending = timers.current;
    return () => Object.values(pending).forEach(clearTimeout);
  }, []);

  /** One save at a time per record, never retried; resolves true when the native side stored it. */
  const save = (registro: Registro, body: Values, showErrors = true) => {
    const next = (queue.current[registro.id] ?? Promise.resolve(true)).then(async () => {
      try {
        await postNativeJson(registro.actualizar_url, body);
        setInvalid((previous) => ({ ...previous, [registro.id]: [] }));
        setStatus((previous) => ({ ...previous, [registro.id]: { tone: "success", text: "Cambios guardados." } }));
        return true;
      } catch (cause) {
        const data = cause instanceof NativeError ? cause.data : {};
        if (Array.isArray(data.invalid_fields)) setInvalid((previous) => ({ ...previous, [registro.id]: data.invalid_fields as string[] }));
        if (data.saved_partial) {
          if (showErrors) setStatus((previous) => ({ ...previous, [registro.id]: { tone: "warning", text: String(data.error || "Se guardaron cambios parciales, pero quedan validaciones pendientes.") } }));
          return true;
        }
        if (showErrors) {
          const text = cause instanceof NativeError ? `Error: ${cause.message}` : cause instanceof TypeError ? "Error al guardar registro" : cause instanceof Error ? cause.message : "Error al guardar registro";
          setStatus((previous) => ({ ...previous, [registro.id]: { tone: "danger", text } }));
        }
        return false;
      }
    });
    queue.current[registro.id] = next;
    return next;
  };

  const edit = (registro: Registro, values: Values, field: string) => {
    setEdits((previous) => ({ ...previous, [registro.id]: values }));
    setInvalid((previous) => ({ ...previous, [registro.id]: (previous[registro.id] ?? registro.invalid_fields).filter((name) => name !== field) }));
    clearTimeout(timers.current[registro.id]);
    timers.current[registro.id] = setTimeout(() => void save(registro, values), AUTOSAVE_DELAY_MS);
  };

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
    let aviso = "";
    void run(async () => {
      // Like the native page, every record is saved (pending edits included) before reprocessing.
      let exitosos = 0;
      let fallidos = 0;
      for (const registro of registros) {
        clearTimeout(timers.current[registro.id]);
        if (await save(registro, edits[registro.id] ?? initialValues(registro, catalogos), false)) exitosos += 1;
        else fallidos += 1;
      }
      if (fallidos > 0) aviso = `Se guardaron ${exitosos} registros antes de reprocesar y ${fallidos} siguen con errores de validacion.`;
      return postNativeJson(reprocesarUrl, {});
    }, (result) => {
      const feedback = reprocesarFeedback(result);
      if (feedback.queue) queueTimedAlert(expedienteIdFromPath(), "success", String(result.alerta_resumen));
      return { tone: aviso ? "warning" : feedback.tone, text: aviso ? `${aviso}\n${feedback.text}` : feedback.text };
    });
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
        {open === registro.id && <tr key={`${registro.id}-form`}><td colSpan={4}>
          <RegistroForm registro={registro} catalogos={catalogos} values={edits[registro.id]} invalid={invalid[registro.id] ?? registro.invalid_fields}
            status={status[registro.id]} disabled={disabled} onEdit={(values, field) => edit(registro, values, field)}
            onRetry={() => void save(registro, edits[registro.id] ?? initialValues(registro, catalogos))} />
        </td></tr>}
      </Fragment>)}</tbody></table></div>
  </section>;
}
