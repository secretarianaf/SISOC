import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import type { CanonicalParams } from "./screens";
import { CanonicalError, internal, loadProjection, sendNative } from "./transport";

/**
 * Canonical alta (`/celiaquia/expedientes/nuevo/`) and edición
 * (`/celiaquia/expedientes/<pk>/editar/`) of an Expediente. Django keeps the
 * native form, lookup and service: this screen reads the JSON projection of
 * the same URL and posts the multipart form back to it with
 * `Accept: application/json`.
 */

type TextField = { label: string; required: boolean; value: string; max_length?: number };
type ExcelField = { label: string; required: boolean; accept: string; max_bytes: number; current: { name: string; url: string } | null };
type Projection = {
  version: number; mode: "create" | "edit"; title: string; expediente: { id: number; numero: string } | null;
  fields: { numero_expediente: TextField; observaciones: TextField; excel_masivo: ExcelField };
  urls: { preview: string; plantilla: string; localidades: string; cancel: string };
  preview_max_limit: number; provincias: { id: number; nombre: string }[];
};
type Errors = Record<string, string[]>;
type Preview = { headers: string[]; rows: Record<string, unknown>[]; total_rows?: number; shown_rows?: number };
type Localidad = { provincia_id: number | null; provincia_nombre: string | null; municipio_id: number | null; municipio_nombre: string | null; localidad_id: number; localidad_nombre: string };
type Props = { params: CanonicalParams; navigate?: (url: string) => void };

const PREVIEW_LIMITS = ["10", "50", "100", "500"];
const STYLE = `.canonical-expediente-form{max-width:52rem;margin:auto;padding:1rem}
.canonical-expediente-form label{display:block;font-weight:600;margin-top:1rem}
.canonical-expediente-form input,.canonical-expediente-form textarea,.canonical-expediente-form select,.canonical-expediente-form button,.canonical-expediente-form a.button{font:inherit;padding:.5rem;max-width:100%;box-sizing:border-box}
.canonical-expediente-form input[type=text],.canonical-expediente-form textarea,.canonical-expediente-form input[type=file]{width:100%}
.canonical-expediente-form .help{color:#4a5563;font-size:.9rem;margin:.25rem 0}
.canonical-expediente-form .error{color:#a11d1d;margin:.25rem 0}
.canonical-expediente-form .actions{display:flex;flex-wrap:wrap;justify-content:space-between;gap:.5rem;margin-top:1rem}
.canonical-expediente-form .actions>div{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}
.canonical-expediente-form a.button{display:inline-block;border:1px solid #6b7280;border-radius:4px;text-decoration:none}
.canonical-expediente-form table{border-collapse:collapse;width:100%}
.canonical-expediente-form td,.canonical-expediente-form th{border:1px solid #aab2bd;padding:.4rem;text-align:left}
.canonical-expediente-form .scroll{overflow-x:auto}
.canonical-expediente-form .panel{border:1px solid #aab2bd;border-radius:6px;padding:1rem;margin-top:1rem}
.canonical-expediente-form .filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));gap:.5rem;align-items:end}
.canonical-expediente-form :focus-visible{outline:3px solid #1263b5;outline-offset:2px}`;

function fileProblem(file: File | null, field: ExcelField) {
  if (!file) return "";
  if (!file.name.toLowerCase().endsWith(".xlsx")) return "Solo se permiten archivos .xlsx.";
  if (file.size > field.max_bytes) return `El archivo supera el tamaño máximo de ${Math.round(field.max_bytes / (1024 * 1024))} MB.`;
  return "";
}

function describedBy(...ids: (string | false)[]) {
  const value = ids.filter(Boolean).join(" ");
  return value || undefined;
}

function FieldErrors({ id, messages }: { id: string; messages?: string[] }) {
  if (!messages?.length) return null;
  return <p id={id} className="error">{messages.join(" ")}</p>;
}

function csvLocalidades(rows: Localidad[]) {
  const escape = (value: unknown) => {
    const text = String(value ?? "");
    const safe = /^[=+\-@]/.test(text) ? `'${text}` : text;
    return `"${safe.replace(/"/g, '""')}"`;
  };
  const lines = rows.map((item) => [item.provincia_id, item.provincia_nombre, item.municipio_id, item.municipio_nombre, item.localidad_id, item.localidad_nombre].map(escape).join(","));
  return `\uFEFFProvincia ID,Provincia,Municipio ID,Municipio,Localidad ID,Localidad\n${lines.map((line) => `${line}\n`).join("")}`;
}

