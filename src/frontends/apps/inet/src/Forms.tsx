import { InetDialog as Dialog } from "./Dialog";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { Accordion, AccordionDetails, AccordionSummary, Alert, AlertTitle, Box, Button, DialogActions, DialogContent, DialogTitle, IconButton, LinearProgress, Stack, Typography, FormControl, FormLabel, RadioGroup, FormControlLabel, Radio } from "@mui/material";
import ExpandMore from "@mui/icons-material/ExpandMore";
import Close from "@mui/icons-material/Close";
import Add from "@mui/icons-material/Add";
import Delete from "@mui/icons-material/Delete";
import ArrowBack from "@mui/icons-material/ArrowBack";
import School from "@mui/icons-material/School";
import { detail, fieldLabels, frames, joinDays, scheduleSummary } from "./design";
import { inetClient, mensajeDeError, type InetForm, type InetFormInput, type InetItem, type InetPage, type InetSession } from "@sisoc/api";
import { Field } from "./Fields";
import { formatDate, queryString, resources, ROOT, shortDate, useInet, updateField, validationFields, type Resource } from "./data";

// Textos de ayuda y placeholders de Figma; sólo describen reglas existentes del backend.
const helpTexts: Record<string, string> = {
  plan_estudio: "Planes cargados en Planes curriculares", ubicacion: "Sede o anexos cargados en Ubicaciones",
  fecha_fin: "Igual o posterior a la fecha de inicio", observaciones: "Opcional",
};
const placeholders: Partial<Record<Resource, Record<string, string>>> = {
  cursos: { observaciones: "Requisitos, materiales o aclaraciones" },
  comisiones: { observaciones: "Requisitos, materiales o aclaraciones para los inscriptos" },
};

