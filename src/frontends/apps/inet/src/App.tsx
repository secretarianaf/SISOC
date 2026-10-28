import { InetStateChip as StateChip } from "./State";
import { InetDialog as Dialog } from "./Dialog";
import { useState } from "react";
import { Routes, Route, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Alert, Box, Breadcrumbs, Button, DialogActions, DialogContent, DialogContentText, DialogTitle, IconButton, LinearProgress, Link, Snackbar, Stack, Tab, Tabs, Tooltip, Typography } from "@mui/material";
import School from "@mui/icons-material/School";
import Edit from "@mui/icons-material/Edit";
import Delete from "@mui/icons-material/Delete";
import Close from "@mui/icons-material/Close";
import ArrowBack from "@mui/icons-material/ArrowBack";
import MenuBook from "@mui/icons-material/MenuBook";
import { inetClient, mensajeDeError, type InetDeletePreview, type InetItem, type InetSession, type InetForm } from "@sisoc/api";
import { V2Layout } from "@sisoc/ui";
import { useInet, ROOT, shortDate, type Resource } from "./data";
import { ResourceTable } from "./ResourceTable";
import { FormDialog, CommissionForm, EditCommission } from "./Forms";
import { EnrollmentDialog, EnrollmentState } from "./Enrollment";
import { Attendance } from "./Attendance";
import { SearchPage } from "./Search";
import { CenterPanel, CommissionPanel } from "./DetailPanels";
import { detail, frames, joinDays, scheduleSummary, schedules } from "./design";
import { InetNavigation, InetLogout } from "./Navigation";
import { ScreenBoundary } from "./ErrorBoundary";

type Editor = { resource: Resource; item?: InetItem; initial?: Record<string, unknown> };
type Actions = { edit: (resource: Resource, item?: InetItem, initial?: Record<string, unknown>) => void; remove: (resource: Resource, item: InetItem) => void; enroll: (id: number) => void; state: (item: InetItem, cancel: boolean) => void };

