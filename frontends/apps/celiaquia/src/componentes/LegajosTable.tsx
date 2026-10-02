import { Fragment, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Collapse from "@mui/material/Collapse";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { SearchField, SectionCard, Stack, StateChip, formatearFecha, toneCupo, toneRevision, toneSintys } from "@sisoc/ui";
import type { AccionRevision, Legajo } from "@sisoc/api";
import { TablaCargando } from "./Estados";

const etiquetaRevision: Record<string, string> = {
  APROBADO: "Aprobado",
  RECHAZADO: "Rechazado",
  SUBSANAR: "Subsanar",
  SUBSANADO: "Subsanado",
  PENDIENTE: "Pendiente",
};

/** Un legajo ya resuelto no se vuelve a revisar: se corrige por otra via. */
const esFinal = (revision: string) =>
  revision === "APROBADO" || revision === "RECHAZADO";

export type RevisionPedida = {
  legajoId: number;
  accion: AccionRevision;
  texto_libre?: string;
};

function FilaLegajo({
  leg,
  onRevisar,
  deshabilitado,
}: {
  leg: Legajo;
  onRevisar: (pedido: RevisionPedida) => void;
  deshabilitado: boolean;
}) {
  const [abierto, setAbierto] = useState(false);
  const [motivoDe, setMotivoDe] = useState<AccionRevision | null>(null);
  const [textoLibre, setTextoLibre] = useState("");
  // El schema declara estos campos opcionales: el serializer los omite
  // cuando el legajo todavia no fue evaluado.
  const revision = leg.revision_tecnico ?? "PENDIENTE";
  const estadoCupo = leg.estado_cupo ?? "SIN_ASIGNAR";
  const tone = toneRevision(revision);
  const bloqueado = deshabilitado || esFinal(revision);

  const confirmarConMotivo = () => {
    if (!motivoDe) return;
    onRevisar({
      legajoId: leg.id,
      accion: motivoDe,
      texto_libre: textoLibre,
    });
    setMotivoDe(null);
    setTextoLibre("");
  };

  return (
    <Fragment>
      <TableRow
        hover
        sx={{
          "& > td": { borderBottom: abierto ? "none" : undefined },
          borderLeft: (t) =>
            `${t.border.accent}px solid ${
              tone === "neutral" ? t.palette.divider : t.palette[tone].main
            }`,
        }}
      >
        <TableCell>
          <Typography variant="body2" color="text.secondary">
            #{leg.id}
          </Typography>
        </TableCell>

        <TableCell>
          <Typography variant="subtitle1Medium" component="div">
            {leg.ciudadano}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            CUIL: {leg.documento ?? "—"}
          </Typography>
        </TableCell>

        <TableCell>
          <StateChip
            label={etiquetaRevision[revision] ?? revision}
            tone={tone}
          />
        </TableCell>

        <TableCell>
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
            <StateChip
              label={`Sintys: ${leg.resultado_sintys ?? "—"}`}
              tone={toneSintys(leg.resultado_sintys ?? "")}
            />
            <StateChip
              label={`Cupo: ${estadoCupo}`}
              tone={toneCupo(estadoCupo)}
            />
          </Stack>
        </TableCell>

        <TableCell>
          {leg.subsanacion_motivo ? (
            <Typography variant="body2">{leg.subsanacion_motivo}</Typography>
          ) : (
            <Typography variant="body2" color="text.secondary">
              —
            </Typography>
          )}
        </TableCell>

        <TableCell align="right">
          <Stack direction="row" spacing={0.5} justifyContent="flex-end">
            <Tooltip title={abierto ? "Ocultar detalle" : "Ver detalle"}>
              <IconButton size="small" onClick={() => setAbierto((v) => !v)}>
                {abierto ? (
                  <KeyboardArrowUpIcon fontSize="small" />
                ) : (
                  <KeyboardArrowDownIcon fontSize="small" />
                )}
              </IconButton>
            </Tooltip>
            <Tooltip title="Eliminar legajo">
              <span>
                <IconButton
                  size="small"
                  color="error"
                  disabled={deshabilitado}
                  onClick={() =>
                    onRevisar({ legajoId: leg.id, accion: "ELIMINAR" })
                  }
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          </Stack>
        </TableCell>
      </TableRow>

      <TableRow>
        <TableCell colSpan={6} sx={{ p: 0, border: 0 }}>
          <Collapse in={abierto} timeout="auto" unmountOnExit>
            <Box sx={{ p: 2, bgcolor: "action.hover" }}>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                    <Typography variant="captionBold" color="text.secondary">
                      Datos del titular
                    </Typography>
                    <Stack spacing={0.5} sx={{ mt: 1 }}>
                      <Typography variant="body2">
                        {leg.ciudadano}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        CUIL {leg.documento ?? "—"}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Alta {formatearFecha(leg.creado_en)}
                      </Typography>
                    </Stack>
                    <Divider sx={{ my: 1.5 }} />
                    <StateChip
                      label={
                        leg.es_titular_activo
                          ? "Titular activo"
                          : "No activo"
                      }
                      tone={leg.es_titular_activo ? "success" : "neutral"}
                    />
                  </Paper>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                    <Typography variant="captionBold" color="text.secondary">
                      Revisión técnica
                    </Typography>
                    <Stack spacing={1.5} sx={{ mt: 1 }}>
                      {esFinal(revision) ? (
                        <Typography variant="body2" color="text.secondary">
                          El legajo ya tiene evaluación final
                          {` (${etiquetaRevision[revision]})`}. Se
                          corrige desde la pantalla de corrección.
                        </Typography>
                      ) : (
                        <ButtonGroup size="small" fullWidth disabled={bloqueado}>
                          <Button
                            color="success"
                            onClick={() =>
                              onRevisar({
                                legajoId: leg.id,
                                accion: "APROBAR",
                              })
                            }
                          >
                            Aprobar
                          </Button>
                          <Button
                            color="warning"
                            onClick={() => setMotivoDe("SUBSANAR")}
                          >
                            Subsanar
                          </Button>
                          <Button
                            color="error"
                            onClick={() => setMotivoDe("RECHAZAR")}
                          >
                            Rechazar
                          </Button>
                        </ButtonGroup>
                      )}
                    </Stack>
                  </Paper>
                </Grid>
              </Grid>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>

      <Dialog
        open={motivoDe !== null}
        onClose={() => setMotivoDe(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {motivoDe === "RECHAZAR" ? "Motivo del rechazo" : "Motivo de la subsanación"}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              El motivo final lo arma el sistema: a este texto se le suman las
              observaciones técnicas ya cargadas en el legajo.
            </Typography>
            <TextField
              label="Texto complementario"
              multiline
              minRows={3}
              fullWidth
              value={textoLibre}
              onChange={(e) => setTextoLibre(e.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMotivoDe(null)}>Cancelar</Button>
          <Button
            variant="contained"
            color={motivoDe === "RECHAZAR" ? "error" : "warning"}
            onClick={confirmarConMotivo}
          >
            Confirmar
          </Button>
        </DialogActions>
      </Dialog>
    </Fragment>
  );
}

export function LegajosTable({
  legajos,
  cargando,
  onRevisar,
  revisando,
}: {
  legajos: Legajo[];
  cargando: boolean;
  onRevisar: (pedido: RevisionPedida) => void;
  revisando: boolean;
}) {
  const [q, setQ] = useState("");

  const filas = useMemo(() => {
    const texto = q.trim().toLowerCase();
    if (!texto) return legajos;
    return legajos.filter((l) =>
      `${l.id} ${l.ciudadano} ${l.documento}`
        .toLowerCase()
        .includes(texto),
    );
  }, [q, legajos]);

  const aSubsanar = legajos.filter(
    (l) => l.revision_tecnico === "SUBSANAR",
  ).length;

  return (
    <SectionCard
      title={
        <Stack direction="row" spacing={1} alignItems="center">
          <span>Legajos</span>
          <StateChip label={`${legajos.length} personas`} tone="primary" />
          {aSubsanar > 0 ? (
            <StateChip label={`${aSubsanar} a subsanar`} tone="warning" />
          ) : null}
        </Stack>
      }
      action={
        <SearchField
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por ID, nombre, apellido o CUIL"
        />
      }
      disableGutters
    >
      {cargando ? <TablaCargando /> : null}

      {!cargando ? (
        <TableContainer sx={{ overflowX: "auto" }}>
          <Table sx={{ minWidth: 1068 }} size="small">
            <TableHead>
              <TableRow>
                <TableCell width="8%">ID</TableCell>
                <TableCell width="26%">Beneficiario</TableCell>
                <TableCell width="14%">Estado</TableCell>
                <TableCell width="20%">Cruce y cupo</TableCell>
                <TableCell width="20%">Observaciones</TableCell>
                <TableCell width="12%" align="right">
                  Acciones
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filas.map((leg) => (
                <FilaLegajo
                  key={leg.id}
                  leg={leg}
                  onRevisar={onRevisar}
                  deshabilitado={revisando}
                />
              ))}

              {filas.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No hay legajos que coincidan con la búsqueda.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null}
    </SectionCard>
  );
}
