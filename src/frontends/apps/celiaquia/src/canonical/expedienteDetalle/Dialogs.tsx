import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { ErrorText, Modal, getNative, postNative, formatDate, type NativeResult } from "./native";
import { SearchableSelect } from "./SearchableSelect";
import type { Catalogos, Detalle, Legajo, Notice } from "./types";

/** Runs a native mutation; resolves true when it succeeded and the page reloaded. */
export type Run = (task: () => Promise<NativeResult | void>, success?: (result: NativeResult) => string | Notice) => Promise<boolean>;
type Common = { onClose: () => void; run: Run; pending: boolean; error: string };

const MENSAJE_SIN_MOTIVO = "Seleccioná al menos un motivo o completá la información complementaria.";

function Footer({ onClose, pending, label, form }: { onClose: () => void; pending: boolean; label: string; form: string }) {
  return <><button type="button" onClick={onClose}>Cancelar</button><button type="submit" form={form} disabled={pending}>{pending ? "Enviando…" : label}</button></>;
}

type Motivo = { id: string | number; etiqueta: string; pendiente: boolean };

/** Rechazar / Subsanar: motives come from the native preview endpoint, only ids travel back. */
export function MotivoDialog({ kind, legajo, complementaria, onClose, run, pending, error }: Common & { kind: "RECHAZAR" | "SUBSANAR"; legajo: Legajo; complementaria: Detalle["complementaria"] }) {
  const [motivos, setMotivos] = useState<Motivo[] | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [localError, setLocalError] = useState("");
  useEffect(() => {
    if (!legajo.actions.motivo_preview) return;
    getNative(legajo.actions.motivo_preview)
      .then((data) => setMotivos(data.tiene_observaciones ? (data.opciones as Motivo[]) : []))
      .catch(() => setPreviewError("No se pudo cargar la previsualización."));
  }, [legajo.actions.motivo_preview]);
  const subsanar = kind === "SUBSANAR";
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const texto = String(form.get("texto_libre") ?? "").trim();
    if (!form.getAll("observaciones_ids").length && !texto) return setLocalError(MENSAJE_SIN_MOTIVO);
    const archivos = form.getAll("documentacion_complementaria").filter((file) => file instanceof File && file.size > 0) as File[];
    if (archivos.length > complementaria.max_archivos) return setLocalError(`Podés adjuntar hasta ${complementaria.max_archivos} archivos.`);
    if (archivos.some((file) => file.size > complementaria.max_mb * 1024 * 1024)) return setLocalError(`Cada archivo puede pesar hasta ${complementaria.max_mb} MB.`);
    setLocalError("");
    const body = new FormData();
    body.append("accion", kind);
    body.append("texto_libre", texto);
    form.getAll("observaciones_ids").forEach((id) => body.append("observaciones_ids", String(id)));
    archivos.forEach((file) => body.append("documentacion_complementaria", file));
    void run(() => postNative(legajo.actions.revisar!, body), () => `Legajo ${subsanar ? "enviado a subsanar" : "rechazado"}.`);
  };
  const formId = `motivo-${kind}`;
  return <Modal title={subsanar ? "Solicitud de subsanación" : "Motivo del Rechazo"} onClose={onClose} footer={<Footer onClose={onClose} pending={pending} label="Confirmar" form={formId} />}>
    <form id={formId} onSubmit={submit}>
      <fieldset><legend>{subsanar ? "Motivos a subsanar" : "Motivos del rechazo"}</legend>
        {previewError ? <p>{previewError}</p> : motivos === null ? <p role="status">Cargando…</p> : motivos.length === 0 ? <p>El legajo no tiene comentarios técnicos con observaciones. Para continuar, completá la información complementaria.</p>
          : motivos.map((motivo) => <label key={motivo.id} className="ed-check"><input type="checkbox" name="observaciones_ids" value={motivo.id} defaultChecked={motivo.pendiente} />{motivo.etiqueta}{!motivo.pendiente && <small> (ya comunicada en una instancia anterior)</small>}</label>)}
        <small>Elegí las observaciones de Comentarios Técnicos que corresponden a esta instancia. Las que no elijas quedan en el historial y no se le vuelven a pedir a la provincia.</small>
      </fieldset>
      <label>Información complementaria (opcional)<textarea name="texto_libre" rows={3} placeholder="Agregá algo puntual que no esté en las observaciones…" /></label>
      {subsanar && <label>Documentación complementaria (opcional)<input type="file" name="documentacion_complementaria" accept={complementaria.accept} multiple />
        <small>Hasta {complementaria.max_archivos} archivos PDF, JPG o PNG de {complementaria.max_mb} MB cada uno. Se adjunta a la solicitud completa y la provincia va a poder consultarla.</small></label>}
      <p><small>El legajo quedará en estado <strong>{subsanar ? "SUBSANAR" : "RECHAZADO"}</strong>{subsanar ? " y la provincia podrá actualizar los archivos." : " y la provincia verá los motivos elegidos."}</small></p>
      <ErrorText error={localError || error} />
    </form>
  </Modal>;
}

