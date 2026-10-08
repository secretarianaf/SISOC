import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { V2Layout } from "@sisoc/ui";
import { Accordion, AccordionDetails, AccordionSummary, Alert, Autocomplete, Button, Card as MuiCard, IconButton, InputAdornment, Link, MenuItem, Skeleton, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, TextField, Tooltip, Typography, useMediaQuery } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DownloadIcon from "@mui/icons-material/Download";
import EditIcon from "@mui/icons-material/Edit";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SearchIcon from "@mui/icons-material/Search";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import {
  ApiError,
  get,
  postForm,
  type Itinerario,
  type Jornada,
  type Options,
  type Page,
  type Sede,
  type Session,
  type Registro,
  type Laboratorio,
} from "./api";
import { ActionButton, BulkLaboratory, EvaluateItinerary, WorkflowForm } from "./Workflow";
import { StateChip } from "./StateChip";
import { formatDate, formatDateTime } from "./dates";

const ROOT = "/v2/vpsl/";
type Route = {
  kind: "itinerarios" | "sedes" | "itinerario" | "jornada" | "sede" | "nuevo" | "form";
  id?: number;
  formKind?: string;
};

export function route(pathname: string): Route {
  const parts = pathname
    .replace(/^\/v2\/vpsl\/?/, "")
    .split("/")
    .filter(Boolean);
  if (parts[0] === "forms" && parts[1] && parts[2])
    return { kind: "form", formKind: parts[1], id: Number(parts[2]) };
  if (parts[0] === "sedes" && parts[1])
    return { kind: "sede", id: Number(parts[1]) };
  if (parts[0] === "sedes") return { kind: "sedes" };
  if (parts[0] === "jornadas" && parts[1])
    return { kind: "jornada", id: Number(parts[1]) };
  if (parts[0] === "itinerarios" && parts[1] === "nuevo")
    return { kind: "nuevo" };
  if (parts[0] === "itinerarios" && parts[1])
    return { kind: "itinerario", id: Number(parts[1]) };
  return { kind: "itinerarios" };
}

function useRoute() {
  const location = useLocation();
  const navigateTo = useNavigate();
  const current = route(location.pathname);
  function navigate(path: string) {
    navigateTo(`${ROOT}${path}`);
    window.scrollTo(0, 0);
  }
  return { current, navigate };
}

function ErrorMessage({ error }: { error: unknown }) {
  if (!error) return null;
  if (error instanceof ApiError && error.status === 403) return (
    <MuiCard component="section" className="card" role="alert">
      <Typography variant="h4Bold" component="h1">Sin permiso</Typography>
      <p>No tenés permiso para acceder a esta sección.</p>
      <Link href="/">Volver a SISOC</Link>
    </MuiCard>
  );
  const message = error instanceof Error ? error.message : "Ocurrió un error.";
  return (
    <Alert severity="error" role="alert" sx={{ mb: 2 }}>
      {message}
      {error instanceof ApiError && error.status === 401 && (
        <>
          {" "}
          <Link href={`/login/?next=${encodeURIComponent(window.location.pathname)}`}>Iniciar sesión</Link>
        </>
      )}
    </Alert>
  );
}

function useData<T>(path: string) {
  const { data, error } = useQuery<T, Error>({ queryKey: ["vpsl", path], queryFn: () => get<T>(path) });
  return { data, error };
}

function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <MuiCard component="section" className={`card ${className}`}>{children}</MuiCard>;
}

function TableActionIcon({ label, onClick, icon }: { label: string; onClick: () => void; icon: React.ReactNode }) {
  return <Tooltip title={label}><IconButton size="small" color="primary" aria-label={label} onClick={onClick}>{icon}</IconButton></Tooltip>;
}

function OverviewTiles({ items }: { items: { label: string; value: string | number; detail: string }[] }) {
  return <section className="overview-tiles" aria-label="Resumen de la vista">
    {items.map((item) => <div className="overview-tile" key={item.label}>
      <span className="overview-label">{item.label}</span>
      <strong>{item.value}</strong>
      <small>{item.detail}</small>
    </div>)}
  </section>;
}

function LoadingOverview({ label }: { label: string }) {
  const reducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const skeletonAnimation = reducedMotion ? false : "pulse";
  return <section className="overview-tiles" role="status" aria-label={`Cargando ${label}`}>
    {[0, 1, 2].map((item) => <div className="overview-tile" key={item}>
      <Skeleton animation={skeletonAnimation} width="55%" height={18} />
      <Skeleton animation={skeletonAnimation} width="35%" height={42} />
      <Skeleton animation={skeletonAnimation} width="70%" height={16} />
    </div>)}
  </section>;
}

