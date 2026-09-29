export {
  crearCliente,
  leerCookie,
  mensajeDeError,
  redirigirALogin,
  SinPermiso,
} from "./client";
export { celiaquiaApi } from "./celiaquia";
export type { CeliaquiaApi } from "./celiaquia";
export * from "./tipos";

/** Descarga un blob que devolvio la API con el nombre indicado. */
export const descargarBlob = (blob: Blob, nombre: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};
