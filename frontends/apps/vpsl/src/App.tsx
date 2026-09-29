import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { V2Layout } from "@sisoc/ui";
import { Alert, Autocomplete, Button, Card as MuiCard, Tab, TableContainer, Tabs, TextField, Typography } from "@mui/material";
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
    <section className="card" role="alert">
      <Typography variant="h4Bold" component="h1">Sin permiso</Typography>
      <p>No tenés permiso para acceder a esta sección.</p>
      <a href="/">Volver a SISOC</a>
    </section>
  );
  const message = error instanceof Error ? error.message : "Ocurrió un error.";
  return (
    <Alert severity="error" role="alert" sx={{ mb: 2 }}>
      {message}
      {error instanceof ApiError && error.status === 401 && (
        <>
          {" "}
          <a href={`/login/?next=${encodeURIComponent(window.location.pathname)}`}>Iniciar sesión</a>
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

function Pagination({
  page,
  hasNext,
  hasPrevious,
  onPage,
}: {
  page: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onPage: (page: number) => void;
}) {
  if (!hasNext && !hasPrevious) return null;
  return (
    <div className="pagination">
      <Button variant="outlined" disabled={!hasPrevious} onClick={() => onPage(page - 1)}>
        Anterior
      </Button>
      <span>
        Página {page}
      </span>
      <Button variant="outlined" disabled={!hasNext} onClick={() => onPage(page + 1)}>
        Siguiente
      </Button>
    </div>
  );
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
          <button
            className="primary"
            onClick={() => navigate("itinerarios/nuevo/")}
          >
            Nuevo itinerario
          </button>
        )}
      </div>
      <Card>
        <form
          className="search"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            setSearch(query);
          }}
        >
          <label htmlFor="itinerarios-q">
            Buscar por código, provincia o referente
          </label>
          <div>
            <input
              id="itinerarios-q"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar itinerarios"
            />
            <button type="submit">Buscar</button>
          </div>
          <label htmlFor="itinerarios-estado">Estado</label>
          <select id="itinerarios-estado" value={state} onChange={(event) => { setPage(1); setState(event.target.value); }}><option value="">Todos</option>{data?.estados?.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
        </form>
      </Card>
      <ErrorMessage error={error} />
      {!data && !error && <p>Cargando itinerarios…</p>}
      {data && (
        <Card>
          <div className="card-header">
            <h2>Resultados</h2>
            <span>{data.count} itinerarios</span>
          </div>
          {data.count === 0 ? (
            <p>No se encontraron itinerarios.</p>
          ) : (
            <TableContainer className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Provincia</th>
                    <th>Período</th>
                    <th>Referente</th>
                    <th>Estado</th>
                    <th>Jornadas</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <button
                          className="link"
                          onClick={() => navigate(`itinerarios/${item.id}/`)}
                        >
                          {item.codigo}
                        </button>
                      </td>
                      <td>{item.provincia}</td>
                      <td>
                        {formatDate(item.fecha_inicio)} → {formatDate(item.fecha_fin)}
                      </td>
                      <td>{item.referente}</td>
                      <td>
                        <StateChip state={item.estado} label={item.estado_label} />
                      </td>
                      <td>{item.jornadas_total ?? "—"}</td>
                      <td className="workflow-actions">
                        {permissions.change_itinerariovpsl && (
                          <button onClick={() => navigate(`forms/itinerario-${item.estado === "en_subsanacion" ? "subsanar" : "edit"}/${item.id}/`)}>
                            Editar
                          </button>
                        )}
                        {permissions.delete_itinerariovpsl && (
                          <ActionButton
                            kind="eliminar-itinerario"
                            id={item.id}
                            label="Eliminar"
                            after={() => window.location.reload()}
                          />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableContainer>
          )}
          <Pagination page={page} hasNext={!!data.next} hasPrevious={!!data.previous} onPage={setPage} />
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
        {canAdd && <button className="primary" onClick={() => navigate("forms/sede-create/0/")}>Nueva sede</button>}
      </div>
      <Card>
        <form
          className="search"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            setSearch(query);
          }}
        >
          <label htmlFor="sedes-q">Buscar sede</label>
          <div>
            <input
              id="sedes-q"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Nombre, CUE, localidad…"
            />
            <button type="submit">Buscar</button>
          </div>
        </form>
      </Card>
      <ErrorMessage error={error} />
      {!data && !error && <p>Cargando sedes…</p>}
      {data && (
        <Card>
          <div className="card-header">
            <h2>Resultados</h2>
            <span>{data.count} sedes</span>
          </div>
          {data.count === 0 ? (
            <p>No se encontraron sedes.</p>
          ) : (
            <TableContainer className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Sede</th>
                    <th>CUE</th>
                    <th>Localidad</th>
                    <th>Jurisdicción</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((item) => (
                    <tr key={item.id}>
                      <td><button className="link" onClick={() => navigate(`sedes/${item.id}/`)}>{item.nombre}</button></td>
                      <td>{item.cueanexo || "—"}</td>
                      <td>{item.localidad}</td>
                      <td>{item.jurisdiccion}</td>
                      <td className="workflow-actions">
                        {permissions.change_sedevpsl && (
                          <button onClick={() => navigate(`forms/sede-edit/${item.id}/`)}>Editar</button>
                        )}
                        {permissions.delete_sedevpsl && (
                          <ActionButton
                            kind="eliminar-sede"
                            id={item.id}
                            label="Eliminar"
                            after={() => window.location.reload()}
                          />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableContainer>
          )}
          <Pagination page={page} hasNext={!!data.next} hasPrevious={!!data.previous} onPage={setPage} />
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
      <button className="back" onClick={() => navigate("")}>
        ← Itinerarios
      </button>
      <div className="heading">
        <div>
          <p className="eyebrow">Itinerario · {data.provincia}</p>
          <Typography variant="h4Bold" component="h1">{data.codigo}</Typography>
          <p>
            <StateChip state={data.estado} label={data.estado_label} />
          </p>
        </div>
      </div>
      <Card>
        <div className="workflow-actions">
          {permissions.change_itinerariovpsl && data.estado !== "rechazado" && <button onClick={() => navigate(`forms/itinerario-${data.estado === "en_subsanacion" ? "subsanar" : "edit"}/${id}/`)}>{data.estado === "en_subsanacion" ? "Subsanar" : "Editar"}</button>}
          {permissions.change_itinerariovpsl && ["borrador", "observado"].includes(data.estado) && <ActionButton kind="presentar" id={id} label="Presentar" />}
          {canExport && <a href={`/api/vpsl/exports/itinerario/${id}/`}>Exportar CSV</a>}
        </div>
      </Card>
      {permissions.change_itinerariovpsl && ["presentado", "en_revision", "subsanado"].includes(data.estado) && <EvaluateItinerary itinerary={data} />}
      {data.subsanacion_observaciones && <Alert severity="info" sx={{ mb: 2 }}><strong>Observaciones de evaluación:</strong> {data.subsanacion_observaciones}</Alert>}
      <Card><h2>Cartas</h2>
        {data.carta_archivo_url && <p><a href={data.carta_archivo_url} target="_blank" rel="noreferrer">Ver carta adjunta</a> · {data.carta_archivo_estado}</p>}
        {data.carta_referencia && <p>Referencia: {data.carta_referencia} · {data.carta_referencia_estado}</p>}
      </Card>
      <div className="grid two">
        <Card>
          <h2>Planificación</h2>
          <dl>
            <dt>Período</dt>
            <dd>
              {formatDate(data.fecha_inicio)} al {formatDate(data.fecha_fin)}
            </dd>
            <dt>Referente</dt>
            <dd>{data.referente}</dd>
            <dt>Teléfono</dt><dd>{data.referente_telefono || "Sin especificar"}</dd>
            <dt>Correo</dt><dd>{data.referente_email || "Sin especificar"}</dd>
            <dt>Localidades</dt>
            <dd>{data.localidades || "Sin especificar"}</dd>
            <dt>Observaciones</dt>
            <dd>{data.observaciones || "Sin observaciones"}</dd>
          </dl>
        </Card>
        <Card><h2>Jornadas</h2><p>La sede y la ubicación se definen al crear cada jornada.</p></Card>
      </div>
      <Card>
        <div className="card-header">
          <h2>Jornadas</h2>
          <span>{data.jornadas?.length ?? 0}</span>
          {permissions.add_jornadavpsl && data.estado === "aprobado" && (
            <button onClick={() => navigate(`forms/jornada-create/${id}/`)}>Nueva jornada</button>
          )}
        </div>
        {data.jornadas?.length ? (
          <TableContainer className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Sede</th>
                  <th>Estado</th>
                  <th>Registros</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {data.jornadas.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <button
                        className="link"
                        onClick={() => navigate(`jornadas/${item.id}/`)}
                      >
                        {formatDate(item.fecha)}
                      </button>
                    </td>
                    <td>{item.sede}</td>
                    <td>
                      <StateChip state={item.estado} label={item.estado_label} />
                    </td>
                    <td>{item.registros_total ?? "—"}</td>
                    <td className="workflow-actions">
                      {permissions.change_jornadavpsl && (
                        <button onClick={() => navigate(`forms/jornada-edit/${item.id}/`)}>Editar</button>
                      )}
                      {permissions.delete_jornadavpsl && (
                        <ActionButton
                          kind="eliminar-jornada"
                          id={item.id}
                          label="Eliminar"
                          after={() => window.location.reload()}
                        />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
      <button
        className="back"
        onClick={() => navigate(`itinerarios/${data.itinerario_id}/`)}
      >
        ← Itinerario
      </button>
      <div className="heading">
        <div>
          <Typography component="p" sx={{ fontSize: 20, fontWeight: 700, color: "primary.text" }}>Jornada · {formatDate(data.fecha)}</Typography>
          <Typography variant="h4Bold" component="h1">{data.sede}</Typography>
          <p>
            <StateChip state={data.estado} label={data.estado_label} />
          </p>
        </div>
      </div>
      <Card><div className="workflow-actions">
        {permissions.change_jornadavpsl && <button onClick={() => navigate(`forms/jornada-edit/${id}/`)}>Editar jornada</button>}
        {permissions.add_checklistjornadavpsl && <button onClick={() => navigate(`forms/checklist/${id}/`)}>Checklist</button>}
        {permissions.add_cierrediariovpsl && ["habilitada", "en_progreso", "pendiente_cierre", "pendiente_cierre_observada"].includes(data.estado) && <button onClick={() => navigate(`forms/cierre/${id}/`)}>Cierre diario</button>}
        {canExport && <a href={`/api/vpsl/exports/jornada/${id}/`}>Exportar CSV</a>}
      </div></Card>
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
      {data.mapa_query && <Card><h2>Ubicación</h2><iframe className="location-map" title="Mapa de la jornada" loading="lazy" src={`https://www.google.com/maps?q=${encodeURIComponent(data.mapa_query)}&output=embed`} />{data.ubicacion_url && <p><a href={data.ubicacion_url} target="_blank" rel="noreferrer">Abrir en Google Maps</a></p>}</Card>}
      <div className="grid two"><Card><h2>Checklist de jornada</h2><ul className="item-list">{data.checklist?.map((entry) => <li key={entry.item}>{entry.descripcion}: {entry.cumple === null ? "Pendiente" : entry.cumple ? "Sí" : "No"}{entry.observacion && <small>{entry.observacion}</small>}
        {entry.evidencia_url && <a href={entry.evidencia_url} target="_blank" rel="noreferrer">Ver evidencia</a>}
        {entry.historial.length > 0 && <details><summary>Historial</summary><ul>{entry.historial.map((record) => <li key={record.fecha}>{formatDateTime(record.fecha)} · {record.responsable}: {record.antes === null ? "Pendiente" : record.antes ? "Sí" : "No"} → {record.despues === null ? "Pendiente" : record.despues ? "Sí" : "No"}{record.observacion && <p>{record.observacion}</p>}</li>)}</ul></details>}
      </li>)}</ul>{!data.checklist?.length && <p>Sin checklist cargado.</p>}</Card>
      <Card><h2>Cierre diario</h2>{data.cierre ? <>
        {!data.cierre.consistente && <Alert severity="warning" sx={{ mb: 2 }}>No hay coincidencia entre los registros nominales y el cierre.</Alert>}
        <dl><dt>Responsable</dt><dd>{data.cierre.responsable}</dd><dt>Atenciones</dt><dd>{data.cierre.atenciones}</dd><dt>Lentes</dt><dd>{data.cierre.lentes}</dd><dt>Casos de laboratorio</dt><dd>{data.cierre.casos}</dd><dt>Consistencia</dt><dd>{data.cierre.consistente ? "Consistente" : "Requiere revisión"}</dd></dl>
        {data.cierre.observaciones && <p>{data.cierre.observaciones}</p>}
        {data.cierre.acta_adjunta_url && <p><a href={data.cierre.acta_adjunta_url} target="_blank" rel="noreferrer">Descargar acta de cierre</a></p>}
        {permissions.change_jornadavpsl && (
          data.cierre.consistente
            ? <ActionButton kind="cierre-definitivo" id={id} label="Cierre definitivo" />
            : <span title="Las cantidades del acta de cierre no coincide con los registros nominales. Subsanar para continuar."><button type="button" disabled>Cierre definitivo</button></span>
        )}
        {data.cierre.historial.length > 0 && <details><summary>Historial de cambios</summary><ul>{data.cierre.historial.map((record) => <li key={formatDateTime(record.fecha)}>{formatDateTime(record.fecha)} · {record.responsable} · {record.atenciones} atenciones · {record.lentes} lentes · {record.casos} casos{record.acta_adjunta_url && <a href={record.acta_adjunta_url} target="_blank" rel="noreferrer">Descargar acta anterior</a>}</li>)}</ul></details>}
      </> : <p>Aún no se registró el cierre.</p>}</Card></div>
      <ErrorMessage error={registrosError || laboratorioError} />
      <Card><div className="card-header"><h2>Registros nominales</h2>{permissions.add_registronominalvpsl && ["habilitada", "en_progreso", "pendiente_cierre", "pendiente_cierre_observada"].includes(data.estado) && <button onClick={() => navigate(`forms/registro-create/${id}/`)}>Nuevo registro</button>}</div><TableContainer className="table-wrap"><table><thead><tr><th>Acta</th><th>DNI</th><th>Persona</th><th>Resultado</th><th>Graduación I / D</th><th>Acciones</th></tr></thead><tbody>{registros?.results.map((entry) => <tr key={entry.id}><td>{entry.numero_acta}</td><td>{entry.dni}</td><td>{entry.apellido}, {entry.nombre}</td><td>{entry.resultado}</td><td>{entry.graduacion_izquierda || "—"} / {entry.graduacion_derecha || "—"}</td><td><div className="workflow-actions">{permissions.change_registronominalvpsl && <button onClick={() => navigate(`forms/registro-edit/${entry.id}/`)}>Editar</button>}{permissions.delete_registronominalvpsl && <ActionButton kind="eliminar-registro" id={entry.id} label="Eliminar" />}</div></td></tr>)}</tbody></table></TableContainer>{registros && !registros.results.length && <p>Sin registros nominales.</p>}<Pagination page={registrosPage} hasNext={!!registros?.next} hasPrevious={!!registros?.previous} onPage={setRegistrosPage} /></Card>
      <Card><h2>Laboratorio</h2>{laboratorio?.results.map((caso) => <div className="lab-row" key={caso.id}><span>{caso.persona} · {caso.estado}{caso.historial.length > 0 && <details><summary>Historial</summary><ul>{caso.historial.map((record) => <li key={formatDateTime(record.fecha)}>{formatDateTime(record.fecha)}: {record.antes} → {record.despues} · {record.responsable}</li>)}</ul></details>}</span>{permissions.change_casolaboratoriovpsl && caso.siguiente && <button onClick={() => navigate(`forms/laboratorio/${caso.id}/`)}>Actualizar estado</button>}</div>)}{laboratorio && !laboratorio.results.length && <p>Sin casos de laboratorio.</p>}<Pagination page={laboratorioPage} hasNext={!!laboratorio?.next} hasPrevious={!!laboratorio?.previous} onPage={setLaboratorioPage} /></Card>
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
      <button className="back" onClick={() => navigate("sedes/")}>
        ← Sedes
      </button>
      <div className="heading">
        <div>
          <p className="eyebrow">Sede · {data.jurisdiccion}</p>
          <Typography variant="h4Bold" component="h1">{data.nombre}</Typography>
          <p>{data.localidad}</p>
        </div>
      </div>
      <Card><div className="workflow-actions">{permissions.change_sedevpsl && <button onClick={() => navigate(`forms/sede-edit/${id}/`)}>Editar sede y checklist</button>}{permissions.delete_sedevpsl && <ActionButton kind="eliminar-sede" id={id} label="Eliminar sede" after={() => { navigate("sedes/"); window.location.reload(); }} />}</div></Card>
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
      <button className="back" onClick={() => navigate("")}>
        ← Itinerarios
      </button>
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
              renderInput={(params) => <TextField {...params} inputRef={field.ref} size="small" required error={Boolean(errors.provincia)} placeholder="Buscar provincia…" />}
            />} />
            {errors.provincia && <small role="alert">{errors.provincia.message}</small>}
          </label>
          <label>
            Fecha de inicio
            <input {...register("fecha_inicio")} type="date" required />
          </label>
          <label>
            Fecha de fin
            <input {...register("fecha_fin")} type="date" min={fechaInicio || undefined} required />
            {fechaInicio && fechaFin && fechaFin < fechaInicio && <small className="action-error" role="alert">La fecha de fin no puede ser anterior al inicio.</small>}
            {errors.fecha_fin && <small role="alert">{errors.fecha_fin.message}</small>}
          </label>
          <label>
            Nombre del referente
            <input {...register("referente_nombre")} required />
          </label>
          <label>
            Apellido del referente
            <input {...register("referente_apellido")} />
          </label>
          <label>
            Teléfono
            <input {...register("referente_telefono")} required />
          </label>
          <label>
            Correo electrónico
            <input {...register("referente_email")} type="email" required />
            {errors.referente_email && <small role="alert">{errors.referente_email.message}</small>}
          </label>
          <label className="wide">
            Carta archivo
            <input {...register("carta_archivo")} type="file" required />
          </label>
          <label className="wide">
            Observaciones
            <textarea {...register("observaciones")} rows={3} />
          </label>
          <div className="form-actions">
            <button type="button" onClick={() => navigate("")}>
              Cancelar
            </button>
            <button className="primary" type="submit" disabled={saving}>
              {saving ? "Guardando…" : "Crear itinerario"}
            </button>
          </div>
        </form>
      </Card>
    </>
  );
}

export default function App() {
  const { current, navigate } = useRoute();
  const { data: session, error } = useData<Session>("/session/");
  const requestedSection = current.kind === "sede" || current.kind === "sedes" || (current.kind === "form" && current.formKind?.startsWith("sede")) ? "sedes" : "itinerarios";
  const selectedSection = requestedSection === "sedes" && session?.can_view_sedes
    ? "sedes"
    : session?.can_view_itinerarios ? "itinerarios" : "sedes";
  return (
    <V2Layout username={session?.username} modules={session?.can_view_itinerarios || session?.can_view_sedes ? [{ label: "Ver para ser libre", href: ROOT, active: true }] : []}>
      <main className="content">
        {session && (session.can_view_itinerarios || session.can_view_sedes) && <Tabs
          value={selectedSection}
          onChange={(_event, value: string) => navigate(value === "sedes" ? "sedes/" : "")}
          aria-label="Secciones de Ver para ser libre"
          sx={{ mb: 3, borderBottom: 1, borderColor: "divider" }}
        >
          {session.can_view_itinerarios && <Tab value="itinerarios" label="Itinerarios" />}
          {session.can_view_sedes && <Tab value="sedes" label="Sedes" />}
        </Tabs>}
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
      </main>
    </V2Layout>
  );
}