function LocalidadesPanel({ url, provincias, onClose }: { url: string; provincias: Projection["provincias"]; onClose: () => void }) {
  const [rows, setRows] = useState<Localidad[]>([]);
  const [provincia, setProvincia] = useState("");
  const [municipio, setMunicipio] = useState("");
  const [localidad, setLocalidad] = useState("");
  const [texto, setTexto] = useState("");
  const [message, setMessage] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams();
    if (provincia) params.append("provincia", provincia);
    if (municipio) params.append("municipio", municipio);
    fetch(`${internal(url)}?${params}`, { credentials: "same-origin", headers: { Accept: "application/json" }, signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`No se pudieron cargar las localidades (${response.status}).`);
        setRows(await response.json() as Localidad[]);
        setMessage("");
      })
      .catch((cause: unknown) => { if (!controller.signal.aborted) setMessage(cause instanceof Error ? cause.message : "No se pudieron cargar las localidades."); });
    return () => controller.abort();
  }, [url, provincia, municipio]);
  const municipios = useMemo(() => [...new Map(rows.map((item) => [item.municipio_id, item.municipio_nombre])).entries()], [rows]);
  const visible = rows.filter((item) => {
    const query = texto.toLowerCase();
    return (!provincia || String(item.provincia_id) === provincia)
      && (!municipio || String(item.municipio_id) === municipio)
      && (!localidad || String(item.localidad_id) === localidad)
      && [`${item.provincia_id} - ${item.provincia_nombre}`, `${item.municipio_id} - ${item.municipio_nombre}`, `${item.localidad_id} - ${item.localidad_nombre}`].some((label) => label.toLowerCase().includes(query));
  });
  const download = () => {
    if (!rows.length) { setMessage("No hay datos para descargar"); return; }
    const link = document.createElement("a");
    const href = URL.createObjectURL(new Blob([csvLocalidades(rows)], { type: "text/csv;charset=utf-8;" }));
    link.href = href; link.download = "localidades.csv";
    document.body.appendChild(link); link.click(); link.remove();
    URL.revokeObjectURL(href);
  };
  const clear = () => { setProvincia(""); setMunicipio(""); setLocalidad(""); setTexto(""); };
  const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") { event.stopPropagation(); onClose(); } };
  return <section role="dialog" aria-labelledby="localidades-title" className="panel" onKeyDown={onKeyDown}>
    <h2 id="localidades-title" ref={heading} tabIndex={-1}>Buscar Localidades</h2>
    <div className="filters">
      <label>Provincia<select value={provincia} onChange={(e) => { setProvincia(e.target.value); setMunicipio(""); setLocalidad(""); setTexto(""); }}>
        <option value="">Todas</option>{provincias.map((p) => <option key={p.id} value={p.id}>{`${p.id} - ${p.nombre}`}</option>)}
      </select></label>
      <label>Municipio<select value={municipio} onChange={(e) => { setMunicipio(e.target.value); setLocalidad(""); }}>
        <option value="">Todos</option>{municipios.map(([id, nombre]) => <option key={String(id)} value={String(id)}>{`${id} - ${nombre}`}</option>)}
      </select></label>
      <label>Localidad<select value={localidad} onChange={(e) => setLocalidad(e.target.value)}>
        <option value="">Todas</option>{rows.map((item) => <option key={item.localidad_id} value={item.localidad_id}>{`${item.localidad_id} - ${item.localidad_nombre}`}</option>)}
      </select></label>
      <label>Buscar<input type="text" value={texto} placeholder="Buscar..." onChange={(e) => setTexto(e.target.value)} /></label>
      <div><button type="button" onClick={clear}>Limpiar</button> <button type="button" onClick={download}>Descargar</button></div>
    </div>
    {message && <p role="status">{message}</p>}
    <div className="scroll" role="region" aria-label="Localidades encontradas" tabIndex={0}>
      <table><thead><tr><th scope="col">Provincia</th><th scope="col">Municipio</th><th scope="col">Localidad</th></tr></thead>
        <tbody>{visible.map((item) => <tr key={item.localidad_id}>
          <td>{`${item.provincia_id} - ${item.provincia_nombre}`}</td><td>{`${item.municipio_id} - ${item.municipio_nombre}`}</td><td>{`${item.localidad_id} - ${item.localidad_nombre}`}</td>
        </tr>)}</tbody></table>
    </div>
    <button type="button" onClick={onClose}>Cerrar</button>
  </section>;
}

