/**
 * Composiciones del Nuevo DS SISOC que usa PAS (ver `modulo-pas.md` y
 * `nucleo-componentes.md` del equipo de UX). Todo sale de `theme.palette`.
 */
import { useState, type ReactNode } from "react";
import { Alert, alpha, Box, Card, Chip, CircularProgress, Link as MuiLink, Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TablePagination, TableRow, Typography } from "@mui/material";
import type { Curso } from "./api";

export type Tono = "success" | "error" | "warning" | "info" | "primary" | "neutral";

/** Criterio de color de `Sisoc/State chip` aplicado a los estados del titular. */
function tonoEstado(nombre: string): Tono {
  const estado = nombre.trim().toLocaleLowerCase("es");
  if (estado === "activo") return "success";
  if (["suspendido", "baja", "bloqueado"].includes(estado)) return "error";
  if (estado === "reactivado") return "primary";
  return "neutral";
}

/** Regla de severidad: 0 error, 1 a 99 warning, 100 o más success. */
function severidad(valor: number): "error" | "warning" | "success" {
  if (valor <= 0) return "error";
  return valor >= 100 ? "success" : "warning";
}

/** `Sisoc/State chip`: display puro. El Neutral es el `default` de Chip en el theme. */
export function StateChip({ label, tono = "neutral", punto = false }: { label: string; tono?: Tono; punto?: boolean }) {
  return <Chip size="small" label={label} color={tono === "neutral" ? "default" : tono}
    icon={punto ? <Box component="span" aria-hidden="true" sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: "currentColor", ml: "8px !important" }} /> : undefined} />;
}

export function EstadoChip({ nombre }: { nombre: string }) {
  return <StateChip label={nombre} tono={tonoEstado(nombre)} punto />;
}

/** `Sisoc/Score chip`: capa `{color}.main` al 8% y texto `{color}.text`, radius 8. */
export function ScoreChip({ label, tono }: { label: string; tono: "error" | "warning" | "success" }) {
  return <Chip size="small" label={label} sx={(theme) => ({ borderRadius: `${theme.radius.medium}px`, fontWeight: 500,
    bgcolor: alpha(theme.palette[tono].main, 0.08), color: theme.palette[tono].text })} />;
}

/** `Sisoc/Data field` agrupado: título en overline, etiqueta caption y valor subtitle2. */
export function DataGroup({ titulo, campos }: { titulo: string; campos: [string, ReactNode][] }) {
  return <Stack component="dl" spacing={1} sx={{ m: 0, minWidth: 0 }}>
    <Typography component="h3" variant="overline" color="text.primary">{titulo}</Typography>
    {campos.map(([label, valor]) => <div key={label}>
      <Typography component="dt" variant="caption" color="text.secondary">{label}</Typography>
      <Typography component="dd" variant="subtitle2" sx={{ m: 0, overflowWrap: "anywhere" }}>{valor === "" || valor == null ? "—" : valor}</Typography>
    </div>)}
  </Stack>;
}

