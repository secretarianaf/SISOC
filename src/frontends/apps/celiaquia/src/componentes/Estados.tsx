import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Snackbar from "@mui/material/Snackbar";
import { mensajeDeError, SinPermiso } from "@sisoc/api";

/** Placeholder de una tabla mientras carga, con la forma que va a tener. */
export function TablaCargando({ filas = 5 }: { filas?: number }) {
  return (
    <Box sx={{ p: 2 }}>
      <Stack spacing={1}>
        {Array.from({ length: filas }).map((_, i) => (
          <Skeleton key={i} variant="rounded" height={36} />
        ))}
      </Stack>
    </Box>
  );
}

export function Cargando() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
      <CircularProgress />
    </Box>
  );
}

/**
 * Error de carga. Un 403 no manda al login (eso haria un loop): se muestra
 * como "sin permiso", que es lo que realmente paso.
 */
export function ErrorPanel({ error }: { error: unknown }) {
  const esSinPermiso = error instanceof SinPermiso;
  return (
    <Alert severity={esSinPermiso ? "warning" : "error"} sx={{ my: 2 }}>
      <AlertTitle>
        {esSinPermiso ? "Sin permiso" : "No se pudieron cargar los datos"}
      </AlertTitle>
      {esSinPermiso ? error.message : mensajeDeError(error)}
    </Alert>
  );
}

export function Aviso({
  mensaje,
  severidad = "success",
  onClose,
}: {
  mensaje: string | null;
  severidad?: "success" | "error" | "info" | "warning";
  onClose: () => void;
}) {
  return (
    <Snackbar
      open={Boolean(mensaje)}
      autoHideDuration={5000}
      onClose={onClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
    >
      <Alert severity={severidad} onClose={onClose} variant="filled">
        {mensaje}
      </Alert>
    </Snackbar>
  );
}
