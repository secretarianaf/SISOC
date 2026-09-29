import type { components } from "./generated";

type Schema = components["schemas"];

export type Itinerario = Schema["Itinerario"];
export type Jornada = Schema["Jornada"];
export type Sede = Schema["Sede"];
export type Session = Schema["Session"];
export type Options = Schema["Options"];
export type FormField = Schema["FormField"];
export type FormSchema = Schema["FormSchema"];
export type Page<T> = Omit<Schema["ItinerarioPage"], "results"> & { results: T[] };

export type Registro = Schema["Registro"];
export type Laboratorio = Schema["Laboratorio"];
