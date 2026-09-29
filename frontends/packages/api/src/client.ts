import axios from "axios";
import type { AxiosInstance, AxiosError } from "axios";

/**
 * Cliente HTTP de /v2/.
 *
 * Autenticacion por **sesion de Django en el mismo dominio**: no hay tokens en
 * el navegador. Por eso `withCredentials` y el header `X-CSRFToken` leido de la
 * cookie en todo metodo no seguro.
 */

const METODOS_SEGUROS = ["get", "head", "options", "trace"];

export const leerCookie = (nombre: string): string | null => {
  const partes = document.cookie ? document.cookie.split("; ") : [];
  for (const parte of partes) {
    const [clave, ...resto] = parte.split("=");
    if (clave === nombre) return decodeURIComponent(resto.join("="));
  }
  return null;
};

/** Navegacion completa al login, conservando a donde queria ir el usuario. */
export const redirigirALogin = () => {
  const destino = encodeURIComponent(
    window.location.pathname + window.location.search,
  );
  window.location.assign(`/login/?next=${destino}`);
};

export class SinPermiso extends Error {
  constructor(mensaje = "No tiene permisos para esta operación.") {
    super(mensaje);
    this.name = "SinPermiso";
  }
}

/**
 * Mensaje mostrable a partir de un error de DRF.
 *
 * DRF usa `{"detail": "..."}` para errores generales y `{"campo": ["msg"]}`
 * para validaciones. No se inventan otros formatos, asi que alcanza con
 * aplanar lo que venga.
 */
export const mensajeDeError = (error: unknown): string => {
  const axiosError = error as AxiosError<Record<string, unknown>>;
  const data = axiosError?.response?.data;
  if (!data) return "No se pudo completar la operación.";
  if (typeof data === "string") return data;

  const partes: string[] = [];
  for (const [campo, valor] of Object.entries(data)) {
    const texto = Array.isArray(valor) ? valor.join(" ") : String(valor);
    partes.push(campo === "detail" ? texto : `${campo}: ${texto}`);
  }
  return partes.join(" · ") || "No se pudo completar la operación.";
};

export const crearCliente = (baseURL: string): AxiosInstance => {
  const cliente = axios.create({ baseURL, withCredentials: true });

  cliente.interceptors.request.use((config) => {
    const metodo = (config.method ?? "get").toLowerCase();
    if (!METODOS_SEGUROS.includes(metodo)) {
      const csrf = leerCookie("csrftoken");
      if (csrf) config.headers.set("X-CSRFToken", csrf);
    }
    return config;
  });

  cliente.interceptors.response.use(
    (respuesta) => respuesta,
    (error: AxiosError) => {
      const status = error.response?.status;
      // 401: no hay sesion -> al login. 403 con sesion activa NO redirige,
      // para no entrar en un loop: lo maneja la pantalla "sin permiso".
      if (status === 401) {
        redirigirALogin();
      }
      if (status === 403) {
        return Promise.reject(new SinPermiso(mensajeDeError(error)));
      }
      return Promise.reject(error);
    },
  );

  return cliente;
};
