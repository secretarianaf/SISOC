import { InetDialog as Dialog } from "./Dialog";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Accordion, AccordionDetails, AccordionSummary, Alert, AlertTitle, Box, Button, Checkbox, DialogActions, DialogContent, DialogContentText, DialogTitle, FormControlLabel, IconButton, LinearProgress, Stack, TextField, Typography } from "@mui/material";
import { inetClient, mensajeDeError, type InetCitizenPage, type InetEnrollmentInput, type InetForm, type InetItem } from "@sisoc/api";
import Close from "@mui/icons-material/Close";
import ExpandMore from "@mui/icons-material/ExpandMore";
import { fieldLabels, frames } from "./design";
import { Field } from "./Fields";
import { useInet, validationFields } from "./data";

export function EnrollmentDialog({ commissionId, onClose, onSaved }: { commissionId: number; onClose: () => void; onSaved: (message: string) => void }) {
  const [sinDni, setSinDni] = useState(false);
  const [document, setDocument] = useState("");
  const [lookup, setLookup] = useState("");
  const schema = useInet<InetForm>(`ciudadano-form/?sin_dni=${sinDni}`);
  const citizens = useInet<InetCitizenPage>(`comisiones/${commissionId}/ciudadanos/?documento=${encodeURIComponent(lookup)}`, !!lookup && !sinDni);
  const found = !sinDni ? citizens.data?.results[0] : undefined;
  return <Dialog open onClose={onClose} fullWidth maxWidth="sm" aria-labelledby="enrollment-title" data-figma-node={sinDni ? frames.enrollmentNoDocument : lookup && citizens.data?.count === 0 ? frames.enrollmentMissing : frames.enrollmentNew}>
    <DialogTitle id="enrollment-title">Nuevo inscripto<IconButton aria-label="Cerrar formulario" onClick={onClose} sx={{ position: "absolute", top: 8, right: 8 }}><Close /></IconButton></DialogTitle>
    <DialogContent>
      {!sinDni && <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 1, mb: 3, alignItems: "flex-start" }}>
        <TextField label="DNI o pasaporte" required value={document} helperText="Sin puntos ni espacios también vale" onChange={(event) => { setDocument(event.target.value.replace(/[.\s]/g, "")); setLookup(""); }} fullWidth />
        <Button variant="outlined" sx={{ flexShrink: 0, mt: { sm: "11px !important" } }} disabled={document.length < 6 || citizens.isFetching} onClick={() => setLookup(document)}>Buscar en SISOC</Button>
      </Stack>}
      {citizens.isFetching && <LinearProgress aria-label="Buscando ciudadano" sx={{ mb: 2 }} />}
      {citizens.error && <Alert severity="error" sx={{ mb: 3 }}>{mensajeDeError(citizens.error)}</Alert>}
      {found && <Alert severity="success" sx={{ mb: 3 }}><AlertTitle>Encontrado en SISOC</AlertTitle>{found.apellido}, {found.nombre} · {found.documento}. Los datos de identidad se toman de Ciudadanos y no se editan acá.</Alert>}
      {!!lookup && citizens.data?.count === 0 && <Alert severity="warning" sx={{ mb: 3 }}><AlertTitle>No encontramos el documento en SISOC</AlertTitle>Revisá el número. Si es correcto, completá los datos para dar de alta a la persona.</Alert>}
      {!found && <Box sx={{ mt: sinDni ? 1 : 0 }}>
        <FormControlLabel control={<Checkbox checked={sinDni} onChange={(_, checked) => { setSinDni(checked); setLookup(""); }} />} label="La persona no conoce su DNI" />
        <Typography variant="caption" color="text.secondary" component="p" sx={{ ml: 4, mt: -0.5 }}>Se inscribe con sus datos cargados a mano y queda Sin validar</Typography>
      </Box>}
      {sinDni && <Alert severity="info" sx={{ mt: 3 }}><AlertTitle>Se inscribe sin DNI</AlertTitle>Queda Sin validar. Indicá el motivo de acuerdo con el circuito de Ciudadanos.</Alert>}
    </DialogContent>
    {schema.error && <DialogContent><Alert severity="error">{mensajeDeError(schema.error)}</Alert></DialogContent>}
    {schema.data && (sinDni || !!citizens.data) && <EnrollmentFields key={`${sinDni}-${lookup}-${found?.id ?? "new"}`} schema={schema.data} citizenId={found?.id} citizenName={found ? `${found.apellido}, ${found.nombre}` : undefined} commissionId={commissionId} sinDni={sinDni} document={lookup} onClose={onClose} onSaved={onSaved} />}
    {!sinDni && !citizens.data && <DialogActions><Button onClick={onClose}>Cancelar</Button></DialogActions>}
  </Dialog>;
}
function EnrollmentFields({ schema, citizenId, citizenName, commissionId, sinDni, document, onClose, onSaved }: {
  schema: InetForm; citizenId?: number; citizenName?: string; commissionId: number; sinDni: boolean; document: string; onClose: () => void; onSaved: (message: string) => void;
}) {
  const [values, setValues] = useState<Record<string, unknown>>(() => ({ ...Object.fromEntries(schema.fields.map((field) => [field.name, field.value])), documento: document, tipo_documento: /^[0-9]+$/.test(document) ? "DNI" : "PASAPORTE",
    ...(sinDni ? { tipo_registro_identidad: "SIN_DNI", tipo_documento: "DNI" } : {}) }));
  const [observations, setObservations] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const client = useQueryClient();
  async function save(event: React.FormEvent) {
    event.preventDefault(); setPending(true); setError(undefined);
    try {
      const data = { ciudadano_id: citizenId, ciudadano: values, observaciones: observations } as InetEnrollmentInput;
      await inetClient.post(`comisiones/${commissionId}/inscribir/`, data);
      await client.invalidateQueries({ queryKey: ["inet"] });
      const name = citizenName || [values.apellido, values.nombre].filter(Boolean).join(", ");
      onSaved(`${name ? `${name}: ` : ""}inscripción realizada en la comisión ${commissionId}${sinDni ? " · Sin validar" : ""}`);
    } catch (failure) { setError(failure); } finally { setPending(false); }
  }
  return <Box component="form" onSubmit={save}><DialogContent>
    {!!error && <Alert severity="error" sx={{ mb: 2 }}>{mensajeDeError(error)}</Alert>}
    {!citizenId && <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 3 }}>
      {["apellido", "nombre", "fecha_nacimiento", "motivo_sin_dni", "motivo_sin_dni_descripcion", "email", "telefono"].flatMap((name) => schema.fields.filter((field) => field.name === name)).map((field) => <Box key={field.name} sx={{ gridColumn: field.kind === "date" || field.kind === "textarea" ? "1 / -1" : undefined }}><Field field={{ ...field, help_text: field.help_text || (field.name === "telefono" ? "Puede ser de un familiar o referente" : field.name === "email" && !field.required ? "Opcional" : ""), label: fieldLabels[field.name] || field.label }} error={validationFields(error)[field.name]} values={values} value={values[field.name]} onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))} /></Box>)}
    </Box>}
    {!citizenId && schema.fields.some((field) => !["apellido", "nombre", "fecha_nacimiento", "motivo_sin_dni", "motivo_sin_dni_descripcion", "email", "telefono", "documento"].includes(field.name)) && <Accordion disableGutters elevation={0} sx={{ mt: 3 }}><AccordionSummary expandIcon={<ExpandMore />}>Datos adicionales de identidad</AccordionSummary><AccordionDetails><Stack spacing={3}>{schema.fields.filter((field) => !["apellido", "nombre", "fecha_nacimiento", "motivo_sin_dni", "motivo_sin_dni_descripcion", "email", "telefono", "documento"].includes(field.name)).map((field) => <Field key={field.name} field={field} values={values} value={values[field.name]} onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))} />)}</Stack></AccordionDetails></Accordion>}
    <TextField label="Observaciones" placeholder="Aclaraciones sobre la inscripción" helperText="Opcional" multiline minRows={3} fullWidth value={observations} onChange={(event) => setObservations(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} sx={{ mt: 3 }} />
  </DialogContent><DialogActions sx={{ px: 3, pb: 3 }}><Button onClick={onClose} disabled={pending}>Cancelar</Button><Button type="submit" variant="contained" disabled={pending}>Inscribir</Button></DialogActions></Box>;
}
export function EnrollmentState({ item, cancel, onClose, onSaved }: { item: InetItem; cancel: boolean; onClose: () => void; onSaved: () => void }) {
  const schema = useInet<InetForm>(`inscripciones/${item.id}/estado/`);
  if (!schema.data) return <Dialog open onClose={onClose}><DialogContent>{schema.error ? <Alert severity="error">{mensajeDeError(schema.error)}</Alert> : <LinearProgress aria-label="Cargando inscripción" />}</DialogContent><DialogActions><Button onClick={onClose}>Cerrar</Button></DialogActions></Dialog>;
  return <EnrollmentStateFields item={item} cancel={cancel} schema={schema.data} onClose={onClose} onSaved={onSaved} />;
}
function EnrollmentStateFields({ item, cancel, schema, onClose, onSaved }: { item: InetItem; cancel: boolean; schema: InetForm; onClose: () => void; onSaved: () => void }) {
  const [values, setValues] = useState<Record<string, unknown>>(() => ({ ...Object.fromEntries(schema.fields.map((field) => [field.name, field.value])), ...(cancel ? { estado: "abandonada" } : {}) }));
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  const client = useQueryClient();
  async function save() {
    setPending(true); setError(undefined);
    try { await inetClient.post(`inscripciones/${item.id}/estado/`, values); await client.invalidateQueries({ queryKey: ["inet"] }); onSaved(); }
    catch (failure) { setError(failure); } finally { setPending(false); }
  }
  return <Dialog open onClose={onClose} fullWidth maxWidth="sm" aria-labelledby="enrollment-state-title" data-figma-node={cancel ? frames.enrollmentCancel : frames.enrollmentEdit}><DialogTitle id="enrollment-state-title">{cancel ? `¿Dar de baja a ${item.nombre}?` : "Editar inscripto"}<IconButton aria-label="Cerrar formulario" onClick={onClose} sx={{ position: "absolute", top: 8, right: 8 }}><Close /></IconButton></DialogTitle>
    <DialogContent>{!!error && <Alert severity="error" sx={{ mb: 2 }}>{mensajeDeError(error)}</Alert>}
      {cancel ? <DialogContentText>Deja de ocupar un lugar del cupo. Su asistencia se conserva y sigue en la lista con estado Baja.</DialogContentText> : <>
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 3, mb: 3 }}>{[["Apellido y nombre", item.nombre], ["Documento", item.documento || "Sin DNI"]].map(([label, value]) => <Box key={label}><Typography variant="caption" color="text.secondary">{label}</Typography><Typography variant="body2" sx={{ fontWeight: 500 }}>{value}</Typography></Box>)}</Box>
        <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 3, ml: 1.5 }}>La identidad y los datos de contacto se administran en el módulo Ciudadanos.</Typography>
        <Stack spacing={3}><Stack direction={{ xs: "column", sm: "row" }} spacing={2}><TextField fullWidth label="Email" value={item.email || ""} slotProps={{ input: { readOnly: true } }} /><TextField fullWidth label="Teléfono" value={item.telefono || ""} slotProps={{ input: { readOnly: true } }} /></Stack>{schema.fields.map((field) => <Field key={field.name} field={field} values={values} value={values[field.name]} onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))} />)}</Stack>
      </>}
    </DialogContent><DialogActions sx={{ px: 3, pb: 3 }}><Button onClick={onClose} disabled={pending}>{cancel ? "Volver" : "Cancelar"}</Button><Button variant="contained" color={cancel ? "error" : "primary"} onClick={save} disabled={pending}>{cancel ? "Dar de baja" : "Guardar"}</Button></DialogActions></Dialog>;
}
