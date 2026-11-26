import { Alert, CircularProgress } from "@mui/material";
import { statusPas } from "./api";

export function ErrorPas({ error }: { error: unknown }) {
  const status = statusPas(error);
  if (status === 401) {
    return <Alert severity="warning">Tu sesión venció. <a href={`/login/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`}>Iniciar sesión</a></Alert>;
  }
  return <Alert severity="error">{status === 403 ? "No tenés permiso para acceder a esta pantalla." :
    status === 404 ? "No encontramos el registro solicitado." : "No se pudo cargar la información de PAS."}</Alert>;
}

export function Cargando() {
  return <CircularProgress aria-label="Cargando información de PAS" size={28} />;
}

