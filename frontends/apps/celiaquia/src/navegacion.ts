import type { NavSection } from "@sisoc/ui";

/**
 * Prefijo con el que Django publica esta app. Lo consume `BrowserRouter` como
 * `basename`.
 *
 * **Los href de abajo NO lo llevan**: React Router antepone el basename solo,
 * y repetirlo generaba `/v2/celiaquia/v2/celiaquia/expedientes`.
 */
export const BASE = "/v2/celiaquia";

/**
 * Secciones del Drawer.
 *
 * Cada `href` tiene que corresponder a una ruta declarada en `App.tsx`. Lo
 * verifica `src/test/navegacion.test.ts`: un link sin ruta caia en el comodin
 * `*`, que redirige a expedientes, y daba la sensacion de que el menu "no
 * hacia nada".
 *
 * Mientras la API no exponga el contexto del usuario con sesion, esto es fijo
 * (ver frontend_v2.md, seccion 5).
 */
export const secciones: NavSection[] = [
  {
    label: "Módulos",
    esModulos: true,
    items: [
      {
        label: "Celiaquía",
        children: [
          { label: "Expedientes", href: "/expedientes" },
          { label: "Cupos por provincia", href: "/cupos" },
        ],
      },
    ],
  },
];
