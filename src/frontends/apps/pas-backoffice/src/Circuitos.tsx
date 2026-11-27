import { useId, useState, type ReactNode } from "react";
import { Alert, alpha, Box, Button, ButtonBase, Card, CardContent, IconButton, Link as MuiLink, Menu, MenuItem, Paper, Stack,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Tooltip, Typography } from "@mui/material";
import ArrowDownward from "@mui/icons-material/ArrowDownward";
import ArrowUpward from "@mui/icons-material/ArrowUpward";
import Check from "@mui/icons-material/Check";
import ChevronLeft from "@mui/icons-material/ChevronLeft";
import ChevronRight from "@mui/icons-material/ChevronRight";
import Download from "@mui/icons-material/Download";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { descargarNomina, exportarPreliquidacionCsv, exportarSintys, importarSintys, pasGet, pasPost, type Area, type Cruces, type Formacion, type Informe,
  type PuntoControl } from "./api";
import { AccionesPas } from "./AccionesPas";
import { AlertMessage, BarRow, DataCheckRow, Oculto, StatCard, PendingRow, ScoreChip, SinDatos, StateChip, StatusRow, TablaCursos } from "./componentes";
import { Cargando, ErrorPas } from "./Estado";
import { CambiarEstado, ErrorOperacion } from "./Gestion";

function useDatos<T>(path: string) {
  return useQuery({ queryKey: ["pas", path], queryFn: () => pasGet<T>(path) });
}

function Metricas({ children, columnas = 3 }: { children: ReactNode; columnas?: number }) {
  return <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))", md: `repeat(${columnas}, minmax(0, 1fr))` } }}>{children}</Box>;
}

/** Score chip: el color sale del estado de formación con la regla de severidad. */
function tonoFormacion(estado: string | undefined, puntos: number): "error" | "warning" | "success" {
  if (estado === "cumplido") return "success";
  if (estado === "en-curso" || puntos > 0) return "warning";
  return "error";
}

