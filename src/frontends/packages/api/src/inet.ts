import { crearCliente } from "./client";
import type { components } from "./inet.generated";

export type InetItem = components["schemas"]["InetItem"];
export type InetPage = components["schemas"]["InetPage"];
export type InetSession = components["schemas"]["InetSession"];
export type InetForm = components["schemas"]["InetForm"];
export type InetField = components["schemas"]["InetFormField"];
export type InetOption = components["schemas"]["InetOption"];
export type InetOptionsPage = components["schemas"]["InetOptionsPage"];
export type InetFormInput = components["schemas"]["InetFormInput"];
export type InetAttendance = components["schemas"]["InetAsistencia"];
export type InetCitizenPage = components["schemas"]["InetCiudadanoPage"];
export type InetEnrollmentInput = components["schemas"]["InetInscripcionInput"];
export type InetSchedule = components["schemas"]["InetHorario"];
export type InetDeletePreview = components["schemas"]["InetDeletePreview"];

export const inetClient = crearCliente("/api/inet/");
export async function inetGet<T>(path: string): Promise<T> {
  return (await inetClient.get<T>(path)).data;
}
