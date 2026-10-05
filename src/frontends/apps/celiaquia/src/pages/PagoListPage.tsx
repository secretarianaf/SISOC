import { useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Pagination from "@mui/material/Pagination";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PaymentsIcon from "@mui/icons-material/Payments";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { PageHeader, SectionCard, StateChip, formatearFecha } from "@sisoc/ui";
import type { StateTone } from "@sisoc/ui";
import { mensajeDeError, paginasDe } from "@sisoc/api";
import { api } from "../api";
import { Aviso, ErrorPanel, TablaCargando } from "../componentes/Estados";

const tonePago: Record<string, StateTone> = {
  BORRADOR: "neutral",
  ENVIADO: "info",
  PROCESADO: "warning",
  VALIDADO: "success",
  CERRADO: "primary",
};

export function PagoListPage() {
  const { provinciaId } = useParams();
  const provincia = Number(provinciaId);
  const queryClient = useQueryClient();
  const [aviso, setAviso] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  // El back filtra por provincia: filtrar en la pantalla solo veia la primera
  // pagina de todas las provincias juntas.
  const consulta = useQuery({
    queryKey: ["pagos", provincia, page],
    queryFn: () => api.pagos.listar({ provincia, page }),
    enabled: Number.isFinite(provincia),
  });

  const crear = useMutation({
    mutationFn: () => api.pagos.crear(provincia),
    onSuccess: () => {
      setAviso("Expediente de pago generado.");
      queryClient.invalidateQueries({ queryKey: ["pagos"] });
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const filas = consulta.data?.results ?? [];
  const total = consulta.data?.count ?? 0;
  const totalPaginas = paginasDe(total);

  return (
    <>
      <PageHeader
        title="Expedientes de pago"
        crumbs={[
          { label: "Cupos", href: "/cupos" },
          { label: "Pagos" },
        ]}
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
              color="success"
              startIcon={<PaymentsIcon />}
              disabled={crear.isPending}
              onClick={() => crear.mutate()}
            >
              Generar expediente de pago
            </Button>
          </>
        }
      />

      <SectionCard
        title="Períodos"
        subheader={`${total} expedientes de pago`}
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
            <Table size="small" sx={{ minWidth: 798 }}>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Período</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell align="right">Candidatos</TableCell>
                  <TableCell align="right">Validados</TableCell>
                  <TableCell align="right">Excluidos</TableCell>
                  <TableCell>Creado</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filas.map((p) => (
                  <TableRow key={p.id} hover>
                    <TableCell>{p.id}</TableCell>
                    <TableCell>{p.periodo}</TableCell>
                    <TableCell>
                      <StateChip
                        label={p.estado ?? "—"}
                        tone={(p.estado && tonePago[p.estado]) ?? "neutral"}
                      />
                    </TableCell>
                    <TableCell align="right">{p.total_candidatos}</TableCell>
                    <TableCell align="right">{p.total_validados}</TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        sx={{
                          color:
                            (p.total_excluidos ?? 0) > 0
                              ? "error.text"
                              : "inherit",
                        }}
                      >
                        {p.total_excluidos}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {formatearFecha(p.creado_en)}
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<VisibilityIcon />}
                        component={RouterLink}
                        to={`/pagos/expediente/${p.id}`}
                      >
                        Ver
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}

                {filas.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No hay expedientes de pago.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : null}
              </TableBody>
            </Table>
          </TableContainer>
        ) : null}

        {totalPaginas > 1 ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
            <Pagination
              count={totalPaginas}
              page={page}
              onChange={(_e, p) => setPage(p)}
              size="small"
              shape="rounded"
            />
          </Box>
        ) : null}
      </SectionCard>

      <Aviso mensaje={aviso} onClose={() => setAviso(null)} />
      <Aviso mensaje={error} severidad="error" onClose={() => setError(null)} />
    </>
  );
}