function Pagination({
  page,
  count,
  pageSize,
  onPage,
}: {
  page: number;
  count: number;
  pageSize: number;
  onPage: (page: number) => void;
}) {
  if (count <= pageSize) return null;
  return <TablePagination
    component="div"
    className="pagination"
    count={count}
    page={page - 1}
    rowsPerPage={pageSize}
    rowsPerPageOptions={[]}
    onPageChange={(_event, nextPage) => onPage(nextPage + 1)}
    labelDisplayedRows={({ from, to, count: total }) => `${from}–${to} de ${total}`}
    slotProps={{ actions: { previousButton: { 'aria-label': 'Página anterior' }, nextButton: { 'aria-label': 'Página siguiente' } } }}
  />;
}

function Itinerarios({
  navigate,
  canAdd,
  permissions,
}: {
  navigate: (path: string) => void;
  canAdd: boolean;
  permissions: Record<string, boolean>;
}) {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [state, setState] = useState("");
  const [page, setPage] = useState(1);
  const { data, error } = useData<Page<Itinerario>>(
    `/itinerarios/?page=${page}&q=${encodeURIComponent(search)}&estado=${encodeURIComponent(state)}`,
  );
  return (
    <>
      <div className="heading">
        <div>
          <p className="eyebrow">Operación territorial</p>
          <Typography variant="h4Bold" component="h1">Itinerarios</Typography>
          <p>Planificación y seguimiento de Ver para ser libre.</p>
        </div>
        {canAdd && (
          <Button variant="contained" color="primary" size="large" startIcon={<AddIcon />} onClick={() => navigate("itinerarios/nuevo/")}>Nuevo itinerario</Button>
        )}
      </div>
      <Card className="filter-card">
        <form
          className="search search-with-state"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            setSearch(query);
          }}
        >
          <TextField
            id="itinerarios-q"
            label="Código, provincia o referente"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar itinerarios"
            slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> } }}
          />
          <TextField id="itinerarios-estado" select label="Estado" value={state} onChange={(event) => { setPage(1); setState(event.target.value); }}>
            <MenuItem value="">Todos</MenuItem>
            {data?.estados?.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}
          </TextField>
          <Button variant="outlined" size="large" startIcon={<SearchIcon />} type="submit">Buscar</Button>
        </form>
      </Card>
      <ErrorMessage error={error} />
      {data && (
        <Card className="results-card">
          <div className="card-header">
            <h2>Resultados</h2>
            <span>{data.count} itinerarios</span>
          </div>
          {data.count === 0 ? (
            <p>No se encontraron itinerarios.</p>
          ) : (
            <TableContainer className="table-wrap">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Código</TableCell>
                    <TableCell>Provincia</TableCell>
                    <TableCell>Período</TableCell>
                    <TableCell>Referente</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Jornadas</TableCell>
                    <TableCell className="actions-column">Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.results.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <Link component="button" className="link"
                          onClick={() => navigate(`itinerarios/${item.id}/`)}
                        >
                          {item.codigo}
                        </Link>
                      </TableCell>
                      <TableCell>{item.provincia}</TableCell>
                      <TableCell>
                        {formatDate(item.fecha_inicio)} → {formatDate(item.fecha_fin)}
                      </TableCell>
                      <TableCell>{item.referente}</TableCell>
                      <TableCell>
                        <StateChip state={item.estado} label={item.estado_label} />
                      </TableCell>
                      <TableCell>{item.jornadas_total ?? "—"}</TableCell>
                      <TableCell className="actions-column"><div className="workflow-actions">
                        <TableActionIcon label="Ver itinerario" icon={<VisibilityIcon />} onClick={() => navigate(`itinerarios/${item.id}/`)} />
                        {permissions.change_itinerariovpsl && (
                          <TableActionIcon label="Editar itinerario" icon={<EditIcon />} onClick={() => navigate(`forms/itinerario-${item.estado === "en_subsanacion" ? "subsanar" : "edit"}/${item.id}/`)} />
                        )}
                        {permissions.delete_itinerariovpsl && (
                          <ActionButton
                            kind="eliminar-itinerario"
                            id={item.id}
                            label="Eliminar"
                            iconOnly
                            after={() => window.location.reload()}
                          />
                        )}
                      </div></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
          <Pagination page={page} count={data.count} pageSize={10} onPage={setPage} />
        </Card>
      )}
    </>
  );
}