export function CorregirDialog({ legajo, ...common }: Common & { legajo: Legajo }) {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = new FormData();
    body.append("nuevo_estado", String(form.get("nuevo_estado")));
    const motivo = String(form.get("motivo") ?? "").trim();
    if (motivo) body.append("motivo", motivo);
    void common.run(() => postNative(legajo.actions.corregir_evaluacion!, body), (r) => r.message ?? "Evaluación corregida.");
  };
  return <Modal title="Corregir evaluación técnica" onClose={common.onClose} footer={<Footer onClose={common.onClose} pending={common.pending} label="Confirmar corrección" form="form-corregir" />}>
    <form id="form-corregir" onSubmit={submit}>
      <p>Estado actual: <strong>{legajo.revision_tecnico}</strong></p>
      <label>Seleccione acción *<select name="nuevo_estado" required defaultValue=""><option value="">Seleccionar...</option><option value="APROBADO">Validar</option><option value="RECHAZADO">Rechazar</option><option value="SUBSANADO">Marcar como subsanado</option></select></label>
      <label>Motivo de la corrección (opcional)<textarea name="motivo" rows={2} maxLength={500} /></label>
      <small>La corrección quedará registrada en el historial del legajo.</small>
      <ErrorText error={common.error} />
    </form>
  </Modal>;
}

const SLOT: Record<string, string> = { archivo1: "1", archivo2: "2", archivo3: "3" };

export function ArchivoDialog({ legajo, campo, ...common }: Common & { legajo: Legajo; campo: string }) {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body = new FormData(event.currentTarget);
    body.append("slot", SLOT[String(body.get("campo"))]);
    void common.run(() => postNative(legajo.actions.subir_archivo!, body), (r) => r.message ?? "Archivo guardado correctamente.");
  };
  return <Modal title="Subir/Editar archivo del legajo" onClose={common.onClose} footer={<Footer onClose={common.onClose} pending={common.pending} label="Guardar" form="form-archivo" />}>
    <form id="form-archivo" onSubmit={submit}>
      <label>Seleccionar archivo a actualizar<select name="campo" required defaultValue={campo}>{legajo.archivos.map((archivo) => <option key={archivo.campo} value={archivo.campo}>{archivo.label}</option>)}</select></label>
      <label>PDF o imagen<input type="file" name="archivo" required accept=".pdf,.jpg,.jpeg,.png" /></label>
      <ErrorText error={common.error} />
    </form>
  </Modal>;
}

export function RespuestaSubsanacionDialog({ legajo, ...common }: Common & { legajo: Legajo }) {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body = new FormData(event.currentTarget);
    if (!body.get("observacion_id")) body.delete("observacion_id");
    if (!String(body.get("descripcion") ?? "").trim()) body.delete("descripcion");
    void common.run(() => postNative(legajo.actions.responder_subsanacion!, body), (r) => r.message ?? "Archivos de subsanación cargados.");
  };
  return <Modal title="Responder subsanación" onClose={common.onClose} footer={<Footer onClose={common.onClose} pending={common.pending} label="Subir archivos" form="form-resp-subs" />}>
    <form id="form-resp-subs" onSubmit={submit}>
      <label>Observación que corrige (opcional)<select name="observacion_id" defaultValue=""><option value="">General (toda la subsanación)</option>{legajo.subsanacion_activa?.observaciones_opciones.map((obs) => <option key={obs.id} value={obs.id}>{obs.label}</option>)}</select></label>
      <label>Archivos corregidos *<input type="file" name="archivos" multiple required /></label>
      <small>Podés seleccionar varios archivos. La documentación original del legajo se conserva.</small>
      <label>Descripción (opcional)<input type="text" name="descripcion" maxLength={255} placeholder="Ej: DNI frente corregido y nueva biopsia" /></label>
      <ErrorText error={common.error} />
    </form>
  </Modal>;
}