export function FormDialog({ resource, item, initial = {}, onClose, onSaved }: {
  resource: Resource; item?: InetItem; initial?: Record<string, unknown>;
  onClose: () => void; onSaved: (item: InetItem, commission: boolean) => void;
}) {
  const base = `${resource}/${item ? `${item.id}/` : ""}`;
  const query = useInet<InetForm>(`${base}form/?${queryString(initial)}`);
  return <Dialog open onClose={onClose} fullWidth maxWidth={resource === "centros" || resource === "planes" ? "md" : "sm"} slotProps={{ paper: { sx: { maxWidth: resource === "cursos" ? 600 : undefined } } }} data-figma-node={resource === "cursos" ? item ? frames.courseEdit : frames.courseNew : undefined} aria-labelledby="inet-form-title">
    <DialogTitle id="inet-form-title">{item ? "Editar" : ["ubicaciones", "comisiones"].includes(resource) ? "Nueva" : "Nuevo"} {resources[resource].singular}<IconButton aria-label="Cerrar formulario" onClick={onClose} sx={{ position: "absolute", right: 8, top: 8 }}><Close /></IconButton></DialogTitle>
    {query.isLoading && <LinearProgress aria-label="Cargando formulario" />}
    {query.error && <DialogContent><Alert severity="error">{mensajeDeError(query.error)}</Alert></DialogContent>}
    {query.data && <ResourceForm resource={resource} item={item} initial={initial} schema={query.data} base={base} onClose={onClose} onSaved={onSaved} />}
  </Dialog>;
}
function ResourceForm({ resource, item, initial, schema, base, onClose, onSaved }: {
  resource: Resource; item?: InetItem; initial: Record<string, unknown>; schema: InetForm; base: string;
  onClose: () => void; onSaved: (item: InetItem, commission: boolean) => void;
}) {
  const [values, setValues] = useState<Record<string, unknown>>(() => ({ ...Object.fromEntries(schema.fields.map((field) => [field.name, field.value])), ...initial }));
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  const [createCommission, setCreateCommission] = useState(false);
  const errors = validationFields(error);
  const queryClient = useQueryClient();
  const order = resource === "cursos" ? ["plan_estudio", "nombre", "estado", "inscripcion_libre", "observaciones"] : resource === "comisiones" ? ["ubicacion", "cupo_total", "fecha_inicio", "fecha_fin", "observaciones"] : [];
  const visible = schema.fields.filter((field) => !(field.name === "centro" && (initial.centro || item?.centro_id)));
  const mainFields = order.length ? order.flatMap((name) => visible.filter((field) => field.name === name)) : visible;
  const additional = order.length ? visible.filter((field) => !order.includes(field.name)) : [];
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setError(undefined);
    try {
      const payload = { campos: values } as InetFormInput;
      const response = item ? await inetClient.put<InetItem>(base, payload) : await inetClient.post<InetItem>(base, payload);
      await queryClient.invalidateQueries({ queryKey: ["inet"] });
      onSaved(response.data, createCommission);
    } catch (failure) { setError(failure); } finally { setPending(false); }
  }
  return <Box component="form" onSubmit={save}>
    <DialogContent>{resource !== "cursos" && <Typography variant="caption" color="text.secondary">Los campos con * son obligatorios.</Typography>}
      {!!error && <Alert severity="error" sx={{ my: 2 }}>{Object.values(errors).join(" · ") || mensajeDeError(error)}</Alert>}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: ["centros", "planes"].includes(resource) ? "1fr 1fr" : "1fr" }, gap: 3, mt: 3 }}>
        {mainFields.map((field) => <Box key={field.name} sx={{ gridColumn: field.kind === "textarea" ? "1 / -1" : undefined }}>
          {resource === "cursos" && field.name === "inscripcion_libre" ? <FormControl>
            <FormLabel>Modalidad de inscripción *</FormLabel>
            <RadioGroup aria-label="Modalidad de inscripción" value={values.inscripcion_libre ? "libre" : "voucher"} onChange={(_, value) => setValues((current) => ({ ...current, inscripcion_libre: value === "libre" }))}>
              <FormControlLabel value="voucher" control={<Radio />} label={<Box><Typography variant="body1">Inscripción gestionada</Typography><Typography variant="caption" color="text.secondary">Alta por operador de SISOC; los vouchers conservan la configuración del curso</Typography></Box>} />
              <FormControlLabel value="libre" control={<Radio />} label={<Box><Typography variant="body1">Inscripción libre</Typography><Typography variant="caption" color="text.secondary">Abierta a cualquier ciudadano</Typography></Box>} />
            </RadioGroup>
          </FormControl> : <Field placeholder={placeholders[resource]?.[field.name]} field={{ ...field, help_text: field.help_text || (order.length ? helpTexts[field.name] : "") || "", label: resource === "cursos" && field.name === "nombre" ? "Nombre del curso" : resource === "cursos" && field.name === "plan_estudio" ? "Plan curricular" : field.label }} value={values[field.name]} values={values} optionsPath={`${base}options/`} error={errors[field.name]}
            onChange={(value) => setValues((current) => updateField(current, field.name, value))} />}
        </Box>)}
      </Box>
      {!!additional.length && <Accordion disableGutters elevation={0} sx={{ mt: 3, border: 1, borderColor: "divider", "&:before": { display: "none" } }}><AccordionSummary expandIcon={<ExpandMore />}>Configuración adicional</AccordionSummary><AccordionDetails><Stack spacing={3}>{additional.map((field) => <Field key={field.name} field={field} value={values[field.name]} values={values} optionsPath={`${base}options/`} error={errors[field.name]} onChange={(value) => setValues((current) => updateField(current, field.name, value))} />)}</Stack></AccordionDetails></Accordion>}
    </DialogContent>
    <DialogActions sx={{ p: 3 }}><Button onClick={onClose} disabled={pending}>Cancelar</Button>
      <Button type="submit" variant={resource === "cursos" && !item ? "outlined" : "contained"} disabled={pending} onClick={() => setCreateCommission(false)}>Guardar</Button>
      {resource === "cursos" && !item && <Button type="submit" variant="contained" disabled={pending} onClick={() => setCreateCommission(true)}>Guardar y crear comisión</Button>}
    </DialogActions>
  </Box>;
}
export function CommissionForm({ courseId }: { courseId: string }) {
  const query = useInet<InetForm>(`comisiones/form/?curso=${courseId}`);
  const schedule = useInet<InetForm>("horario-form/");
  const course = useInet<InetItem>(`cursos/${courseId}/`);
  if (query.error || schedule.error) return <Alert severity="error">{mensajeDeError(query.error || schedule.error)}</Alert>;
  if (!query.data || !schedule.data) return <LinearProgress aria-label="Cargando comisión" />;
  return <CommissionFields key={courseId} schema={query.data} schedule={schedule.data} courseId={courseId} course={course.data} />;
}
export function EditCommission({ session }: { session: InetSession }) {
  const { id } = useParams();
  const item = useInet<InetItem>(`comisiones/${id}/`);
  const schema = useInet<InetForm>(`comisiones/${id}/form/`);
  const schedule = useInet<InetForm>("horario-form/");
  const rows = useInet<InetPage>(`horarios/?comision=${id}&page_size=200`);
  const failure = item.error || schema.error || schedule.error || rows.error;
  if (failure) return <Alert severity="error">{mensajeDeError(failure)}</Alert>;
  if (!item.data || !schema.data || !schedule.data || !rows.data) return <LinearProgress aria-label="Cargando comisión" />;
  const initialRows = rows.data.results.filter((row) => detail(row, "Vigente") === "Sí").map((row) => ({ vigente: "1", dia_semana: schedule.data!.fields.find((field) => field.name === "dia_semana")?.options.find((option) => option.label === row.nombre)?.value || "", hora_desde: detail(row, "Hora desde").slice(0, 5), hora_hasta: detail(row, "Hora hasta").slice(0, 5) }));
  const manageSchedules = session.permissions.includes("add_comisionhorario") && session.permissions.includes("change_comisionhorario");
  return <CommissionFields key={id} schema={schema.data} schedule={schedule.data} courseId={String(item.data.curso_id)} course={item.data} item={item.data} initialRows={initialRows} manageSchedules={manageSchedules} />;
}
function CommissionFields({ schema, schedule, courseId, course, item, initialRows, manageSchedules = true }: { schema: InetForm; schedule: InetForm; courseId: string; course?: InetItem; item?: InetItem; initialRows?: Record<string, unknown>[]; manageSchedules?: boolean }) {
  const navigate = useNavigate();
  const client = useQueryClient();
  const [values, setValues] = useState<Record<string, unknown>>(() => ({ ...Object.fromEntries(schema.fields.map((field) => [field.name, field.value])), curso: courseId }));
  const [rows, setRows] = useState<Record<string, unknown>[]>(initialRows?.length ? initialRows : [{ vigente: "1" }]);
  const [confirm, setConfirm] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const [locationLabel, setLocationLabel] = useState(item ? detail(item, "Ubicación nombre") : "");
  const totalMinutes = rows.reduce((sum, row) => {
    const minutes = (time: unknown) => String(time ?? "").split(":").reduce((total, part, index) => total + Number(part) * (index === 0 ? 60 : 1), 0);
    return sum + Math.max(0, minutes(row.hora_hasta) - minutes(row.hora_desde));
  }, 0);
  const invalidSchedule = rows.some((row) => {
    const minutes = (value: unknown) => Number(String(value).slice(0, 2)) * 60 + Number(String(value).slice(3, 5));
    const duration = minutes(row.hora_hasta) - minutes(row.hora_desde);
    return !row.dia_semana || !row.hora_desde || !row.hora_hasta || duration < 45 || duration > 240;
  });
  const dayLabel = (row: Record<string, unknown>) => schedule.fields.find((field) => field.name === "dia_semana")?.options.find((option) => option.value === String(row.dia_semana))?.label || "";
  const days = rows.map((row) => schedule.fields.find((field) => field.name === "dia_semana")?.options.find((option) => option.value === String(row.dia_semana))?.label.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, ""));
  const start = new Date(`${values.fecha_inicio}T00:00:00Z`);
  const end = new Date(`${values.fecha_fin}T00:00:00Z`);
  let classes = 0;
  if (Number.isFinite(start.getTime()) && Number.isFinite(end.getTime()) && end >= start && end.getTime() - start.getTime() <= 10 * 366 * 86400000) {
    for (let date = start.getTime(); date <= end.getTime(); date += 86400000) if (days.includes(["domingo", "lunes", "martes", "miercoles", "jueves", "viernes", "sabado"][new Date(date).getUTCDay()])) classes++;
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!item && !confirm) { setConfirm(true); return; }
    setPending(true); setError(undefined);
    try {
      const payload = { campos: values, ...(!item || manageSchedules ? { horarios: rows } : {}) };
      const response = item ? await inetClient.put<InetItem>(`comisiones/${item.id}/`, payload) : await inetClient.post<InetItem>("comisiones/", payload);
      await client.invalidateQueries({ queryKey: ["inet"] });
      navigate(item ? `${ROOT}comisiones/${response.data.id}/` : `${ROOT}centros/${response.data.centro_id}/`, { state: { frame: frames.commissionSaved, success: item ? `Comisión ${response.data.id} actualizada` : `Comisión ${response.data.id}${course?.nombre ? ` de ${course.nombre}` : ""} creada` } });
    } catch (failure) { setError(failure); setConfirm(false); } finally { setPending(false); }
  }
  return <Box component="form" onSubmit={submit} data-figma-node={item ? frames.commissionEdit : confirm ? frames.commissionConfirm : frames.commissionNew}>
    <Button variant="outlined" startIcon={<ArrowBack />} onClick={() => navigate(-1)} sx={{ mb: 4, color: "primary.text" }}>Volver</Button>
    <Stack direction="row" spacing={2} sx={{ alignItems: "center", mb: 3 }}><Box sx={{ p: 1.5, display: "flex", borderRadius: 1, bgcolor: "primary.main", color: "primary.contrastText" }}><School /></Box><Box><Typography variant="h4" component="h1">{item ? "Editar comisión" : "Nueva comisión"}</Typography><Typography variant="body1" color="text.secondary">{item ? [detail(item, "Curso nombre"), `Comisión ${item.id}`, /en curso/i.test(item.estado) ? `En curso desde el ${formatDate(item.fecha_inicio)}` : item.estado].filter(Boolean).join(" · ") : [course?.nombre, course && (detail(course, "Plan nombre") || detail(course, "Plan curricular")) ? `Plan ${detail(course, "Plan nombre") || detail(course, "Plan curricular")}` : "", course ? detail(course, "Centro nombre") : ""].filter(Boolean).join(" · ")}</Typography></Box></Stack>
    {!!error && <Alert severity="error" sx={{ mb: 3 }}>{mensajeDeError(error)}</Alert>}
    <Box sx={{ p: 3, mb: 3, bgcolor: "background.paper", border: 1, borderColor: "divider", borderRadius: (theme) => `${theme.radius.large}px` }}>
      <Typography variant="h6" component="h2">Datos de la comisión</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Los campos con * son obligatorios.</Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
        {["ubicacion", "cupo_total", "fecha_inicio", "fecha_fin", "observaciones"].flatMap((name) => schema.fields.filter((field) => field.name === name)).map((field) => <Box key={field.name} sx={{ gridColumn: field.kind === "textarea" ? "1 / -1" : undefined }}>
          <Field placeholder={placeholders.comisiones?.[field.name]} field={{ ...field, help_text: field.help_text || helpTexts[field.name] || "", label: fieldLabels[field.name] || field.label, disabled: pending }} value={values[field.name]} values={values} optionsPath={item ? `comisiones/${item.id}/options/` : "comisiones/options/"} onOptionLabel={field.name === "ubicacion" ? setLocationLabel : undefined} onChange={(value) => setValues((current) => updateField(current, field.name, value))} />
        </Box>)}
      </Box>
      {schema.fields.some((field) => !["ubicacion", "cupo_total", "fecha_inicio", "fecha_fin", "observaciones"].includes(field.name)) && <Accordion disableGutters elevation={0} sx={{ mt: 3 }}><AccordionSummary expandIcon={<ExpandMore />}>Configuración adicional</AccordionSummary><AccordionDetails><Stack spacing={3}>{schema.fields.filter((field) => !["ubicacion", "cupo_total", "fecha_inicio", "fecha_fin", "observaciones"].includes(field.name)).map((field) => <Field key={field.name} field={{ ...field, disabled: pending }} value={values[field.name]} values={values} optionsPath={item ? `comisiones/${item.id}/options/` : "comisiones/options/"} onOptionLabel={field.name === "ubicacion" ? setLocationLabel : undefined} onChange={(value) => setValues((current) => updateField(current, field.name, value))} />)}</Stack></AccordionDetails></Accordion>}
    </Box>
    <Box sx={{ p: 3, mb: 3, bgcolor: "background.paper", border: 1, borderColor: "divider", borderRadius: (theme) => `${theme.radius.large}px` }}>
      <Typography variant="h6" component="h2">Horarios</Typography><Typography color="text.secondary" variant="body2" sx={{ mb: 3 }}>Al menos un horario. Cada clase dura entre 45 minutos y 4 horas.</Typography>
      {rows.map((row, index) => <Stack key={index} direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 3 }}>
        {schedule.fields.filter((field) => field.name !== "vigente").map((field) => <Box key={field.name} sx={{ flex: field.name === "dia_semana" ? 1.5 : 1 }}><Field field={{ ...field, label: fieldLabels[field.name] || field.label, disabled: pending || !manageSchedules, remote_options: false, options: field.options.filter((option) => field.name !== "dia_semana" || !rows.some((other, number) => number !== index && String(other.dia_semana) === option.value)) }} values={row} value={row[field.name]} onChange={(value) => setRows((current) => current.map((old, number) => number === index ? { ...old, [field.name]: value } : old))} /></Box>)}
        <Typography variant="body2" color="text.secondary" sx={{ alignSelf: "center", minWidth: 120 }}>{row.hora_desde && row.hora_hasta ? `${(Number(String(row.hora_hasta).slice(0, 2)) * 60 + Number(String(row.hora_hasta).slice(3, 5)) - Number(String(row.hora_desde).slice(0, 2)) * 60 - Number(String(row.hora_desde).slice(3, 5))) / 60} h por clase` : "Duración por clase"}</Typography>
        {manageSchedules && <IconButton aria-label={`Eliminar horario ${index + 1}`} disabled={rows.length === 1} onClick={() => setRows((current) => current.filter((_, number) => number !== index))}><Delete /></IconButton>}
      </Stack>)}
      {manageSchedules && <Button startIcon={<Add />} disabled={rows.length >= 7} onClick={() => setRows((current) => [...current, { vigente: "1" }])}>Agregar horario</Button>}
      {item && manageSchedules && totalMinutes >= 120 ? <Alert severity="warning" sx={{ mt: 2 }}><AlertTitle>Los cambios de horario regeneran las clases programadas</AlertTitle>Las clases realizadas y canceladas y sus asistencias no cambian. Total semanal: {totalMinutes / 60} horas.</Alert>
        : <Alert severity={totalMinutes >= 120 ? "success" : "warning"} sx={{ mt: 2 }}><AlertTitle>Total semanal: {totalMinutes / 60} horas</AlertTitle>{totalMinutes >= 120 ? `Cumple el mínimo de 2 horas semanales.${!item && classes ? ` Se van a dictar ${classes} clases entre el ${shortDate(values.fecha_inicio as string | null)} y el ${shortDate(values.fecha_fin as string | null)}.` : ""}` : "El mínimo es de 2 horas semanales."}</Alert>}
    </Box>
    <Dialog open={confirm} onClose={() => !pending && setConfirm(false)} fullWidth maxWidth="sm" aria-labelledby="commission-confirm-title" data-figma-node={frames.commissionConfirm}>
      <DialogTitle id="commission-confirm-title">¿Crear la comisión?</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 3, mb: 3 }}>
          {[["Curso", course?.nombre], ["Ubicación", locationLabel || schema.fields.find((field) => field.name === "ubicacion")?.options.find((option) => option.value === String(values.ubicacion))?.label || "Ubicación seleccionada"], ["Período", `${formatDate(values.fecha_inicio as string | null)} al ${formatDate(values.fecha_fin as string | null)}`], ["Cupo", `${values.cupo_total} estudiantes`], ["Horarios", scheduleSummary(rows.map((row) => `${dayLabel(row)}, ${row.hora_desde} a ${row.hora_hasta}`).join(" · "))], ["Total semanal", `${totalMinutes / 60} horas`]].map(([label, value]) => <Box key={label}><Typography variant="caption" color="text.secondary">{label}</Typography><Typography variant="body2" sx={{ fontWeight: 500 }}>{value}</Typography></Box>)}
        </Box>
        <Alert severity="info"><AlertTitle>Se van a generar {classes} clases</AlertTitle>Una por cada {joinDays(rows.map(dayLabel)).toLowerCase()} entre el {shortDate(values.fecha_inicio as string | null)} y el {shortDate(values.fecha_fin as string | null)}. La comisión queda en estado Planificada.</Alert>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}><Button disabled={pending} onClick={() => setConfirm(false)}>Volver a editar</Button><Button variant="contained" disabled={pending} onClick={(event) => void submit(event)}>Crear comisión</Button></DialogActions>
    </Dialog>
    <Stack direction="row" spacing={2} sx={{ justifyContent: "flex-end" }}><Button onClick={() => confirm ? setConfirm(false) : navigate(-1)} disabled={pending}>Cancelar</Button><Button type="submit" variant="contained" disabled={pending || (manageSchedules && (totalMinutes < 120 || invalidSchedule))}>{item ? "Guardar cambios" : "Crear comisión"}</Button></Stack>
  </Box>;
}