function Sedes({ navigate, canAdd, permissions }: { navigate: (path: string) => void; canAdd: boolean; permissions: Record<string, boolean> }) {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { data, error } = useData<Page<Sede>>(
    `/sedes/?page=${page}&q=${encodeURIComponent(search)}`,
  );
  return (
    <>
      <div className="heading">
        <div>
          <p className="eyebrow">Red territorial</p>
          <Typography variant="h4Bold" component="h1">Sedes</Typography>
          <p>Escuelas y establecimientos vinculados al programa.</p>
        </div>
        {canAdd && <Button variant="contained" color="primary" size="large" startIcon={<AddIcon />} onClick={() => navigate("forms/sede-create/0/")}>Nueva sede</Button>}
      </div>
      {!data && !error && <LoadingOverview label="sedes" />}
      {data && <OverviewTiles items={[
        { label: "Sedes", value: data.count, detail: "Total con la búsqueda actual" },
        { label: "En esta página", value: data.results.length, detail: `Página ${page}` },
        { label: "Localidades visibles", value: new Set(data.results.map((item) => item.localidad).filter(Boolean)).size, detail: "Distintas en esta página" },
      ]} />}
      <Card className="filter-card">
        <form
          className="search"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            setSearch(query);
          }}
        >
          <TextField
            id="sedes-q"
            label="Buscar sede"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Nombre, CUE, localidad…"
            slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> } }}
          />
          <Button variant="outlined" size="large" startIcon={<SearchIcon />} type="submit">Buscar</Button>
        </form>
      </Card>
      <ErrorMessage error={error} />
      {data && (
        <Card className="results-card">
          <div className="card-header">
            <h2>Resultados</h2>
            <span>{data.count} sedes</span>
          </div>
          {data.count === 0 ? (
            <p>No se encontraron sedes.</p>
          ) : (
            <TableContainer className="table-wrap">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Sede</TableCell>
                    <TableCell>CUE</TableCell>
                    <TableCell>Localidad</TableCell>
                    <TableCell>Jurisdicción</TableCell>
                    <TableCell className="actions-column">Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.results.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell><Link component="button" className="link" onClick={() => navigate(`sedes/${item.id}/`)}>{item.nombre}</Link></TableCell>
                      <TableCell>{item.cueanexo || "—"}</TableCell>
                      <TableCell>{item.localidad}</TableCell>
                      <TableCell>{item.jurisdiccion}</TableCell>
                      <TableCell className="actions-column"><div className="workflow-actions">
                        <TableActionIcon label="Ver sede" icon={<VisibilityIcon />} onClick={() => navigate(`sedes/${item.id}/`)} />
                        {permissions.change_sedevpsl && (
                          <TableActionIcon label="Editar sede" icon={<EditIcon />} onClick={() => navigate(`forms/sede-edit/${item.id}/`)} />
                        )}
                        {permissions.delete_sedevpsl && (
                          <ActionButton
                            kind="eliminar-sede"
                            id={item.id}
                            label="Eliminar"
                            iconOnly
                            after={() => window.location.reload()}
                          />
                        )}
                      </div></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
          <Pagination page={page} count={data.count} pageSize={15} onPage={setPage} />
        </Card>
      )}
    </>
  );
}