export function RespuestaRenaperDialog({ legajo, ...common }: Common & { legajo: Legajo }) {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body = new FormData(event.currentTarget);
    void common.run(() => postNative(legajo.actions.responder_renaper!, body), (r) => r.message ?? "Respuesta enviada.");
  };
  return <Modal title="Respuesta a subsanación" onClose={common.onClose} footer={<Footer onClose={common.onClose} pending={common.pending} label="Enviar Respuesta" form="form-resp-renaper" />}>
    <form id="form-resp-renaper" onSubmit={submit}>
      <label>Comentario de respuesta<textarea name="comentario" rows={3} required placeholder="Explique las correcciones realizadas..." defaultValue={legajo.renaper.comentario} /></label>
      <label>Archivo de respuesta *<input type="file" name="archivo" required accept=".pdf,.jpg,.jpeg,.png" /></label>
      <ErrorText error={common.error} />
    </form>
  </Modal>;
}

const RENAPER_FIELDS: [string, string][] = [
  ["documento", "DNI"], ["nombre", "Nombre"], ["apellido", "Apellido"], ["fecha_nacimiento", "Fecha Nacimiento"],
  ["sexo", "Sexo"], ["calle", "Calle"], ["altura", "Altura"], ["piso_departamento", "Piso/Depto"],
  ["ciudad", "Ciudad"], ["provincia", "Provincia"], ["codigo_postal", "Código Postal"],
];
const comparable = (value: unknown) => String(value ?? "").normalize("NFD").replace(/\p{Diacritic}/gu, "").replace(/\s+/g, " ").trim().toLowerCase();

/** Read-only Renaper comparison; the native endpoint is a POST but changes nothing visible here. */
export function RenaperDialog({ legajo, onClose }: { legajo: Legajo; onClose: () => void }) {
  const [data, setData] = useState<NativeResult | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    postNative(legajo.actions.validar_renaper!, new FormData()).then(setData).catch((cause: Error) => setError(`Error validación Renaper: ${cause.message}`));
  }, [legajo.actions.validar_renaper]);
  const provincia = (data?.datos_provincia ?? {}) as Record<string, string>;
  const renaper = (data?.datos_renaper ?? {}) as Record<string, string>;
  const ejemplar = data?.datos_ejemplar as { emision?: string; ejemplar?: string; vencimiento?: string; vencido?: boolean | null } | undefined;
  const table = (title: string, values: Record<string, string>) => <section><h3>{title}</h3><table><tbody>
    {RENAPER_FIELDS.map(([key, label]) => {
      const match = comparable(provincia[key] || "-") === comparable(renaper[key] || "-");
      return <tr key={key} className={match ? "ed-match" : "ed-mismatch"}><th scope="row">{label}</th><td>{values[key] || "-"}{!match && <span className="ed-sr"> (no coincide)</span>}</td></tr>;
    })}</tbody></table></section>;
  const partes = ejemplar ? [ejemplar.emision && `emitido el ${ejemplar.emision}`, ejemplar.ejemplar && `ejemplar ${ejemplar.ejemplar}`, ejemplar.vencimiento && (ejemplar.vencido ? `vencido el ${ejemplar.vencimiento}` : `vence el ${ejemplar.vencimiento}`)].filter(Boolean) : [];
  return <Modal title="Validación Renaper" onClose={onClose} wide footer={<button type="button" onClick={onClose}>Cerrar</button>}>
    <ErrorText error={error} />
    {!data && !error && <p role="status">Consultando datos en Renaper...</p>}
    {data && <><h3>Comparación de datos: {legajo.nombre} {legajo.apellido}</h3><div className="ed-grid2">{table("Datos de la Provincia", provincia)}{table("Datos de Renaper", renaper)}</div>
      {partes.length > 0 && <p className={ejemplar?.vencido ? "ed-alert ed-warning" : "ed-alert ed-info"}>DNI {partes.join(" · ")}. {ejemplar?.vencido ? "Los datos de arriba corresponden a este ejemplar, que ya está vencido." : "Los datos de arriba corresponden a este ejemplar."}</p>}</>}
  </Modal>;
}

export function CruceDialog({ url, ...common }: Common & { url: string }) {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const file = (event.currentTarget.elements.namedItem("excel_cuit") as HTMLInputElement).files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("archivo", file);
    void common.run(() => postNative(url, body), (r) => r.message ?? "Cruce procesado.");
  };
  return <Modal title="Subir Excel de Documentos (con encabezado)" onClose={common.onClose} footer={<Footer onClose={common.onClose} pending={common.pending} label="Ejecutar Cruce" form="form-cruce" />}>
    <form id="form-cruce" onSubmit={submit}>
      <label>Archivo Excel (.xlsx) con columna <code>documento</code><input type="file" name="excel_cuit" required accept=".xlsx,.xls,.csv" /></label>
      <small>Debe incluir encabezado; columna valida: <strong>documento</strong>.</small>
      <ErrorText error={common.error} />
    </form>
  </Modal>;
}

