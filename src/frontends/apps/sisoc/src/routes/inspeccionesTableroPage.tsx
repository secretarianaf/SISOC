import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { apiPath, client } from "./inspeccionesEscuelasApi";
import { Screen } from "./inspeccionesEscuelasPage";
import { useScreen } from "./inspeccionesScreen";
import { datosValid, FILTER_KEYS, shellValid, type Categoria, type Filters, type Indice, type Serie, type TableroDatos, type TableroShell } from "./inspeccionesTableroApi";
import { useLeafletStyles } from "./inspeccionesTableroLeaflet";
import TableroMapa from "./inspeccionesTableroMapa";
import InspToasts from "./inspeccionesToasts";

/**
 * Tablero tab of the Inspecciones panel (`inspecciones/tablero.html` + `tablero.js`,
 * IN03). The shell (filters, options, interval) comes from the vertical's web API;
 * every figure comes from the polled `tablero/datos/` response, the very JSON the
 * native page reads: nothing is derived from the rows on screen. Polling keeps the
 * native rules: every `intervalo_ms`, paused while the tab is hidden, resumed with a
 * fresh read, «Sin conexión» with the last good time and a retry, and a session
 * notice on 401/403. CSV and the PDF/ZIP download are plain links to the backend.
 */
const NEW_MS = 8000;
const COLOR_RESULTADO: Record<string, string> = { constatado: "#3b8681", parcial: "#8fd6d0", cerrada: "#c26a00", no_ingreso: "#7a3a00", sin_dato: "#d6d6d6" };
const COLOR_PRESENCIA: Record<string, string> = { si: "#3b8681", no: "#c26a00", no_constatado: "#9e9e9e", sin_dato: "#d6d6d6" };
const GRIS = "#9e9e9e";
const formatoNumero = new Intl.NumberFormat("es-AR");
const formatoPorcentaje = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const numero = (valor: number | null | undefined) => (valor === null || valor === undefined ? "–" : formatoNumero.format(valor));
const plural = (cantidad: number, singular: string, pluralizado: string) => `${numero(cantidad)} ${cantidad === 1 ? singular : pluralizado}`;
// Argentina time, like the official hour of the actas.
const hora = (date: Date) => date.toLocaleTimeString("es-AR", { timeZone: "America/Argentina/Buenos_Aires", hourCycle: "h23", hour: "2-digit", minute: "2-digit", second: "2-digit" });
const width = (porcentaje: number): CSSProperties => ({ width: `${Math.max(0, Math.min(100, porcentaje))}%` });

type Conn = { estado: "cargando" | "vivo" | "desconectado" | "pausado"; texto: string; ultimaOk: number | null; falla: null | { sesion: boolean } };

/** `querystring()` of `tablero.js`: the non-empty filters; the locality only with a province. */
function queryOf(filters: Filters) {
  const params = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    if (key === "localidad" && !filters.provincia) continue;
    if (filters[key]) params.set(key, filters[key]);
  }
  return params.toString();
}