function ItinerarioDetail({
  id,
  navigate,
  permissions,
  canExport,
}: {
  id: number;
  navigate: (path: string) => void;
  permissions: Record<string, boolean>;
  canExport: boolean;
}) {
  const { data, error } = useData<Itinerario>(`/itinerarios/${id}/`);
  if (error) return <ErrorMessage error={error} />;
  if (!data) return <p>Cargando itinerario…</p>;
  return (
    <>
      <div className="detail-toolbar">
        <Button className="back" variant="text" startIcon={<ArrowBackIcon />} onClick={() => navigate("")}>Itinerarios</Button>
        <div className="detail-toolbar-actions">
          {permissions.change_itinerariovpsl && data.estado !== "rechazado" && <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => navigate(`forms/itinerario-${data.estado === "en_subsanacion" ? "subsanar" : "edit"}/${id}/`)}>{data.estado === "en_subsanacion" ? "Subsanar" : "Editar"}</Button>}
          {permissions.change_itinerariovpsl && ["borrador", "observado"].includes(data.estado) && <ActionButton kind="presentar" id={id} label="Presentar" />}
          {canExport && <Button component="a" variant="text" size="small" startIcon={<DownloadIcon />} href={`/api/vpsl/exports/itinerario/${id}/`}>Exportar CSV</Button>}
        </div>
      </div>
      <div className="heading">
        <div>
          <p className="eyebrow">Itinerario · {data.provincia}</p>
          <Typography variant="h4Bold" component="h1">{data.codigo}</Typography>
          <p>
            <StateChip state={data.estado} label={data.estado_label} />
          </p>
        </div>
      </div>
      {permissions.change_itinerariovpsl && ["presentado", "en_revision", "subsanado"].includes(data.estado) && <EvaluateItinerary itinerary={data} />}
      {data.subsanacion_observaciones && <Alert severity="info" sx={{ mb: 2 }}><strong>Observaciones de evaluación:</strong> {data.subsanacion_observaciones}</Alert>}
      <Card>
        <h2>Resumen del itinerario</h2>
        <div className="itinerary-summary">
          <dl>
            <dt>Período</dt>
            <dd>
              {formatDate(data.fecha_inicio)} al {formatDate(data.fecha_fin)}
            </dd>
            <dt>Referente</dt>
            <dd>{data.referente}</dd>
            <dt>Teléfono</dt><dd>{data.referente_telefono || "Sin especificar"}</dd>
            <dt>Correo</dt><dd>{data.referente_email || "Sin especificar"}</dd>
          </dl>
          <div className="itinerary-summary-letter">
            <Typography variant="h6" component="h3">Carta</Typography>
            {data.carta_archivo_url && <p><Link href={data.carta_archivo_url} target="_blank" rel="noreferrer">Ver carta adjunta</Link> · {data.carta_archivo_estado}</p>}
            {data.carta_referencia && <p>Referencia: {data.carta_referencia} · {data.carta_referencia_estado}</p>}
            {!data.carta_archivo_url && !data.carta_referencia && <Typography color="text.secondary">Sin carta adjunta</Typography>}
          </div>
        </div>
      </Card>
      <Card>
        <div className="card-header">
          <h2>Jornadas</h2>
          <span>{data.jornadas?.length ?? 0}</span>
          {permissions.add_jornadavpsl && data.estado === "aprobado" && (
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => navigate(`forms/jornada-create/${id}/`)}>Nueva jornada</Button>
          )}
        </div>
        {data.jornadas?.length ? (
          <TableContainer className="table-wrap">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Sede</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Registros</TableCell>
                  <TableCell className="actions-column">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.jornadas.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <Link component="button" className="link"
                        onClick={() => navigate(`jornadas/${item.id}/`)}
                      >
                        {formatDate(item.fecha)}
                      </Link>
                    </TableCell>
                    <TableCell>{item.sede}</TableCell>
                    <TableCell>
                      <StateChip state={item.estado} label={item.estado_label} />
                    </TableCell>
                    <TableCell>{item.registros_total ?? "—"}</TableCell>
                    <TableCell className="actions-column"><div className="workflow-actions">
                      <TableActionIcon label="Ver jornada" icon={<VisibilityIcon />} onClick={() => navigate(`jornadas/${item.id}/`)} />
                      {permissions.change_jornadavpsl && (
                        <TableActionIcon label="Editar jornada" icon={<EditIcon />} onClick={() => navigate(`forms/jornada-edit/${item.id}/`)} />
                      )}
                      {permissions.delete_jornadavpsl && (
                        <ActionButton
                          kind="eliminar-jornada"
                          id={item.id}
                          label="Eliminar"
                          iconOnly
                          after={() => window.location.reload()}
                        />
                      )}
                    </div></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <p>Aún no hay jornadas.</p>
        )}
      </Card>
    </>
  );
}

