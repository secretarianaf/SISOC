import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import BadgeIcon from "@mui/icons-material/Badge";
import { Stack } from "@sisoc/ui";
import { mensajeDeError } from "@sisoc/api";
import type { ValidacionRenaper as Comparacion } from "@sisoc/api";
import { api } from "../api";

/** Etiqueta legible de cada campo comparado. */
const etiqueta = (campo: string) =>
  campo.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

/**
 * Validación de un legajo contra RENAPER.
 *
 * Son dos pasos y no uno: primero se consulta y se muestra la comparación
 * contra lo que cargó la provincia, y recién después el técnico decide. Esa
 * separación es del back (`validar-renaper` no guarda nada) y acá se respeta:
 * confirmar sin ver la comparación sería firmar a ciegas.
 *
 * Las tres opciones no son simétricas: rechazar libera el cupo y saca al legajo
 * del padrón, así que se avisa antes de confirmar.
 */
export function ValidacionRenaper({
  legajoId,
  expedienteId,
  deshabilitado = false,
}: {
  legajoId: number;
  expedienteId: number;
  deshabilitado?: boolean;
}) {
  const queryClient = useQueryClient();
  const [comparacion, setComparacion] = useState<Comparacion | null>(null);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  const consultar = useMutation({
    mutationFn: () => api.legajos.validarRenaper(legajoId),
    onSuccess: (datos) => {
      setError("");
      setComparacion(datos);
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const confirmar = useMutation({
    mutationFn: (estado: "1" | "2" | "3") =>
      api.legajos.guardarValidacionRenaper(
        legajoId,
        estado,
        estado === "3" ? motivo : undefined,
      ),
    onSuccess: (r) => {
      setError("");
      setAviso(r.detail);
      setComparacion(null);
      setMotivo("");
      queryClient.invalidateQueries({
        queryKey: ["expediente", expedienteId, "legajos"],
      });
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const campos = comparacion
    ? [
        ...new Set([
          ...Object.keys(comparacion.datos_provincia ?? {}),
          ...Object.keys(comparacion.datos_renaper ?? {}),
        ]),
      ]
    : [];

  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Button
          size="small"
          variant="outlined"
          startIcon={<BadgeIcon />}
          disabled={deshabilitado || consultar.isPending}
          onClick={() => consultar.mutate()}
        >
          {consultar.isPending ? "Consultando…" : "Validar con RENAPER"}
        </Button>
      </Stack>

      {error ? (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      ) : null}
      {aviso ? (
        <Alert severity="success" onClose={() => setAviso("")}>
          {aviso}
        </Alert>
      ) : null}

      <Dialog
        open={Boolean(comparacion)}
        onClose={() => setComparacion(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {comparacion?.ciudadano_nombre} — {comparacion?.documento}
        </DialogTitle>
        <DialogContent dividers>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell width="34%">Campo</TableCell>
                <TableCell width="33%">Cargado</TableCell>
                <TableCell width="33%">RENAPER</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {campos.map((campo) => {
                const cargado = comparacion?.datos_provincia?.[campo] ?? "";
                const renaper = comparacion?.datos_renaper?.[campo] ?? "";
                const difiere =
                  String(cargado).trim().toLowerCase() !==
                  String(renaper).trim().toLowerCase();
                return (
                  <TableRow key={campo} hover>
                    <TableCell>{etiqueta(campo)}</TableCell>
                    <TableCell>{String(cargado) || "—"}</TableCell>
                    <TableCell
                      // Resaltar solo lo que difiere: es lo que hay que mirar.
                      sx={difiere ? { color: "warning.text" } : undefined}
                    >
                      {String(renaper) || "—"}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          <TextField
            fullWidth
            size="small"
            multiline
            minRows={2}
            sx={{ mt: 2 }}
            label="Motivo (solo si pedís subsanación)"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          <Typography variant="caption" color="text.secondary">
            Rechazar libera el cupo y saca al legajo del padrón.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setComparacion(null)}>Cerrar</Button>
          <Button
            color="warning"
            disabled={confirmar.isPending || !motivo.trim()}
            onClick={() => confirmar.mutate("3")}
          >
            Pedir subsanación
          </Button>
          <Button
            color="error"
            disabled={confirmar.isPending}
            onClick={() => confirmar.mutate("2")}
          >
            Datos incorrectos
          </Button>
          <Button
            variant="contained"
            disabled={confirmar.isPending}
            onClick={() => confirmar.mutate("1")}
          >
            Datos correctos
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
