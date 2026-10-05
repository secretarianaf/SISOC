import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
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

/**
 * Reporte de Celiaquía.
 *
 * Todos los números los calcula `reporte_service` en el back, el mismo que usa
 * la pantalla Django. Acá no se suma ni se promedia nada: las reglas de qué
 * cuenta como persona única o como dupla son de negocio y replicarlas daría dos
 * reportes que no cierran entre sí.
 */
export function ReportePage() {
  const [filtros, setFiltros] = useState<Filtros>(VACIOS);
  const [aplicados, setAplicados] = useState<Filtros>(VACIOS);
  const [page, setPage] = useState(1);

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

  const aplicar = () => {
    setAplicados(filtros);
    setPage(1);
  };

  const limpiar = () => {
    setFiltros(VACIOS);
    setAplicados(VACIOS);
    setPage(1);
  };

  if (consulta.isPending) return <Cargando />;
  if (consulta.isError) return <ErrorPanel error={consulta.error} />;

  const r = consulta.data;

  return (
    <>
      <PageHeader
        title="Reporte de Celiaquía"
        crumbs={[{ label: "Expedientes", href: "/expedientes" }, { label: "Reporte" }]}
      />

      <Stack spacing={3}>
        <SectionCard title="Filtros">
          <Grid container spacing={2}>
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
                <Button variant="contained" onClick={aplicar}>
                  Aplicar
                </Button>
                <Button onClick={limpiar}>Limpiar</Button>
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
              ["Revisión técnica", r.resumen_validacion],
              ["Cruce Sintys", r.resumen_sintys],
              ["Cupo", r.resumen_cupo],
            ] as const
          ).map(([titulo, items]) => (
            <Grid key={titulo} size={{ xs: 12, md: 4 }}>
              <SectionCard title={titulo}>
                <Stack spacing={1}>
                  {items.map((it, i) => (
                    <Stack
                      key={`${String(it.label)}-${i}`}
                      direction="row"
                      justifyContent="space-between"
                    >
                      <Typography variant="body2">{String(it.label)}</Typography>
                      <Typography variant="subtitle1Medium">
                        {String(it.count)}{" "}
                        <Typography component="span" variant="caption" color="text.secondary">
                          ({String(it.percentage ?? it.porcentaje ?? 0)}%)
                        </Typography>
                      </Typography>
                    </Stack>
                  ))}
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
                {r.expedientes_por_provincia.map((p, i) => (
                  <Stack
                    key={`${String(p.label ?? p.provincia)}-${i}`}
                    direction="row"
                    justifyContent="space-between"
                  >
                    <Typography variant="body2">
                      {String(p.label ?? p.provincia ?? "")}
                    </Typography>
                    <Typography variant="body2">
                      {String(p.count ?? 0)}{" "}
                      <Typography component="span" variant="caption" color="text.secondary">
                        ({String(p.percentage ?? 0)}%)
                      </Typography>
                    </Typography>
                  </Stack>
                ))}
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
          <TableContainer component={Paper} variant="outlined" sx={{ overflowX: "auto" }}>
            <Table size="small" sx={{ minWidth: 980 }}>
              <TableHead>
                <TableRow>
                  <TableCell>Persona</TableCell>
                  <TableCell>Expediente</TableCell>
                  <TableCell>Provincia</TableCell>
                  <TableCell>Revisión</TableCell>
                  <TableCell>Sintys</TableCell>
                  <TableCell>Cupo</TableCell>
                  <TableCell>Documentación</TableCell>
                  <TableCell>Alta</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {r.casos.map((c) => (
                  <TableRow key={c.id} hover>
                    <TableCell>
                      <Typography variant="body2">{c.ciudadano}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {c.documento}
                      </Typography>
                    </TableCell>
                    <TableCell>{c.expediente_numero || `#${c.expediente_id}`}</TableCell>
                    <TableCell>{c.provincia}</TableCell>
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
                {r.casos.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8}>
                      <Typography variant="body2" color="text.secondary">
                        No hay casos para los filtros aplicados.
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