function JornadaDetail({
  id,
  navigate,
  permissions,
  canExport,
}: {
  id: number;
  navigate: (path: string) => void;
  permissions: Record<string, boolean>;
  canExport: boolean;
}) {
  const { data, error } = useData<Jornada>(`/jornadas/${id}/`);
  const [registrosPage, setRegistrosPage] = useState(1);
  const [laboratorioPage, setLaboratorioPage] = useState(1);
  const { data: registros, error: registrosError } = useData<Page<Registro>>(`/jornadas/${id}/registros/?page=${registrosPage}`);
  const { data: laboratorio, error: laboratorioError } = useData<Page<Laboratorio>>(`/jornadas/${id}/laboratorio/?page=${laboratorioPage}`);

  if (error) return <ErrorMessage error={error} />;
  if (!data) return <p>Cargando jornada…</p>;
  return (
    <>
      <div className="detail-toolbar">
        <Button className="back" variant="text" startIcon={<ArrowBackIcon />} onClick={() => navigate(`itinerarios/${data.itinerario_id}/`)}>Itinerario</Button>
        <div className="detail-toolbar-actions">
          {permissions.change_jornadavpsl && <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => navigate(`forms/jornada-edit/${id}/`)}>Editar jornada</Button>}
          {permissions.add_checklistjornadavpsl && <Button variant="outlined" size="small" startIcon={<TaskAltIcon />} onClick={() => navigate(`forms/checklist/${id}/`)}>Checklist</Button>}
          {permissions.add_cierrediariovpsl && ["habilitada", "en_progreso", "pendiente_cierre", "pendiente_cierre_observada"].includes(data.estado) && <Button variant="outlined" size="small" startIcon={<TaskAltIcon />} onClick={() => navigate(`forms/cierre/${id}/`)}>Cierre diario</Button>}
          {canExport && <Button component="a" variant="text" size="small" startIcon={<DownloadIcon />} href={`/api/vpsl/exports/jornada/${id}/`}>Exportar CSV</Button>}
        </div>
      </div>
      <div className="heading">
        <div>
          <Typography component="p" sx={{ fontSize: 20, fontWeight: 700, color: "primary.text" }}>Jornada · {formatDate(data.fecha)}</Typography>
          <Typography variant="h4Bold" component="h1">{data.sede}</Typography>
          <p>
            <StateChip state={data.estado} label={data.estado_label} />
          </p>
        </div>
      </div>
      <div className={data.mapa_query ? "grid two" : undefined}>
      <Card>
        <h2>Datos de la jornada</h2>
        <dl>
          <dt>Localidad</dt><dd>{data.localidad || "Sin especificar"}</dd>
          <dt>Dirección</dt>
          <dd>{data.direccion || "Sin especificar"}</dd>
          <dt>Vehículos</dt><dd>{data.vehiculos?.length ? data.vehiculos.join(", ") : "Sin asignar"}</dd>
          <dt>Referente</dt>
          <dd>{data.referente || "Sin especificar"}</dd>
          <dt>Teléfono</dt><dd>{data.referente_telefono || "Sin especificar"}</dd>
          <dt>Equipo asignado</dt>
          <dd>{data.equipo_asignado || "Sin especificar"}</dd>
          <dt>Registros nominales</dt>
          <dd>{data.registros_total ?? 0}</dd>
          <dt>Observaciones</dt>
          <dd>{data.observaciones || "Sin observaciones"}</dd>
        </dl>
      </Card>
      {data.mapa_query && <Card><h2>Ubicación</h2><iframe className="location-map" title="Mapa de la jornada" loading="lazy" src={`https://www.google.com/maps?q=${encodeURIComponent(data.mapa_query)}&output=embed`} />{data.ubicacion_url && <p><Link href={data.ubicacion_url} target="_blank" rel="noreferrer">Abrir en Google Maps</Link></p>}</Card>}
      </div>
      <div className="grid two"><Card><h2>Checklist de jornada</h2><ul className="item-list">{data.checklist?.map((entry) => <li key={entry.item}>{entry.descripcion}: {entry.cumple === null ? "Pendiente" : entry.cumple ? "Sí" : "No"}{entry.observacion && <small>{entry.observacion}</small>}
        {entry.evidencia_url && <Link href={entry.evidencia_url} target="_blank" rel="noreferrer">Ver evidencia</Link>}
      </li>)}</ul>{!data.checklist?.length && <p>Sin checklist cargado.</p>}</Card>
      <Card><h2>Cierre diario</h2>{data.cierre ? <>
        {!data.cierre.consistente && <Alert severity="warning" sx={{ mb: 2 }}>No hay coincidencia entre los registros nominales y el cierre.</Alert>}
        <dl><dt>Responsable</dt><dd>{data.cierre.responsable}</dd><dt>Atenciones</dt><dd>{data.cierre.atenciones}</dd><dt>Lentes</dt><dd>{data.cierre.lentes}</dd><dt>Casos de laboratorio</dt><dd>{data.cierre.casos}</dd><dt>Consistencia</dt><dd>{data.cierre.consistente ? "Consistente" : "Requiere revisión"}</dd></dl>
        {data.cierre.observaciones && <p>{data.cierre.observaciones}</p>}
        {data.cierre.acta_adjunta_url && <p><Link href={data.cierre.acta_adjunta_url} target="_blank" rel="noreferrer">Descargar acta de cierre</Link></p>}
        {permissions.change_jornadavpsl && (
          data.cierre.consistente
            ? <ActionButton kind="cierre-definitivo" id={id} label="Cierre definitivo" />
            : <span title="Las cantidades del acta de cierre no coincide con los registros nominales. Subsanar para continuar."><Button variant="outlined" size="small" disabled>Cierre definitivo</Button></span>
        )}
        {data.cierre.historial.length > 0 && <Accordion disableGutters><AccordionSummary expandIcon={<ExpandMoreIcon />}>Historial de cambios</AccordionSummary><AccordionDetails><ul>{data.cierre.historial.map((record) => <li key={formatDateTime(record.fecha)}>{formatDateTime(record.fecha)} · {record.responsable} · {record.atenciones} atenciones · {record.lentes} lentes · {record.casos} casos{record.acta_adjunta_url && <Link href={record.acta_adjunta_url} target="_blank" rel="noreferrer">Descargar acta anterior</Link>}</li>)}</ul></AccordionDetails></Accordion>}
      </> : <p>Aún no se registró el cierre.</p>}</Card></div>
      <ErrorMessage error={registrosError || laboratorioError} />
      <Card>
        <div className="card-header"><h2>Registros nominales</h2>{permissions.add_registronominalvpsl && ["habilitada", "en_progreso", "pendiente_cierre", "pendiente_cierre_observada"].includes(data.estado) && <Button variant="contained" startIcon={<AddIcon />} onClick={() => navigate(`forms/registro-create/${id}/`)}>Nuevo registro</Button>}</div>
        <TableContainer className="table-wrap">
          <Table>
            <TableHead><TableRow><TableCell>Acta</TableCell><TableCell>DNI</TableCell><TableCell>Persona</TableCell><TableCell>Resultado</TableCell><TableCell>Graduación I / D</TableCell><TableCell className="actions-column">Acciones</TableCell></TableRow></TableHead>
            <TableBody>{registros?.results.map((entry) => <TableRow key={entry.id}>
              <TableCell>{entry.numero_acta}</TableCell><TableCell>{entry.dni}</TableCell><TableCell>{entry.apellido}, {entry.nombre}</TableCell><TableCell>{entry.resultado}</TableCell>
              <TableCell>{entry.graduacion_izquierda || "—"} / {entry.graduacion_derecha || "—"}</TableCell>
              <TableCell className="actions-column"><div className="workflow-actions">
                {permissions.change_registronominalvpsl && <TableActionIcon label="Editar registro" icon={<EditIcon />} onClick={() => navigate(`forms/registro-edit/${entry.id}/`)} />}
                {permissions.delete_registronominalvpsl && <ActionButton kind="eliminar-registro" id={entry.id} label="Eliminar" iconOnly />}
              </div></TableCell>
            </TableRow>)}</TableBody>
          </Table>
        </TableContainer>
        {registros && !registros.results.length && <p>Sin registros nominales.</p>}
        <Pagination page={registrosPage} count={registros?.count ?? 0} pageSize={25} onPage={setRegistrosPage} />
      </Card>
      <Card><h2>Laboratorio</h2>{laboratorio?.results.map((caso) => <div className="lab-row" key={caso.id}><div>{caso.persona} · {caso.estado}{caso.historial.length > 0 && <Accordion disableGutters><AccordionSummary expandIcon={<ExpandMoreIcon />}>Historial</AccordionSummary><AccordionDetails><ul>{caso.historial.map((record) => <li key={formatDateTime(record.fecha)}>{formatDateTime(record.fecha)}: {record.antes} → {record.despues} · {record.responsable}</li>)}</ul></AccordionDetails></Accordion>}</div>{permissions.change_casolaboratoriovpsl && caso.siguiente && <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => navigate(`forms/laboratorio/${caso.id}/`)}>Actualizar estado</Button>}</div>)}{laboratorio && !laboratorio.results.length && <p>Sin casos de laboratorio.</p>}<Pagination page={laboratorioPage} count={laboratorio?.count ?? 0} pageSize={25} onPage={setLaboratorioPage} /></Card>
      {permissions.change_casolaboratoriovpsl && <BulkLaboratory jornada={{ ...data, laboratorio: laboratorio?.results }} />}
    </>
  );
}