export default function App() {
  const session = useInet<InetSession>("session/");
  const navigate = useNavigate();
  const location = useLocation();
  const client = useQueryClient();
  const [editor, setEditor] = useState<Editor>();
  const [deletion, setDeletion] = useState<Editor>();
  const [enrollment, setEnrollment] = useState<number>();
  const [state, setState] = useState<{ item: InetItem; cancel: boolean }>();
  const [success, setSuccess] = useState("");
  const [successFrame, setSuccessFrame] = useState<string>();
  const [successAction, setSuccessAction] = useState<{ label: string; href: string }>();
  const notice = success || location.state?.success || "";
  const closeNotice = () => { setSuccess(""); setSuccessAction(undefined); if (location.state?.success) navigate(`${location.pathname}${location.search}`, { replace: true, state: {} }); };
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  const actions: Actions = {
    edit: (resource, item, initial) => resource === "comisiones" && item ? navigate(`${ROOT}comisiones/${item.id}/editar/`) : setEditor({ resource, item, initial }),
    remove: (resource, item) => { setError(undefined); setDeletion({ resource, item }); },
    enroll: setEnrollment, state: (item, cancel) => setState({ item, cancel }),
  };
  async function remove() {
    if (!deletion?.item) return;
    setPending(true); setError(undefined);
    try {
      await inetClient.delete(`${deletion.resource}/${deletion.item.id}/`);
      await client.invalidateQueries({ queryKey: ["inet"] });
      setDeletion(undefined); setSuccess("Registro eliminado correctamente.");
      if (location.pathname === `${ROOT}${deletion.resource}/${deletion.item.id}/`) navigate(ROOT);
    } catch (failure) { setError(failure); } finally { setPending(false); }
  }
  return <V2Layout navigation={(close) => <InetNavigation session={session.data} close={close} />} sidebarFooter={<InetLogout />} sidebarWidth={230} sectionLabel="INET" username={session.data?.nombre || session.data?.username} modules={[
    { label: "Centros de Formación Profesional", href: `${ROOT}centros/`, active: !location.pathname.includes("/planes"), icon: <School />, onNavigate: () => navigate(`${ROOT}centros/`) },
    ...(session.data?.puede_ver_planes ? [{ label: "Planes curriculares", href: `${ROOT}planes/`, active: location.pathname.includes("/planes"), icon: <MenuBook />, onNavigate: () => navigate(`${ROOT}planes/`) }] : []),
  ]}>
    <Box component="main" sx={{ p: { xs: 2, md: 3 }, maxWidth: 1600, mx: "auto" }}>
      {session.isLoading && <LinearProgress aria-label="Cargando INET" />}
      {session.error && <Alert severity="error">{mensajeDeError(session.error)}</Alert>}
      {session.data && <ScreenBoundary resetKey={`${location.pathname}${location.search}`}><Routes>
        <Route path="/v2/inet/" element={<SearchPage session={session.data} onEdit={actions.edit} onDelete={actions.remove} />} />
        <Route path="/v2/inet/centros/" element={<SearchPage session={session.data} onEdit={actions.edit} onDelete={actions.remove} />} />
        <Route path="/v2/inet/centros/:id/" element={<DetailPage resource="centros" session={session.data} actions={actions} />} />
        <Route path="/v2/inet/comisiones/nueva/" element={<NewCommission />} />
        <Route path="/v2/inet/comisiones/:id/editar/" element={<EditCommission session={session.data} />} />
        <Route path="/v2/inet/comisiones/:id/" element={<DetailPage resource="comisiones" session={session.data} actions={actions} />} />
        <Route path="/v2/inet/sesiones/:id/asistencia/" element={<AttendancePage />} />
        <Route path="/v2/inet/planes/" element={<SearchPage plans session={session.data} onEdit={actions.edit} onDelete={actions.remove} />} />
        <Route path="/v2/inet/planes/:id/" element={<DetailPage resource="planes" session={session.data} actions={actions} />} />
        <Route path="*" element={<Alert severity="info">Pantalla no encontrada. <Button onClick={() => navigate(ROOT)}>Volver a INET</Button></Alert>} />
      </Routes></ScreenBoundary>}
    </Box>
    {editor && <FormDialog {...editor} onClose={() => setEditor(undefined)} onSaved={(item, commission) => {
      setEditor(undefined); setSuccess(editor.resource === "cursos" ? `Curso ${item.nombre} ${editor.item ? "actualizado" : "creado"}` : "Datos guardados correctamente."); setSuccessFrame(editor.resource === "cursos" ? frames.courseSaved : undefined);
      setSuccessAction(editor.resource === "cursos" && !editor.item && !commission ? { label: "Crear comisión", href: `${ROOT}comisiones/nueva/?curso=${item.id}` } : undefined);
      if (commission) navigate(`${ROOT}comisiones/nueva/?curso=${item.id}`);
      else if (editor.resource === "centros" && !editor.item) navigate(`${ROOT}centros/${item.id}/`);
    }} />}
    {deletion?.item && <DeleteDialog resource={deletion.resource} item={deletion.item} pending={pending} error={error} onClose={() => setDeletion(undefined)} onDelete={remove} onChanged={() => { setDeletion(undefined); setSuccess("Estado actualizado. Se conserva el historial."); }} />}
    {enrollment !== undefined && <EnrollmentDialog commissionId={enrollment} onClose={() => setEnrollment(undefined)} onSaved={(message) => { setEnrollment(undefined); setSuccess(message); setSuccessFrame(frames.enrollmentSaved); }} />}
    {state && <EnrollmentState {...state} onClose={() => setState(undefined)} onSaved={() => { setState(undefined); setSuccess(state.cancel ? `${state.item.nombre}: inscripción dada de baja` : `${state.item.nombre}: inscripción actualizada`); setSuccessFrame(state.cancel ? frames.enrollmentCancelled : frames.enrollmentSaved); }} />}
    <Snackbar open={!!notice} autoHideDuration={6000} onClose={closeNotice} data-figma-node={successFrame || location.state?.frame}><Alert severity="success" variant="filled" onClose={successAction ? undefined : closeNotice} action={successAction && <Button color="inherit" size="small" onClick={() => { const href = successAction.href; closeNotice(); navigate(href); }}>{successAction.label}</Button>} sx={{ minWidth: { sm: 520 } }}>{notice}</Alert></Snackbar>
  </V2Layout>;
}
function Details({ item }: { item: InetItem }) {
  return <Box component="section" sx={{ bgcolor: "background.paper", border: 1, borderColor: "divider", borderRadius: (theme) => `${theme.radius.large}px`, p: 3, mb: 3 }}>
    <Typography variant="h6" component="h2" sx={{ mb: 3 }}>Información general</Typography>
    <Box component="dl" sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "1fr 1fr 1fr" }, gap: 3, m: 0 }}>
      {item.detalle.map((field) => <Box key={field.label}><Typography component="dt" variant="caption" color="text.secondary">{field.label}</Typography><Typography component="dd" variant="body2" sx={{ m: 0, overflowWrap: "anywhere" }}>{field.value || "—"}</Typography></Box>)}
    </Box>
  </Box>;
}
function DetailPage({ resource, session, actions }: { resource: Resource; session: InetSession; actions: Actions }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "informacion";
  const query = useInet<InetItem>(`${resource}/${id}/`);
  if (query.error) return <Alert severity="error">{mensajeDeError(query.error)}</Alert>;
  if (!query.data) return <LinearProgress aria-label="Cargando legajo" />;
  const item = query.data;
  const scopedSession = item.puede_gestionar ? session : { ...session, permissions: session.permissions.filter((code) => !code.startsWith("add_")) };
  const table = (kind: Resource, filters: Record<string, unknown>) => <ResourceTable resource={kind} subtitle={kind === "inscripciones" ? `${item.inscriptos_count} de ${detail(item, "Cupo total")} lugares ocupados · la asistencia se calcula sobre las clases completadas` : kind === "sesiones" ? `${item.clases_count} clases · ${joinDays(schedules(detail(item, "Horarios")).map((row) => row.day)).toLowerCase() || detail(item, "Horarios")} del ${shortDate(item.fecha_inicio)} al ${shortDate(item.fecha_fin)}` : undefined} filters={filters} session={scopedSession} onEdit={actions.edit} onDelete={actions.remove} onEnroll={() => actions.enroll(item.id)} onState={actions.state} />;
  return <Box data-figma-node={resource === "centros" ? tab === "ubicaciones" ? frames.locations : tab === "contactos" ? frames.contacts : frames.centerInfo : resource === "comisiones" ? tab === "inscripciones" ? frames.enrollments : tab === "sesiones" ? frames.classes : frames.commissionInfo : undefined}>
    <Stack direction="row" sx={{ mb: 3, alignItems: "center" }}><Button variant="outlined" startIcon={<ArrowBack />} sx={{ color: "primary.text" }} onClick={() => resource === "comisiones" && item.centro_id ? navigate(`${ROOT}centros/${item.centro_id}/`) : navigate(resource === "planes" ? `${ROOT}planes/` : ROOT)}>Volver</Button><Box sx={{ flexGrow: 1 }} />
      {item.puede_editar && <Tooltip title="Editar"><IconButton color="primary" aria-label={`Editar ${item.nombre}`} onClick={() => actions.edit(resource, item)}><Edit /></IconButton></Tooltip>}
      {item.puede_eliminar && <Tooltip title="Eliminar"><IconButton color="error" aria-label={`Eliminar ${item.nombre}`} onClick={() => actions.remove(resource, item)}><Delete /></IconButton></Tooltip>}
    </Stack>
    {resource === "comisiones" && <Breadcrumbs aria-label="Ubicación" sx={{ mb: 3 }}><Link component="button" variant="caption" underline="hover" sx={{ fontWeight: 700 }} onClick={() => navigate(`${ROOT}centros/${item.centro_id}/`)}>{detail(item, "Centro nombre") || "CFP"}</Link><Typography variant="body2" color="text.primary">Comisión {item.id}</Typography></Breadcrumbs>}
    <Stack direction="row" spacing={2} sx={{ mb: 3, alignItems: "center" }}>
      <Box sx={{ bgcolor: "primary.main", color: "primary.contrastText", p: 1.5, borderRadius: 1, display: "flex" }}><School /></Box>
      <Box sx={{ flexGrow: 1 }}><Stack direction="row" spacing={2} useFlexGap sx={{ flexWrap: "wrap", alignItems: "center" }}><Typography variant="h4" component="h1">{resource === "comisiones" ? `${detail(item, "Curso nombre") || item.nombre} · Comisión ${item.id}` : item.nombre}</Typography><StateChip label={item.estado} tone={item.estado === "Activo" || item.estado === "En Curso" ? "success" : "neutral"} dot /></Stack><Typography variant="body1" color="text.secondary">{resource === "centros" ? `CUE ${item.cue} · ${item.provincia}, ${item.localidad}` : resource === "comisiones" ? [detail(item, "Ubicación nombre"), scheduleSummary(detail(item, "Horarios"))].filter(Boolean).join(" · ") : item.provincia}</Typography></Box>
    </Stack>
    {resource === "comisiones" && <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" }, gap: 3, mb: 3 }}>
      {[{ label: "Inscriptos", value: item.inscriptos_count, reference: `de ${detail(item, "Cupo total") || "—"} lugares` }, { label: "Clases dictadas", value: item.clases_realizadas, reference: `de ${item.clases_count} clases` }, { label: "Asistencia general", value: item.asistencia_pct === null ? "—" : `${item.asistencia_pct}%`, reference: `promedio de ${item.clases_realizadas} clases` }].map((stat) => <Box key={stat.label} sx={{ bgcolor: "background.paper", borderRadius: (theme) => `${theme.radius.large}px`, borderLeft: 4, borderColor: "primary.main", boxShadow: 3, p: 2 }}><Typography variant="overline" color="text.secondary">{stat.label}</Typography><Typography variant="h4Bold" color="primary.text">{stat.value}</Typography><Typography variant="body2" color="text.secondary" sx={{ pt: .5 }}>{stat.reference}</Typography></Box>)}
    </Box>}
    {resource !== "planes" && <Tabs value={tab} onChange={(_, next) => setParams({ tab: next })} variant="scrollable" scrollButtons="auto" sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }} aria-label="Secciones del legajo">
      <Tab label={resource === "comisiones" ? "Información" : "Información general"} value="informacion" />
      {resource === "centros" ? [<Tab key="ubicaciones" label={`Ubicaciones (${detail(item, "Ubicaciones") || "0"})`} value="ubicaciones" />, <Tab key="contactos" label={`Contactos (${detail(item, "Contactos") || "0"})`} value="contactos" />] : [<Tab key="inscripciones" label={`Inscriptos (${item.inscriptos_count})`} value="inscripciones" />, <Tab key="sesiones" label={`Clases (${item.clases_count})`} value="sesiones" />]}
    </Tabs>}
    {(tab === "informacion" || resource === "planes") && (resource === "centros" ? <CenterPanel item={item} /> : resource === "comisiones" ? <CommissionPanel item={item} /> : <Details item={item} />)}
    {resource === "centros" && <>
      {tab === "ubicaciones" && table("ubicaciones", { centro: item.id })}
      {tab === "contactos" && table("contactos", { centro: item.id })}
      {table("cursos", { centro: item.id })}{table("comisiones", { centro: item.id })}
    </>}
    {resource === "comisiones" && <>
      {tab === "inscripciones" && table("inscripciones", { comision: item.id })}
      {tab === "sesiones" && table("sesiones", { comision: item.id })}
    </>}
  </Box>;
}
function NewCommission() {
  const [params] = useSearchParams();
  const id = params.get("curso");
  return id && /^\d+$/.test(id) ? <CommissionForm courseId={id} /> : <Alert severity="error">Seleccioná un curso desde la oferta educativa de un CFP.</Alert>;
}
function AttendancePage() {
  const { id } = useParams();
  return <Attendance sessionId={id!} />;
}