export function FormacionPage() {
  const [params, setParams] = useSearchParams();
  const [filtros, setFiltros] = useState(false);
  const search = params.toString();
  const query = useDatos<Formacion>(`areas/formacion/${search ? `?${search}` : ""}`);
  const paginas = useInfiniteQuery({
    queryKey: ["pas", "formacion-personas", search],
    queryFn: ({ pageParam }) => {
      const siguientes = new URLSearchParams(search);
      siguientes.set("page", String(pageParam));
      return pasGet<Pick<Formacion, "personas" | "next_page">>(`formacion/personas/?${siguientes}`);
    },
    initialPageParam: 1,
    initialData: query.data && { pages: [{ personas: query.data.personas, next_page: query.data.next_page }], pageParams: [1] },
    getNextPageParam: (ultima) => ultima.next_page ?? undefined,
    enabled: false,
  });
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  const { persona_seleccionada, resumen, formaciones } = query.data;
  const personas = paginas.data?.pages.flatMap((page) => page.personas) ?? query.data.personas;
  const porcentaje = resumen && resumen.objetivo > 0 ? (resumen.puntos / resumen.objetivo) * 100 : 0;
  const tonoSemaforo = porcentaje <= 0 ? "error" : porcentaje >= 100 ? "success" : "warning";
  const items = persona_seleccionada && !personas.some(({ id }) => id === persona_seleccionada.id)
    ? [{ ...persona_seleccionada, puntos_formacion: resumen?.puntos ?? 0, estado_formacion: resumen?.estado }, ...personas] : personas;
  return <Stack spacing={2}>
    <Oculto component="h1">Formación FCH</Oculto>
    <Stack direction={{ xs: "column", md: "row" }} spacing={3}>
      {/* Sisoc/Scoring selector: Paper outlined, sin acciones al pie. */}
      <Paper component="aside" variant="outlined" aria-label="Seleccionar titular" sx={{ width: { xs: "100%", md: 240 }, flexShrink: 0, alignSelf: "flex-start", overflow: "hidden" }}>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", p: 2, borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="overline" color="text.secondary">Seleccionar titular</Typography>
          <AccionesPas label="Opciones del selector de titulares" items={[{
            label: filtros ? "Ocultar filtros" : "Mostrar filtros", run: () => setFiltros(!filtros),
          }]} />
        </Stack>
        {filtros && <Stack component="form" spacing={1} sx={{ p: 2, borderBottom: 1, borderColor: "divider" }} key={search} onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          setParams({ q: String(form.get("q") ?? ""), estado_formacion: String(form.get("estado_formacion") ?? "todos") });
        }}>
          <TextField size="small" label="Buscar titular" name="q" defaultValue={params.get("q") ?? ""} />
          <TextField size="small" select label="Estado de formación" name="estado_formacion" defaultValue={params.get("estado_formacion") ?? "todos"}>
            <MenuItem value="todos">Todos</MenuItem><MenuItem value="cumplido">Cumplido</MenuItem>
            <MenuItem value="en-curso">En curso</MenuItem><MenuItem value="sin-formacion">Sin formación</MenuItem>
          </TextField>
          <Button type="submit" size="small" variant="outlined">Buscar</Button>
        </Stack>}
        <Stack spacing={0.5} sx={{ p: 1, maxHeight: 490, overflowY: "auto" }}>
          {items.map((item) => {
            const selected = persona_seleccionada?.id === item.id;
            // Sisoc/Scoring card: ButtonBase con el Score chip como display.
            return <ButtonBase key={item.id} component={Link} to={`?${new URLSearchParams({ ...Object.fromEntries(params), persona: String(item.id) })}`}
              aria-current={selected ? "true" : undefined} sx={(theme) => ({ display: "block", textAlign: "left", p: 2, border: 1,
                borderRadius: `${theme.radius.large}px`, borderColor: selected ? "primary.main" : "divider",
                bgcolor: selected ? alpha(theme.palette.primary.main, 0.08) : "background.paper",
                "&:hover": { bgcolor: alpha(theme.palette.primary.main, selected ? 0.12 : 0.04) },
                "&.Mui-focusVisible": { outline: `${theme.border.focus}px solid ${theme.palette.primary.main}`, outlineOffset: 2 } })}>
              <Typography variant="subtitle2" component="span" sx={{ display: "block" }}>
                <Box component="span" sx={{ textTransform: "uppercase" }}>{item.apellidos}</Box>, {item.nombres}</Typography>
              <Box sx={{ mt: 0.5 }}><ScoreChip label={`${item.puntos_formacion} pts`} tono={tonoFormacion(item.estado_formacion, item.puntos_formacion)} /></Box>
            </ButtonBase>;
          })}
          {!items.length && <Typography variant="body2" color="text.secondary">Sin titulares en el padrón.</Typography>}
          {paginas.hasNextPage && <Button size="small" disabled={paginas.isFetchingNextPage} onClick={() => void paginas.fetchNextPage()}>Cargar más titulares</Button>}
          {paginas.isFetchNextPageError && <Typography color="error.text" variant="body2">No se pudieron cargar más titulares.</Typography>}
        </Stack>
      </Paper>
      <Stack spacing={2.5} sx={{ flex: 1, minWidth: 0 }}>
        {resumen ? <>
          <AlertMessage porcentaje={porcentaje}
            puntos={resumen.puntos} titulo={resumen.titulo} detalle={resumen.detalle} />
          {/* Las tres cifras llevan el color del semáforo, como en Figma. */}
          <Metricas>
            <StatCard label="Puntos acumulados" value={resumen.puntos} tone={tonoSemaforo}
              hint={`/ ${resumen.objetivo} requeridos${resumen.credito_inicial ? ` · incluye ${resumen.credito_inicial} de crédito arrastrado` : ""}`} />
            <StatCard label="Día del período" value={resumen.dia_actual} hint={`/ ${resumen.duracion_dias} corridos`} tone={tonoSemaforo} />
            <StatCard label="Crédito excedente" value={`+${resumen.excedente}`} hint="para próximo período" tone={tonoSemaforo} />
          </Metricas>
          {resumen.bloquea_pago && <Alert severity="error">Titular bloqueado para la liquidación hasta cumplir la condicionalidad formativa.</Alert>}
          {resumen.integrada === false && <Alert severity="info" variant="outlined">La fuente FCH todavía no está integrada: la formación no bloquea el pago.</Alert>}
        </> : <Alert severity="info">Seleccioná un titular para consultar su formación.</Alert>}
        <TablaCursos key={persona_seleccionada?.id} rows={formaciones} constancia
          emptyMessage={persona_seleccionada ? undefined : "Seleccioná un titular para ver sus cursos."} />
      </Stack>
    </Stack>
  </Stack>;
}

/** Estado de una alerta de incompatibilidad, como chip de color (Pendiente o Gestionada). */
function tonoAlerta(estado: string): "success" | "warning" {
  return estado.toLocaleLowerCase("es").startsWith("gestion") ? "success" : "warning";
}

