import { useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import TuneIcon from "@mui/icons-material/Tune";
import {
  PageHeader,
  SectionCard,
  Stack,
  StatCard,
  StateChip,
  toneCupo,
  toneRevision,
  toneSintys,
} from "@sisoc/ui";
import { mensajeDeError } from "@sisoc/api";
import type { Legajo } from "@sisoc/api";
import { api } from "../api";
import { Aviso, Cargando, ErrorPanel, TablaCargando } from "../componentes/Estados";

type AccionCupo = "baja" | "suspender" | "reactivar";

function TablaTitulares({
  titulo,
  legajos,
  cargando,
  conAcciones,
  onAccion,
  ocupado,
}: {
  titulo: string;
  legajos: Legajo[];
  cargando: boolean;
  conAcciones?: boolean;
  onAccion?: (legajo: Legajo, accion: AccionCupo) => void;
  ocupado?: boolean;
}) {
  return (
    <SectionCard
      title={titulo}
      subheader={`${legajos.length} titulares`}
      disableGutters
    >
      {cargando ? <TablaCargando filas={3} /> : null}
      {!cargando ? (
        <TableContainer sx={{ overflowX: "auto" }}>
          <Table size="small" sx={{ minWidth: 798 }}>
            <TableHead>
              <TableRow>
                <TableCell>CUIL</TableCell>
                <TableCell>Nombre</TableCell>
                <TableCell>Apellido</TableCell>
                <TableCell>Revisión</TableCell>
                <TableCell>Resultado</TableCell>
                <TableCell>Estado cupo</TableCell>
                <TableCell>Activo</TableCell>
                {conAcciones ? (
                  <TableCell align="right">Acciones</TableCell>
                ) : null}
              </TableRow>
            </TableHead>
            <TableBody>
              {legajos.map((l) => (
                <TableRow key={l.id} hover>
                  <TableCell>{l.documento ?? "—"}</TableCell>
                  <TableCell>{l.nombre ?? "—"}</TableCell>
                  <TableCell>{l.apellido ?? "—"}</TableCell>
                  <TableCell>
                    <StateChip
                      label={l.revision_tecnico}
                      tone={toneRevision(l.revision_tecnico)}
                    />
                  </TableCell>
                  <TableCell>
                    <StateChip
                      label={l.resultado_sintys ?? "—"}
                      tone={toneSintys(l.resultado_sintys ?? "")}
                    />
                  </TableCell>
                  <TableCell>
                    <StateChip
                      label={l.estado_cupo}
                      tone={toneCupo(l.estado_cupo)}
                    />
                  </TableCell>
                  <TableCell>
                    <StateChip
                      label={l.es_titular_activo ? "Sí" : "No"}
                      tone={l.es_titular_activo ? "success" : "neutral"}
                    />
                  </TableCell>
                  {conAcciones ? (
                    <TableCell align="right">
                      <ButtonGroup
                        size="small"
                        variant="outlined"
                        disabled={ocupado}
                      >
                        {l.es_titular_activo ? (
                          <Button
                            color="warning"
                            onClick={() => onAccion?.(l, "suspender")}
                          >
                            Suspender
                          </Button>
                        ) : (
                          <Button
                            color="success"
                            onClick={() => onAccion?.(l, "reactivar")}
                          >
                            Reactivar
                          </Button>
                        )}
                        <Button
                          color="error"
                          onClick={() => onAccion?.(l, "baja")}
                        >
                          Baja
                        </Button>
                      </ButtonGroup>
                    </TableCell>
                  ) : null}
                </TableRow>
              ))}

              {legajos.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={conAcciones ? 8 : 7}
                    align="center"
                    sx={{ py: 4 }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      Sin titulares en esta lista.
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

export function CupoProvinciaPage() {
  const { provinciaId } = useParams();
  const cupoId = Number(provinciaId);
  const queryClient = useQueryClient();

  const [aviso, setAviso] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modalConfig, setModalConfig] = useState(false);
  const [total, setTotal] = useState("");
  const [pendiente, setPendiente] = useState<{
    legajo: Legajo;
    accion: AccionCupo;
  } | null>(null);
  const [motivo, setMotivo] = useState("");

  const cupo = useQuery({
    queryKey: ["cupo", cupoId],
    queryFn: () => api.cupos.listar().then((p) => p.results.find((c) => c.id === cupoId)),
    enabled: Number.isFinite(cupoId),
  });

  const metricas = useQuery({
    queryKey: ["cupo", cupoId, "metricas"],
    queryFn: () => api.cupos.metricas(cupoId),
    enabled: Number.isFinite(cupoId),
  });

  const ocupados = useQuery({
    queryKey: ["cupo", cupoId, "ocupados"],
    queryFn: () => api.cupos.ocupados(cupoId),
    enabled: Number.isFinite(cupoId),
  });

  const suspendidos = useQuery({
    queryKey: ["cupo", cupoId, "suspendidos"],
    queryFn: () => api.cupos.suspendidos(cupoId),
    enabled: Number.isFinite(cupoId),
  });

  const refrescar = () =>
    queryClient.invalidateQueries({ queryKey: ["cupo", cupoId] });

  const configurar = useMutation({
    mutationFn: () =>
      api.cupos.configurar(cupo.data!.provincia, Number(total)),
    onSuccess: () => {
      setAviso("Cupo configurado.");
      setModalConfig(false);
      queryClient.invalidateQueries({ queryKey: ["cupos"] });
      refrescar();
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const mover = useMutation({
    mutationFn: ({ legajo, accion }: { legajo: Legajo; accion: AccionCupo }) => {
      if (accion === "baja") return api.cupos.baja(legajo.id, motivo);
      if (accion === "suspender") return api.cupos.suspender(legajo.id, motivo);
      return api.cupos.reactivar(legajo.id, motivo);
    },
    onSuccess: (_d, variables) => {
      setAviso(
        variables.accion === "baja"
          ? "Titular dado de baja."
          : variables.accion === "suspender"
            ? "Titular suspendido."
            : "Titular reactivado.",
      );
      setPendiente(null);
      setMotivo("");
      refrescar();
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  if (cupo.isPending) return <Cargando />;
  if (cupo.isError) return <ErrorPanel error={cupo.error} />;
  if (!cupo.data) return <ErrorPanel error={new Error("Cupo inexistente.")} />;

  const nombre = cupo.data.provincia_nombre ?? `Provincia ${cupo.data.provincia}`;
  const sinConfigurar = cupo.data.total_asignado === null;

  return (
    <>
      <PageHeader
        title={nombre}
        crumbs={[{ label: "Cupos", href: "/cupos" }, { label: nombre }]}
        actions={
          <>
            <Button
              size="small"
              variant="text"
              color="inherit"
              startIcon={<ArrowBackIcon />}
              component={RouterLink}
              to="/cupos"
            >
              Volver
            </Button>
            <Button
              size="small"
              variant="contained"
              startIcon={<TuneIcon />}
              onClick={() => {
                setTotal(String(cupo.data?.total_asignado ?? ""));
                setModalConfig(true);
              }}
            >
              Configurar cupo
            </Button>
            <Button
              size="small"
              variant="outlined"
              color="success"
              component={RouterLink}
              to={`/pagos/${cupo.data.provincia}`}
            >
              Expedientes de pago
            </Button>
          </>
        }
      />

      <Stack spacing={3}>
        {sinConfigurar ? (
          <ErrorPanel error={new Error("La provincia no tiene cupo configurado.")} />
        ) : (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
              <StatCard
                label="Total asignado"
                value={metricas.data?.total_asignado ?? "—"}
                tone="primary"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
              <StatCard
                label="Usados"
                value={metricas.data?.usados ?? "—"}
                tone="secondary"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
              <StatCard
                label="Disponibles"
                value={metricas.data?.disponibles ?? "—"}
                tone="success"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
              <StatCard
                label="Fuera de cupo"
                value={metricas.data?.fuera ?? "—"}
                tone="error"
              />
            </Grid>
          </Grid>
        )}

        <TablaTitulares
          titulo="Cupos ocupados (titulares activos)"
          legajos={ocupados.data ?? []}
          cargando={ocupados.isPending}
          conAcciones
          ocupado={mover.isPending}
          onAccion={(legajo, accion) => setPendiente({ legajo, accion })}
        />

        <TablaTitulares
          titulo="Suspendidos (cupo ocupado, no activos)"
          legajos={suspendidos.data ?? []}
          cargando={suspendidos.isPending}
          conAcciones
          ocupado={mover.isPending}
          onAccion={(legajo, accion) => setPendiente({ legajo, accion })}
        />
      </Stack>

      <Dialog
        open={modalConfig}
        onClose={() => setModalConfig(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Configurar cupo para {nombre}</DialogTitle>
        <DialogContent dividers>
          <TextField
            label="Total asignado"
            type="number"
            fullWidth
            value={total}
            onChange={(e) => setTotal(e.target.value)}
            placeholder="Ej.: 500"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModalConfig(false)}>Cancelar</Button>
          <Button
            variant="contained"
            disabled={configurar.isPending || total === ""}
            onClick={() => configurar.mutate()}
          >
            Guardar
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={pendiente !== null}
        onClose={() => setPendiente(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>
          {pendiente?.accion === "baja"
            ? "Dar de baja titular"
            : pendiente?.accion === "suspender"
              ? "Suspender titular"
              : "Reactivar titular"}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              {pendiente
                ? `${pendiente.legajo.nombre} ${pendiente.legajo.apellido} · ${pendiente.legajo.documento}`
                : ""}
            </Typography>
            <TextField
              label="Motivo"
              multiline
              minRows={3}
              fullWidth
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendiente(null)}>Cancelar</Button>
          <Button
            variant="contained"
            color={pendiente?.accion === "baja" ? "error" : "warning"}
            disabled={mover.isPending}
            onClick={() => pendiente && mover.mutate(pendiente)}
          >
            Confirmar
          </Button>
        </DialogActions>
      </Dialog>

      <Aviso mensaje={aviso} onClose={() => setAviso(null)} />
      <Aviso mensaje={error} severidad="error" onClose={() => setError(null)} />
    </>
  );
}