function SedeDetail({
  id,
  navigate,
  permissions,
}: {
  id: number;
  navigate: (path: string) => void;
  permissions: Record<string, boolean>;
}) {
  const { data, error } = useData<Sede>(`/sedes/${id}/`);
  if (error) return <ErrorMessage error={error} />;
  if (!data) return <p>Cargando sede…</p>;
  return (
    <>
      <Button className="back" variant="text" startIcon={<ArrowBackIcon />} onClick={() => navigate("sedes/")}>Sedes</Button>
      <div className="heading">
        <div>
          <p className="eyebrow">Sede · {data.jurisdiccion}</p>
          <Typography variant="h4Bold" component="h1">{data.nombre}</Typography>
          <p>{data.localidad}</p>
        </div>
      </div>
      <Card><div className="workflow-actions">{permissions.change_sedevpsl && <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => navigate(`forms/sede-edit/${id}/`)}>Editar sede y checklist</Button>}{permissions.delete_sedevpsl && <ActionButton kind="eliminar-sede" id={id} label="Eliminar sede" after={() => { navigate("sedes/"); window.location.reload(); }} />}</div></Card>
      <Card>
        <h2>Información de la sede</h2>
        <dl>
          <dt>CUE anexo</dt>
          <dd>{data.cueanexo || "Sin especificar"}</dd>
          <dt>Domicilio</dt>
          <dd>{data.domicilio}</dd>
          <dt>Teléfono</dt>
          <dd>{data.telefono || "Sin especificar"}</dd>
          <dt>Correo</dt>
          <dd>{data.mail || "Sin especificar"}</dd>
          <dt>Checklist</dt>
          <dd>{data.checklist_aprobado ? "Aprobado" : "Pendiente"}</dd>
        </dl>
      </Card>
      {data.mapa_query && <Card><h2>Ubicación</h2><iframe className="location-map" title="Mapa de la sede" loading="lazy" src={`https://www.google.com/maps?q=${encodeURIComponent(data.mapa_query)}&output=embed`} /></Card>}
    </>
  );
}