type LegajoForm = Record<string, string>;

export function EditarLegajoDialog({ legajo, catalogos, ...common }: Common & { legajo: Legajo; catalogos: Catalogos | null }) {
  const [values, setValues] = useState<LegajoForm | null>(null);
  const [loadError, setLoadError] = useState("");
  useEffect(() => {
    getNative(legajo.actions.editar!).then((data) => {
      const raw = (data.legajo ?? {}) as Record<string, unknown>;
      setValues(Object.fromEntries(Object.entries(raw).map(([key, value]) => [key, value == null ? "" : String(value)])));
    }).catch((cause: Error) => setLoadError(cause.message || "Error al cargar los datos del legajo."));
  }, [legajo.actions.editar]);
  const set = (key: string, value: string) => setValues((previous) => ({ ...previous!, [key]: value, ...(key === "municipio" ? { localidad: "" } : {}) }));
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void common.run(() => postNative(legajo.actions.editar!, new FormData(event.currentTarget)), (r) => r.message ?? "Legajo actualizado.");
  };
  const field = (name: string, label: string, props: Record<string, unknown> = {}) => <label>{label}<input name={name} value={values?.[name] ?? ""} onChange={(e) => set(name, e.target.value)} {...props} /></label>;
  const select = (name: string, label: string, options: { id: number; label: string }[], required = true) => <label>{label}<select name={name} required={required} value={values?.[name] ?? ""} onChange={(e) => set(name, e.target.value)}><option value="">Seleccionar...</option>{options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}</select></label>;
  // Long lists use a search box like the select2 widgets of the native modal.
  const searchable = (name: string, label: string, options: { id: number; label: string }[]) => <SearchableSelect label={label} name={name} required placeholder="Seleccionar..." value={values?.[name] ?? ""} onChange={(value) => set(name, value)} options={options.map((o) => ({ value: String(o.id), label: o.label }))} />;
  const localidades = (catalogos?.localidades ?? []).filter((loc) => String(loc.municipio_id) === (values?.municipio ?? "")).map((loc) => ({ id: loc.id, label: `${loc.label} (${loc.municipio})` }));
  return <Modal title="Editar datos del legajo" wide onClose={common.onClose} footer={values ? <Footer onClose={common.onClose} pending={common.pending} label="Guardar cambios" form="form-editar-legajo" /> : undefined}>
    <ErrorText error={loadError} />
    {!values && !loadError && <p role="status">Cargando…</p>}
    {values && <form id="form-editar-legajo" className="ed-form-grid" onSubmit={submit}>
      {field("apellido", "Apellido *", { required: true })}{field("nombre", "Nombre *", { required: true })}
      {field("documento", "CUIL *", { required: true })}{field("fecha_nacimiento", "Fecha de Nacimiento *", { required: true, type: "date" })}
      {select("sexo", "Sexo *", catalogos?.sexos ?? [])}{searchable("nacionalidad", "Nacionalidad *", catalogos?.nacionalidades ?? [])}
      {field("telefono", "Teléfono")}{field("email", "Email", { type: "email" })}
      {field("calle", "Calle")}{field("altura", "Altura")}{field("codigo_postal", "Código Postal")}
      {searchable("municipio", "Municipio *", catalogos?.municipios ?? [])}{searchable("localidad", "Localidad *", localidades)}
      <ErrorText error={common.error} />
    </form>}
  </Modal>;
}