function useLive(shell: TableroShell, query: string) {
  const [data, setData] = useState<TableroDatos | null>(null);
  const [conn, setConn] = useState<Conn>({ estado: "cargando", texto: "Conectando…", ultimaOk: null, falla: null });
  const [now, setNow] = useState(() => Date.now());
  const [fit, setFit] = useState(0);
  const [seenAt, setSeenAt] = useState<Map<string, number>>(() => new Map());
  const known = useRef<Map<string, number> | null>(null);
  const url = apiPath(shell.urls.datos);
  const interval = shell.intervalo_ms;

  // A change of filters resets what `alCambiarFiltros` resets; the effect below reads again.
  const reset = useCallback(() => {
    known.current = null;
    setSeenAt(new Map());
    setFit((n) => n + 1);
    setConn((c) => ({ ...c, estado: "cargando", texto: "Actualizando…" }));
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let current: AbortController | null = null;
    const fail = (sesion: boolean) => setConn((c) => ({ ...c, estado: "desconectado", texto: "Sin conexión", falla: { sesion } }));
    const poll = () => {
      clearTimeout(timer);
      current?.abort();
      const mine = new AbortController();
      current = mine;
      client.get(`${url}${query ? `?${query}` : ""}`, {
        signal: mine.signal, validateStatus: () => true, headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
      }).then(({ data: body, status }: { data: unknown; status: number }) => {
        if (mine.signal.aborted) return;
        if (status === 401 || status === 403) fail(true);
        else if (status < 200 || status >= 300 || !datosValid(body)) fail(false);
        else {
          // `pintarUltimas`: the first read marks nothing as new; later unseen actas are new for 8 s.
          const firstRead = known.current === null;
          const map = known.current ?? new Map<string, number>();
          for (const acta of body.ultimas) if (!map.has(acta.numero)) map.set(acta.numero, firstRead ? 0 : Date.now());
          known.current = map;
          setSeenAt(new Map(map));
          setData(body);
          setConn({ estado: "vivo", texto: "En vivo", ultimaOk: Date.now(), falla: null });
        }
      }).catch(() => { if (!mine.signal.aborted) fail(false); }).finally(() => {
        if (current === mine) {
          current = null;
          if (!document.hidden) timer = setTimeout(poll, interval);
        }
      });
    };
    const visibility = () => {
      if (document.hidden) {
        clearTimeout(timer);
        current?.abort();
        current = null;
        setConn((c) => ({ ...c, estado: "pausado", texto: "En pausa (pestaña oculta)" }));
      } else {
        setConn((c) => ({ ...c, estado: "cargando", texto: "Actualizando…" }));
        poll();
      }
    };
    document.addEventListener("visibilitychange", visibility);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    poll();
    return () => {
      document.removeEventListener("visibilitychange", visibility);
      clearInterval(tick);
      clearTimeout(timer);
      current?.abort();
    };
  }, [url, interval, query]);
  return { data, conn, now, fit, seenAt, reset };
}

function Kpis({ d }: { d: TableroDatos | null }) {
  const i = d?.indicadores;
  return (
    <div className="insp-totales insp-totales-5">
      <div className="insp-kpi insp-kpi-teal">
        <div className="insp-kpi-titulo">Escuelas únicas inspeccionadas</div>
        <div className="insp-kpi-valor" data-kpi="escuelas_unicas">{numero(i?.escuelas_unicas)}</div>
        <div className="insp-kpi-detalle">sin contar anuladas ni de prueba</div>
      </div>
      <div className="insp-kpi insp-kpi-teal">
        <div className="insp-kpi-titulo">Actas finalizadas válidas</div>
        <div className="insp-kpi-valor" data-kpi="actas_validas">{numero(i?.actas_validas)}</div>
        <div className="insp-kpi-detalle"><span data-kpi="escuelas_con_mas_de_una_visita">{numero(i?.escuelas_con_mas_de_una_visita)}</span> escuelas con más de una visita</div>
      </div>
      <div className="insp-kpi">
        <div className="insp-kpi-titulo">Inspectores con actividad</div>
        <div className="insp-kpi-valor">
          <span data-kpi="inspectores_con_actividad">{numero(i?.inspectores.con_actividad)}</span>{" "}
          <span className="insp-kpi-total">/ <span data-kpi="inspectores_habilitados">{numero(i?.inspectores.habilitados)}</span></span>
        </div>
        <div className="insp-kpi-detalle"><span data-kpi="inspectores_sin_actividad">{numero(i?.inspectores.sin_actividad)}</span> sin actas ni borradores</div>
      </div>
      <div className="insp-kpi insp-kpi-celeste">
        <div className="insp-kpi-titulo">Borradores en curso</div>
        <div className="insp-kpi-valor" data-kpi="borradores_en_curso">{numero(i?.borradores_en_curso)}</div>
        <div className="insp-kpi-detalle">avance provisional, no suma</div>
      </div>
      <div className="insp-kpi insp-kpi-ambar">
        <div className="insp-kpi-titulo">Notificación pendiente</div>
        <div className="insp-kpi-valor" data-kpi="notificacion_pendiente">{numero(i?.notificacion_pendiente)}</div>
        <div className="insp-kpi-detalle"><span data-kpi="notificacion_cargada">{numero(i?.notificacion_cargada)}</span> cargadas</div>
      </div>
    </div>
  );
}