const nuevoItinerarioSchema = z.object({
  provincia: z.string().min(1, "Seleccioná una provincia."),
  fecha_inicio: z.string().min(1, "Ingresá la fecha de inicio."),
  fecha_fin: z.string().min(1, "Ingresá la fecha de fin."),
  referente_nombre: z.string().trim().min(1, "Ingresá el nombre."),
  referente_apellido: z.string(),
  referente_telefono: z.string().trim().min(1, "Ingresá el teléfono."),
  referente_email: z.email("Ingresá un correo válido."),
  carta_archivo: z.any(),
  observaciones: z.string(),
}).refine((value) => value.fecha_fin >= value.fecha_inicio, { path: ["fecha_fin"], message: "La fecha de fin debe ser posterior al inicio." });

type NuevoItinerarioValues = z.infer<typeof nuevoItinerarioSchema>;

function NuevoItinerario({ navigate }: { navigate: (path: string) => void }) {
  const { data, error: optionsError } = useData<Options>("/options/");
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const { register, control, watch, handleSubmit, setValue, setError: setFieldError, formState: { errors } } = useForm<NuevoItinerarioValues>({
    defaultValues: { provincia: "", fecha_inicio: "", fecha_fin: "", referente_nombre: "", referente_apellido: "", referente_telefono: "", referente_email: "", observaciones: "" },
  });
  const fechaInicio = watch("fecha_inicio");
  const fechaFin = watch("fecha_fin");
  function muiField(name: Parameters<typeof register>[0]) {
    const { ref, ...props } = register(name);
    return { ...props, inputRef: ref };
  }
  useEffect(() => {
    if (data?.provincias.length === 1)
      setValue("provincia", String(data.provincias[0].id));
  }, [data, setValue]);
  async function submit(values: NuevoItinerarioValues) {
    const validated = nuevoItinerarioSchema.safeParse(values);
    if (!validated.success) {
      for (const issue of validated.error.issues) {
        const field = issue.path[0];
        if (typeof field === "string") setFieldError(field as keyof NuevoItinerarioValues, { message: issue.message });
      }
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const payload = new FormData();
      for (const [key, value] of Object.entries(values)) {
        if (key === "carta_archivo") {
          const file = (value as FileList | undefined)?.[0];
          if (file) payload.set(key, file);
        } else payload.set(key, String(value));
      }
      const created = await postForm<Itinerario>(
        "/itinerarios/",
        payload,
      );
      navigate(`itinerarios/${created.id}/`);
    } catch (reason) {
      setError(reason);
    } finally {
      setSaving(false);
    }
  }
  return (
    <>
      <Button className="back" variant="text" startIcon={<ArrowBackIcon />} onClick={() => navigate("")}>Itinerarios</Button>
      <div className="heading">
        <div>
          <p className="eyebrow">Planificación</p>
          <Typography variant="h4Bold" component="h1">Nuevo itinerario</Typography>
          <p>Completá los datos principales y adjuntá la carta requerida.</p>
        </div>
      </div>
      <ErrorMessage error={optionsError || error} />
      {error instanceof ApiError && error.fields && (
        <Alert severity="error" role="alert" sx={{ mb: 2 }}>
          <ul>
            {Object.entries(error.fields).map(([field, messages]) => (
              <li key={field}>
                {field}: {messages.map((item) => item.message).join(", ")}
              </li>
            ))}
          </ul>
        </Alert>
      )}
      <Card>
        <form className="form-grid" onSubmit={handleSubmit(submit)}>
          <label htmlFor="itinerario-provincia">
            Provincia
            <Controller name="provincia" control={control} render={({ field }) => <Autocomplete
              id="itinerario-provincia"
              options={data?.provincias ?? []}
              getOptionLabel={(option) => option.nombre}
              isOptionEqualToValue={(option, current) => option.id === current.id}
              value={data?.provincias.find((option) => String(option.id) === field.value) ?? null}
              onChange={(_event, option) => field.onChange(option ? String(option.id) : "")}
              onBlur={field.onBlur}
              noOptionsText="No se encontraron provincias"
              clearText="Limpiar selección"
              openText="Mostrar provincias"
              closeText="Cerrar provincias"
              renderInput={(params) => <TextField {...params} inputRef={field.ref} required error={Boolean(errors.provincia)} helperText={errors.provincia?.message} placeholder="Buscar provincia…" />}
            />} />
          </label>
          <label>
            Fecha de inicio
            <TextField {...muiField("fecha_inicio")} type="date" fullWidth required />
          </label>
          <label>
            Fecha de fin
            <TextField {...muiField("fecha_fin")} type="date" fullWidth required error={Boolean(errors.fecha_fin) || Boolean(fechaInicio && fechaFin && fechaFin < fechaInicio)} helperText={errors.fecha_fin?.message || (fechaInicio && fechaFin && fechaFin < fechaInicio ? "La fecha de fin no puede ser anterior al inicio." : undefined)} slotProps={{ htmlInput: { min: fechaInicio || undefined } }} />
          </label>
          <label>
            Nombre del referente
            <TextField {...muiField("referente_nombre")} fullWidth required />
          </label>
          <label>
            Apellido del referente
            <TextField {...muiField("referente_apellido")} fullWidth />
          </label>
          <label>
            Teléfono
            <TextField {...muiField("referente_telefono")} fullWidth required />
          </label>
          <label>
            Correo electrónico
            <TextField {...muiField("referente_email")} type="email" fullWidth required error={Boolean(errors.referente_email)} helperText={errors.referente_email?.message} />
          </label>
          <label className="wide">
            Carta archivo
            <TextField {...muiField("carta_archivo")} type="file" fullWidth required />
          </label>
          <label className="wide">
            Observaciones
            <TextField {...muiField("observaciones")} multiline minRows={3} fullWidth />
          </label>
          <div className="form-actions">
            <Button variant="outlined" type="button" onClick={() => navigate("")}>Cancelar</Button>
            <Button variant="contained" startIcon={<AddIcon />} type="submit" disabled={saving}>{saving ? "Guardando…" : "Crear itinerario"}</Button>
          </div>
        </form>
      </Card>
    </>
  );
}

