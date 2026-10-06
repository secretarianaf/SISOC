import { Fragment, useCallback, useEffect, useState, type FormEvent, type ReactElement } from "react";
import { Alert, Autocomplete, Button, Card, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, IconButton, Link, MenuItem, Snackbar, TextField, Tooltip, Typography, useMediaQuery } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { ApiError, get, postForm, type FormField, type FormSchema, type Itinerario, type Jornada } from "./api";

const titles: Record<string, string> = {
  "itinerario-edit": "Editar itinerario",
  "itinerario-subsanar": "Subsanar itinerario",
  "sede-create": "Nueva sede",
  "sede-edit": "Editar sede",
  "jornada-create": "Nueva jornada",
  "jornada-edit": "Editar jornada",
  checklist: "Checklist de jornada",
  "registro-create": "Nuevo registro nominal",
  "registro-edit": "Editar registro nominal",
  laboratorio: "Actualizar laboratorio",
  cierre: "Cierre diario",
};

function destination(kind: string, id: number) {
  if (kind.startsWith("itinerario")) return kind === "itinerario-create" ? "" : `itinerarios/${id}/`;
  if (kind.startsWith("sede")) return "sedes/";
  if (kind === "jornada-create") return `itinerarios/${id}/`;
  if (kind === "jornada-edit" || kind === "checklist" || kind === "registro-create" || kind === "cierre") return `jornadas/${id}/`;
  return "";
}

function renderField(field: FormField, update: (name: string, value: string | string[]) => void, value: string | string[], searchable = false, readOnly = false, errorText = "", externalLabel = false) {
  const common = { name: field.name, id: field.name, disabled: field.disabled, required: field.required };
  const helper = { error: Boolean(errorText), helperText: errorText || field.help || undefined };
  if (searchable && field.type === "select") {
    const selected = field.choices.find((choice) => choice.value !== "" && choice.value === String(value)) ?? null;
    return <>
      <input type="hidden" name={field.name} value={selected?.value ?? ""} disabled={field.disabled} />
      <Autocomplete
        id={field.name}
        disabled={field.disabled}
        options={field.choices.filter((choice) => choice.value !== "")}
        getOptionLabel={(option) => option.label}
        isOptionEqualToValue={(option, current) => option.value === current.value}
        value={selected}
        onChange={(_event, newValue) => update(field.name, newValue?.value ?? "")}
        noOptionsText="No se encontraron localidades"
        clearText="Limpiar selección"
        openText="Mostrar localidades"
        closeText="Cerrar localidades"
        renderInput={(params) => <TextField {...params} {...helper} label={externalLabel ? undefined : field.label} required={field.required} placeholder="Buscar localidad…" />}
      />
    </>;
  }
  if (field.type === "file") return <TextField {...common} {...helper} type="file" fullWidth />;
  if (field.type === "textarea") return <TextField {...common} {...helper} value={String(value)} multiline minRows={3} fullWidth onChange={(event) => update(field.name, event.target.value)} />;
  if (field.type === "multiselect") {
    const selected = (Array.isArray(value) ? value : []).flatMap((entry) => field.choices.filter((choice) => choice.value === entry));
    return <Autocomplete
      multiple
      disabled={field.disabled}
      options={field.choices}
      getOptionLabel={(option) => option.label}
      isOptionEqualToValue={(option, current) => option.value === current.value}
      value={selected}
      onChange={(_event, newValue) => update(field.name, newValue.map((option) => option.value))}
      renderInput={(params) => <TextField {...params} {...helper} placeholder="Buscar vehículo…" />}
    />;
  }
  if (field.type === "select") {
    return <TextField {...common} {...helper} select label={externalLabel ? undefined : field.label.replace(/\s*\*+\s*$/, "")} slotProps={externalLabel ? { select: { 'aria-labelledby': `${field.name}-label` } } : undefined} fullWidth value={String(value)} onChange={(event) => update(field.name, event.target.value)}>
      {field.choices.map((choice) => <MenuItem key={choice.value} value={choice.value}>{choice.label}</MenuItem>)}
    </TextField>;
  }
  if (field.type === "checkbox") return <Checkbox {...common} size="small" checked={value === "True" || value === "true"} onChange={(event) => update(field.name, event.target.checked ? "true" : "false")} />;
  return <TextField {...common} {...helper} type={field.type || "text"} value={String(value)} fullWidth slotProps={{ input: { readOnly }, htmlInput: { min: field.min || undefined, max: field.max || undefined, step: field.step || undefined } }} onChange={(event) => update(field.name, event.target.value)} />;
}