function DeleteDialog({ resource, item, pending, error, onClose, onDelete, onChanged }: { resource: Resource; item: InetItem; pending: boolean; error: unknown; onClose: () => void; onDelete: () => void; onChanged: () => void }) {
  const preview = useInet<InetDeletePreview>(`${resource}/${item.id}/delete-preview/`);
  const hasHistory = resource === "cursos" ? item.comisiones_count > 0 : resource === "comisiones" && (item.inscriptos_count > 0 || item.clases_realizadas > 0 || !!preview.data?.desglose_por_modelo.some((group) => /inscripci/i.test(group.modelo) && group.cantidad > 0));
  const schema = useInet<InetForm>(`${resource}/${item.id}/form/`, hasHistory && item.puede_editar);
  const client = useQueryClient();
  const [changing, setChanging] = useState(false);
  const [changeError, setChangeError] = useState<unknown>();
  async function cancelResource() {
    if (!schema.data) return;
    setChanging(true); setChangeError(undefined);
    try {
      await inetClient.put(`${resource}/${item.id}/`, { campos: { ...Object.fromEntries(schema.data.fields.map((field) => [field.name, field.value])), estado: "cancelado" } });
      await client.invalidateQueries({ queryKey: ["inet"] }); onChanged();
    } catch (failure) { setChangeError(failure); } finally { setChanging(false); }
  }
  const name = resource === "comisiones" ? `la comisión ${item.id}` : item.nombre;
  const frame = resource === "cursos" ? hasHistory ? frames.courseDelete : frames.courseDeleteEmpty : resource === "comisiones" ? hasHistory ? frames.commissionDelete : frames.commissionDeleteEmpty : undefined;
  return <Dialog open onClose={() => !pending && !changing && onClose()} fullWidth maxWidth="sm" slotProps={{ paper: { sx: { maxWidth: 480 } } }} aria-labelledby="delete-title" data-figma-node={frame}>
    <DialogTitle id="delete-title" sx={{ pr: 6 }}>{hasHistory ? `No se puede eliminar ${name}` : `¿Eliminar ${name}?`}<IconButton aria-label="Cerrar confirmación" disabled={pending || changing} onClick={onClose} sx={{ position: "absolute", top: 8, right: 8 }}><Close /></IconButton></DialogTitle>
    <DialogContent>
      {!!(error || changeError || schema.error) && <Alert severity="error" sx={{ mb: 2 }}>{mensajeDeError(error || changeError || schema.error)}</Alert>}
      {preview.error && <Alert severity="error">{mensajeDeError(preview.error)}</Alert>}
      {preview.isLoading && <LinearProgress aria-label="Consultando registros afectados" />}
      {hasHistory ? <DialogContentText>{resource === "cursos" ? `Tiene ${item.comisiones_count} ${item.comisiones_count === 1 ? "comisión" : "comisiones"}. Para que deje de ofrecerse, pasalo a Cancelado: sus comisiones y su historial se conservan.` : `Tiene ${item.inscriptos_count} inscriptos y ${item.clases_realizadas} clases dictadas. Si no va a continuar, cancelala: queda en estado Cancelada y se conservan los inscriptos y las asistencias.`}</DialogContentText>
        : preview.data && <DialogContentText>{resource === "cursos" ? `El curso no tiene comisiones ni inscriptos. Se elimina de la oferta educativa${detail(item, "Centro nombre") ? ` del ${detail(item, "Centro nombre")}` : ""} y la acción no se puede deshacer.` : resource === "comisiones" ? `${detail(item, "Curso nombre") || "La comisión"} · Comisión ${item.id} está ${item.estado} y no tiene inscriptos. Se eliminan también sus ${item.clases_count} clases programadas. La acción no se puede deshacer.` : `Se afectarán ${preview.data.total_afectados} registros. La acción no se puede deshacer.`}</DialogContentText>}
    </DialogContent>
    <DialogActions sx={{ px: 3, pb: 3 }}><Button onClick={onClose} disabled={pending || changing}>{resource === "comisiones" ? "Volver" : "Cancelar"}</Button>{hasHistory ? item.puede_editar && <Button variant="contained" color={resource === "comisiones" ? "error" : "primary"} disabled={changing || !schema.data} onClick={() => void cancelResource()}>{resource === "comisiones" ? "Cancelar comisión" : "Pasar a Cancelado"}</Button> : <Button color="error" variant="contained" onClick={onDelete} disabled={pending || !preview.data}>Eliminar</Button>}</DialogActions>
  </Dialog>;
}