/** "noviembre de 2026" → "Noviembre 2026", como en Figma. */
function mesAnio(fecha: Date) {
  const texto = fecha.toLocaleDateString("es-AR", { month: "long", year: "numeric" }).replace(" de ", " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/**
 * Stepper del `Sisoc/Monthly circuit stepper` (Figma): círculo de 32px verde con
 * tilde si el paso está completo, ámbar con el número si está en curso y gris si
 * está pendiente; conector de 2px y textos de 12px alineados a la izquierda.
 */
function CircuitoStepper({ etapas }: { etapas: Cruces["etapas"] }) {
  // Las integraciones pendientes (Justicia, Migraciones) quedan en gris y no
  // frenan el avance: el paso en curso es el primero integrado sin completar.
  const activa = etapas.findIndex(({ completada, integracion_pendiente }) => !completada && !integracion_pendiente);
  return <Box component="ol" aria-label="Pasos del circuito mensual" sx={{ display: "flex", listStyle: "none", m: 0, p: 0, pt: 3, minWidth: 900 }}>
    {etapas.map((etapa, i) => {
      const estado = etapa.completada ? "completo" : i === activa ? "activo" : "pendiente";
      const ultimo = i === etapas.length - 1;
      return <Box component="li" key={etapa.numero} sx={{ flex: 1, minWidth: 0 }} aria-current={estado === "activo" ? "step" : undefined}>
        <Stack direction="row" sx={{ alignItems: "center", height: 32 }}>
          <Box aria-hidden="true" sx={{ width: 32, height: 32, borderRadius: "50%", display: "grid", placeItems: "center", flexShrink: 0, typography: "captionBold",
            bgcolor: estado === "completo" ? "success.main" : estado === "activo" ? "warning.main" : "action.disabledBackground",
            color: estado === "completo" ? "success.contrastText" : estado === "activo" ? "warning.contrastText" : "action.disabled" }}>
            {estado === "completo" ? <Check sx={{ fontSize: 20 }} /> : etapa.numero}
          </Box>
          {!ultimo && <Box aria-hidden="true" sx={{ flex: 1, height: 2, mx: 1, borderRadius: 9999, bgcolor: estado === "completo" ? "success.main" : "action.disabledBackground" }} />}
        </Stack>
        <Box sx={{ pt: 1, pr: 1 }}>
          <Typography variant="captionBold" component="p" color={estado === "pendiente" ? "text.secondary" : "text.primary"}>{etapa.nombre}</Typography>
          <Typography variant="caption" component="p" sx={{ pt: 0.5, color: estado === "activo" ? "warning.text" : estado === "pendiente" ? "text.disabled" : "text.secondary" }}>
            {etapa.completada ? (etapa.fecha_texto || "Completo") : estado === "activo" ? "En curso" : "Pendiente"}
          </Typography>
        </Box>
      </Box>;
    })}
  </Box>;
}

/**
 * Fuentes de cruce de Figma. Supervivencia (RENAPER y SINTyS), Ingresos y
 * Patrimonio (retorno SINTyS) están integradas; el resto se muestra como
 * "Sin integrar", sin inventar alertas.
 */
const fuentesCruce = [
  { label: "Supervivencia (RENAPER)", categoria: "Supervivencia" },
  { label: "Ingresos (ARCA/Empleo)", categoria: "Ingresos" }, { label: "Patrimonio (DNRPA/CNBP)", categoria: "Patrimonio" },
  { label: "Situación Penal (M. Justicia)" }, { label: "Cuentas BNA sin movimiento" }, { label: "Migraciones — Traslados ext." },
];

/** Encabezado de los paneles de Figma: 16/24 de padding y línea inferior. */
function EncabezadoPanel({ titulo, subtitulo, acciones }: { titulo: string; subtitulo?: string; acciones?: ReactNode }) {
  return <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, px: 3, py: 2, borderBottom: 1, borderColor: "divider" }}>
    <div>
      <Typography component="h2" variant="subtitle1Medium">{titulo}</Typography>
      {subtitulo && <Typography variant="caption" color="text.secondary" component="p" sx={{ pt: 0.5 }}>{subtitulo}</Typography>}
    </div>
    {acciones}
  </Stack>;
}

type Alerta = Cruces["incompatibilidades"][number];

/** Botón "Gestionar" de la bandeja: Confirmar el cambio propuesto o Modificarlo. */
function GestionarAlerta({ item, onConfirmar, onModificar, disabled }: {
  item: Alerta; onConfirmar: () => void; onModificar: () => void; disabled: boolean;
}) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const id = useId();
  return <>
    <Button size="small" id={id} aria-haspopup="menu" aria-expanded={Boolean(anchor)} disabled={disabled}
      aria-label={`Gestionar a ${item.titular}`} onClick={(event) => setAnchor(event.currentTarget)}>Gestionar</Button>
    <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)} slotProps={{ list: { "aria-labelledby": id } }}>
      <MenuItem onClick={() => { setAnchor(null); onConfirmar(); }}>Confirmar</MenuItem>
      <MenuItem onClick={() => { setAnchor(null); onModificar(); }}>Modificar</MenuItem>
    </Menu>
  </>;
}

