import { celiaquiaApi, crearCliente } from "@sisoc/api";

/**
 * Instancia unica del cliente. La API del modulo vive en `/api/celiaquia/`,
 * en el mismo dominio que el front, que es lo que permite usar la sesion de
 * Django sin tokens.
 */
export const http = crearCliente("/api/celiaquia/");
export const api = celiaquiaApi(http);