function Segmentos({ categorias, colores }: { categorias: Categoria[]; colores: Record<string, string> }) {
  const total = categorias.reduce((sum, c) => sum + (c.cantidad || 0), 0);
  return (
    <div className="insp-segmentos" role="img" aria-label={categorias.map((c) => `${numero(c.cantidad)} ${c.etiqueta}`).join(", ")}>
      {categorias.map((c) => <span key={c.valor} className="insp-segmento" style={{ backgroundColor: colores[c.valor] || GRIS, ...width(total ? (c.cantidad / total) * 100 : 0) }} />)}
    </div>
  );
}

function Leyenda({ categorias, colores }: { categorias: Categoria[]; colores: Record<string, string> }) {
  return (
    <>
      {categorias.map((c) => (
        <li key={c.valor} className="insp-leyenda-item"><i className="insp-leyenda-punto" aria-hidden="true" style={{ backgroundColor: colores[c.valor] || GRIS }} />{`${c.etiqueta} · ${numero(c.cantidad)}`}</li>
      ))}
    </>
  );
}

const excede = (i: Indice) => i.presente > i.previsto;
const fraccionAusentismo = (i: Indice) => (excede(i)
  ? { texto: `${numero(i.presente)} / ${numero(i.previsto)}`, etiqueta: "presentes / previstos" }
  : { texto: `${numero(i.previsto - i.presente)} / ${numero(i.previsto)}`, etiqueta: "ausentes / previstos" });
const fraccionAulas = (i: Indice) => ({ texto: `${numero(i.presente)} / ${numero(i.previsto)}`, etiqueta: "funcionando / previstas" });

/** `pintarIndice`: the text of an index; without data the template placeholders stay. */
function indiceTexts(prefix: string, i: Indice | undefined, o: { descripcion: string; etiquetaBase: string; fraccion: (i: Indice) => { texto: string; etiqueta: string } }) {
  if (!i) return { porcentaje: "–", fraccion: "–", etiqueta: prefix === "ausentismo" ? "ausentes / previstos" : "funcionando / previstas", descripcion: "–", excluidas: "–" };
  const actas = i.computables + i.excluidas;
  const fraccion = o.fraccion(i);
  return {
    porcentaje: i.porcentaje === null ? "Sin datos computables" : `${formatoPorcentaje.format(i.porcentaje)} %`,
    fraccion: i.computables ? fraccion.texto : "–",
    etiqueta: i.computables ? fraccion.etiqueta : o.etiquetaBase,
    descripcion: `${o.descripcion} · ${actas ? `${plural(i.colegios, "colegio", "colegios")} · ${numero(i.computables)} de ${plural(actas, "acta computable", "actas computables")}` : "sin actas computables"}`,
    excluidas: plural(i.excluidas, "excluida", "excluidas"),
  };
}

function Seccion({ id, title, nota, children }: { id: string; title: string; nota?: ReactNode; children: ReactNode }) {
  return (
    <section className="insp-seccion" aria-labelledby={id}>
      <div className="insp-seccion-cabecera"><h2 id={id}>{title}</h2>{nota}</div>
      {children}
    </section>
  );
}

