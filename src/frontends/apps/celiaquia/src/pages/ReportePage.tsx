import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import {
  formatearFecha,
  PageHeader,
  SectionCard,
  Stack,
  StatCard,
  StateChip,
  type StateTone,
} from "@sisoc/ui";
import { api } from "../api";
import { Cargando, ErrorPanel } from "../componentes/Estados";

/** Opciones de los filtros por estado, iguales a las de la pantalla Django. */
const REVISION = ["PENDIENTE", "APROBADO", "RECHAZADO", "SUBSANAR", "SUBSANADO"];
const SINTYS = ["SIN_CRUCE", "MATCH", "NO_MATCH"];
const CUPO = ["NO_EVAL", "DENTRO", "FUERA"];

type Filtros = {
  provincia: string;
  fecha_desde: string;
  fecha_hasta: string;
  expediente_numero: string;
  documento_persona: string;
  revision_tecnico: string;
  resultado_sintys: string;
  estado_cupo: string;
};

const VACIOS: Filtros = {
  provincia: "",
  fecha_desde: "",
  fecha_hasta: "",
  expediente_numero: "",
  documento_persona: "",
  revision_tecnico: "",
  resultado_sintys: "",
  estado_cupo: "",
};

const tonoRevision = (valor: string) =>
  valor === "APROBADO"
    ? "success"
    : valor === "RECHAZADO"
      ? "error"
      : valor === "SUBSANAR"
        ? "warning"
        : "neutral";

function tonoRol(tone?: string): StateTone {
  if (tone === "success" || tone === "primary" || tone === "warning") return tone;
  return tone === "accent" ? "info" : "neutral";
}

function FilaResumen({ label, count, percentage, subtitle, onSelect, selected }: {
  label: string;
  count: string;
  percentage: string;
  subtitle?: string;
  onSelect?: () => void;
  selected?: boolean;
}) {
  const contenido = <>
    <Stack component="span" sx={{ textAlign: "left" }}>
      <Typography component="span" variant="body2">{label}</Typography>
      {subtitle ? <Typography component="span" variant="caption">{subtitle}</Typography> : null}
    </Stack>
    <Typography component="span" variant="subtitle1Medium">
      {count} <Typography component="span" variant="caption">({percentage}%)</Typography>
    </Typography>
  </>;

  if (!onSelect) return <Stack direction="row" justifyContent="space-between">{contenido}</Stack>;
  return (
    <Button
      type="button"
      variant={selected ? "contained" : "outlined"}
      onClick={onSelect}
      aria-label={label}
      aria-pressed={selected}
      sx={{ justifyContent: "space-between", textTransform: "none" }}
    >
      {contenido}
    </Button>
  );
}

/**
 * Reporte de Celiaquía.
 *
 * Todos los números los calcula `reporte_service` en el back, el mismo que usa
 * la pantalla Django. Acá no se suma ni se promedia nada: las reglas de qué
 * cuenta como persona única o como dupla son de negocio y replicarlas daría dos
 * reportes que no cierran entre sí.
 */
export function ReportePage({ canonical = false }: { canonical?: boolean } = {}) {
  return canonical ? <ReporteCanonico /> : <ReporteV2 />;
}

function ReporteV2() {
  const [aplicados, setAplicados] = useState<Filtros>(VACIOS);
  const [page, setPage] = useState(1);
  return (
    <ReporteContenido
      aplicados={aplicados}
      page={page}
      setPage={setPage}
      onFilters={(filtros) => { setAplicados(filtros); setPage(1); }}
    />
  );
}

function ReporteCanonico() {
  const [params, setParams] = useSearchParams();
  const filtros = { ...VACIOS };
  for (const campo of Object.keys(filtros) as (keyof Filtros)[]) {
    filtros[campo] = params.get(campo) ?? "";
  }
  const rawPage = (params.get("page") ?? "").trim();
  const numero = /^[+-]?\d+$/.test(rawPage) ? Number(rawPage) : 1;
  const page = Number.isSafeInteger(numero) ? numero : 1;

  return (
    <ReporteContenido
      key={params.toString()}
      canonical
      aplicados={filtros}
      page={page}
      setPage={(nextPage) => setParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("page", String(nextPage));
        return next;
      })}
      onFilters={(filtrosAplicados) => setParams(
        Object.entries(filtrosAplicados).filter(([, valor]) => valor.trim() !== ""),
      )}
    />
  );
}

