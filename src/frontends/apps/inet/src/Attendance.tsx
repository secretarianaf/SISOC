import { InetStateChip as StateChip } from "./State";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Accordion, AccordionDetails, AccordionSummary, Alert, Box, Breadcrumbs, Button, Checkbox, LinearProgress, Link, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from "@mui/material";
import { inetClient, mensajeDeError, type InetAttendance, type InetItem } from "@sisoc/api";
import ArrowBack from "@mui/icons-material/ArrowBack";
import ExpandMore from "@mui/icons-material/ExpandMore";
import { detail, frames } from "./design";
import School from "@mui/icons-material/School";
import { formatDate, useInet, ROOT, weekdayDate } from "./data";

export function Attendance({ sessionId }: { sessionId: string }) {
  const context = useInet<InetItem>(`sesiones/${sessionId}/`);
  const query = useInet<InetAttendance>(`sesiones/${sessionId}/asistencia/`);
  if (query.error) return <Alert severity="error">{mensajeDeError(query.error)}</Alert>;
  if (!query.data) return <LinearProgress aria-label="Cargando asistencia" />;
  return <AttendanceFields key={sessionId} data={query.data} context={context.data} />;
}
function AttendanceFields({ data, context }: { data: InetAttendance; context?: InetItem }) {
  const [rows, setRows] = useState(data.filas);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const client = useQueryClient();
  const navigate = useNavigate();
  const back = () => context?.comision_id ? navigate(`${ROOT}comisiones/${context.comision_id}/?tab=sesiones`) : navigate(-1);
  const present = rows.filter((row) => row.presente).length;
  async function save(event: React.FormEvent) {
    event.preventDefault(); setPending(true); setError(undefined);
    try { await inetClient.put(`sesiones/${data.sesion_id}/asistencia/`, { filas: rows }); await client.invalidateQueries({ queryKey: ["inet"] }); back(); }
    catch (failure) { setError(failure); } finally { setPending(false); }
  }
  return <Box component="form" onSubmit={save} data-figma-node={frames.attendance}>
    <Button variant="outlined" startIcon={<ArrowBack />} onClick={back} sx={{ mb: 3, color: "primary.text" }}>Volver</Button>
    <Breadcrumbs aria-label="Ubicación" sx={{ mb: 3 }}><Link component="button" type="button" variant="caption" underline="hover" sx={{ fontWeight: 700 }} onClick={back}>Comisión {context?.comision_id}</Link><Typography variant="body2" color="text.primary">{context?.nombre}</Typography></Breadcrumbs>
    <Stack direction="row" spacing={2} sx={{ alignItems: "center", mb: 3, flexWrap: "wrap" }}>
      <Box sx={{ p: 1.5, bgcolor: "primary.main", color: "primary.contrastText", borderRadius: 1, display: "flex" }}><School /></Box>
      <Box><Typography variant="h4" component="h1">Asistencia · {context?.nombre || formatDate(data.fecha)}</Typography><Typography variant="body1" color="text.secondary">{[weekdayDate(data.fecha), context && detail(context, "Desde") ? `${detail(context, "Desde")} a ${detail(context, "Hasta")}` : "", context ? detail(context, "Curso nombre") : "", context?.comision_id ? `Comisión ${context.comision_id}` : ""].filter(Boolean).join(" · ")}</Typography></Box>
      {context?.estado && <StateChip label={context.estado === "Realizada" ? "Asistencia registrada" : "Asistencia pendiente"} tone={context.estado === "Realizada" ? "success" : "warning"} dot />}
    </Stack>
    {!!error && <Alert severity="error" sx={{ mb: 3 }}>{mensajeDeError(error)}</Alert>}
    <Box sx={{ bgcolor: "background.paper", border: 1, borderColor: "divider", borderRadius: (theme) => `${theme.radius.large}px`, mb: 3, overflow: "hidden" }}>
      <Box sx={{ p: 2, pt: 3 }}><Typography variant="h6" component="h2">Registro de asistencia</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Marcá quiénes estuvieron presentes. Al guardar, quienes no estén marcados quedan como ausentes.</Typography>
        <Button variant="outlined" disabled={pending} onClick={() => setRows((current) => current.map((row) => ({ ...row, presente: true })))}>Marcar todos presentes</Button></Box>
      <TableContainer><Table size="small" aria-label="Registro de asistencia" sx={{ minWidth: 700 }}>
        <TableHead><TableRow><TableCell><Checkbox checked={!!rows.length && present === rows.length} indeterminate={present > 0 && present < rows.length} disabled={pending} slotProps={{ input: { "aria-label": "Marcar toda la nómina" } }} onChange={(_, checked) => setRows((current) => current.map((row) => ({ ...row, presente: checked })))} /></TableCell><TableCell sx={{ width: "100%" }}><Typography variant="overline" color="text.secondary">Apellido y nombre</Typography></TableCell><TableCell sx={{ minWidth: 160 }}><Typography variant="overline" color="text.secondary">Documento</Typography></TableCell></TableRow></TableHead>
        <TableBody>{rows.map((row, index) => <TableRow key={row.inscripcion_id}><TableCell><Checkbox checked={!!row.presente} disabled={pending} slotProps={{ input: { "aria-label": `Presente ${row.nombre}` } }} onChange={(_, checked) => setRows((current) => current.map((item, number) => number === index ? { ...item, presente: checked } : item))} /></TableCell><TableCell>{row.nombre}</TableCell><TableCell>{row.documento}</TableCell></TableRow>)}</TableBody>
      </Table></TableContainer>
    </Box>
    <Accordion disableGutters elevation={0} sx={{ mb: 3, border: 1, borderColor: "divider" }}><AccordionSummary expandIcon={<ExpandMore />}>Observaciones por persona</AccordionSummary><AccordionDetails><Stack spacing={2}>{rows.map((row, index) => <TextField key={row.inscripcion_id} label={`Observaciones de ${row.nombre}`} value={row.observaciones ?? ""} disabled={pending} onChange={(event) => setRows((current) => current.map((item, number) => number === index ? { ...item, observaciones: event.target.value } : item))} />)}</Stack></AccordionDetails></Accordion>
    <Stack direction="row" spacing={2} sx={{ alignItems: "center", bgcolor: "background.paper", border: 1, borderColor: "divider", borderRadius: (theme) => `${theme.radius.large}px`, p: 2 }}><Typography sx={{ flexGrow: 1, fontWeight: 500 }}>{present} presentes · {rows.length - present} ausentes</Typography><Button disabled={pending} onClick={back}>Cancelar</Button><Button type="submit" variant="contained" disabled={pending || rows.length === 0}>Guardar asistencia</Button></Stack>
  </Box>;
}
