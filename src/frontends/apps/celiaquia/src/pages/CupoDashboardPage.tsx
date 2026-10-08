import { Link as RouterLink } from "react-router-dom";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import {
  PageHeader,
  SectionCard,
  severidad,
  Stack,
  StateChip,
} from "@sisoc/ui";
import Alert from "@mui/material/Alert";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import AddIcon from "@mui/icons-material/Add";
import { mensajeDeError } from "@sisoc/api";
import type { FilaCupoProvincia } from "@sisoc/api";
import { api } from "../api";
import { ErrorPanel, TablaCargando } from "../componentes/Estados";

/**
 * Tope de `ProvinciaCupo.total_asignado`: la columna es un entero sin signo y
 * pasarse hacia que MySQL tirara "Out of range value", que llegaba como un 500.
 * El back valida igual; esto evita el viaje y avisa mientras se escribe.
 */
const CUPO_MAXIMO = 4294967295;

export function CupoDashboardPage() {
  const queryClient = useQueryClient();
  const [aConfigurar, setAConfigurar] = useState<FilaCupoProvincia | null>(null);
  const [total, setTotal] = useState("");
  const [error, setError] = useState("");

  // `dashboard` trae **todas** las provincias, también las que no tienen cupo:
  // sin eso no hay forma de asignarle cupo a una provincia nueva.
  const consulta = useQuery({
    queryKey: ["cupos-dashboard"],
    queryFn: () => api.cupos.dashboard(),
  });

  const configurar = useMutation({
    mutationFn: () =>
      api.cupos.configurar(aConfigurar!.provincia_id, Number(total)),
    onSuccess: () => {
      setError("");
      setAConfigurar(null);
      setTotal("");
      queryClient.invalidateQueries({ queryKey: ["cupos-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["cupos"] });
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const totalNumero = Number(total);
  const totalInvalido =
    total === "" ||
    !Number.isInteger(totalNumero) ||
    totalNumero < 0 ||
    totalNumero > CUPO_MAXIMO;

  const abrir = (fila: FilaCupoProvincia) => {
    setAConfigurar(fila);
    setTotal(fila.total_asignado != null ? String(fila.total_asignado) : "");
    setError("");
  };

  const filas = consulta.data ?? [];

  return (
    <>
      <PageHeader
        title="Cupos por provincia"
        crumbs={[{ label: "Expedientes", href: "/expedientes" }, { label: "Cupos" }]}
      />

      <SectionCard
        title="Provincias"
        subheader={consulta.data ? `${consulta.data.length} provincias` : "Cargando…"}
        disableGutters
      >
        {consulta.isPending ? <TablaCargando /> : null}
        {consulta.isError ? (
          <Box sx={{ px: 2 }}>
            <ErrorPanel error={consulta.error} />
          </Box>
        ) : null}

        {consulta.isSuccess ? (
          <TableContainer sx={{ overflowX: "auto" }}>
            <Table sx={{ minWidth: 798 }} size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Provincia</TableCell>
                  <TableCell align="right">Total asignado</TableCell>
                  <TableCell align="right">Usados</TableCell>
                  <TableCell width="22%">Ocupación</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filas.map((r) => {
                  const sinConfigurar = !r.configurado;
                  const pct = sinConfigurar
                    ? 0
                    : Math.round(
                        ((r.usados ?? 0) / (r.total_asignado || 1)) * 100,
                      );
                  return (
                    <TableRow key={r.provincia_id} hover>
                      <TableCell>{r.provincia}</TableCell>
                      <TableCell align="right">
                        {sinConfigurar ? (
                          <StateChip label="Sin configurar" tone="neutral" />
                        ) : (
                          r.total_asignado
                        )}
                      </TableCell>
                      <TableCell align="right">{r.usados ?? "—"}</TableCell>
                      <TableCell>
                        {sinConfigurar ? (
                          <Typography variant="body2" color="text.secondary">
                            —
                          </Typography>
                        ) : (
                          <Stack spacing={0.5}>
                            <LinearProgress
                              variant="determinate"
                              value={Math.min(pct, 100)}
                              color={severidad(pct)}
                              sx={{ height: 6, borderRadius: 3 }}
                            />
                            <Typography
                              variant="caption"
                              sx={{ color: `${severidad(pct)}.text` }}
                            >
                              {pct}% del cupo ocupado
                            </Typography>
                          </Stack>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {sinConfigurar ? (
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={<AddIcon />}
                            onClick={() => abrir(r)}
                          >
                            Asignar cupo
                          </Button>
                        ) : (
                          <Stack direction="row" spacing={1} justifyContent="flex-end">
                            <Button size="small" onClick={() => abrir(r)}>
                              Editar
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              component={RouterLink}
                              to={`/cupos/${r.cupo_id}`}
                            >
                              Ver
                            </Button>
                          </Stack>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}

                {filas.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No hay provincias para mostrar.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : null}
              </TableBody>
            </Table>
          </TableContainer>
        ) : null}
      </SectionCard>

      <Dialog
        open={Boolean(aConfigurar)}
        onClose={() => setAConfigurar(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>
          {aConfigurar?.configurado ? "Editar cupo" : "Asignar cupo"} —{" "}
          {aConfigurar?.provincia}
        </DialogTitle>
        <DialogContent>
          {error ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          ) : null}
          <TextField
            autoFocus
            fullWidth
            size="small"
            type="number"
            label="Cupo total"
            value={total}
            onChange={(e) => setTotal(e.target.value)}
            error={total !== "" && totalInvalido}
            slotProps={{ htmlInput: { min: 0, max: CUPO_MAXIMO, step: 1 } }}
            helperText={
              total !== "" && totalInvalido
                ? `Tiene que ser un entero entre 0 y ${CUPO_MAXIMO.toLocaleString("es-AR")}`
                : aConfigurar?.configurado
                  ? `Usados actualmente: ${aConfigurar.usados ?? 0}`
                  : "Cantidad de titulares que la provincia puede tener activos"
            }
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAConfigurar(null)}>Cancelar</Button>
          <Button
            variant="contained"
            disabled={configurar.isPending || totalInvalido}
            onClick={() => configurar.mutate()}
          >
            {configurar.isPending ? "Guardando…" : "Guardar"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