export function CrucesPage() {
  const query = useDatos<Cruces>("cruces/");
  const cache = useQueryClient();
  const [modificando, setModificando] = useState<Alerta | null>(null);
  const accion = useMutation({
    mutationFn: async (archivo: File | null | "renaper") => {
      if (archivo === "renaper") {
        const data = await pasPost<{ message: string }>("cruces/actualizar-renaper/");
        return data.message;
      }
      if (archivo) return (await importarSintys(archivo)).message;
      await exportarSintys();
      return "Padrón exportado.";
    },
    onSettled: () => query.refetch(),
  });
  const confirmar = useMutation({
    mutationFn: (alerta: Alerta) => pasPost<{ message: string }>(`cruces/incompatibilidades/${alerta.id}/confirmar/`),
    onSettled: () => cache.invalidateQueries({ queryKey: ["pas"] }),
  });
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  const { circuito, etapas, renaper, incompatibilidades, importacion_sintys: importacion, cambio_estado: opcionesEstado } = query.data;
  const gestionable = (item: Alerta) => query.data.can_change && item.id != null;
  const pendientes = incompatibilidades.filter(({ estado }) => tonoAlerta(estado) === "warning").length;
  const completas = etapas.filter(({ completada }) => completada).length;
  const alertasDe = (categoria?: string) => categoria ? incompatibilidades.filter((item) => item.categoria === categoria && tonoAlerta(item.estado) === "warning").length : null;
  return <Stack>
    <Oculto component="h1">Cruces y novedades</Oculto>
    {/* Sisoc/Monthly circuit stepper: Card con título, botones y stepper (padding 24). */}
    <Card sx={{ p: 3 }}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { md: "center" } }}>
        <div>
          <Typography component="h2" variant="subtitle1Medium">Circuito Administrativo Mensual</Typography>
          <Typography variant="caption" color="text.secondary" component="p">
            Período {circuito.periodo_texto} · {completas} de {etapas.length} pasos completos · RENAPER: {renaper.total} consultas, {renaper.errores} errores
          </Typography>
        </div>
        {query.data.can_change && <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap", alignItems: "center" }}>
          <Button variant="contained" size="small" startIcon={<ArrowUpward />} disabled={accion.isPending} onClick={() => accion.mutate(null)}>Exportar a SINTyS (VIAS)</Button>
          <Button component="label" variant="outlined" size="small" startIcon={<ArrowDownward />} disabled={accion.isPending}>
            Importar retorno Sintys
            <input type="file" hidden accept=".txt,.csv,.xlsx" onChange={(event) => {
              const archivo = event.currentTarget.files?.[0];
              event.currentTarget.value = "";
              if (archivo && !accion.isPending) accion.mutate(archivo);
            }} />
          </Button>
          <AccionesPas label="Otras acciones de Cruces" items={[{ label: "Actualizar RENAPER", disabled: accion.isPending, run: () => {
            if (window.confirm("¿Solicitar la actualización de RENAPER para el período?")) accion.mutate("renaper");
          } }]} />
        </Stack>}
      </Stack>
      {accion.isSuccess && <Alert severity="success" sx={{ mt: 2 }}>{accion.data}</Alert>}
      {accion.isError && (accion.variables instanceof File ? <Box sx={{ mt: 2 }}><ErrorOperacion error={accion.error} /></Box>
        : <Alert severity="error" sx={{ mt: 2 }}>No se pudo confirmar la operación. Revisá el circuito antes de reintentar.</Alert>)}
      {importacion && importacion.errores.length > 0 && <Alert severity="warning" sx={{ mt: 2 }}>
        Último retorno SINTyS: {importacion.errores.length} {importacion.errores.length === 1 ? "fila con observaciones" : "filas con observaciones"}.
        <Box component="ul" sx={{ m: 0, pl: 2.5 }}>{importacion.errores.slice(0, 10).map((error) => <li key={error}>{error}</li>)}</Box>
      </Alert>}
      <Box sx={{ overflowX: "auto", position: "relative" }}><CircuitoStepper etapas={etapas} /></Box>
    </Card>
    {/* Sisoc/Data check row: una por fuente de cruce, State chip sin punto. */}
    <Box aria-label="Resultado de los cruces" role="list" sx={{ pt: 2.5, display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))", lg: "repeat(3, minmax(0, 1fr))" } }}>
      {fuentesCruce.map(({ label, categoria }) => {
        const alertas = alertasDe(categoria);
        return <div role="listitem" key={label}>
          <DataCheckRow label={label} valor={alertas == null ? "Sin integrar" : alertas ? `${alertas} ${alertas === 1 ? "alerta" : "alertas"}` : "Sin alertas"}
            tono={alertas == null ? "neutral" : alertas ? "warning" : "success"} />
        </div>;
      })}
    </Box>
    {/* Sisoc/Incompatibility alerts: Card + Table. */}
    <Card sx={{ mt: 2.5 }}>
      <EncabezadoPanel titulo="Bandeja de Alertas de Incompatibilidad"
        acciones={<StateChip label={`${pendientes} ${pendientes === 1 ? "pendiente" : "pendientes"}`} tono={pendientes ? "error" : "success"} />} />
      {confirmar.isSuccess && <Alert severity="success" sx={{ mx: 3, my: 1.5 }}>{confirmar.data.message}</Alert>}
      {confirmar.isError && <Box sx={{ mx: 3, my: 1.5 }}><ErrorOperacion error={confirmar.error} /></Box>}
      {incompatibilidades.length ? <TableContainer sx={{ position: "relative" }}>
        <Table sx={{ minWidth: 1000 }} aria-label="Alertas de incompatibilidad">
          <TableHead><TableRow>{([["Titular", 180], ["DNI", 150], ["Categoría", 140], ["Detalle", undefined], ["Detección", 110], ["Estado", 150], ["", 90]] as [string, number | undefined][]).map(([label, width], i) =>
            <TableCell key={i} sx={{ width, py: 0.5, ...(i === 0 && { pl: 3 }), ...(i === 6 && { pr: 3 }) }}>{label || <Oculto>Gestión</Oculto>}</TableCell>)}</TableRow></TableHead>
          <TableBody>{incompatibilidades.map((item, index) => <TableRow key={index}>
            <TableCell sx={{ pl: 3, typography: "subtitle2" }}>{item.titular}</TableCell>
            <TableCell sx={{ typography: "caption", color: "text.secondary" }}>{item.dni}</TableCell>
            <TableCell><StateChip label={item.categoria} /></TableCell>
            <TableCell sx={{ typography: "caption", color: "text.secondary" }}>
              {item.detalle || "—"}
              {item.cambio_propuesto && <Box component="span" sx={{ display: "block", color: "text.primary" }}>
                {item.estado_actual ? `${item.estado_actual} → ` : "Propone: "}{item.cambio_propuesto}</Box>}
            </TableCell>
            <TableCell sx={{ typography: "caption", color: "text.secondary" }}>{item.fecha_deteccion || "—"}</TableCell>
            <TableCell><StateChip label={item.estado || "—"} tono={tonoAlerta(item.estado)} /></TableCell>
            <TableCell align="right" sx={{ pr: 3 }}>{gestionable(item)
              ? <GestionarAlerta item={item} disabled={confirmar.isPending}
                onConfirmar={() => {
                  const cambio = item.cambio_propuesto ? ` y pasar a ${item.cambio_propuesto}` : "";
                  if (window.confirm(`¿Confirmar la alerta de ${item.titular}${cambio}?`)) confirmar.mutate(item);
                }}
                onModificar={() => { confirmar.reset(); setModificando(item); }} />
              : <MuiLink component={Link} to={`/titulares?${new URLSearchParams({ q: String(item.dni) })}`}
                aria-label={`Gestionar a ${item.titular}`}>Gestionar</MuiLink>}</TableCell>
          </TableRow>)}</TableBody>
        </Table>
      </TableContainer> : <Box sx={{ px: 3 }}><SinDatos>Sin alertas registradas para el período.</SinDatos></Box>}
    </Card>
    {modificando && opcionesEstado && <CambiarEstado key={modificando.id} id={String(modificando.persona_id)} opciones={opcionesEstado}
      open endpoint={`cruces/incompatibilidades/${modificando.id}/modificar/`} titulo={`Modificar estado de ${modificando.titular}`}
      confirmacion={`¿Confirmar el cambio de estado de ${modificando.titular}? La alerta quedará confirmada.`}
      onClose={() => setModificando(null)} />}
  </Stack>;
}