function ageFromBirthDate(value: string) {
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/) ?? value.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (!match) return "";
  const iso = value.includes("-");
  const birth = new Date(Number(match[iso ? 1 : 3]), Number(match[2]) - 1, Number(match[iso ? 3 : 1]));
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (today.getMonth() < birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())) age -= 1;
  return age >= 0 ? String(age) : "";
}

export function WorkflowForm({ kind, id, navigate }: { kind: string; id: number; navigate: (path: string) => void }) {
  const isJornada = kind.startsWith("jornada");
  const isRegistro = kind.startsWith("registro");
  const [schema, setSchema] = useState<FormSchema | null>(null);
  const [values, setValues] = useState<Record<string, string | string[]>>({});
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const [verified, setVerified] = useState(false);
  const [renaperMessage, setRenaperMessage] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [province, setProvince] = useState("");
  const [location, setLocation] = useState<{ query: string; direccion: string } | null>(null);
  const [locationBusy, setLocationBusy] = useState(false);
  const applySchema = useCallback((data: FormSchema) => {
    setSchema(data);
    const initial = Object.fromEntries(data.fields.map((field) => [field.name, field.value as string | string[]]));
    if (isRegistro && initial.resultado === "no_requiere") Object.assign(initial, { cantidad_lentes: "0", graduacion_izquierda: "", graduacion_derecha: "" });
    setValues(initial);
    setVerified(initial.renaper_estado === "validado");
    setRenaperMessage(initial.renaper_estado === "validado" ? "Validado RENAPER" : "");
  }, [isRegistro]);
  useEffect(() => {
    let active = true;
    get<FormSchema>(`/forms/${kind}/${id}/`)
      .then((data) => {
        if (!active) return;
        applySchema(data);
      })
      .catch((reason) => active && setError(reason));
    return () => { active = false; };
  }, [kind, id, applySchema]);
  useEffect(() => {
    if (!province || !kind.startsWith("sede")) return;
    get<FormSchema>(`/forms/${kind}/${id}/?provincia=${encodeURIComponent(province)}`)
      .then((data) => setSchema(data))
      .catch(setError);
  }, [kind, id, province]);
  function update(name: string, value: string | string[]) {
    setValues((current) => ({ ...current, [name]: value, ...(isRegistro && name === "resultado" && value === "no_requiere" ? { cantidad_lentes: "0", graduacion_izquierda: "", graduacion_derecha: "" } : {}) }));
    if (name === "ubicacion_url") setLocation(null);
    if (name === "provincia" && kind.startsWith("sede")) setProvince(String(value));
    if (name === "dni" || name === "referente_dni" || name === "sexo" || name === "referente_sexo") { setVerified(false); setRenaperMessage(""); }
  }
  async function verify() {
    setError(null);
    setVerifying(true);
    setVerified(false);
    setRenaperMessage("");
    const dni = String(values[isRegistro ? "dni" : "referente_dni"] || "");
    const sexo = String(values[isRegistro ? "sexo" : "referente_sexo"] || "");
    try {
      const jornada = kind === "registro-create" ? String(id) : schema?.back.match(/^jornadas\/(\d+)\//)?.[1] ?? "";
      const result = await get<{ success: boolean; message: string; data?: Record<string, string> }>(`/renaper/?dni=${encodeURIComponent(dni)}&sexo=${encodeURIComponent(sexo)}${isRegistro ? `&registro_nominal=1&jornada=${jornada}&registro=${kind === "registro-edit" ? id : ""}` : ""}`);
      setVerified(result.success);
      setRenaperMessage(result.message);
      if (result.success && result.data) {
        const person = result.data;
        setValues((current) => ({ ...current,
          ...Object.fromEntries(Object.entries(person).filter(([key]) => ["nombre", "apellido", "edad", "genero"].includes(key))),
          ...(isRegistro ? {
            edad: ageFromBirthDate(person.fecha_nacimiento || ""),
            ...(person.telefono ? { telefono: person.telefono } : {}),
            ...(["M", "F", "X"].includes(person.sexo) ? { sexo: person.sexo } : {}),
          } : {}),
        }));
      }
    } catch (reason) { setError(reason); }
    finally { setVerifying(false); }
  }
  async function previewLocation() {
    setError(null);
    setLocationBusy(true);
    const data = new FormData();
    data.set("ubicacion_url", String(values.ubicacion_url || ""));
    try {
      const result = await postForm<{ success: boolean; ubicacion_url: string; query: string; direccion: string }>("/ubicacion/", data);
      setLocation({ query: result.query, direccion: result.direccion });
      setValues((current) => {
        const initialAddress = schema?.fields.find((field) => field.name === "direccion")?.value;
        const unchangedAddress = !String(current.direccion || "").trim() || String(current.direccion).trim() === String(initialAddress || "").trim();
        return { ...current, ubicacion_url: result.ubicacion_url, direccion: unchangedAddress && result.direccion ? result.direccion : current.direccion };
      });
    } catch (reason) { setError(reason); }
    finally { setLocationBusy(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSaveMessage("");
    if (isRegistro && !verified) { setError(new Error("Debe verificar RENAPER antes de guardar.")); return; }
    setSaving(true);
    const data = new FormData(event.currentTarget);
    for (const field of schema?.fields || []) {
      if (field.disabled && field.name === "provincia") data.set("provincia", String(values.provincia || ""));
      if (field.type === "multiselect") {
        data.delete(field.name);
        for (const value of (values[field.name] as string[] || [])) data.append(field.name, value);
      }
    }
    if (isRegistro) {
      data.set("renaper_estado", verified ? "validado" : "");
      if (values.resultado === "no_requiere") {
        data.set("cantidad_lentes", "0");
        data.set("graduacion_izquierda", "");
        data.set("graduacion_derecha", "");
      }
    }
    if (kind.startsWith("jornada") && verified) {
      data.set("referente_nombre_renaper", String(values.nombre || ""));
      data.set("referente_apellido_renaper", String(values.apellido || ""));
    }
    try {
      const result = await postForm<{ redirect?: string }>(`/forms/${kind}/${id}/`, data, isRegistro);
      if (kind === "registro-create") {
        setSchema(null);
        setSaveMessage("Se creó el registro correctamente. Podés cargar el siguiente.");
        applySchema(await get<FormSchema>(`/forms/${kind}/${id}/`));
      } else navigate(result.redirect || schema?.back || destination(kind, id));
    } catch (reason) { setError(reason); }
    finally { setSaving(false); }
  }
  function registroField(name: string, wide = false) {
    const field = schema?.fields.find((entry) => entry.name === name);
    if (!field) return null;
    if (name === "cantidad_lentes" && values.resultado === "no_requiere") return <input key={name} type="hidden" name={name} value="0" />;
    if (field.type === "checkbox") return <FormControlLabel
      key={name}
      className="wide registro-checkbox"
      label={<span>{field.label}{field.help && <small>{field.help}</small>}</span>}
      control={<Checkbox size="small" name={name} disabled={field.disabled} checked={values[name] === "true" || values[name] === "True"} onChange={(event) => update(name, event.target.checked ? "true" : "false")} />}
    />;
    const required = name.startsWith("graduacion_")
      ? !field.graduacion_opcional && ["entregado_dia", "derivado", "enviado_laboratorio"].includes(String(values.resultado))
      : field.required;
    const readOnly = ["nombre", "apellido", "edad", "genero"].includes(name);
    const fieldErrors = error instanceof ApiError ? error.fields?.[name] : undefined;
    if (field.type === "select") return <div key={name} className={wide ? "wide" : ""}>
      {name === "sexo" && <Typography component="label" id="sexo-label" className="external-field-label">{field.label}{required ? " *" : ""}</Typography>}
      {renderField({ ...field, required, disabled: field.disabled || (verifying && ["dni", "sexo"].includes(name)) }, update, values[name] ?? field.value, false, readOnly, fieldErrors?.map((message) => message.message).join(", "), name === "sexo")}
    </div>;
    return <label key={name} className={`${wide ? "wide " : ""}${readOnly ? "registro-readonly" : ""}`} htmlFor={name}>
      {field.label}{required ? " *" : ""}
      {renderField({ ...field, required, disabled: field.disabled || (verifying && ["dni", "sexo"].includes(name)) }, update, values[name] ?? field.value, false, readOnly, fieldErrors?.map((message) => message.message).join(", "))}
      {readOnly && <small>Se completa al verificar RENAPER.</small>}
      {field.file_url && <Link href={field.file_url} target="_blank" rel="noreferrer">Ver archivo actual</Link>}
      {field.type === "checkbox" && field.help && <small>{field.help}</small>}
    </label>;
  }
  const attentionFields = ["graduacion_izquierda", "graduacion_derecha", "resultado", "cantidad_lentes", "adjunto", "primera_vez_anteojos", "observaciones"];
  return <>
    <Button className="back" variant="text" startIcon={<ArrowBackIcon />} onClick={() => navigate(schema?.back || destination(kind, id))}>Volver</Button>
    <div className="heading"><div><p className="eyebrow">Ver para ser libre</p><Typography variant="h4Bold" component="h1">{titles[kind] || "Formulario"}</Typography></div></div>
    {error && <Alert severity="error" role="alert" sx={{ mb: 2 }}>{error instanceof Error ? error.message : "Error al cargar el formulario."}{error instanceof ApiError && error.fields && <ul>{Object.entries(error.fields).map(([field, messages]) => <li key={field}>{field}: {messages.map((message) => message.message).join(", ")}</li>)}</ul>}</Alert>}
    <Snackbar open={Boolean(saveMessage)} autoHideDuration={6000} anchorOrigin={{ vertical: "bottom", horizontal: "left" }} onClose={() => setSaveMessage("")} sx={{ left: { xs: 3, md: 33 }, maxWidth: 520 }}>
      <Alert severity="success" variant="filled" elevation={6} role="status" onClose={() => setSaveMessage("")}>{saveMessage}</Alert>
    </Snackbar>
    {!schema && !error && <p>Cargando formulario…</p>}
    {schema?.instrucciones && <Alert severity="info" sx={{ mb: 2 }}><strong>Correcciones solicitadas:</strong> {schema.instrucciones}</Alert>}
    {schema && <Card component="section" className="card"><form className={`form-grid${isJornada ? " jornada-form" : ""}${isRegistro ? " registro-form" : ""}`} onSubmit={submit}>
      {isRegistro && <input type="hidden" name="renaper_estado" value={verified ? "validado" : ""} />}
      {isRegistro ? <>
        <section className="wide registro-section" aria-labelledby="registro-identificacion">
          <Typography id="registro-identificacion" component="h2" variant="h6" className="registro-section-title">Identificación RENAPER</Typography>
          <div className="form-grid registro-fields">
            {registroField("dni")}{registroField("sexo")}
            <div className="wide registro-verification">
              <Button type="button" size="small" variant="outlined" disabled={verifying} onClick={verify}>{verifying ? "Verificando…" : "Verificar RENAPER"}</Button>
              {renaperMessage && <Alert severity={verified ? "success" : "error"} role="status">{renaperMessage}</Alert>}
            </div>
          </div>
        </section>
        <section className="wide registro-section" aria-labelledby="registro-nominales">
          <Typography id="registro-nominales" component="h2" variant="h6" className="registro-section-title">Datos nominales</Typography>
          <div className="form-grid registro-fields">
            {schema.fields.filter((field) => !["dni", "sexo", "renaper_estado", ...attentionFields].includes(field.name)).map((field) => registroField(field.name))}
          </div>
        </section>
        <section className="wide registro-section" aria-labelledby="registro-atencion">
          <Typography id="registro-atencion" component="h2" variant="h6" className="registro-section-title">Atención oftalmológica</Typography>
          <div className="form-grid registro-fields">
            <Typography component="h3" variant="subtitle1Medium" className="wide">Graduación</Typography>
            {registroField("graduacion_izquierda")}{registroField("graduacion_derecha")}
            <div className="wide form-grid registro-resultados">{registroField("resultado")}{registroField("cantidad_lentes")}</div>
            {registroField("adjunto")}
            {registroField("primera_vez_anteojos", true)}
            {registroField("observaciones", true)}
          </div>
        </section>
      </> : kind === "checklist" ? schema.fields.filter((field) => field.name.endsWith("_cumple")).map((item) => {
        const prefix = item.name.slice(0, -"_cumple".length);
        const itemFields = [item, ...schema.fields.filter((field) => field.name === `${prefix}_observacion` || field.name === `${prefix}_evidencia`)];
        return <fieldset className="wide checklist-item" key={prefix} aria-label={item.label.replace(/\s*\*+\s*$/, "")}>
          {itemFields.map((field) => field.type === "checkbox" ? <FormControlLabel
            key={field.name}
            className="checkbox-row"
            label={<span>{field.label.replace(/\s*\*+\s*$/, "")}{field.help && <small>{field.help}</small>}</span>}
            control={renderField(field, update, values[field.name] ?? field.value) as ReactElement}
          /> : field.type === "select" ? <div key={field.name}>
            {renderField(field, update, values[field.name] ?? field.value)}
          </div> : <label key={field.name} htmlFor={field.name}>
            {field.label.replace(/\s*\*+\s*$/, "")}{field.required ? " *" : ""}
            {renderField(field, update, values[field.name] ?? field.value)}
            {field.file_url && <Link href={field.file_url} target="_blank" rel="noreferrer">Ver archivo actual</Link>}
          </label>)}
        </fieldset>;
      }) : schema.fields.filter((field) => field.name !== "localidad_filtro").map((field) => {
        const isPhoneField = field.name === "referente_telefono" || field.name === "telefono";
        const pairWithRenaper = isPhoneField && (kind.startsWith("registro") || kind.startsWith("jornada"));
        const fieldLabel = field.type === "checkbox" ? <FormControlLabel
          className="checkbox-row"
          label={<span>{field.label}{field.help && <small>{field.help}</small>}</span>}
          control={renderField(field, update, values[field.name] ?? field.value) as ReactElement}
        /> : field.type === "select" ? <div>
          {isJornada && field.name === "localidad" && <Typography component="label" htmlFor={field.name} className="external-field-label">{field.label}{field.required ? " *" : ""}</Typography>}
          {renderField(field, update, values[field.name] ?? field.value, isJornada && field.name === "localidad", false, "", isJornada && field.name === "localidad")}
        </div> : <label className={field.type === "textarea" || field.type === "multiselect" ? "wide" : ""} htmlFor={field.name}>
          {field.label}{field.required ? " *" : ""}
          {renderField(field, update, values[field.name] ?? field.value, isJornada && field.name === "localidad")}
          {field.file_url && <Link href={field.file_url} target="_blank" rel="noreferrer">Ver archivo actual</Link>}
        </label>;
        return <Fragment key={field.name}>
          {pairWithRenaper ? (
            <div className={`wide field-with-action${isJornada ? " jornada-referente" : ""}`}>
              {!isJornada && fieldLabel}
              <div className="verify-action">
                <Button type="button" variant="outlined" onClick={verify}>Consultar RENAPER</Button>
                {renaperMessage && <span className="verification" role="status">{renaperMessage}</span>}
              </div>
              {isJornada && fieldLabel}
            </div>
          ) : fieldLabel}
          {field.name === "direccion" && isJornada && <>
            <div className="location-action">
              <Button type="button" variant="outlined" disabled={locationBusy || !values.ubicacion_url} onClick={previewLocation}>{locationBusy ? "Buscando…" : "Verificar ubicación"}</Button>
            </div>
            {location?.query && <div className="wide location-preview">
              <p role="status">Dirección encontrada: {location.direccion || "Coordenadas confirmadas"}</p>
              <iframe className="location-map" title="Vista previa de la ubicación" loading="lazy" src={`https://www.google.com/maps?q=${encodeURIComponent(location.query)}&output=embed`} />
            </div>}
          </>}
        </Fragment>;
      })}
      <div className="form-actions"><Button variant="outlined" size={isRegistro ? "small" : "large"} type="button" onClick={() => navigate(schema?.back || destination(kind, id))}>{isRegistro ? "Volver" : "Cancelar"}</Button><Button variant="contained" size={isRegistro ? "small" : "large"} disabled={saving || verifying} type="submit">{saving ? "Guardando…" : kind === "registro-create" ? "Guardar y continuar" : "Guardar"}</Button></div>
    </form></Card>}
  </>;
}

export function ActionButton({ kind, id, label, after, data, iconOnly = false }: { kind: string; id: number; label: string; after?: () => void; data?: FormData; iconOnly?: boolean }) {
  const reducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<{ total_afectados: number; total_borrado_fisico: number; desglose_por_modelo: { modelo: string; cantidad: number; modo: string }[] } | null>(null);
  async function execute() {
    setBusy(true);
    setError("");
    try {
      await postForm(`/actions/${kind}/${id}/`, data || new FormData());
      setPreview(null);
      if (after) after();
      else window.location.reload();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo completar la acción."); }
    finally { setBusy(false); }
  }
  async function run() {
    if (!kind.startsWith("eliminar-")) { await execute(); return; }
    setBusy(true);
    setError("");
    try {
      const response = await get<{ preview: NonNullable<typeof preview> }>(`/actions/${kind}/${id}/`);
      setPreview(response.preview);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo cargar el detalle de la operación."); }
    finally { setBusy(false); }
  }
  const destructive = kind.startsWith("eliminar-");
  const actionIcon = destructive ? <DeleteIcon /> : kind === "presentar" ? <ArrowForwardIcon /> : kind === "cierre-definitivo" ? <CheckIcon /> : undefined;
  return <span className="action-control">
    {iconOnly
      ? <Tooltip title={label}><span><IconButton size="small" color="error" aria-label={label} disabled={busy} onClick={run}><DeleteIcon /></IconButton></span></Tooltip>
      : <Button variant="outlined" size="small" color={destructive ? "error" : "primary"} startIcon={actionIcon} disabled={busy} onClick={run}>{busy ? "Procesando…" : label}</Button>}
    {error && !preview && <small className="action-error" role="alert">{error}</small>}
    <Dialog open={!!preview} onClose={() => { if (!busy) setPreview(null); }} aria-labelledby={`delete-title-${kind}-${id}`} className="vpsl-delete-dialog" transitionDuration={reducedMotion ? 0 : undefined}>
      <DialogTitle id={`delete-title-${kind}-${id}`}>Confirmar: {label.toLowerCase()}</DialogTitle>
      <DialogContent>
        <p>Esta operación afecta {preview?.total_afectados} elementos. Revisá el detalle antes de continuar.</p>
        <ul>{preview?.desglose_por_modelo.map((item) => <li key={item.modelo}>{item.modelo}: {item.cantidad} ({item.modo === "borrado_fisico" ? "borrado físico" : "baja lógica"})</li>)}</ul>
        {error && <Alert severity="error" role="alert">{error}</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setPreview(null)} disabled={busy}>Cancelar</Button>
        <Button color="error" variant="contained" startIcon={<DeleteIcon />} onClick={execute} disabled={busy}>{busy ? "Eliminando…" : label}</Button>
      </DialogActions>
    </Dialog>
  </span>;
}

export function EvaluateItinerary({ itinerary }: { itinerary: Itinerario }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [cartaArchivoEstado, setCartaArchivoEstado] = useState(itinerary.carta_archivo_estado || "pendiente");
  const [cartaReferenciaEstado, setCartaReferenciaEstado] = useState(itinerary.carta_referencia_estado || "pendiente");
  const [observaciones, setObservaciones] = useState(itinerary.subsanacion_observaciones || "");
  const cartas = [
    itinerary.carta_archivo_url ? cartaArchivoEstado : null,
    itinerary.carta_referencia ? cartaReferenciaEstado : null,
  ].filter((value): value is string => value !== null);
  const pendientes = cartas.some((value) => value === "pendiente");
  const cartaRechazada = cartas.some((value) => value === "rechazado");
  const cartaAprobada = cartas.some((value) => value === "aprobado");
  const requiereSubsanacion = cartas.some((value) => value === "subsanar");
  const aprobarDisabled = pendientes || cartaRechazada || !cartaAprobada || requiereSubsanacion;
  const subsanarDisabled = pendientes || cartaRechazada || !requiereSubsanacion;
  const rechazarDisabled = pendientes;
  let feedback = { severity: "info" as "info" | "error" | "warning" | "success", text: "Debe evaluar todas las cartas para continuar." };
  if (!pendientes) {
    if (cartaRechazada) feedback = { severity: "error", text: "Aprobar está deshabilitado porque hay una carta rechazada. La opción permitida es Rechazar." };
    else if (requiereSubsanacion) feedback = { severity: "warning", text: "Debe indicar los campos a subsanar y enviar a Subsanación." };
    else if (!cartaAprobada) feedback = { severity: "warning", text: "Aprobar está deshabilitado: se requiere al menos una carta aprobada." };
    else feedback = { severity: "success", text: "La evaluación está completa y el itinerario puede aprobarse." };
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const accion = submitter?.value || "";
    if (accion === "subsanar" && !observaciones.trim()) {
      setError("Debe indicar qué campos debe subsanar Provincia.");
      return;
    }
    setBusy(true);
    const data = new FormData(event.currentTarget);
    data.set("accion_evaluacion", accion);
    try {
      await postForm(`/actions/evaluar/${itinerary.id}/`, data);
      window.location.reload();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo evaluar el itinerario."); }
    finally { setBusy(false); }
  }
  const options = itinerary.estados_evaluacion || [];
  return <Card component="section" className="card"><h2>Evaluación del itinerario</h2><p>Revisá la carta y decidí el estado del itinerario.</p>
    {error && <Alert severity="error" role="alert" sx={{ mb: 2 }}>{error}</Alert>}
    <form className="form-grid" onSubmit={submit}>
      {itinerary.carta_archivo_url && <label>Carta archivo <Link href={itinerary.carta_archivo_url} target="_blank" rel="noreferrer">Ver archivo</Link><TextField select name="carta_archivo_estado" fullWidth value={cartaArchivoEstado} onChange={(event) => setCartaArchivoEstado(event.target.value)}>{options.map((option) => <MenuItem value={option.value} key={option.value}>{option.label}</MenuItem>)}</TextField></label>}
      {itinerary.carta_referencia && <label>Carta referencia<TextField select name="carta_referencia_estado" fullWidth value={cartaReferenciaEstado} onChange={(event) => setCartaReferenciaEstado(event.target.value)}>{options.map((option) => <MenuItem value={option.value} key={option.value}>{option.label}</MenuItem>)}</TextField></label>}
      <label className="wide">Observaciones para Provincia<TextField name="subsanacion_observaciones" multiline minRows={3} fullWidth value={observaciones} onChange={(event) => setObservaciones(event.target.value)} /></label>
      <Alert severity={feedback.severity} sx={{ mt: 1 }} className="wide">{feedback.text}</Alert>
      <div className="form-actions">
        <Button variant="contained" startIcon={<CheckIcon />} disabled={busy || aprobarDisabled} type="submit" name="accion_evaluacion" value="aprobar">Aprobar</Button>
        <Button variant="outlined" startIcon={<ArrowForwardIcon />} disabled={busy || subsanarDisabled} type="submit" name="accion_evaluacion" value="subsanar">Pedir subsanación</Button>
        <Button variant="outlined" color="error" startIcon={<CloseIcon />} disabled={busy || rechazarDisabled} type="submit" name="accion_evaluacion" value="rechazar">Rechazar</Button>
      </div>
    </form>
  </Card>;
}

export function BulkLaboratory({ jornada }: { jornada: Jornada }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const available = jornada.laboratorio?.filter((caso) => caso.siguiente) || [];
  if (!available.length) return null;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try { await postForm(`/actions/laboratorio-masivo/${jornada.id}/`, new FormData(event.currentTarget)); window.location.reload(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudieron actualizar los casos."); }
    finally { setBusy(false); }
  }
  return <Card component="section" className="card"><h2>Actualizar laboratorio en lote</h2><p>Seleccioná casos de esta página que estén en el mismo estado.</p>{error && <Alert severity="error" role="alert" sx={{ mb: 2 }}>{error}</Alert>}
    <form className="form-grid" onSubmit={submit}>
      <div className="wide">{available.map((caso) => <FormControlLabel key={caso.id} className="checkbox-row" label={`${caso.persona} · ${caso.estado}`} control={<Checkbox size="small" name="casos" value={caso.id} />} />)}</div>
      <label>Fecha<TextField name="fecha" type="date" fullWidth required /></label><label>Responsable<TextField name="responsable" fullWidth required /></label>
      <div className="form-actions"><Button variant="contained" startIcon={<CheckIcon />} type="submit" disabled={busy}>{busy ? "Actualizando…" : "Actualizar seleccionados"}</Button></div>
    </form>
  </Card>;
}