function ExpedienteForm({ url, navigate }: { url: string; navigate: (url: string) => void }) {
  const [data, setData] = useState<Projection | null>(null);
  const [loadError, setLoadError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [limit, setLimit] = useState("all");
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [localidades, setLocalidades] = useState(false);
  const localidadesButton = useRef<HTMLButtonElement>(null);
  const summary = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    loadProjection<Projection>(url, controller.signal).then((body) => {
      if (body.version !== 1 || !body.fields?.excel_masivo) throw new Error("La pantalla no es compatible con esta versión.");
      setData(body);
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setLoadError(cause instanceof CanonicalError || cause instanceof Error ? cause.message : "No se pudo cargar la pantalla.");
    });
    return () => controller.abort();
  }, [url]);

  useEffect(() => { if (formError) summary.current?.focus(); }, [formError]);

  if (!data) return <main className="canonical-expediente-form"><h1>Expediente</h1>{loadError ? <p role="alert">{loadError}</p> : <p role="status">Cargando…</p>}</main>;

  const { numero_expediente: numero, observaciones, excel_masivo: excel } = data.fields;
  const clientFileError = fileProblem(file, excel);
  const excelErrors = clientFileError ? [clientFileError] : errors.excel_masivo;
  const disabled = pending || uncertain;

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (disabled || clientFileError) return;
    setPending(true); setErrors({}); setFormError("");
    try {
      const body = new FormData(event.currentTarget);
      // Send only a chosen file: an empty part must not replace the current Excel.
      body.delete("excel_masivo");
      if (file) body.append("excel_masivo", file);
      const response = await sendNative(url, "POST", body);
      const result = await response.json().catch(() => null) as { ok?: boolean; redirect?: string; errors?: Errors } | null;
      if (response.ok && result?.ok && result.redirect) { navigate(internal(result.redirect)); return; }
      if (response.status === 400 && result?.errors) {
        const { __all__: general = [], ...fields } = result.errors;
        setErrors(fields);
        setFormError(general.length ? general.join(" ") : "Revisá los campos marcados.");
      } else {
        setFormError(response.status === 403 ? "No tiene permiso para guardar este expediente." : `No se pudo guardar el expediente (${response.status}).`);
      }
      setPending(false);
    } catch (cause) {
      // The request may have been committed: never retry automatically.
      setUncertain(true); setPending(false);
      setFormError(cause instanceof TypeError ? "No se pudo confirmar el resultado. Revisá el listado de expedientes antes de volver a guardar." : "No se pudo guardar el expediente.");
    }
  };

  const runPreview = async () => {
    setPreviewError(""); setPreview(null);
    if (!file) { setPreviewError("Primero seleccioná un archivo Excel."); return; }
    const body = new FormData();
    body.append("excel_masivo", file);
    body.append("limit", limit);
    setPreviewing(true);
    try {
      const response = await sendNative(data.urls.preview, "POST", body);
      const result = await response.json().catch(() => null) as (Preview & { error?: string }) | null;
      if (!response.ok || !result || result.error) throw new Error(result?.error ?? `HTTP ${response.status}`);
      setPreview(result);
    } catch (cause) {
      setPreviewError(`Error al previsualizar: ${cause instanceof Error ? cause.message : "error inesperado"}`);
    } finally { setPreviewing(false); }
  };

  const closeLocalidades = () => { setLocalidades(false); localidadesButton.current?.focus(); };

  return <main className="canonical-expediente-form">
    <style>{STYLE}</style>
    <h1>{data.title}</h1>
    <form id="expediente-form" onSubmit={(event) => void submit(event)} noValidate aria-describedby={formError ? "expediente-form-error" : undefined}>
      {formError && <div id="expediente-form-error" role="alert" tabIndex={-1} ref={summary} className="error">{formError}</div>}
      <label htmlFor="id_numero_expediente">{numero.label}</label>
      <input id="id_numero_expediente" name="numero_expediente" type="text" defaultValue={numero.value} maxLength={numero.max_length} required={numero.required}
        aria-invalid={errors.numero_expediente ? true : undefined} aria-describedby={describedBy(!!errors.numero_expediente && "numero-errors")} />
      <FieldErrors id="numero-errors" messages={errors.numero_expediente} />

      <label htmlFor="id_observaciones">{observaciones.label}</label>
      <textarea id="id_observaciones" name="observaciones" rows={3} defaultValue={observaciones.value} required={observaciones.required}
        aria-invalid={errors.observaciones ? true : undefined} aria-describedby={describedBy(!!errors.observaciones && "observaciones-errors")} />
      <FieldErrors id="observaciones-errors" messages={errors.observaciones} />

      <label htmlFor="id_excel_masivo">{excel.label}{excel.required && !excel.current ? " *" : ""}</label>
      {excel.current && <p className="help">Actualmente: <a href={internal(excel.current.url)}>{excel.current.name}</a></p>}
      <input id="id_excel_masivo" name="excel_masivo" type="file" accept={excel.accept} required={excel.required && !excel.current}
        onChange={(e) => { setFile(e.target.files?.[0] ?? null); setPreview(null); setPreviewError(""); }}
        aria-invalid={excelErrors?.length ? true : undefined} aria-describedby={describedBy("excel-help", !!excelErrors?.length && "excel-errors")} />
      <p id="excel-help" className="help">Solo archivos .xlsx de hasta {Math.round(excel.max_bytes / (1024 * 1024))} MB.{excel.current ? " Si no seleccionás otro, se conserva el archivo actual." : ""}</p>
      <FieldErrors id="excel-errors" messages={excelErrors} />
      {previewError && <p className="error" role="status">{previewError}</p>}

      <div className="actions">
        <div>
          <button type="button" ref={localidadesButton} aria-expanded={localidades} aria-controls="localidades-panel" onClick={() => setLocalidades((open) => !open)}>Buscar localidades</button>
          <label style={{ margin: 0, fontWeight: 400 }}>Filas a previsualizar <select value={limit} onChange={(e) => setLimit(e.target.value)}>
            {PREVIEW_LIMITS.map((value) => <option key={value} value={value}>{value}</option>)}
            <option value={String(data.preview_max_limit)}>{data.preview_max_limit}</option>
            <option value="all">Todas</option>
          </select></label>
          <button type="button" onClick={() => void runPreview()} disabled={previewing} aria-busy={previewing || undefined}>{previewing ? "Cargando…" : "Previsualizar Excel"}</button>
        </div>
        <div>
          <a className="button" href={internal(data.urls.plantilla)}>Descargar plantilla</a>
          <button type="submit" disabled={disabled} aria-busy={pending || undefined}>{pending ? "Guardando…" : "Guardar"}</button>
          <a className="button" href={internal(data.urls.cancel)}>Cancelar</a>
        </div>
      </div>
    </form>
    <div id="localidades-panel">{localidades && <LocalidadesPanel url={data.urls.localidades} provincias={data.provincias} onClose={closeLocalidades} />}</div>
    {preview && <section aria-labelledby="preview-title">
      <h2 id="preview-title">Vista previa del Excel</h2>
      {typeof preview.total_rows === "number" && <p>{`Mostrando ${preview.shown_rows ?? preview.rows.length} de ${preview.total_rows} filas.`}</p>}
      <div className="scroll" role="region" aria-label="Tabla de vista previa" tabIndex={0}>
        <table aria-labelledby="preview-title"><thead><tr>{preview.headers.map((header) => <th key={header} scope="col">{header}</th>)}</tr></thead>
          <tbody>{preview.rows.map((row, index) => <tr key={index}>{preview.headers.map((header) => <td key={header}>{String(row[header] ?? "")}</td>)}</tr>)}</tbody></table>
      </div>
    </section>}
  </main>;
}

const defaultNavigate = (url: string) => window.location.assign(url);

export function ExpedienteNuevoScreen({ navigate = defaultNavigate }: Props) {
  return <ExpedienteForm url="/celiaquia/expedientes/nuevo/" navigate={navigate} />;
}

export function ExpedienteEditarScreen({ params, navigate = defaultNavigate }: Props) {
  const pk = /^\d+$/.test(params.pk ?? "") ? params.pk : "";
  if (!pk) return <main><p role="alert">No se encontró el recurso solicitado.</p></main>;
  return <ExpedienteForm url={`/celiaquia/expedientes/${pk}/editar/`} navigate={navigate} />;
}