type ReporteContenidoProps = {
  aplicados: Filtros;
  page: number;
  setPage: (page: number) => void;
  onFilters: (filtros: Filtros) => void;
  canonical?: boolean;
};

function ReporteContenido({ aplicados, page, setPage, onFilters, canonical }: ReporteContenidoProps) {
  const [filtros, setFiltros] = useState<Filtros>(aplicados);
  const [busquedaRapida, setBusquedaRapida] = useState("");

  const consulta = useQuery({
    queryKey: ["reporte", aplicados, page],
    queryFn: () =>
      api.reporte.obtener({
        ...Object.fromEntries(
          Object.entries(aplicados).filter(([, v]) => v !== ""),
        ),
        provincia: aplicados.provincia ? Number(aplicados.provincia) : undefined,
        page,
      }),
  });

  const aplicar = () => onFilters(filtros);
  const aplicarAcceso = (campo: keyof Filtros, valor: string) => onFilters({ ...filtros, [campo]: valor });

  const limpiar = () => {
    setFiltros(VACIOS);
    onFilters(VACIOS);
  };

  if (consulta.isPending) return <Cargando />;
  if (consulta.isError) return <ErrorPanel error={consulta.error} />;

  const r = consulta.data;
  const termino = busquedaRapida.trim().toLowerCase();
  const casosVisibles = canonical && termino
    ? r.casos.filter((caso) => [
        caso.ciudadano, caso.documento, caso.expediente_numero || `#${caso.expediente_id}`,
        caso.provincia, caso.revision_tecnico, caso.resultado_sintys, caso.estado_cupo,
        caso.archivos_ok ? "Completa" : "Incompleta", formatearFecha(caso.creado_en),
        caso.clasificacion_label, caso.integra_dupla ? "Dupla" : "",
      ].join(" ").toLowerCase().includes(termino))
    : r.casos;

  const ranking = canonical ? r.expedientes_por_provincia.slice(0, 8) : r.expedientes_por_provincia;

  return (
    <>
      <PageHeader
        title="Reporte de Celiaquía"
        crumbs={canonical ? [] : [{ label: "Expedientes", href: "/expedientes" }, { label: "Reporte" }]}
        actions={canonical ? <Button component="a" href="/">Volver a SISOC</Button> : undefined}
      />

      <Stack spacing={3}>
        <SectionCard title="Filtros">
          <Grid
            component={canonical ? "form" : "div"}
            container
            spacing={2}
            onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); aplicar(); }}
          >
            {!r.es_usuario_provincial ? (
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  select
                  fullWidth
                  size="small"
                  label="Provincia"
                  value={filtros.provincia}
                  onChange={(e) =>
                    setFiltros({ ...filtros, provincia: e.target.value })
                  }
                >
                  <MenuItem value="">Todas</MenuItem>
                  {r.provincias.map((p) => (
                    <MenuItem key={String(p.id)} value={String(p.id)}>
                      {String(p.nombre)}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
            ) : null}
            {(
              [
                ["fecha_desde", "Desde", "date"],
                ["fecha_hasta", "Hasta", "date"],
                ["expediente_numero", "Expediente", "text"],
                ["documento_persona", "Documento", "text"],
              ] as const
            ).map(([campo, label, tipo]) => (
              <Grid key={campo} size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  fullWidth
                  size="small"
                  type={tipo}
                  label={label}
                  slotProps={{ inputLabel: { shrink: true } }}
                  value={filtros[campo]}
                  onChange={(e) =>
                    setFiltros({ ...filtros, [campo]: e.target.value })
                  }
                />
              </Grid>
            ))}
            {(
              [
                ["revision_tecnico", "Revisión técnica", REVISION],
                ["resultado_sintys", "Sintys", SINTYS],
                ["estado_cupo", "Cupo", CUPO],
              ] as const
            ).map(([campo, label, opciones]) => (
              <Grid key={campo} size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  select
                  fullWidth
                  size="small"
                  label={label}
                  value={filtros[campo]}
                  onChange={(e) =>
                    setFiltros({ ...filtros, [campo]: e.target.value })
                  }
                >
                  <MenuItem value="">Todos</MenuItem>
                  {opciones.map((o) => (
                    <MenuItem key={o} value={o}>
                      {o.replace(/_/g, " ")}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
            ))}
            <Grid size={{ xs: 12 }}>
              <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  type={canonical ? "submit" : "button"}
                  onClick={canonical ? undefined : aplicar}
                >
                  Aplicar
                </Button>
                <Button type="button" onClick={limpiar}>Limpiar</Button>
              </Stack>
            </Grid>
          </Grid>

          {r.filtros_activos.length > 0 ? (
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
              {r.filtros_activos.map((f, i) => (
                <Chip
                  key={`${String(f.label)}-${i}`}
                  size="small"
                  label={`${String(f.label)}: ${String(f.value ?? f.valor ?? "")}`}
                />
              ))}
            </Stack>
          ) : null}
        </SectionCard>

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Casos" value={r.total_casos} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard
              label="Documentación completa"
              value={r.casos_documentos_ok}
              hint={`${r.porcentaje_documentos_ok}%`}
              tone="success"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard
              label="Documentación incompleta"
              value={r.casos_documentos_incompletos}
              hint={`${r.porcentaje_documentos_incompletos}%`}
              tone="warning"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Con comentarios" value={r.casos_con_comentarios} />
          </Grid>
        </Grid>

        <Grid container spacing={2}>
          {(
            [
              ["Revisión técnica", r.resumen_validacion, "revision_tecnico"],
              ["Cruce Sintys", r.resumen_sintys, "resultado_sintys"],
              ["Cupo", r.resumen_cupo, "estado_cupo"],
            ] as const
          ).map(([titulo, items, campo]) => (
            <Grid key={titulo} size={{ xs: 12, md: 4 }}>
              <SectionCard title={titulo}>
                <Stack spacing={1}>
                  {items.map((it, i) => {
                    const code = typeof it.code === "string" ? it.code : "";
                    return (
                      <FilaResumen
                        key={`${String(it.label)}-${i}`}
                        label={String(it.label)}
                        count={String(it.count)}
                        percentage={String(it.percentage ?? it.porcentaje ?? 0)}
                        onSelect={canonical && code ? () => aplicarAcceso(campo, code) : undefined}
                        selected={aplicados[campo] === code}
                      />
                    );
                  })}
                </Stack>
              </SectionCard>
            </Grid>
          ))}
        </Grid>

        <SectionCard
          title="Aprobados"
          subheader={`Total: ${String(r.clasificacion_aprobados.total ?? 0)}`}
        >
          <Stack spacing={1}>
            {((r.clasificacion_aprobados.items ?? []) as Record<string, unknown>[]).map(
              (it, i) => (
                <Stack
                  key={`${String(it.code)}-${i}`}
                  direction="row"
                  justifyContent="space-between"
                >
                  <Typography variant="body2">{String(it.label)}</Typography>
                  <Typography variant="subtitle1Medium">
                    {String(it.count)}{" "}
                    <Typography component="span" variant="caption" color="text.secondary">
                      ({String(it.percentage ?? 0)}%)
                    </Typography>
                  </Typography>
                </Stack>
              ),
            )}
          </Stack>
        </SectionCard>

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <SectionCard title="Tendencia mensual">
              <Stack spacing={0.5}>
                {r.tendencia_mensual.map((t, i) => (
                  <Stack
                    key={`${String(t.label ?? t.mes)}-${i}`}
                    direction="row"
                    justifyContent="space-between"
                  >
                    <Typography variant="body2">
                      {String(t.label ?? t.mes ?? "")}
                    </Typography>
                    <Typography variant="body2">{String(t.count ?? 0)}</Typography>
                  </Stack>
                ))}
                {r.tendencia_mensual.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    Sin datos para el período.
                  </Typography>
                ) : null}
              </Stack>
            </SectionCard>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <SectionCard title="Expedientes por provincia">
              <Stack spacing={0.5}>
                {ranking.map((p, i) => {
                  const label = String(p.nombre ?? p.label ?? p.provincia ?? "");
                  const provinciaId = p.provincia_id;
                  const permiteFiltrar = canonical && !r.es_usuario_provincial
                    && typeof provinciaId === "number" && provinciaId > 0;
                  return (
                    <FilaResumen
                      key={`${label}-${i}`}
                      label={label}
                      subtitle={canonical ? `${String(p.expedientes ?? 0)} expedientes` : undefined}
                      count={String(p.casos ?? p.count ?? 0)}
                      percentage={String(p.share ?? p.percentage ?? 0)}
                      onSelect={permiteFiltrar ? () => aplicarAcceso("provincia", String(provinciaId)) : undefined}
                      selected={aplicados.provincia === String(provinciaId)}
                    />
                  );
                })}
                {r.expedientes_por_provincia.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    Sin datos.
                  </Typography>
                ) : null}
              </Stack>
            </SectionCard>
          </Grid>
        </Grid>

        <SectionCard title="Detalle" disableGutters>
          {canonical ? (
            <Stack spacing={1} sx={{ p: 2 }}>
              <TextField
                type="search"
                label="Buscar en esta página"
                placeholder="Filtrar filas visibles"
                size="small"
                value={busquedaRapida}
                onChange={(e) => setBusquedaRapida(e.target.value)}
              />
              <Typography variant="caption" role="status" aria-label="Resultados de la búsqueda rápida">
                {casosVisibles.length} {casosVisibles.length === 1 ? "registro visible" : "registros visibles"} en esta página
              </Typography>
            </Stack>
          ) : null}
          <TableContainer component={Paper} variant="outlined" sx={{ overflowX: "auto" }}>
            <Table size="small" sx={{ minWidth: 980 }}>
              <TableHead>
                <TableRow>
                  <TableCell>Persona</TableCell>
                  <TableCell>Expediente</TableCell>
                  <TableCell>Provincia</TableCell>
                  {canonical ? <TableCell>Rol</TableCell> : null}
                  <TableCell>Revisión</TableCell>
                  <TableCell>Sintys</TableCell>
                  <TableCell>Cupo</TableCell>
                  <TableCell>Documentación</TableCell>
                  <TableCell>Alta</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {casosVisibles.map((c) => (
                  <TableRow key={c.id} hover>
                    <TableCell>
                      <Typography variant="body2">{c.ciudadano}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {canonical && c.expediente_id !== null && c.documento
                          ? <Link href={`/celiaquia/expedientes/${c.expediente_id}/`}>{c.documento}</Link>
                          : c.documento}
                      </Typography>
                    </TableCell>
                    <TableCell>{c.expediente_numero || `#${c.expediente_id}`}</TableCell>
                    <TableCell>{c.provincia}</TableCell>
                    {canonical ? (
                      <TableCell>
                        <Stack direction="row" spacing={1}>
                          <StateChip label={c.clasificacion_label ?? "-"} tone={tonoRol(c.clasificacion_tone)} />
                          {c.integra_dupla === true ? (
                            <StateChip label="Dupla" tone="info" title="Hijo aprobado asociado a un responsable aprobado" />
                          ) : null}
                        </Stack>
                      </TableCell>
                    ) : null}
                    <TableCell>
                      <StateChip
                        label={c.revision_tecnico}
                        tone={tonoRevision(c.revision_tecnico)}
                      />
                    </TableCell>
                    <TableCell>{c.resultado_sintys}</TableCell>
                    <TableCell>{c.estado_cupo}</TableCell>
                    <TableCell>
                      <StateChip
                        label={c.archivos_ok ? "Completa" : "Incompleta"}
                        tone={c.archivos_ok ? "success" : "warning"}
                      />
                    </TableCell>
                    <TableCell>{formatearFecha(c.creado_en)}</TableCell>
                  </TableRow>
                ))}
                {casosVisibles.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={canonical ? 9 : 8}>
                      <Typography variant="body2" color="text.secondary">
                        {r.casos.length === 0
                          ? "No hay casos para los filtros aplicados."
                          : "No hay filas que coincidan en esta página."}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : null}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={r.total_casos}
            page={Math.max(0, r.page - 1)}
            rowsPerPage={r.page_size}
            rowsPerPageOptions={[r.page_size]}
            onPageChange={(_, p) => setPage(p + 1)}
            labelDisplayedRows={() =>
              `${r.detalle_desde}–${r.detalle_hasta} de ${r.total_casos}`
            }
          />
        </SectionCard>
      </Stack>
    </>
  );
}