function Presencia({ d }: { d: TableroDatos | null }) {
  const p = d?.presencia;
  const base = p ? `Base: ${numero(p.personal.denominador)} actas con la pregunta respondida (personal) y ${numero(p.estudiantes.denominador)} (estudiantes), de ${numero(p.personal.total)}. «No constatado» y «Sin dato» se cuentan aparte: no son cero.` : "–";
  const serie = (clave: "personal" | "estudiantes", s: Serie | undefined) => (
    <>
      <div data-tablero-presencia={clave}>{s && <Segmentos categorias={s.categorias} colores={COLOR_PRESENCIA} />}</div>
      <ul className={`insp-leyenda-lista${clave === "personal" ? " mb-2" : ""}`} data-tablero-presencia-leyenda={clave}>{s && <Leyenda categorias={s.categorias} colores={COLOR_PRESENCIA} />}</ul>
    </>
  );
  return (
    <div className="insp-seccion-cuerpo">
      <div className="insp-tablero-texto">
        Hay personal educativo <span className="text-body-secondary" data-tablero-presencia-total="personal">{p ? `(${numero(p.personal.denominador)})` : ""}</span>
      </div>
      {serie("personal", p?.personal)}
      <div className="insp-tablero-texto">
        Hay estudiantes <span className="text-body-secondary" data-tablero-presencia-total="estudiantes">{p ? `(${numero(p.estudiantes.denominador)})` : ""}</span>
      </div>
      {serie("estudiantes", p?.estudiantes)}
      <div className="insp-tablero-texto-secundario mt-2" data-tablero-presencia-denominador="">{base}</div>
      <div className="insp-tablero-texto-secundario mt-1">El personal incluye docentes y no docentes; no equivale a adhesión al paro.</div>
    </div>
  );
}

function ActaNumber({ numero: n, url }: { numero: string; url: string | null }) {
  return url ? <a className="insp-tablero-numero" href={url}>{n}</a> : <span className="insp-tablero-numero">{n}</span>;
}

function Ultimas({ d, now, seenAt }: { d: TableroDatos | null; now: number; seenAt: Map<string, number> }) {
  if (!d) return <tr><td colSpan={8} className="text-center text-body-secondary py-3">Cargando…</td></tr>;
  const rows = d.ultimas.map((acta) => ({ acta, fresh: now - (seenAt.get(acta.numero) ?? 0) < NEW_MS }));
  if (!rows.length) return <tr><td colSpan={8} className="text-center text-body-secondary py-3">Sin actas con estos filtros.</td></tr>;
  return (
    <>
      {rows.map(({ acta, fresh }) => (
        <tr key={acta.numero} className={fresh ? "insp-tablero-nueva" : ""}>
          <td>{acta.hora}{fresh && <span className="insp-tablero-badge insp-tablero-badge-nueva">nueva</span>}</td>
          <td><ActaNumber numero={acta.numero} url={acta.url} /></td>
          <td className="insp-tablero-escuela">{acta.escuela}</td>
          <td>{acta.provincia || "–"}</td>
          <td>{acta.turno}</td>
          <td>{acta.inspector}</td>
          <td><span className={`insp-tablero-badge ${acta.firma.tipo === "firma" ? "insp-tablero-badge-ok" : "insp-tablero-badge-alerta"}`}>{acta.firma.etiqueta}</span></td>
          <td><span className={`insp-tablero-badge ${acta.notificacion.estado === "cargada" ? "insp-tablero-badge-ok" : "insp-tablero-badge-alerta"}`}>{acta.notificacion.etiqueta}</span></td>
        </tr>
      ))}
    </>
  );
}