/** Encabezado de un panel: título h6 y subtítulo body2, con acciones a la derecha. */
export function PanelHeader({ titulo, subtitulo, acciones, id }: { titulo: string; subtitulo?: ReactNode; acciones?: ReactNode; id?: string }) {
  return <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
    <div>
      <Typography component="h2" variant="h6" id={id}>{titulo}</Typography>
      {subtitulo && <Typography variant="body2" color="text.secondary">{subtitulo}</Typography>}
    </div>
    {acciones && <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap", alignItems: "center" }}>{acciones}</Stack>}
  </Stack>;
}

/**
 * `Sisoc/Alert message` (Figma: 898x120, radius 8): capa `{color}.main` al 8%,
 * textos en `{color}.text` y un anillo de 64px (grosor 8) con los puntos
 * adentro. El color sale del puntaje con la regla de severidad.
 */
export function AlertMessage({ porcentaje, puntos, volanta = "Semáforo de Validación de Pago", titulo, detalle }:
  { porcentaje: number; puntos: number; volanta?: string; titulo: string; detalle: string }) {
  const tono = severidad(porcentaje);
  const valor = Math.max(0, Math.min(100, Math.round(porcentaje)));
  // CircularProgress dibuja sobre un viewBox de 44: 5.5 equivale a 8px en 64px.
  const grosor = 5.5;
  return <Alert severity={tono} icon={<Box sx={{ position: "relative", display: "inline-flex", width: 64, height: 64 }}>
    <CircularProgress variant="determinate" value={100} size={64} thickness={grosor} sx={{ color: "action.disabledBackground", position: "absolute" }} aria-hidden="true" />
    <CircularProgress variant="determinate" value={valor} size={64} thickness={grosor} color={tono} aria-label={`${valor}% del objetivo`} />
    <Typography variant="caption" sx={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", color: `${tono}.text` }}>{puntos} Pts</Typography>
  </Box>} sx={(theme) => ({ minHeight: 120, alignItems: "center", px: 2, py: 0.75, borderRadius: `${theme.radius.medium}px`,
    bgcolor: alpha(theme.palette[tono].main, 0.08), color: theme.palette[tono].text,
    "& .MuiAlert-icon": { mr: 0, pl: 0, pr: 1.5, py: 1, opacity: 1 }, "& .MuiAlert-message": { py: 1, display: "flex", flexDirection: "column", gap: 0.5 } })}>
    <Typography variant="overline" component="p" sx={{ lineHeight: "32px" }}>{volanta}</Typography>
    <Typography variant="h6" component="p" sx={{ textTransform: "uppercase" }}>{titulo}</Typography>
    <Typography variant="body2">{detalle}</Typography>
  </Alert>;
}

/**
 * `Sisoc/Stat card` (Figma: radius 16, borde izquierdo de 4px en
 * `{color}.main`, padding 16): rótulo overline, valor h4Bold en `{color}.text`
 * y referencia body2. El color refuerza el significado del dato, no se calcula.
 */
export function StatCard({ label, value, hint, tone = "primary" }: { label: string; value: ReactNode; hint?: string; tone?: "primary" | "success" | "warning" | "error" | "info" }) {
  return <Paper sx={(theme) => ({ p: 2, minHeight: 134, borderRadius: `${theme.radius.large}px`, bgcolor: "background.paper",
    borderLeft: `${theme.border.accent}px solid ${theme.palette[tone].main}` })} elevation={0}>
    <Typography variant="overline" component="p" color="text.secondary">{label}</Typography>
    <Typography variant="h4Bold" component="p" sx={{ pt: 0.5, color: `${tone}.text` }}>{value}</Typography>
    {hint && <Typography variant="body2" color="text.secondary" sx={{ pt: 0.5 }}>{hint}</Typography>}
  </Paper>;
}

/** `Sisoc/Data check row`: Paper outlined con label y State chip sin punto. */
export function DataCheckRow({ label, valor, tono }: { label: string; valor: string; tono: Tono }) {
  return <Paper variant="outlined" sx={{ px: 2, py: 1.5, borderRadius: (theme) => `${theme.radius.medium}px` }}>
    <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center", minHeight: 30 }}>
      <Typography variant="body2">{label}</Typography>
      <StateChip label={valor} tono={tono} />
    </Stack>
  </Paper>;
}

/** `Sisoc/Status row` (Figma): label body2 en `text.secondary` y valor body1, separados por `divider`. */
export function StatusRow({ label, valor }: { label: string; valor: ReactNode }) {
  return <Stack direction="row" spacing={2} sx={{ justifyContent: "space-between", alignItems: "center", py: 1.5, borderBottom: 1, borderColor: "divider" }}>
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Typography variant="body1" component="span" sx={{ textAlign: "right" }}>{valor ?? "—"}</Typography>
  </Stack>;
}

/**
 * `Sisoc/Pending row` (Figma: 48px, padding 12/24, gap 16): punto en
 * `warning.main`, contador en State chip Neutral y acción. Sin dato, guión largo.
 */
export function PendingRow({ label, cantidad, accion }: { label: string; cantidad: number | null; accion: ReactNode }) {
  return <Stack component="li" direction="row" spacing={2} sx={{ alignItems: "center", minHeight: 48, px: 3, py: 1.5, borderBottom: 1, borderColor: "divider" }}>
    <Box aria-hidden="true" sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: "warning.main", flexShrink: 0 }} />
    <Typography variant="body2" sx={{ flex: 1, minWidth: 0 }}>{label}</Typography>
    <StateChip label={cantidad == null ? "—" : cantidad.toLocaleString("es-AR")} />
    {accion}
  </Stack>;
}

/**
 * `Sisoc/Bar row` (Figma: 32px): etiqueta body2 de 140px, riel en
 * `action.disabledBackground`, barra en `chart.series5` de 8px y valor subtitle2
 * de 112px a la derecha. Sin dato, la barra queda vacía y el valor en guión largo.
 */
export function BarRow({ label, porcentaje, texto }: { label: string; porcentaje: number | null; texto?: string }) {
  const ancho = porcentaje == null ? 0 : Math.max(0, Math.min(100, porcentaje));
  return <Stack direction="row" spacing={2} sx={{ alignItems: "center", minHeight: 32, py: 0.5 }}>
    <Typography variant="body2" sx={{ width: 140, flexShrink: 0 }}>{label}</Typography>
    <Box aria-hidden="true" sx={{ flex: 1, height: 8, borderRadius: 9999, bgcolor: "action.disabledBackground", overflow: "hidden" }}>
      <Box sx={{ width: `${ancho}%`, height: "100%", borderRadius: 9999, bgcolor: "chart.series5" }} />
    </Box>
    <Typography variant="subtitle2" sx={{ width: 112, flexShrink: 0, textAlign: "right" }}>{texto ?? "—"}</Typography>
  </Stack>;
}