export default function App() {
  const { current, navigate } = useRoute();
  const pageKey = `${current.kind}-${current.id ?? ""}-${current.formKind ?? ""}`;
  const { data: session, error } = useData<Session>("/session/");
  const requestedSection = current.kind === "sede" || current.kind === "sedes" || (current.kind === "form" && current.formKind?.startsWith("sede")) ? "sedes" : "itinerarios";
  return (
    <V2Layout username={session?.username} sectionLabel="Ver para ser libre" modules={[
      ...(session?.can_view_itinerarios ? [{ label: "Itinerarios", href: ROOT, active: requestedSection === "itinerarios", icon: <CalendarTodayIcon />, onNavigate: () => navigate("") }] : []),
      ...(session?.can_view_sedes ? [{ label: "Sedes", href: `${ROOT}sedes/`, active: requestedSection === "sedes", icon: <LocationOnIcon />, onNavigate: () => navigate("sedes/") }] : []),
    ]}>
      <main className="content vpsl-experiment">
        <div className="vpsl-page" key={pageKey}>
          {error ? (
            <ErrorMessage error={error} />
          ) : !session ? (
            <p>Verificando sesión…</p>
          ) : current.kind === "itinerarios" && session.can_view_itinerarios ? (
            <Itinerarios
              navigate={navigate}
              canAdd={session.can_add_itinerarios}
              permissions={session.permissions}
            />
          ) : current.kind === "sedes" && session.can_view_sedes ? (
            <Sedes navigate={navigate} canAdd={session.permissions.add_sedevpsl} permissions={session.permissions} />
          ) : current.kind === "itinerario" && session.can_view_itinerarios ? (
            <ItinerarioDetail id={current.id!} navigate={navigate} permissions={session.permissions} canExport={session.can_export} />
          ) : current.kind === "jornada" && session.can_view_itinerarios ? (
            <JornadaDetail id={current.id!} navigate={navigate} permissions={session.permissions} canExport={session.can_export} />
          ) : current.kind === "sede" && session.can_view_sedes ? (
            <SedeDetail id={current.id!} navigate={navigate} permissions={session.permissions} />
          ) : current.kind === "form" ? (
            <WorkflowForm kind={current.formKind!} id={current.id!} navigate={navigate} />
          ) : current.kind === "nuevo" && session.can_add_itinerarios ? (
            <NuevoItinerario navigate={navigate} />
          ) : (
            <Alert severity="warning">No tenés acceso a esta sección.</Alert>
          )}
        </div>
      </main>
    </V2Layout>
  );
}
