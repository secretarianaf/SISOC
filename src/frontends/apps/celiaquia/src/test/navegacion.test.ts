import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { BASE, secciones } from "../navegacion";
import type { NavSection } from "@sisoc/ui";

/**
 * Contrato entre el Drawer y el router.
 *
 * Dos bugs reales que estos tests fijan:
 *
 * 1. Los `href` llevaban el basename (`/v2/celiaquia/expedientes`) y
 *    `BrowserRouter` lo volvia a anteponer, generando
 *    `/v2/celiaquia/v2/celiaquia/expedientes`.
 * 2. Esa URL no matcheaba ninguna ruta, caia en el comodin `*`, y el
 *    `<Navigate to="expedientes">` de ahi era **relativo**: cada rebote sumaba
 *    otro segmento. De ahi el `expedientes/expedientes/expedientes/...`.
 */

const app = readFileSync(resolve(__dirname, "../App.tsx"), "utf8");

/** Rutas declaradas en App.tsx, normalizadas con "/" adelante. */
const rutasDeclaradas = [...app.matchAll(/path="([^"]+)"/g)]
  .map((m) => m[1])
  .filter((p) => p !== "*")
  .map((p) => (p.startsWith("/") ? p : `/${p}`));

const enlaces = (items: NavSection["items"]): string[] =>
  items.flatMap((n) => [...(n.href ? [n.href] : []), ...enlaces(n.children ?? [])]);

const hrefs = secciones.flatMap((s) => enlaces(s.items));

describe("enlaces del sidebar", () => {
  it("no repiten el basename, porque lo antepone el router", () => {
    for (const href of hrefs) {
      expect(href.startsWith(BASE), `${href} repite ${BASE}`).toBe(false);
    }
  });

  it("son absolutos: uno relativo se concatena a la URL actual", () => {
    for (const href of hrefs) {
      expect(href.startsWith("/"), `${href} es relativo`).toBe(true);
    }
  });

  it("cada uno tiene una ruta declarada en App.tsx", () => {
    const sinRuta = hrefs.filter((href) => !rutasDeclaradas.includes(href));
    expect(sinRuta, `sin ruta: ${sinRuta.join(", ")}`).toEqual([]);
  });

  it("hay al menos un enlace, para que el test no pase por vacio", () => {
    expect(hrefs.length).toBeGreaterThan(0);
    expect(rutasDeclaradas).toContain("/expedientes");
  });
});

describe("redirecciones de App.tsx", () => {
  it("son absolutas: una relativa en el comodin acumula segmentos", () => {
    const relativas = [...app.matchAll(/<Navigate\s+to="([^"]+)"/g)]
      .map((m) => m[1])
      .filter((destino) => !destino.startsWith("/"));

    expect(relativas, `Navigate relativos: ${relativas.join(", ")}`).toEqual([]);
  });
});
