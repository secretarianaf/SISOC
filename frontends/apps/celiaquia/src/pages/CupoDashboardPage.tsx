import { Link as RouterLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
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
import { api } from "../api";
import { ErrorPanel, TablaCargando } from "../componentes/Estados";

export function CupoDashboardPage() {
  const consulta = useQuery({
    queryKey: ["cupos"],
    queryFn: () => api.cupos.listar(),
  });

  const filas = consulta.data?.results ?? [];

  return (
    <>
      <PageHeader
        title="Cupos por provincia"
        crumbs={[{ label: "Expedientes", href: "/expedientes" }, { label: "Cupos" }]}
      />

      <SectionCard
        title="Provincias"
        subheader={consulta.data ? `${consulta.data.count} provincias` : "Cargando…"}
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
                  const sinConfigurar =
                    r.total_asignado === null || r.total_asignado === undefined;
                  const pct = sinConfigurar
                    ? 0
                    : Math.round(
                        ((r.usados ?? 0) / (r.total_asignado || 1)) * 100,
                      );
                  return (
                    <TableRow key={r.id} hover>
                      <TableCell>{r.provincia_nombre ?? r.provincia}</TableCell>
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
                        <Button
                          size="small"
                          variant="outlined"
                          component={RouterLink}
                          to={`/cupos/${r.id}`}
                        >
                          Ver
                        </Button>
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
    </>
  );
}
