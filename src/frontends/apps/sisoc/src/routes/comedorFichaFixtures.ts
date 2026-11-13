import type { Bloques } from "./comedorFichaBloques";
import type { Tablero } from "./comedorFichaTablero";

/** Synthetic `tablero` block of the ficha API for the unit tests. */
export const tableroFixture = (over: Partial<Tablero> = {}): Tablero => ({
  timeline: { admision: { clase: "step active", circulo: "1", completada: false, fecha: "05/11/2026" }, conector: "connector", ejecucion: { clase: "step", circulo: "2" }, rendicion: { circulo: "3" } },
  resumen: [
    { icon: "bi bi-cup-hot", valor: "120", label: "Prestaciones mensuales" }, { icon: "bi bi-person-walking", valor: "2", label: "Actividades Comunitarias" },
    { icon: "bi bi-clipboard-check", valor: "1", label: "Acompañamiento Territorial" }, { icon: "bi bi-graph-up-arrow", valor: "1° / 2", label: "Numero de Convenio" },
  ],
  grafico: [["Sin dato", 5], ["0-13 años", 12.5], ["14-17 años", 0], ["18-49 años", 60], ["50-65 años", 15], ["+66 años", 7.5]].map(([label, valor]) => ({ label: String(label), valor: Number(valor) })),
  detalles: { tipo: "admision", titulo: "Detalles de Admisión", filas: [{ label: "Fecha", value: "05/11/2026" }, { label: "Número de expediente", value: "EX-1", mayusculas: true }], accion: { label: "Ver detalles", url: "/comedores/7/admision/3/detalle/" } },
  responsable_tarjeta: null, ...over,
});

/** Synthetic lower blocks (top-level keys) of the ficha API for the unit tests. */
export const bloquesFixture = (over: Partial<Bloques> = {}): Bloques => ({
  certificaciones: {
    historial: "/comedores/7/certificaciones-prestaciones/",
    items: [
      { id: 2, periodo: "10/2026", usuario: "Ana Gómez", conforme: true, creado: "05/11/2026 10:30", pdf: "/comedores/7/certificaciones-prestaciones/2/pdf/" },
      { id: 1, periodo: "09/2026", usuario: "-", conforme: false, creado: "05/10/2026 09:00", pdf: null },
    ],
  }, ...over,
});
