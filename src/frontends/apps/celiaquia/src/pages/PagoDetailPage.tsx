import { useRef, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@mui/material/Button";
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
import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  PageHeader,
  SectionCard,
  Stack,
  StatCard,
  StateChip,
} from "@sisoc/ui";
import type { StateTone } from "@sisoc/ui";
import { descargarBlob, mensajeDeError } from "@sisoc/api";
import { api } from "../api";
import { Aviso, Cargando, ErrorPanel, TablaCargando } from "../componentes/Estados";

const tonePago: Record<string, StateTone> = {
  BORRADOR: "neutral",
  ENVIADO: "info",
  PROCESADO: "warning",
  VALIDADO: "success",
  CERRADO: "primary",
};

export function PagoDetailPage() {
  const { id } = useParams();
  const pagoId = Number(id);
  const queryClient = useQueryClient();
  const inputArchivo = useRef<HTMLInputElement>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pago = useQuery({
    queryKey: ["pago", pagoId],
    queryFn: () => api.pagos.obtener(pagoId),
    enabled: Number.isFinite(pagoId),
  });

  const nomina = useQuery({
    queryKey: ["pago", pagoId, "nomina"],
    queryFn: () => api.pagos.nomina(pagoId),
    enabled: Number.isFinite(pagoId),
  });

  const procesar = useMutation({
    mutationFn: (archivo: File) => api.pagos.procesarRespuesta(pagoId, archivo),
    onSuccess: () => {
      setAviso("Respuesta de Sintys procesada.");
      queryClient.invalidateQueries({ queryKey: ["pago", pagoId] });
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const exportar = useMutation({
    mutationFn: async () => {
      const blob = await api.pagos.exportarNomina(pagoId);
      descargarBlob(blob, `nomina_pago_${pagoId}.xlsx`);
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  if (pago.isPending) return <Cargando />;
  if (pago.isError) return <ErrorPanel error={pago.error} />;

  const p = pago.data;

  return (
    <>
      <PageHeader
        title={
          <Stack direction="row" spacing={1.5} alignItems="center">
            <span>
              Pago #{p.id} — {p.periodo}
            </span>
            <StateChip
              label={p.estado ?? "—"}
              tone={(p.estado && tonePago[p.estado]) ?? "neutral"}
            />
          </Stack>
        }
        crumbs={[
          { label: "Cupos", href: "/cupos" },
          { label: "Pagos", href: `/pagos/${p.provincia}` },
          { label: `Pago #${p.id}` },
        ]}
        actions={
          <>
            <Button
              size="small"
              variant="text"
              color="inherit"
              startIcon={<ArrowBackIcon />}
              component={RouterLink}
              to={`/pagos/${p.provincia_id}`}
            >
              Volver
            </Button>
            <Button
              size="small"
              variant="contained"
              color="success"
              startIcon={<DownloadIcon />}
              disabled={exportar.isPending}
              onClick={() => exportar.mutate()}
            >
              Exportar nómina
            </Button>
          </>
        }
      />

      <Stack spacing={3}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 4 }}>
            <StatCard
              label="Candidatos"
              value={p.total_candidatos}
              tone="primary"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <StatCard label="Validados" value={p.total_validados} tone="success" />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <StatCard label="Excluidos" value={p.total_excluidos} tone="error" />
          </Grid>
        </Grid>

        <SectionCard title="Subir respuesta de Sintys">
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            alignItems={{ sm: "center" }}
            justifyContent="space-between"
          >
            <Stack spacing={0.5}>
              <input
                ref={inputArchivo}
                type="file"
                accept=".xlsx,.xls"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) procesar.mutate(f);
                  e.target.value = "";
                }}
              />
              <Button
                variant="outlined"
                startIcon={<UploadFileIcon />}
                disabled={procesar.isPending}
                onClick={() => inputArchivo.current?.click()}
              >
                {procesar.isPending ? "Procesando…" : "Seleccionar archivo"}
              </Button>
              <Typography variant="caption" color="text.secondary">
                Se acepta el Excel devuelto por Sintys para el período {p.periodo}.
              </Typography>
            </Stack>
          </Stack>
        </SectionCard>

        <SectionCard
          title="Nómina validada"
          subheader={
            nomina.data ? `${nomina.data.count} registros` : "Cargando…"
          }
          disableGutters
        >
          {nomina.isPending ? <TablaCargando /> : null}
          {nomina.isSuccess ? (
            <TableContainer sx={{ overflowX: "auto" }}>
              <Table size="small" sx={{ minWidth: 798 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>CUIL</TableCell>
                    <TableCell>Nombre</TableCell>
                    <TableCell>Apellido</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Observación</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {nomina.data.results.map((r) => (
                    <TableRow key={r.id} hover>
                      <TableCell>{r.documento}</TableCell>
                      <TableCell>{r.nombre}</TableCell>
                      <TableCell>{r.apellido}</TableCell>
                      <TableCell>
                        <StateChip
                          label={r.estado ?? "—"}
                          tone={r.estado === "VALIDADO" ? "success" : "error"}
                        />
                      </TableCell>
                      <TableCell>{r.observacion || "—"}</TableCell>
                    </TableRow>
                  ))}

                  {nomina.data.results.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                        <Typography variant="body2" color="text.secondary">
                          Todavía no hay nómina validada.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : null}
                </TableBody>
              </Table>
            </TableContainer>
          ) : null}
        </SectionCard>
      </Stack>

      <Aviso mensaje={aviso} onClose={() => setAviso(null)} />
      <Aviso mensaje={error} severidad="error" onClose={() => setError(null)} />
    </>
  );
}