export function ComentarioDialog({ legajo, comentarios, ...common }: Common & { legajo: Legajo; comentarios: Detalle["comentarios"] }) {
  const [tipo, setTipo] = useState("");
  const [tiene, setTiene] = useState("");
  const [codigo, setCodigo] = useState("");
  const opciones = comentarios.catalogo[tipo] ?? [];
  const libre = tiene === "si" && Boolean(opciones.find((o) => o.codigo === codigo)?.libre);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void common.run(() => postNative(legajo.actions.agregar_comentario!, new FormData(event.currentTarget)), (r) => r.message ?? "Comentario agregado.");
  };
  return <Modal title="Agregar comentario técnico" onClose={common.onClose} footer={<Footer onClose={common.onClose} pending={common.pending} label="Guardar comentario" form="form-comentario" />}>
    <form id="form-comentario" onSubmit={submit}>
      <label>Tipo de documento *<select name="tipo_documento" required value={tipo} onChange={(e) => { setTipo(e.target.value); setCodigo(""); }}><option value="">Seleccioná un tipo…</option>{comentarios.tipos_documento.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}</select></label>
      <label>¿Tiene observaciones? *<select name="tiene_observaciones" required value={tiene} onChange={(e) => setTiene(e.target.value)}><option value="">Seleccioná…</option><option value="si">Sí</option><option value="no">No</option></select></label>
      {tiene === "si" && <fieldset><legend>Observaciones *</legend>
        {opciones.length === 0 ? <p>Seleccioná primero un tipo de documento.</p> : opciones.map((o) => <label key={o.codigo} className="ed-check"><input type="radio" name="observacion_codigo" value={o.codigo} required checked={codigo === o.codigo} onChange={() => setCodigo(o.codigo)} />{o.texto}</label>)}
      </fieldset>}
      {libre && <label>Redactá la observación *<textarea name="observacion_libre" required rows={3} placeholder="Escribí la observación que se le va a comunicar a la provincia…" /></label>}
      <ErrorText error={common.error} />
    </form>
  </Modal>;
}

export function historialHref(page: number) {
  const params = new URLSearchParams(window.location.search);
  params.set("historial_page", String(page));
  return `${window.location.pathname}?${params}`;
}

export function HistorialDialog({ historial, onClose, onNavigate }: { historial: Detalle["historial"]; onClose: () => void; onNavigate: (href: string) => void }) {
  const pages = Array.from({ length: historial.num_pages }, (_, i) => i + 1);
  const link = (page: number, label: ReactNode, aria?: string) => <a href={historialHref(page)} aria-label={aria} aria-current={page === historial.page ? "page" : undefined} onClick={(event) => { event.preventDefault(); onNavigate(historialHref(page)); }}>{label}</a>;
  return <Modal title="Historial de Estados" wide onClose={onClose} footer={<button type="button" onClick={onClose}>Cerrar</button>}>
    <div className="ed-scroll" tabIndex={0} role="region" aria-label="Historial de estados"><table><thead><tr><th scope="col">Fecha</th><th scope="col">Estado Anterior</th><th scope="col">Estado Nuevo</th><th scope="col">Usuario</th><th scope="col">Observaciones</th></tr></thead>
      <tbody>{historial.items.length === 0 ? <tr><td colSpan={5}>Sin cambios de estado</td></tr> : historial.items.map((item) => <tr key={item.id}><td>{formatDate(item.fecha, true)}</td><td>{item.estado_anterior}</td><td>{item.estado_nuevo}</td><td>{item.usuario ?? "-"}</td><td className="ed-pre">{item.observaciones || "-"}</td></tr>)}</tbody></table></div>
    {historial.num_pages > 1 && <nav aria-label="Páginas del historial" className="ed-pages">
      {historial.page > 1 && link(historial.page - 1, "«", "Anterior")}
      {pages.map((page) => <span key={page}>{link(page, page)}</span>)}
      {historial.page < historial.num_pages && link(historial.page + 1, "»", "Siguiente")}
    </nav>}
  </Modal>;
}

export function FamiliasDialog({ legajos, onClose }: { legajos: Legajo[]; onClose: () => void }) {
  return <Modal title="Estructura Familiar" wide onClose={onClose} footer={<button type="button" onClick={onClose}>Cerrar</button>}>
    <div className="ed-scroll" tabIndex={0} role="region" aria-label="Estructura familiar"><table><thead><tr><th scope="col">Nombre</th><th scope="col">CUIL</th><th scope="col">Rol</th><th scope="col">Relación</th><th scope="col">Estado</th></tr></thead>
      <tbody>{legajos.map((leg) => <tr key={leg.id}><td>{leg.nombre} {leg.apellido}</td><td>{leg.documento}</td><td>{leg.es_responsable ? "Responsable" : "Beneficiario"}</td>
        <td>{leg.es_responsable ? (leg.hijos_a_cargo.length ? `A cargo de: ${leg.hijos_a_cargo.map((h) => `${h.nombre} ${h.apellido}`).join(", ")}` : "Sin hijos a cargo") : leg.responsables.map((name) => `Responsable: ${name}`).join(" ")}</td>
        <td>{leg.estado}</td></tr>)}</tbody></table></div>
  </Modal>;
}
