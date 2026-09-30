import { useRef, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@mui/material/Button";
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
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DownloadIcon from "@mui/icons-material/Download";
import HistoryIcon from "@mui/icons-material/History";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  PageHeader,
  SectionCard,
  Stack,
  StateChip,
  toneExpediente,
} from "@sisoc/ui";
import { descargarBlob, mensajeDeError } from "@sisoc/api";
import { api } from "../api";
import { Aviso, Cargando, ErrorPanel } from "../componentes/Estados";
import { LegajosTable } from "../componentes/LegajosTable";
import type { RevisionPedida } from "../componentes/LegajosTable";
import { RegistrosErroneos } from "../componentes/RegistrosErroneos";

function Dato({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Stack direction="row" spacing={1} sx={{ py: 0.5 }}>
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 168 }}>
        {label}
      </Typography>
      <Typography variant="body2" component="div">
        {children}
      </Typography>
    </Stack>
  );
}

export function ExpedienteDetailPage() {
  const { id } = useParams();
  const expedienteId = Number(id);
  const queryClient = useQueryClient();
  const inputCruce = useRef<HTMLInputElement>(null);

  const [aviso, setAviso] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modalHistorial, setModalHistorial] = useState(false);

  const expediente = useQuery({
    queryKey: ["expediente", expedienteId],
    queryFn: () => api.expedientes.obtener(expedienteId),
    enabled: Number.isFinite(expedienteId),
  });

  const legajos = useQuery({
    queryKey: ["expediente", expedienteId, "legajos"],
    queryFn: () => api.expedientes.legajos(expedienteId),
    enabled: Number.isFinite(expedienteId),
  });

  const registros = useQuery({
    queryKey: ["expediente", expedienteId, "registros-erroneos"],
    queryFn: () => api.expedientes.registrosErroneos(expedienteId),
    enabled: Number.isFinite(expedienteId),
  });

  const historial = useQuery({
    queryKey: ["expediente", expedienteId, "historial"],
    queryFn: () => api.expedientes.historialEstados(expedienteId),
    enabled: modalHistorial,
  });

  const refrescar = () => {
    queryClient.invalidateQueries({ queryKey: ["expediente", expedienteId] });
  };

  const revisar = useMutation({
    mutationFn: (pedido: RevisionPedida) =>
      api.legajos.revisar(pedido.legajoId, {
        accion: pedido.accion,
        texto_libre: pedido.texto_libre,
      }),
    onSuccess: (_data, pedido) => {
      setAviso(
        pedido.accion === "ELIMINAR"
          ? "Legajo eliminado."
          : `Legajo ${pedido.accion.toLowerCase()}.`,
      );
      refrescar();
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const subirCruce = useMutation({
    mutationFn: (archivo: File) =>
      api.expedientes.subirCruce(expedienteId, archivo),
    onSuccess: () => {
      setAviso("Cruce procesado.");
      refrescar();
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const descargar = useMutation({
    mutationFn: async (tipo: "sintys" | "padron") => {
      const blob =
        tipo === "sintys"
          ? await api.expedientes.nominaSintys(expedienteId)
          : await api.expedientes.padronFinal(expedienteId);
      descargarBlob(
        blob,
        tipo === "sintys"
          ? `nomina_sintys_${expedienteId}.xlsx`
          : `padron_final_${expedienteId}.xlsx`,
      );
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  if (expediente.isPending) return <Cargando />;
  if (expediente.isError) return <ErrorPanel error={expediente.error} />;

  const exp = expediente.data;
  const nombreEstado = exp.estado;

  return (
    <>
      <PageHeader
        title={
          <Stack direction="row" spacing={1.5} alignItems="center">
            <span>Expediente #{exp.id}</span>
            <StateChip
              label={nombreEstado}
              tone={toneExpediente(nombreEstado)}
            />
          </Stack>
        }
        crumbs={[
          { label: "Expedientes", href: "/expedientes" },
          { label: `Expediente #${exp.id}` },
        ]}
        actions={
          <>
            <Button
              size="small"
              variant="text"
              color="inherit"
              startIcon={<ArrowBackIcon />}
              component={RouterLink}
              to="/expedientes"
            >
              Volver
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<DownloadIcon />}
              disabled={descargar.isPending}
              onClick={() => descargar.mutate("sintys")}
            >
              Nómina Sintys
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<DownloadIcon />}
              disabled={descargar.isPending}
              onClick={() => descargar.mutate("padron")}
            >
              Padrón final
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<HistoryIcon />}
              onClick={() => setModalHistorial(true)}
            >
              Historial
            </Button>
            <input
              ref={inputCruce}
              type="file"
              accept=".xlsx,.xls"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) subirCruce.mutate(f);
                e.target.value = "";
              }}
            />
            <Button
              size="small"
              variant="contained"
              startIcon={<UploadFileIcon />}
              disabled={subirCruce.isPending}
              onClick={() => inputCruce.current?.click()}
            >
              {subirCruce.isPending ? "Procesando…" : "Subir Excel de cruce"}
            </Button>
          </>
        }
      />

      <Stack spacing={3}>
        <SectionCard title="Detalle del expediente">
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Dato label="ID del expediente">{exp.id}</Dato>
              <Dato label="Número de expediente">
                {exp.numero_expediente ?? "—"}
              </Dato>
              <Dato label="Estado">{nombreEstado}</Dato>
              <Dato label="Fecha de creación">
                {new Date(exp.fecha_creacion).toLocaleDateString("es-AR")}
              </Dato>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Dato label="Provincia">{exp.provincia ?? "—"}</Dato>
              <Dato label="Legajos">{exp.legajos_total ?? 0}</Dato>
              <Dato label="Observaciones">{exp.observaciones || "—"}</Dato>
            </Grid>
          </Grid>
        </SectionCard>

        <LegajosTable
          legajos={legajos.data?.results ?? []}
          cargando={legajos.isPending}
          onRevisar={(pedido) => revisar.mutate(pedido)}
          revisando={revisar.isPending}
        />

        {registros.data ? (
          <RegistrosErroneos
            registros={registros.data}
            expedienteId={expedienteId}
          />
        ) : null}
      </Stack>

      <Dialog
        open={modalHistorial}
        onClose={() => setModalHistorial(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Historial de estados</DialogTitle>
        <DialogContent dividers sx={{ p: 0 }}>
          {historial.isPending ? <Cargando /> : null}
          {historial.isSuccess ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Fecha</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Usuario</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {historial.data.map((h) => (
                    <TableRow key={h.id} hover>
                      <TableCell>
                        {new Date(h.fecha).toLocaleString("es-AR")}
                      </TableCell>
                      <TableCell>{h.estado}</TableCell>
                      <TableCell>{h.usuario?.nombre ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModalHistorial(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>

      <Aviso mensaje={aviso} onClose={() => setAviso(null)} />
      <Aviso mensaje={error} severidad="error" onClose={() => setError(null)} />
    </>
  );
}