function FiltersBar({ shell, filters, setFilters, localidades }: { shell: TableroShell; filters: Filters; setFilters: (f: Filters) => void; localidades: { value: string; label: string }[] }) {
  const set = (key: keyof Filters, value: string) => setFilters({ ...filters, [key]: value, ...(key === "provincia" ? { localidad: "" } : {}) });
  const o = shell.options;
  return (
    <form method="get" action="/inspecciones/tablero/" className="insp-seccion-barra insp-filtros" onSubmit={(event) => event.preventDefault()}>
      <label className="visually-hidden" htmlFor="tablero-fecha">Jornada</label>
      <input type="date" className="form-control" id="tablero-fecha" name="fecha" value={filters.fecha} required onChange={(event) => set("fecha", event.target.value)} />
      <label className="visually-hidden" htmlFor="tablero-provincia">Provincia</label>
      <select className="form-select" id="tablero-provincia" name="provincia" value={filters.provincia} onChange={(event) => set("provincia", event.target.value)}>
        <option value="">Todas las provincias</option>
        {o.provincias.map((p) => <option key={p.id} value={String(p.id)}>{p.nombre}</option>)}
      </select>
      <label className="visually-hidden" htmlFor="tablero-localidad">Localidad</label>
      <select className="form-select" id="tablero-localidad" name="localidad" value={filters.localidad} disabled={!filters.provincia} onChange={(event) => set("localidad", event.target.value)}>
        <option value="">Localidad</option>
        {localidades.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
      </select>
      <label className="visually-hidden" htmlFor="tablero-inspector">Inspector</label>
      <select className="form-select" id="tablero-inspector" name="inspector" value={filters.inspector} onChange={(event) => set("inspector", event.target.value)}>
        <option value="">Todos los inspectores</option>
        {o.inspectores.map((i) => <option key={i.id} value={String(i.id)}>{i.nombre}</option>)}
      </select>
      <label className="visually-hidden" htmlFor="tablero-turno">Turno</label>
      <select className="form-select" id="tablero-turno" name="turno" value={filters.turno} onChange={(event) => set("turno", event.target.value)}>
        <option value="">Todos los turnos</option>
        {o.turnos.map((t) => <option key={t.valor} value={t.valor}>{t.etiqueta}</option>)}
      </select>
      <label className="visually-hidden" htmlFor="tablero-notificacion">Notificación</label>
      <select className="form-select" id="tablero-notificacion" name="notificacion" value={filters.notificacion} onChange={(event) => set("notificacion", event.target.value)}>
        <option value="">Notificación: todas</option>
        {o.notificaciones.map((n) => <option key={n.valor} value={n.valor}>{n.etiqueta}</option>)}
      </select>
      <span className="insp-espacio" />
      <span className="insp-tablero-ayuda">Los filtros aplican al mapa, los indicadores y la tabla</span>
    </form>
  );
}

function Tablero({ shell }: { shell: TableroShell }) {
  useLeafletStyles();
  const [filters, setFilters] = useState<Filters>(shell.filters);
  const query = useMemo(() => queryOf(filters), [filters]);
  const { data, conn, now, fit, seenAt, reset } = useLive(shell, query);
  const applyFilters = (next: Filters) => { setFilters(next); reset(); };
  // `history.replaceState` with the applied filters, as `alCambiarFiltros` does.
  useEffect(() => { window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : "")); }, [query]);
  // tablero.css follows `panel.css` in the head of the native page.
  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/static/inspecciones/tablero/tablero.css";
    link.dataset.claroFrame = "";
    document.head.appendChild(link);
    return () => link.remove();
  }, []);
  const localidades = useMemo(() => {
    if (!filters.provincia || !data) return [];
    const list = data.opciones.localidades.map((l) => ({ value: String(l.id), label: l.nombre }));
    if (filters.localidad && !list.some((l) => l.value === filters.localidad)) list.push({ value: filters.localidad, label: "Localidad elegida (sin actas)" });
    return list;
  }, [data, filters.provincia, filters.localidad]);
  const hace = conn.ultimaOk ? `· actualizado hace ${Math.max(0, Math.round((now - conn.ultimaOk) / 1000))} s` : "";
  const aviso = conn.falla === null ? "" : conn.falla.sesion ? "La sesión venció o ya no tiene permiso. Recargá la página para volver a ingresar."
    : `${conn.ultimaOk ? `Los datos son de las ${hora(new Date(conn.ultimaOk))} (última consulta correcta). ` : "Todavía no se pudo cargar el tablero. "}Se reintenta cada ${Math.round(shell.intervalo_ms / 1000)} s.`;
  const suffix = query ? `?${query}` : "";
  const aus = indiceTexts("ausentismo", data?.ausentismo, { descripcion: "Personal ausente sobre el previsto", etiquetaBase: "ausentes / previstos", fraccion: fraccionAusentismo });
  const aul = indiceTexts("aulas", data?.aulas, { descripcion: "Aulas funcionando sobre las previstas", etiquetaBase: "funcionando / previstas", fraccion: fraccionAulas });
  const mapa = data?.mapa;
  return (
    <div className="insp-tablero" id="insp-tablero" data-url-datos={shell.urls.datos} data-url-exportar={shell.urls.exportar} data-url-descargar={shell.urls.descargar} data-intervalo-ms={shell.intervalo_ms}>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2">
        <h1 className="insp-titulo">Inspecciones escolares</h1>
        <div className="insp-tablero-vivo" data-tablero-vivo="" data-estado={conn.estado}>
          <span className="insp-tablero-vivo-punto" aria-hidden="true" />
          <span role="status" aria-live="polite" data-tablero-estado="">{conn.texto}</span>
          <span data-tablero-hace="">{hace}</span>
          <span className="insp-tablero-vivo-intervalo">· se actualiza cada {shell.intervalo_ms / 1000} s</span>
        </div>
      </div>
      <ul className="nav insp-tabs border-bottom mb-3" aria-label="Secciones">
        {shell.tabs.map((tab) => (
          <li key={tab.id} className="nav-item">
            <a className={`nav-link${tab.id === "tablero" ? " active" : ""}`} href={tab.url} aria-current={tab.id === "tablero" ? "page" : undefined}>{tab.label}</a>
          </li>
        ))}
      </ul>
      <div className={`insp-aviso insp-aviso-rojo${conn.falla ? "" : " d-none"}`} role="alert" data-tablero-desconexion="">
        <strong>Sin conexión con el servidor.</strong>{" "}<span data-tablero-desconexion-texto="">{aviso}</span>
      </div>
      <FiltersBar shell={shell} filters={filters} setFilters={applyFilters} localidades={localidades} />
      <Kpis d={data} />
      <div className="insp-tablero-grilla-mapa">
        <section className="insp-seccion" aria-labelledby="tablero-h-mapa">
          <div className="insp-seccion-cabecera">
            <h2 id="tablero-h-mapa">Cobertura territorial</h2>
            <span className="insp-seccion-nota">clic en un punto: escuela, turno, inspector y número de acta</span>
          </div>
          <div className="insp-tablero-mapa-contenedor">
            <TableroMapa puntos={mapa?.puntos ?? null} fitToken={fit} territory={!!(filters.provincia || filters.localidad)} />
            <ul className="insp-tablero-leyenda insp-leyenda-lista">
              <li className="text-body-secondary">Qué significa cada color</li>
              <li><i className="insp-tablero-leyenda-punto insp-tablero-constatada" aria-hidden="true" />Constatada (total o parcial)</li>
              <li><i className="insp-tablero-leyenda-punto insp-tablero-sin-constatacion" aria-hidden="true" />Sin constatación (cerrada o no dejó ingresar)</li>
              <li className="text-body-secondary" data-tablero-sin-gps="">
                {!mapa ? "–" : mapa.sin_coordenadas
                  ? `${numero(mapa.sin_coordenadas)} actas sin ubicación GPS, fuera del mapa (${numero(mapa.manual)} con ubicación manual · ${numero(mapa.sin_ubicacion)} sin ubicación)`
                  : "Todas las actas tienen ubicación GPS"}
              </li>
            </ul>
          </div>
        </section>
        <div className="d-flex flex-column gap-3">
          <Seccion id="tablero-h-turno" title="Visitas por turno">
            <div className="insp-seccion-cuerpo" data-tablero-turnos="">
              {data?.turnos.map((turno) => {
                const maximo = data.turnos.reduce((m, t) => Math.max(m, t.cantidad || 0), 0);
                return (
                  <div key={turno.valor} className="insp-barra">
                    <span className="insp-barra-etiqueta">{turno.etiqueta}</span>
                    <div className="insp-barra-pista"><div className="insp-barra-relleno" style={width(maximo ? (turno.cantidad / maximo) * 100 : 0)} /></div>
                    <span className="insp-barra-valor">{numero(turno.cantidad)}</span>
                  </div>
                );
              })}
            </div>
          </Seccion>
          <Seccion id="tablero-h-resultado" title="Resultado de la constatación" nota={<span className="insp-seccion-nota"><span data-kpi="actas_validas">{numero(data?.indicadores.actas_validas)}</span> actas</span>}>
            <div className="insp-seccion-cuerpo">
              <div data-tablero-resultados="">{data && <Segmentos categorias={data.resultados} colores={COLOR_RESULTADO} />}</div>
              <ul className="insp-leyenda-lista" data-tablero-resultados-leyenda="">{data && <Leyenda categorias={data.resultados} colores={COLOR_RESULTADO} />}</ul>
            </div>
          </Seccion>
        </div>
      </div>
      <div className="insp-tablero-grilla-3">
        <Seccion id="tablero-h-ausentismo" title="Ausentismo observado por colegio">
          <div className="insp-seccion-cuerpo d-flex flex-column gap-1">
            <div className="insp-tablero-indice-fila">
              <div className="insp-tablero-indice" data-indice="ausentismo-porcentaje">{aus.porcentaje}</div>
              <div className="insp-tablero-indice-numeros">
                <span data-indice="ausentismo-fraccion">{aus.fraccion}</span>{" "}
                <span className="insp-tablero-texto-secundario" data-indice="ausentismo-fraccion-etiqueta">{aus.etiqueta}</span>
              </div>
            </div>
            <div className="insp-tablero-texto" data-indice="ausentismo-descripcion">{aus.descripcion}</div>
            <div className={`insp-aviso insp-aviso-ambar${data && excede(data.ausentismo) ? "" : " d-none"}`} role="status" data-indice="ausentismo-aviso-exceso">
              Hay más personal presente que el previsto: revisá la carga de las actas.
            </div>
            <div className="insp-tablero-texto-secundario">
              <span data-indice="ausentismo-excluidas">{aus.excluidas}</span>: sin constatación, sin dato (no informado o no constatado) o previsto igual a cero
            </div>
            <div className="insp-tablero-aviso">El personal incluye docentes y no docentes; no equivale a adhesión al paro.</div>
          </div>
        </Seccion>
        <Seccion id="tablero-h-aulas" title="Aulas en funcionamiento">
          <div className="insp-seccion-cuerpo d-flex flex-column gap-1">
            <div className="insp-tablero-indice-fila">
              <div className="insp-tablero-indice" data-indice="aulas-porcentaje">{aul.porcentaje}</div>
              <div className="insp-tablero-indice-numeros">
                <span data-indice="aulas-fraccion">{aul.fraccion}</span>{" "}
                <span className="insp-tablero-texto-secundario" data-indice="aulas-fraccion-etiqueta">{aul.etiqueta}</span>
              </div>
            </div>
            <div className="insp-tablero-texto" data-indice="aulas-descripcion">{aul.descripcion}</div>
            <div className="insp-tablero-texto-secundario"><span data-indice="aulas-excluidas">{aul.excluidas}</span> · totales por visitas, no por personas únicas</div>
          </div>
        </Seccion>
        <Seccion id="tablero-h-presencia" title="Presencia constatada"><Presencia d={data} /></Seccion>
      </div>
      <section className="insp-seccion" aria-labelledby="tablero-h-ultimas">
        <div className="insp-seccion-cabecera">
          <h2 id="tablero-h-ultimas">Últimas actas</h2>
          <div className="d-flex flex-wrap justify-content-end gap-2">
            <a className="btn btn-outline-primary btn-sm" href={`${shell.urls.descargar}${suffix}`} data-tablero-descargar="">Descargar actas completas</a>
            <a className="btn btn-outline-primary btn-sm" href={`${shell.urls.exportar}${suffix}`} data-tablero-exportar="">Exportar CSV (filtros aplicados)</a>
          </div>
        </div>
        <div className="table-responsive">
          <table className="table insp-tabla insp-tablero-tabla">
            <thead>
              <tr>{["Hora", "Acta", "Escuela", "Provincia", "Turno", "Inspector", "Firma", "Notificación"].map((h) => <th key={h} scope="col">{h}</th>)}</tr>
            </thead>
            <tbody data-tablero-ultimas=""><Ultimas d={data} now={now} seenAt={seenAt} /></tbody>
          </table>
        </div>
      </section>
      <InspToasts messages={shell.messages} />
    </div>
  );
}

export default function TableroPage() {
  const { state } = useScreen(`web/inspecciones/tablero/${window.location.search}`, shellValid);
  return <Screen state={state} noun="tablero" title="Tablero · Inspecciones escolares">{(shell) => <Tablero shell={shell} />}</Screen>;
}
