import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import { PageHeader } from "@sisoc/ui";

/**
 * Pantalla de 403 con sesion activa. No redirige al login: eso haria un loop,
 * porque el usuario esta logueado, lo que le falta es el permiso.
 */
export function SinPermisoPage() {
  return (
    <>
      <PageHeader title="Sin permiso" />
      <Alert severity="warning">
        <AlertTitle>No tenés permiso para ver esta sección</AlertTitle>
        Si creés que deberías tenerlo, pedíselo a quien administra los permisos
        de Celiaquía.
      </Alert>
    </>
  );
}
