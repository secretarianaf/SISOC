import type { NavSection } from "@sisoc/ui";

export const BASE = "/v2/celiaquia";

/**
 * Modulos muestra solo lo del modulo actual; Administracion y Tableros son
 * secciones de sistema y muestran siempre todo su contenido.
 */
export const secciones: NavSection[] = [
  {
    label: "Módulos",
    esModulos: true,
    items: [
      {
        label: "Celiaquía",
        children: [
          { label: "Expedientes", href: `${BASE}/expedientes` },
          { label: "Cupos por provincia", href: `${BASE}/cupos` },
        ],
      },
    ],
  },
  {
    label: "Administración",
    items: [
      { label: "Usuarios", href: `${BASE}/usuarios` },
      { label: "Auditoría", href: `${BASE}/auditoria` },
    ],
  },
  {
    label: "Tableros",
    items: [{ label: "Resumen general", href: `${BASE}/tableros` }],
  },
];
