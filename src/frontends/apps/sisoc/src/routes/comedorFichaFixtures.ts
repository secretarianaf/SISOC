import type { Relaciones } from "./comedorFichaRelaciones";
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
  },
  colaboradores: {
    agregar: "/comedores/7/colaboradores/crear/",
    items: [
      { id: 5, nombre: "Gomez, Ana", dni: "28999111", cuil: "27289991116", sexo: "Femenino", genero: "Mujer", telefono: "11 5555", alta: "26/03/2026", baja: "-", actividades: "Compras,Cocina",
        editar: "/comedores/7/colaboradores/5/editar/", eliminar: { url: "/api/web/comedores/colaboradores/comedor/7/5/eliminar/", deshabilitado: false } },
      { id: 6, nombre: "Perez, Beto", dni: "30111222", cuil: "-", sexo: "-", genero: "No declara", telefono: "-", alta: "01/02/2026", baja: "01/04/2026", actividades: "-",
        editar: null, eliminar: { url: "/api/web/comedores/colaboradores/comedor/7/6/eliminar/", deshabilitado: true } },
    ],
    resultados: "Se encontraron 2 resultados.",
  },
  interacciones: { labels: ["Mar 2026", "May 2026"], values: [2, 1] },
  capacitaciones: {
    items: [
      { id: 11, capacitacion: "Seguridad en la Cocina - Alimentar Comunidad", estado: "presentado", archivo: "http://testserver/media/c.pdf", observacion: "-", revisar: "/api/web/comedores/comedores/7/capacitaciones/11/estado/" },
      { id: 12, capacitacion: "Creación de Usuario en Plataforma Alimentar Comunidad", estado: "sin_presentar", archivo: null, observacion: "-", revisar: "/api/web/comedores/comedores/7/capacitaciones/12/estado/" },
      { id: 13, capacitacion: "Pautas de Higiene - Alimentar Comunidad", estado: "rechazado", archivo: null, observacion: "Ilegible", revisar: "/api/web/comedores/comedores/7/capacitaciones/13/estado/" },
    ],
  }, ...over,
});

/** Synthetic nómina / interventions / observations keys of the ficha API for the unit tests. */
export const relacionesFixture = (over: Partial<Relaciones> = {}): Relaciones => ({
  nomina: { ver: "/comedores/7/admision/3/nomina/", pendiente: true, importar: "/comedores/7/admision/3/nomina/importar/", directa: false, identidad_reservada: null,
    cifras: { asistentes: "10", hombres: "4", mujeres: "6", menores: "2", espera: "1", bajas: "0" } },
  intervenciones: {
    encabezados: ["Fecha", "Intervención", "Sub intervención", "Doc. adjunta", "Destinatario", "Usuario creador", "Acciones"],
    filas: [[{ texto: "12/03/2026" }, { texto: "Entrevista" }, { texto: "-" }, { insignia: "bg-secondary", texto: "No" }, { texto: "Titular" }, { texto: "Ana Gómez" },
      { acciones: [{ url: "/comedores/intervencion/9", clase: "btn btn-sm btn-primary", nueva_ventana: false, label: "Ver" }, { url: "/comedores/7/intervencion/9/eliminar", clase: "btn btn-sm btn-danger", nueva_ventana: false, label: "Eliminar" }] }]],
    paginacion: { param: "intervenciones_page", anterior: null, siguiente: 2, paginas: [{ numero: 1, activa: true }, { numero: 2, activa: false }] }, resultados: 12,
    convenios: [{ id: 3, texto: "C-1", cerrada: false, seleccionada: true }, { id: 4, texto: "Admisión #4", cerrada: true, seleccionada: false }],
    modal: {
      crear: "/api/web/comedores/intervenciones/comedor/7/crear/", formulario: "/comedores/intervencion/crear/7", subestados: "/api/web/comedores/intervenciones/subestados/", next: "/comedores/7?admision_id=3", admision_id: 3,
      fecha: { id: "id_fecha", label: "Fecha", required: true },
      tipo_intervencion: { id: "id_tipo_intervencion", label: "Tipo de Intervención", required: true, options: [{ value: "", label: "---------" }, { value: "1", label: "Entrevista" }] },
      subintervencion: { id: "id_subintervencion", label: "Subtipo de Intervención", required: false, options: [{ value: "", label: "---------" }] },
      destinatario: { id: "id_destinatario", label: "Destinatario", required: true, options: [{ value: "", label: "---------" }, { value: "2", label: "Titular" }] },
      forma_contacto: { id: "id_forma_contacto", label: "Forma de Contacto", required: true, options: [{ value: "", label: "---------" }, { value: "3", label: "Telefonico" }] },
      observaciones: { id: "id_observaciones", label: "Descripción", required: false }, tiene_documentacion: { id: "id_tiene_documentacion", label: "Documentación Adjunta" },
      documentacion: { id: "id_documentacion", label: "Cargar Documentación" },
    },
  },
  observaciones: {
    encabezados: ["Fecha", "Observador", "Observación", "Acciones"],
    filas: [[{ texto: "01/10/2026 10:30" }, { texto: "Ana" }, { texto: "Todo bien" }, { acciones: [{ url: "/comedores/observacion/5", clase: "btn btn-sm btn-primary", nueva_ventana: false, label: "Ver" }] }]],
    paginacion: null, resultados: 1,
    modal: { crear: "/api/web/comedores/observaciones/comedor/7/crear/", formulario: "/comedores/7/observacion/crear", next: "/comedores/7", campo: { id: "id_observacion", label: "Observación", required: true, rows: 4, placeholder: "Describa la observación" } },
  }, ...over,
});
