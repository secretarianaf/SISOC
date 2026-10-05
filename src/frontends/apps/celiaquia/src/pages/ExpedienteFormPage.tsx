import { useRef, useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { PageHeader, SectionCard, Stack } from "@sisoc/ui";
import { mensajeDeError } from "@sisoc/api";
import type { PreviewExcel } from "@sisoc/api";
import { api } from "../api";
import { Aviso, ErrorPanel } from "../componentes/Estados";

export function ExpedienteFormPage() {
  const navigate = useNavigate();
  const inputArchivo = useRef<HTMLInputElement>(null);

  const [numero, setNumero] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewExcel | null>(null);
  const [error, setError] = useState<string | null>(null);

  const previsualizar = useMutation({
    mutationFn: (f: File) => api.expedientes.previewExcel(f, 50),
    onSuccess: setPreview,
    onError: (e) => setError(mensajeDeError(e)),
  });

  const guardar = useMutation({
    mutationFn: () =>
      api.expedientes.crear({
        numero_expediente: numero || undefined,
        observaciones: observaciones || undefined,
        excel_masivo: archivo,
      }),
    onSuccess: (expediente) => navigate(`/expedientes/${expediente.id}`),
    onError: (e) => setError(mensajeDeError(e)),
  });

  return (
    <>
      <PageHeader
        title="Crear expediente"
        crumbs={[{ label: "Expedientes", href: "/expedientes" }, { label: "Nuevo" }]}
      />

      <Box sx={{ maxWidth: 900, mx: "auto" }}>
        <SectionCard title="Datos del expediente">
          <Stack spacing={2.5}>
            <TextField
              label="Número de expediente"
              placeholder="EX-2026-00000000"
              value={numero}
              onChange={(e) => setNumero(e.target.value)}
              fullWidth
            />
            <TextField
              label="Observaciones"
              multiline
              minRows={3}
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
              fullWidth
            />

            <Box>
              <Typography variant="captionBold" color="text.secondary">
                Excel masivo
              </Typography>
              <input
                ref={inputArchivo}
                type="file"
                accept=".xlsx,.xls"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0] ?? null;
                  setArchivo(f);
                  setPreview(null);
                }}
              />
              <Button
                variant="outlined"
                startIcon={<UploadFileIcon />}
                sx={{ mt: 1, display: "block" }}
                onClick={() => inputArchivo.current?.click()}
              >
                {archivo ? "Cambiar archivo" : "Seleccionar archivo"}
              </Button>
              <Typography variant="caption" color="text.secondary">
                {archivo ? archivo.name : "Formatos aceptados: .xlsx, .xls"}
              </Typography>
            </Box>

            <Divider />

            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1.5}
              justifyContent="space-between"
            >
              <Button
                variant="outlined"
                disabled={!archivo || previsualizar.isPending}
                onClick={() => archivo && previsualizar.mutate(archivo)}
              >
                {previsualizar.isPending
                  ? "Leyendo…"
                  : "Previsualizar Excel"}
              </Button>

              <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  color="success"
                  disabled={guardar.isPending}
                  onClick={() => guardar.mutate()}
                >
                  {guardar.isPending ? "Guardando…" : "Guardar"}
                </Button>
                <Button
                  variant="text"
                  color="inherit"
                  component={RouterLink}
                  to="/expedientes"
                >
                  Cancelar
                </Button>
              </Stack>
            </Stack>

            {previsualizar.isError ? (
              <ErrorPanel error={previsualizar.error} />
            ) : null}
          </Stack>
        </SectionCard>

        {preview ? (
          <Box sx={{ mt: 3 }}>
            <SectionCard
              title="Vista previa del Excel"
              subheader={`${preview.rows.length} filas leídas`}
              disableGutters
            >
              <TableContainer sx={{ overflowX: "auto", maxHeight: 420 }}>
                <Table size="small" stickyHeader sx={{ minWidth: 798 }}>
                  <TableHead>
                    <TableRow>
                      {preview.headers.map((h) => (
                        <TableCell key={h}>
                          {h.charAt(0).toUpperCase() +
                            h.slice(1).replaceAll("_", " ")}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {preview.rows.map((row, i) => (
                      <TableRow key={i} hover>
                        {preview.headers.map((h) => (
                          <TableCell key={h}>{String(row[h] ?? "")}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </SectionCard>
          </Box>
        ) : null}
      </Box>

      <Aviso mensaje={error} severidad="error" onClose={() => setError(null)} />
    </>
  );
}