/** Columnas de `Sisoc/Preliquidation row`: Titular FILL ≥160, el resto con ancho fijo. Mínimo 798px. */
const columnasPreliquidacion: { label: string; width?: number; align?: "right" }[] = [
  { label: "Titular" }, { label: "CUIL", width: 130 }, { label: "CBU BNA", width: 110 }, { label: "Monto", width: 110, align: "right" },
  { label: "FCH", width: 90 }, { label: "Cruces", width: 90 }, { label: "DDJJ", width: 90 }, { label: "Estado final", width: 260 },
];

const severidadPunto: Record<PuntoControl["estado"], "success" | "warning" | "info"> = { ok: "success", pendiente: "warning", sin_integrar: "info" };
const textoPunto: Record<PuntoControl["estado"], string> = { ok: "OK", pendiente: "Pendiente", sin_integrar: "Sin integrar" };
const tonoFch: Record<string, "success" | "warning" | "error"> = { verde: "success", amarillo: "warning", rojo: "error" };

function pesos(monto: string) {
  return Number(monto).toLocaleString("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 });
}

function Validacion({ ok }: { ok: boolean }) {
  return <StateChip label={ok ? "OK" : "No"} tono={ok ? "success" : "error"} />;
}

export function LiquidacionPage() {
  const query = useDatos<Area>("areas/liquidacion/");
  const descarga = useMutation({ mutationFn: descargarNomina, onSettled: () => query.refetch() });
  const csv = useMutation({ mutationFn: exportarPreliquidacionCsv });
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  const liquidacion = query.data.liquidacion;
  if (!liquidacion) return <ErrorPas error={new Error("Sin datos de liquidación")} />;
  const periodo = mesAnio(new Date(`${liquidacion.periodo}T00:00:00`));
  const motivos = (descarga.error as { response?: { data?: { motivos?: string[] } } } | null)?.response?.data?.motivos;
  const puedeDescargar = Boolean(query.data.can_download) && liquidacion.descarga_habilitada && !descarga.isPending;
  return <Stack spacing={2.5} sx={{ pt: 2 }}>
    <Oculto component="h1">Liquidación</Oculto>
    <Metricas>
      <StatCard label="Titulares a acreditar" value={liquidacion.titulares_a_acreditar.toLocaleString("es-AR")} hint="Activos con DDJJ y sin alertas pendientes" tone="success" />
      <StatCard label="Titulares bloqueados" value={liquidacion.titulares_bloqueados.toLocaleString("es-AR")} hint="Suspendidos / DDJJ / Cruces / FCH" tone="error" />
      <StatCard label="Total a liquidar" value={pesos(liquidacion.total_a_liquidar)} hint={`${pesos(liquidacion.monto_mensual)} por titular`} />
    </Metricas>
    <Box sx={{ display: "grid", gap: 2.5, alignItems: "start", gridTemplateColumns: { xs: "1fr", lg: "320px minmax(0, 1fr)" } }}>
      {/* Sisoc/Liquidation panel (Figma: 320px, padding 24, gap 24). */}
      <Card sx={{ p: 3 }}>
        <Stack spacing={3}>
          <div>
            <Typography component="h2" variant="h6">Motor de Liquidación</Typography>
            <Typography variant="overline" component="p" color="text.secondary">Puntos de Control — {periodo}</Typography>
          </div>
          <Stack component="ol" spacing={1.5} aria-label="Puntos de control" sx={{ listStyle: "none", m: 0, p: 0 }}>
            {liquidacion.puntos_control.map((punto) => <li key={punto.clave}>
              <Alert severity={severidadPunto[punto.estado]} variant="outlined">
                <Typography variant="subtitle1Medium" component="p">{punto.titulo} · {textoPunto[punto.estado]}</Typography>
                <Typography variant="body2">{punto.detalle}</Typography>
              </Alert>
            </li>)}
          </Stack>
          {liquidacion.nomina_generada
            ? <Alert severity="success" variant="outlined">Nómina generada el {liquidacion.fecha_cierre}. Se descarga el mismo padrón final.</Alert>
            : !liquidacion.descarga_habilitada && <Alert severity="warning" variant="outlined">La descarga está bloqueada hasta que todos los puntos de control sean OK.</Alert>}
          {descarga.isError && <Alert severity="error">
            {motivos?.length ? <>La nómina está bloqueada:<Box component="ul" sx={{ m: 0, pl: 2.5 }}>{motivos.map((motivo) => <li key={motivo}>{motivo}</li>)}</Box></>
              : "No se pudo descargar la nómina."}
          </Alert>}
          <Tooltip title={query.data.can_download ? "" : "Requiere el permiso para descargar la nómina de pago"}><span>
            <Button variant="contained" size="large" fullWidth startIcon={<Download />} disabled={!puedeDescargar}
              sx={{ whiteSpace: "nowrap", px: 1 }} onClick={() => {
                if (liquidacion.nomina_generada || window.confirm(`¿Generar la nómina de pago de ${periodo}? Se cierra el circuito mensual.`)) descarga.mutate();
              }}>Descargar nómina de pago</Button>
          </span></Tooltip>
        </Stack>
      </Card>
      <Card sx={{ minWidth: 0 }}>
        <EncabezadoPanel titulo="Listado pre-liquidación analítico"
          subtitulo={liquidacion.total_filas > liquidacion.filas.length
            ? `Validación por titular · primeros ${liquidacion.filas.length} de ${liquidacion.total_filas.toLocaleString("es-AR")}`
            : "Validación de cruces y condiciones previas al cierre"}
          acciones={<Tooltip title={!query.data.can_export_csv ? "Requiere el permiso de exportación a CSV"
            : !liquidacion.total_filas ? "Sin titulares para exportar" : ""}><span>
            <Button variant="outlined" size="small" startIcon={<ArrowUpward />}
              disabled={!query.data.can_export_csv || !liquidacion.total_filas || csv.isPending}
              onClick={() => csv.mutate()}>{csv.isPending ? "Exportando…" : "Exportar CSV"}</Button>
          </span></Tooltip>} />
        {csv.isError && <Alert severity="error" onClose={() => csv.reset()} sx={{ mx: 3, my: 1.5 }}>No se pudo exportar el CSV. Reintentá en unos minutos.</Alert>}
        {/* Titular se ajusta al nombre más largo; el resto tiene un mínimo para no cortar. */}
        <TableContainer><Table sx={{ tableLayout: "auto" }} aria-label="Listado de preliquidación">
          <TableHead><TableRow>{columnasPreliquidacion.map(({ label, width, align }, i) =>
            <TableCell key={label} align={align} sx={{ minWidth: width, whiteSpace: "nowrap", py: 0.5, ...(i === 0 && { pl: 2, width: "1%" }) }}>{label}</TableCell>)}</TableRow></TableHead>
          <TableBody>
            {!liquidacion.filas.length && <TableRow><TableCell colSpan={columnasPreliquidacion.length} sx={{ pl: 2, color: "text.secondary" }}>Sin titulares para liquidar.</TableCell></TableRow>}
            {liquidacion.filas.map((fila) => <TableRow key={fila.id}>
              <TableCell sx={{ pl: 2, typography: "subtitle2", whiteSpace: "nowrap" }}>
                <MuiLink component={Link} to={`/titulares/${fila.id}`}>{fila.titular}</MuiLink></TableCell>
              <TableCell sx={{ typography: "caption", whiteSpace: "nowrap" }}>{fila.cuil || "—"}</TableCell>
              <TableCell sx={{ typography: "caption", color: "text.secondary" }}>{fila.cbu || "—"}</TableCell>
              <TableCell align="right" sx={{ typography: "caption", whiteSpace: "nowrap" }}>{pesos(fila.monto)}</TableCell>
              <TableCell>{fila.fch ? <StateChip label={fila.fch} tono={tonoFch[fila.fch] ?? "neutral"} /> : <Typography variant="caption" color="text.secondary">N/I</Typography>}</TableCell>
              <TableCell><Validacion ok={fila.cruces_ok} /></TableCell>
              <TableCell><Validacion ok={fila.ddjj_ok} /></TableCell>
              <TableCell sx={{ typography: "caption", color: fila.habilitado ? "success.text" : "error.text" }}>{fila.estado_final}</TableCell>
            </TableRow>)}
          </TableBody>
        </Table></TableContainer>
      </Card>
    </Box>
  </Stack>;
}

export function InformesPage() {
  const [params, setParams] = useSearchParams();
  const query = useDatos<{ results: Informe[]; previous: number | null; next: number | null; can_generate: boolean }>(`informes/?${params}`);
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  const ir = (page: number | null) => {
    if (page == null) return;
    const next = new URLSearchParams(params);
    next.set("page", String(page));
    setParams(next);
  };
  return <Stack spacing={3}>
    <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
      <div><Typography component="h1" variant="h5">Informes PAS</Typography>
        <Typography variant="body2" color="text.secondary">Exportaciones del padrón con sus filtros y cambios de estado</Typography></div>
      {query.data.can_generate && <Button component={Link} to="/informes/generar" variant="contained" size="large" startIcon={<ArrowUpward />}>Generar informe</Button>}
    </Stack>
    <Card>
      <CardContent sx={{ pb: 2 }}>
        <Stack component="form" role="search" direction={{ xs: "column", sm: "row" }} spacing={2} key={params.toString()} onSubmit={(event) => {
          event.preventDefault();
          setParams({ q: String(new FormData(event.currentTarget).get("q") ?? "") });
        }}>
          <TextField name="q" label="Buscar informes" defaultValue={params.get("q") ?? ""} sx={{ flex: 1 }} />
          <Button type="submit" variant="outlined" sx={{ alignSelf: { sm: "center" } }}>Buscar</Button>
        </Stack>
      </CardContent>
      <TableContainer><Table sx={{ minWidth: 560 }} aria-label="Informes PAS">
        <TableHead><TableRow><TableCell sx={{ pl: 3 }}>Informe</TableCell><TableCell>Fecha</TableCell><TableCell align="right">Personas</TableCell><TableCell>Descarga</TableCell></TableRow></TableHead>
        <TableBody>
          {!query.data.results.length && <TableRow><TableCell colSpan={4} sx={{ pl: 3, color: "text.secondary" }}>Sin informes registrados.</TableCell></TableRow>}
          {query.data.results.map((item) => <TableRow key={item.id}>
            <TableCell sx={{ pl: 3 }}><MuiLink component={Link} to={`/informes/${item.id}`}>{item.numero}</MuiLink></TableCell>
            <TableCell>{item.creado}</TableCell>
            <TableCell align="right">{item.total_personas}</TableCell>
            <TableCell>{item.download_url ? <MuiLink href={item.download_url}>Descargar CSV</MuiLink> : "—"}</TableCell>
          </TableRow>)}
        </TableBody>
      </Table></TableContainer>
      <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end", p: 1 }}>
        <Tooltip title="Página anterior"><span><IconButton aria-label="Página anterior" disabled={query.data.previous == null} onClick={() => ir(query.data.previous)}><ChevronLeft /></IconButton></span></Tooltip>
        <Tooltip title="Página siguiente"><span><IconButton aria-label="Página siguiente" disabled={query.data.next == null} onClick={() => ir(query.data.next)}><ChevronRight /></IconButton></span></Tooltip>
      </Stack>
    </Card>
  </Stack>;
}

/**
 * Dashboard — Reporte PAS, con la estructura de Figma. Usa lo que el backend ya
 * informa (padrón, circuito e incompatibilidades de Cruces); lo que todavía no
 * tiene fuente queda con guión largo.
 */
export function DashboardPage() {
  const query = useDatos<Area>("areas/liquidacion/");
  const cruces = useQuery({ queryKey: ["pas", "cruces/"], queryFn: () => pasGet<Cruces>("cruces/"), retry: false });
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  const etapas = cruces.data?.etapas ?? [];
  const completas = etapas.filter(({ completada }) => completada).length;
  const abiertas = cruces.data ? (cruces.data.incompatibilidades ?? []).filter(({ estado }) => tonoAlerta(estado) === "warning").length : null;
  const periodoIso = cruces.data?.circuito?.periodo;
  const periodo = mesAnio(periodoIso ? new Date(`${periodoIso}T00:00:00`) : new Date());
  const sinDato = "Sin datos del período";
  const liquidacionMes = query.data.liquidacion;
  const panel = { p: 3, borderRadius: (theme: { radius: { large: number } }) => `${theme.radius.large}px` };
  return <Stack spacing={3}>
    <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { lg: "center" }, pt: 1 }}>
      <div><Typography component="h1" variant="h5">Reporte PAS</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ pt: 0.5 }}>Lectura ejecutiva del Programa de Acompañamiento Social</Typography></div>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "center" } }}>
        <TextField select label="Provincia" value="todas" disabled sx={{ width: { xs: "100%", sm: 220 } }}>
          <MenuItem value="todas">Todas las provincias</MenuItem></TextField>
        <TextField select label="Período" value="actual" disabled sx={{ width: { xs: "100%", sm: 220 } }}>
          <MenuItem value="actual">{periodo}</MenuItem></TextField>
        <Button component={Link} to="/informes/generar" variant="contained" size="large" startIcon={<ArrowUpward />} sx={{ whiteSpace: "nowrap", flexShrink: 0 }}>Exportar información filtrada</Button>
      </Stack>
    </Stack>
    <Metricas columnas={4}>
      <StatCard label="Titulares PAS" value={query.data.total_padron.toLocaleString("es-AR")} hint="Padrón total del programa" />
      <StatCard label="DDJJ completada" value="—" hint={sinDato} tone="success" />
      <StatCard label="Formación cumplida" value="—" hint={sinDato} tone="success" />
      <StatCard label="Liquidación del mes" value={liquidacionMes ? liquidacionMes.titulares_a_acreditar.toLocaleString("es-AR") : "—"}
        hint={liquidacionMes ? "Titulares a acreditar" : sinDato} tone="warning" />
    </Metricas>
    <Box sx={{ display: "grid", gap: 3, alignItems: "start", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 520px" } }}>
      <Card sx={panel}>
        <Typography component="h2" variant="h6">Cumplimiento de condicionalidades</Typography>
        <Stack spacing={2} sx={{ pt: 2 }}>
          {["Declaración jurada", "Formación FCH", "Cruces mensuales", "Reclamos resueltos"].map((label) =>
            <BarRow key={label} label={label} porcentaje={label === "Cruces mensuales" && etapas.length ? (completas / etapas.length) * 100 : null}
              texto={label === "Cruces mensuales" && etapas.length ? `${Math.round((completas / etapas.length) * 100)}%` : undefined} />)}
        </Stack>
      </Card>
      <Card sx={panel}>
        <Typography component="h2" variant="h6">Estado operativo del mes</Typography>
        <Box sx={{ pt: 1 }}>
          <StatusRow label="Cruces · circuito mensual" valor={!etapas.length ? null : completas === etapas.length ? "Completo" : completas ? "En proceso" : "Pendiente"} />
          <StatusRow label="Formación FCH · período" valor={null} />
          <StatusRow label="Liquidación · preliquidación" valor={liquidacionMes?.nomina_generada ? "Nómina generada"
            : liquidacionMes?.descarga_habilitada ? "Lista para descargar" : "Bloqueada"} />
        </Box>
      </Card>
      <Card sx={panel}>
        <Typography component="h2" variant="h6">Requieren atención</Typography>
        <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0, pt: 1 }}>
          <PendingRow label="Titulares sin DDJJ vigente" cantidad={null} accion={<Button component={Link} to="/buscador" size="small">Ver casos</Button>} />
          <PendingRow label="Con condicionalidad formativa pendiente" cantidad={null}
            accion={<Button component={Link} to="/formacion?estado_formacion=sin-formacion" size="small">Ver casos</Button>} />
          <PendingRow label="Incompatibilidades abiertas" cantidad={abiertas} accion={<Button component={Link} to="/cruces" size="small">Ver casos</Button>} />
          <PendingRow label="Titulares bloqueados para liquidación" cantidad={liquidacionMes?.titulares_bloqueados ?? null} accion={<Button component={Link} to="/liquidacion" size="small">Ver casos</Button>} />
        </Box>
      </Card>
      <Card sx={panel}>
        <Typography component="h2" variant="h6">Distribución de titulares</Typography>
        <Stack spacing={3} sx={{ pt: 3 }}>
          {["Por provincia", "Por género", "Por edad"].map((grupo) => <Stack key={grupo} spacing={0.5}>
            <Typography component="h3" variant="overline" color="text.primary">{grupo}</Typography>
            <BarRow label="Sin desagregación" porcentaje={null} />
          </Stack>)}
        </Stack>
      </Card>
    </Box>
  </Stack>;
}
