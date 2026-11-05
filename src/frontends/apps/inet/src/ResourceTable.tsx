import { InetStateChip as StateChip } from "./State";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Box, Button, IconButton, InputAdornment, MenuItem, Skeleton, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, TextField, Tooltip, Typography } from "@mui/material";
import Add from "@mui/icons-material/Add";
import Edit from "@mui/icons-material/Edit";
import Delete from "@mui/icons-material/Delete";
import Visibility from "@mui/icons-material/Visibility";
import PersonRemove from "@mui/icons-material/PersonRemove";
import Search from "@mui/icons-material/Search";
import { mensajeDeError, type InetItem, type InetPage, type InetSession } from "@sisoc/api";
import { detail } from "./design";
import { formatDate, queryString, resources, ROOT, useInet, weekdayDate, type Resource } from "./data";

function detailValue(item: InetItem, label: string) {
  const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  return item.detalle.find((field) => normalize(field.label).includes(normalize(label)))?.value || "—";
}
function State({ item, resource }: { item: InetItem; resource: Resource }) {
  let label = resource === "sesiones" ? detail(item, "Estado visual") || item.estado : item.estado;
  if (resource === "inscripciones" && ["Inscripta", "Validada presencial"].includes(label)) label = "Activo";
  if (resource === "inscripciones" && label === "Abandonada") label = "Baja";
  if (resource === "cursos") label = item.comisiones_count ? "Con comisión" : "Sin comisión";
  if (resource === "inscripciones" && item.identidad_pendiente && !["Rechazada", "Abandonada"].includes(item.estado)) label = "Sin validar";
  const warning = ["Sin comisión", "Sin validar", "Planificada", "Pre-inscripta", "En Espera", "Asistencia pendiente"].includes(label);
  const neutral = ["Inactivo", "Rechazada", "Baja", "Cancelada", "Programada"].includes(label);
  return <StateChip label={label || "—"} tone={neutral ? "neutral" : warning ? "warning" : "success"} dot />;
}
const columns: Record<Resource, string[]> = {
  centros: ["Nombre", "Provincia", "Localidad", "CUE", "Estado"],
  cursos: ["Plan curricular", "Curso", "Comisiones", "Estado de carga"],
  comisiones: ["Curso", "Comisión", "Ubicación", "Inicio", "Fin", "Cupo"],
  contactos: ["Nombre y apellido", "Documento", "Rol", "Principal", "Teléfono"],
  ubicaciones: ["Nombre", "Característica", "Localidad", "Domicilio"],
  planes: ["Nombre", "Provincia", "Sector", "Horas reloj", "Estado"],
  inscripciones: ["Apellido y nombre", "Documento", "Email", "Teléfono", "Asistencia", "Estado"],
  sesiones: ["Clase", "Fecha", "Horario", "Estado", "Presentes", "Ausentes"],
  horarios: ["Día", "Desde", "Hasta", "Vigente"],
};
// Columnas numéricas alineadas a la derecha, como en las tablas de Figma.
const numeric: Partial<Record<Resource, string[]>> = { cursos: ["Comisiones"], comisiones: ["Cupo"], inscripciones: ["Asistencia"], sesiones: ["Presentes", "Ausentes"] };
const inactiveEnrollment = (item: InetItem) => ["Abandonada", "Rechazada"].includes(item.estado);
function attendanceAction(item: InetItem) {
  const state = detail(item, "Estado visual") || item.estado;
  if (state === "Completada") return "ver";
  const date = detail(item, "Fecha");
  const today = new Date().toLocaleDateString("en-CA");
  return state === "Asistencia pendiente" || (state === "Programada" && !!date && date <= today) ? "cargar" : undefined;
}
function cells(item: InetItem, resource: Resource) {
  switch (resource) {
    case "centros": return [item.nombre, item.provincia, item.localidad, item.cue, <State key="state" item={item} resource={resource} />];
    case "cursos": return [detail(item, "Plan nombre") || detailValue(item, "plan"), item.nombre, item.comisiones_count, <State key="state" item={item} resource={resource} />];
    case "comisiones": return [detail(item, "Curso nombre") || detailValue(item, "curso"), item.id, detail(item, "Ubicación nombre") || detailValue(item, "ubicaci"), formatDate(item.fecha_inicio), formatDate(item.fecha_fin), detailValue(item, "cupo total")];
    case "contactos": return [item.nombre, detailValue(item, "documento"), detailValue(item, "rol"), detailValue(item, "principal"), detailValue(item, "telefono")];
    case "ubicaciones": return [item.nombre, detailValue(item, "rol"), detailValue(item, "localidad"), detailValue(item, "domicilio")];
    case "planes": return [item.nombre, item.provincia || "Nacional", detailValue(item, "sector"), detailValue(item, "horas"), <State key="state" item={item} resource={resource} />];
    case "inscripciones": return [item.nombre, item.documento || "—", item.email || "—", item.telefono || "—", item.asistencia_pct === null ? "—" : `${item.asistencia_pct}%`, <State key="state" item={item} resource={resource} />];
    case "sesiones": return [detailValue(item, "número"), weekdayDate(detail(item, "Fecha") || null), `${detail(item, "Desde")} a ${detail(item, "Hasta")}`, <State key="state" item={item} resource={resource} />, detail(item, "Presentes") || "—", detail(item, "Ausentes") || "—"];
    case "horarios": return [item.nombre, detailValue(item, "desde"), detailValue(item, "hasta"), detailValue(item, "vigente")];
  }
}
export function ResourceTable({ resource, filters = {}, session, onEdit, onDelete, onEnroll, onState, presentation = "panel", subtitle }: {
  resource: Resource; filters?: Record<string, unknown>; session: InetSession;
  onEdit: (resource: Resource, item?: InetItem, initial?: Record<string, unknown>) => void;
  onDelete: (resource: Resource, item: InetItem) => void;
  onEnroll?: () => void; onState?: (item: InetItem, cancel: boolean) => void;
  presentation?: "panel" | "search"; subtitle?: string;
}) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(resource === "centros" ? 6 : 10);
  const [loadState, setLoadState] = useState("");
  const [course, setCourse] = useState("");
  const courses = useInet<InetPage>(`cursos/?${queryString({ centro: filters.centro, page_size: 200 })}`, resource === "comisiones");
  const query = useInet<InetPage>(`${resource}/?${queryString({ ...filters, ...(presentation !== "search" ? { search } : {}), estado_carga: loadState, estado_asistencia: resource === "sesiones" ? loadState : undefined, ...(course ? { curso: course } : {}), page: page + 1, page_size: pageSize })}`);
  const filterCount = Object.values(filters).filter((value) => value !== "" && value !== undefined && value !== null).length;
  const total = useInet<InetPage>(`${resource}/?page_size=1`, presentation === "search" && filterCount > 0);
  const canCreate = session.permissions.includes(`add_${resources[resource].model}`);
  const canEditEnrollment = session.permissions.includes("change_inscripcion");
  const add = canCreate && !["sesiones", "comisiones"].includes(resource) ? <Button variant="contained" startIcon={<Add />} onClick={() => resource === "inscripciones" ? onEnroll?.() : onEdit(resource, undefined, Object.fromEntries(Object.entries(filters).filter(([key]) => ["centro", "curso", "comision"].includes(key))))}>Agregar {resources[resource].singular}</Button> : null;
  const caption = subtitle || ({ ubicaciones: "Sede y anexos donde se dictan los cursos", contactos: "El contacto principal es el referente del centro", cursos: `Ciclo lectivo ${new Date().getFullYear()}`, comisiones: `Ciclo lectivo ${new Date().getFullYear()}` } as Record<string, string>)[resource];
  return <Box component="section" sx={{ mb: 3 }}>
    {presentation === "search" && <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, mb: 3 }}><Typography variant="body2" color="text.secondary">{query.data ? `${query.data.count}${filterCount && total.data ? ` de ${total.data.count}` : ""} ${resource === "centros" ? "CFP" : "planes"}${filterCount ? ` con ${filterCount} ${filterCount === 1 ? "filtro" : "filtros"}` : ""}` : "Cargando resultados…"}</Typography>{add}</Box>}
    <Box sx={{ bgcolor: "background.paper", border: 1, borderColor: "divider", borderRadius: (theme) => `${theme.radius.large}px`, overflow: "hidden" }}>
    {presentation !== "search" && <Box sx={{ p: 2, display: "flex", flexWrap: "wrap", gap: 2, alignItems: "center" }}>
      <Box sx={{ flexBasis: ["ubicaciones", "contactos"].includes(resource) ? "auto" : "100%", flexGrow: 1 }}><Typography variant="h6" component="h2">{resources[resource].title}</Typography><Typography variant="body2" color="text.secondary">{caption || (query.data ? `${query.data.count} resultados` : "Cargando resultados…")}</Typography></Box>
      {!["sesiones", "ubicaciones", "contactos"].includes(resource) && <TextField placeholder={resource === "inscripciones" ? "Buscar por apellido o documento…" : `Buscar ${resources[resource].singular}…`} value={search}
        onChange={(event) => { setSearch(event.target.value); setPage(0); }}
        slotProps={{ htmlInput: { "aria-label": `Buscar en ${resources[resource].title}` }, input: { startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> } }} sx={{ width: { xs: "100%", sm: 320 } }} />}
      {resource === "sesiones" && <TextField select slotProps={{ inputLabel: { shrink: true }, select: { displayEmpty: true } }} label="Estado" value={loadState} onChange={(event) => { setLoadState(event.target.value); setPage(0); }} sx={{ width: { xs: "100%", sm: 260 } }}><MenuItem value="">Todos</MenuItem><MenuItem value="completada">Completada</MenuItem><MenuItem value="pendiente">Asistencia pendiente</MenuItem><MenuItem value="programada">Programada</MenuItem><MenuItem value="cancelada">Cancelada</MenuItem></TextField>}
      {resource === "cursos" && <TextField select slotProps={{ inputLabel: { shrink: true }, select: { displayEmpty: true } }} label="Estado de carga" value={loadState} onChange={(event) => { setLoadState(event.target.value); setPage(0); }} sx={{ width: { xs: "100%", sm: 240 } }}><MenuItem value="">Todos</MenuItem><MenuItem value="con_comision">Con comisión</MenuItem><MenuItem value="sin_comision">Sin comisión</MenuItem></TextField>}
      {resource === "comisiones" && <TextField select slotProps={{ inputLabel: { shrink: true }, select: { displayEmpty: true } }} label="Curso" value={course} onChange={(event) => { setCourse(event.target.value); setPage(0); }} sx={{ width: { xs: "100%", sm: 240 } }}><MenuItem value="">Todos</MenuItem>{courses.data?.results.map((item) => <MenuItem key={item.id} value={String(item.id)}>{item.nombre}</MenuItem>)}</TextField>}
      <Box sx={{ flexGrow: 1 }} />
      {add}
    </Box>}
    {query.error && <Alert severity="error">{mensajeDeError(query.error)}</Alert>}
    <TableContainer sx={{ overflowX: "auto" }}>
      <Table size="small" aria-label={resources[resource].title} sx={{ minWidth: resource === "inscripciones" ? 1050 : resource === "comisiones" ? 1000 : 700 }}>
        <TableHead><TableRow>{columns[resource].map((label) => <TableCell key={label} align={numeric[resource]?.includes(label) ? "right" : undefined}><Typography variant="overline" color="text.secondary">{label}</Typography></TableCell>)}<TableCell align="right"><Typography variant="overline" color="text.secondary">Acciones</Typography></TableCell></TableRow></TableHead>
        <TableBody>
          {query.isLoading && Array.from({ length: 4 }, (_, index) => <TableRow key={index}><TableCell colSpan={columns[resource].length + 1}><Skeleton height={42} /></TableCell></TableRow>)}
          {query.data?.results.map((item) => <TableRow key={item.id} hover>
            {cells(item, resource).map((value, index) => <TableCell key={index} align={numeric[resource]?.includes(columns[resource][index]) ? "right" : undefined} sx={{ py: 1 }}>{value}</TableCell>)}
            <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
              {resource === "cursos" && session.permissions.includes("add_comisioncurso") && <Button size="small" startIcon={<Add />} onClick={() => navigate(`${ROOT}comisiones/nueva/?curso=${item.id}`)}>Comisión</Button>}
              {["centros", "comisiones", "planes"].includes(resource) && <Tooltip title={resource === "sesiones" ? "Registrar asistencia" : "Ver legajo"}><IconButton size="small" color="primary" aria-label={`${resource === "sesiones" ? "Registrar asistencia" : "Ver"} ${item.nombre}`} onClick={() => navigate(`${ROOT}${resource}/${item.id}/${resource === "sesiones" ? "asistencia/" : ""}`)}><Visibility fontSize="small" /></IconButton></Tooltip>}
              {resource === "sesiones" && attendanceAction(item) && <Button size="small" variant={attendanceAction(item) === "ver" ? "text" : "contained"} startIcon={attendanceAction(item) === "ver" ? <Visibility fontSize="small" /> : undefined} onClick={() => navigate(`${ROOT}sesiones/${item.id}/asistencia/`)}>{attendanceAction(item) === "ver" ? "Ver asistencia" : "Cargar asistencia"}</Button>}
              {item.puede_editar && resource !== "sesiones" && <Tooltip title="Editar"><IconButton size="small" color="primary" aria-label={`Editar ${item.nombre}`} onClick={() => resource === "inscripciones" ? onState?.(item, false) : onEdit(resource, item)}><Edit fontSize="small" /></IconButton></Tooltip>}
              {resource === "inscripciones" && item.puede_editar && canEditEnrollment && <Tooltip title={inactiveEnrollment(item) ? "Ya está dada de baja" : "Dar de baja"}><span><IconButton size="small" color="error" disabled={inactiveEnrollment(item)} aria-label={`Dar de baja a ${item.nombre}`} onClick={() => onState?.(item, true)}><PersonRemove fontSize="small" /></IconButton></span></Tooltip>}
              {item.puede_eliminar && !["inscripciones", "sesiones"].includes(resource) && <Tooltip title="Eliminar"><IconButton size="small" color="error" aria-label={`Eliminar ${item.nombre}`} onClick={() => onDelete(resource, item)}><Delete fontSize="small" /></IconButton></Tooltip>}
            </TableCell>
          </TableRow>)}
          {query.data?.count === 0 && <TableRow><TableCell colSpan={columns[resource].length + 1}><Typography sx={{ py: 4, textAlign: "center" }} color="text.secondary">No hay resultados para esta búsqueda.</Typography></TableCell></TableRow>}
        </TableBody>
      </Table>
    </TableContainer>
    <TablePagination component="div" count={query.data?.count ?? 0} page={page} rowsPerPage={pageSize} rowsPerPageOptions={[6, 10, 25, 50]}
      onPageChange={(_, next) => setPage(next)} onRowsPerPageChange={(event) => { setPageSize(Number(event.target.value)); setPage(0); }}
      getItemAriaLabel={(type) => type === "previous" ? "Página anterior" : type === "next" ? "Página siguiente" : type === "first" ? "Primera página" : "Última página"} labelRowsPerPage="Filas por página:" labelDisplayedRows={({ from, to, count }) => `${from}–${to} de ${count}`} />
    </Box>
  </Box>;
}
