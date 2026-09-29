import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Pagination from "@mui/material/Pagination";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import InboxIcon from "@mui/icons-material/MoveToInbox";
import SettingsIcon from "@mui/icons-material/Settings";
import VisibilityIcon from "@mui/icons-material/Visibility";
import {
  FilterChipGroup,
  PageHeader,
  SearchField,
  SectionCard,
  Stack,
  StateChip,
  toneExpediente,
} from "@sisoc/ui";
import { mensajeDeError } from "@sisoc/api";
import { api } from "../api";
import { Aviso, ErrorPanel, TablaCargando } from "../componentes/Estados";

const FILTROS = [
  { value: "", label: "Todos" },
  { value: "CREADO", label: "Creados" },
  { value: "EN_ESPERA", label: "En espera" },
  { value: "CONFIRMACION_DE_ENVIO", label: "Por recepcionar" },
  { value: "ASIGNADO", label: "Asignados" },
  { value: "CRUCE_FINALIZADO", label: "Cruce finalizado" },
];

export function ExpedienteListPage() {
  const queryClient = useQueryClient();
  const [estado, setEstado] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [page, setPage] = useState(1);
  const [aviso, setAviso] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const consulta = useQuery({
    queryKey: ["expedientes", { estado, busqueda, page }],
    queryFn: () =>
      api.expedientes.listar({
        estado: estado || undefined,
        numero_expediente: busqueda || undefined,
        page,
      }),
  });

  /** Las transiciones comparten el mismo manejo: avisar y recargar la lista. */
  const accion = useMutation({
    mutationFn: ({
      id,
      tipo,
    }: {
      id: number;
      tipo: "procesar" | "confirmar" | "recepcionar";
    }) => {
      if (tipo === "procesar") return api.expedientes.procesar(id);
      if (tipo === "confirmar") return api.expedientes.confirmarEnvio(id);
      return api.expedientes.recepcionar(id);
    },
    onSuccess: (_data, variables) => {
      setAviso(
        variables.tipo === "procesar"
          ? "Expediente procesado."
          : variables.tipo === "confirmar"
            ? "Envío confirmado."
            : "Expediente recepcionado.",
      );
      queryClient.invalidateQueries({ queryKey: ["expedientes"] });
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const filas = consulta.data?.results ?? [];
  const totalPaginas = Math.max(1, Math.ceil((consulta.data?.count ?? 0) / 20));

  return (
    <>
      <PageHeader
        title="Expedientes de Celiaquía"
        crumbs={[{ label: "Expedientes" }, { label: "Listar" }]}
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            component={RouterLink}
            to="/expedientes/nuevo"
          >
            Nuevo expediente
          </Button>
        }
      />

      <SectionCard
        title="Listado"
        subheader={
          consulta.data ? `${consulta.data.count} expedientes` : "Cargando…"
        }
        action={
          <SearchField
            value={busqueda}
            onChange={(e) => {
              setBusqueda(e.target.value);
              setPage(1);
            }}
            placeholder="Buscar por número de expediente"
          />
        }
        disableGutters
      >
        <Box sx={{ px: 2, py: 1.5 }}>
          <FilterChipGroup
            options={FILTROS}
            value={estado}
            onChange={(v) => {
              setEstado(v);
              setPage(1);
            }}
          />
        </Box>

        {consulta.isPending ? <TablaCargando /> : null}
        {consulta.isError ? (
          <Box sx={{ px: 2 }}>
            <ErrorPanel error={consulta.error} />
          </Box>
        ) : null}

        {consulta.isSuccess ? (
          <TableContainer sx={{ overflowX: "auto" }}>
            <Table sx={{ minWidth: 900 }} size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Número de expediente</TableCell>
                  <TableCell>Fecha creación</TableCell>
                  <TableCell>Provincia</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell align="right">Legajos</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filas.map((e) => {
                  const nombreEstado = e.estado?.nombre ?? "";
                  return (
                    <TableRow key={e.id} hover>
                      <TableCell>{e.id}</TableCell>
                      <TableCell>{e.numero_expediente ?? "—"}</TableCell>
                      <TableCell>
                        {new Date(e.fecha_creacion).toLocaleString("es-AR")}
                      </TableCell>
                      <TableCell>{e.provincia ?? "—"}</TableCell>
                      <TableCell>
                        <StateChip
                          label={e.estado?.display_name ?? nombreEstado ?? "—"}
                          tone={toneExpediente(nombreEstado)}
                        />
                      </TableCell>
                      <TableCell align="right">
                        {e.legajos_total ?? 0}
                      </TableCell>
                      <TableCell align="right">
                        <Stack
                          direction="row"
                          spacing={0.5}
                          justifyContent="flex-end"
                        >
                          <Tooltip title="Ver detalle">
                            <IconButton
                              size="small"
                              color="primary"
                              component={RouterLink}
                              to={`/expedientes/${e.id}`}
                            >
                              <VisibilityIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>

                          {nombreEstado === "CREADO" ? (
                            <Tooltip title="Procesar expediente">
                              <IconButton
                                size="small"
                                disabled={accion.isPending}
                                onClick={() =>
                                  accion.mutate({ id: e.id, tipo: "procesar" })
                                }
                              >
                                <SettingsIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : null}

                          {nombreEstado === "EN_ESPERA" ? (
                            <Tooltip title="Confirmar envío">
                              <IconButton
                                size="small"
                                color="success"
                                disabled={accion.isPending}
                                onClick={() =>
                                  accion.mutate({ id: e.id, tipo: "confirmar" })
                                }
                              >
                                <CheckCircleIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : null}

                          {nombreEstado === "CONFIRMACION_DE_ENVIO" ? (
                            <Tooltip title="Recepcionar expediente">
                              <IconButton
                                size="small"
                                disabled={accion.isPending}
                                onClick={() =>
                                  accion.mutate({
                                    id: e.id,
                                    tipo: "recepcionar",
                                  })
                                }
                              >
                                <InboxIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : null}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })}

                {filas.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No hay expedientes que coincidan con el filtro.
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
      <Aviso
        mensaje={error}
        severidad="error"
        onClose={() => setError(null)}
      />
    </>
  );
}