/**
 * Texto solo para lectores de pantalla. Lleva 1px de ancho y recorte: sin eso,
 * el `position: absolute` escapa del scroll de una tabla y estira la página.
 */
export function Oculto({ children, component = "span" }: { children: ReactNode; component?: "span" | "h1" }) {
  return <Box component={component} sx={{ position: "absolute", width: "1px", height: "1px", p: 0, m: "-1px", overflow: "hidden",
    clip: "rect(0 0 0 0)", whiteSpace: "nowrap", border: 0 }}>{children}</Box>;
}

/** Panel sin datos: el guión largo de la regla general, con el motivo. */
export function SinDatos({ children }: { children: ReactNode }) {
  return <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>{children}</Typography>;
}

/** Un curso FCH solo está Inscripto (info) o Aprobado (success), como en Figma. */
function estadoCurso(curso: Curso): { label: string; tono: Tono } {
  const aprobado = curso.estado.trim().toLocaleLowerCase("es") === "aprobado";
  return aprobado ? { label: "Aprobado", tono: "success" } : { label: "Inscripto", tono: "info" };
}

/**
 * Tabla de cursos de FCH (Figma: Card radius 16, encabezado con línea
 * inferior, Curso en 14 medio y el resto en 12). Un curso en marcha muestra
 * Fin y Puntos en guión largo. Se pagina de a 10.
 */
export function TablaCursos({ rows, titulo = "Cursos registrados — Portal FCH", emptyMessage = "No hay cursos registrados.", constancia = false, paginacion = "siempre" }:
  { rows: Curso[]; titulo?: string; emptyMessage?: string; constancia?: boolean; paginacion?: "siempre" | "auto" }) {
  const [page, setPage] = useState(0);
  const [porPagina, setPorPagina] = useState(10);
  // Anchos de Figma sobre 896px: Curso 282 · Inscripción 137 · Fin 122 · Puntos 106 · Estado 134 · Constancia 83.
  const columnas: [string, string][] = [["Inscripción", "15%"], ["Fin", "14%"], ["Puntos", "12%"], ["Estado", "15%"], ...(constancia ? [["Constancia", "11%"] as [string, string]] : [])];
  const celda = { typography: "caption", py: 1.5 };
  return <Card sx={{ minWidth: 0 }}>
    <Box sx={{ px: 3, py: 2, borderBottom: 1, borderColor: "divider" }}>
      <Typography component="h2" variant="subtitle1Medium">{titulo}</Typography>
    </Box>
    <TableContainer>
      <Table sx={{ minWidth: constancia ? 680 : 600 }} aria-label={titulo}>
        <TableHead><TableRow>
          <TableCell sx={{ pl: 3 }}>Curso</TableCell>
          {columnas.map(([label, width]) => <TableCell key={label} sx={{ width }}>{label}</TableCell>)}
        </TableRow></TableHead>
        <TableBody>
          {!rows.length && <TableRow><TableCell colSpan={columnas.length + 1} sx={{ pl: 3, color: "text.secondary" }}>{emptyMessage}</TableCell></TableRow>}
          {rows.slice(page * porPagina, page * porPagina + porPagina).map((curso, index) => <TableRow key={`${curso.curso}-${index}`}>
            <TableCell sx={{ pl: 3, typography: "subtitle2" }}>{curso.curso || "—"}</TableCell>
            <TableCell sx={celda}>{curso.inicio || "—"}</TableCell>
            <TableCell sx={celda}>{curso.fin || "—"}</TableCell>
            <TableCell sx={celda}>{curso.fin && curso.puntos ? `${curso.puntos} pts` : "—"}</TableCell>
            <TableCell sx={celda}><StateChip {...estadoCurso(curso)} /></TableCell>
            {constancia && <TableCell sx={celda}>{curso.certificado_url ? <MuiLink href={curso.certificado_url}>Descargar</MuiLink> : "—"}</TableCell>}
          </TableRow>)}
        </TableBody>
      </Table>
    </TableContainer>
    {(paginacion === "siempre" || rows.length > 10) && <TablePagination component="div" count={rows.length} page={page} rowsPerPage={porPagina} rowsPerPageOptions={[10, 25, 50]}
      onPageChange={(_, next) => setPage(next)} onRowsPerPageChange={(event) => { setPorPagina(Number(event.target.value)); setPage(0); }}
      labelRowsPerPage="Filas por página:" labelDisplayedRows={({ from, to, count }) => `${from}–${to} de ${count}`}
      slotProps={{ actions: { previousButton: { "aria-label": "Página anterior" }, nextButton: { "aria-label": "Página siguiente" } } }} />}
  </Card>;
}
