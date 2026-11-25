import type { FichaExtra } from "./ciudadano360Ficha";

/** The JSON of `ciudadanos.web_ficha.proyectar_ficha` for a ciudadano with every section filled. */
export const fichaExtra = (over: Partial<FichaExtra> = {}): FichaExtra => ({
  identidad: { mostrar: false, sin_dni: false, no_validado: false, requiere_revision: false, motivo_texto: "", descripcion_texto: "" },
  acciones: { historial_url: null, editar_url: "/ciudadanos/editar/7", eliminar_url: "/ciudadanos/eliminar/7", familiar_nuevo_url: "/ciudadanos/7/familiares/nuevo", marcar_revisado_url: null },
  datos: {
    cuil_cuit: "-", apellido: "Aporte", nombre: "Ana", tipo_documento: "DNI", numero_documento: "30111222", pais_emisor: null, provincia: "-", municipio: "-",
    localidad: "-", calle_altura: "Mitre 123", codigo_postal: "-", fecha_nacimiento: "17/05/1990", edad: "36", genero: "F", estado_civil: "-", nacionalidad: "-",
    telefono: "1155550000", telefono_alternativo: "-", email: "-", fecha_actualizacion: "12/11/2026 15:00", origen_dato: "Carga manual",
  },
  mapa: null, foto_url: null, familia: [],
  historial: { labels: ["Mar"], auh: [10], prestacion: [0], centro_familia: [0], comedor: [2.5] },
  interacciones: [], observaciones: "", messages: [], ...over,
});
