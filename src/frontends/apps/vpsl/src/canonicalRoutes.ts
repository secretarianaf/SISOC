import { generatePath, matchPath } from "react-router-dom";

export const V2_ROOT = "/v2/vpsl/";
export const CANONICAL_ROOT = "/ver-para-ser-libre/";

const paths = [
  ["/", "/"],
  ["/sedes", "/sedes"],
  ["/crear", "/itinerarios/nuevo"],
  ["/:id", "/itinerarios/:id"],
  ["/:id/editar", "/forms/itinerario-edit/:id"],
  ["/:id/subsanar", "/forms/itinerario-subsanar/:id"],
  ["/sedes/crear", "/forms/sede-create/0"],
  ["/sedes/:id/editar", "/forms/sede-edit/:id"],
  ["/:id/jornadas/crear", "/forms/jornada-create/:id"],
  ["/jornadas/:id", "/jornadas/:id"],
  ["/jornadas/:id/editar", "/forms/jornada-edit/:id"],
  ["/jornadas/:id/checklist/crear", "/forms/checklist/:id"],
  ["/jornadas/:id/registros/crear", "/forms/registro-create/:id"],
  ["/registros/:id/editar", "/forms/registro-edit/:id"],
  ["/laboratorio/:id/editar", "/forms/laboratorio/:id"],
  ["/jornadas/:id/cierre/crear", "/forms/cierre/:id"],
  ["/:id/eliminar", "/delete/eliminar-itinerario/:id"],
  ["/sedes/:id/eliminar", "/delete/eliminar-sede/:id"],
  ["/jornadas/:id/eliminar", "/delete/eliminar-jornada/:id"],
  ["/registros/:id/eliminar", "/delete/eliminar-registro/:id"],
] as const;

function mapPath(path: string, canonical: boolean) {
  for (const [from, to] of paths) {
    const match = matchPath({ path: canonical ? from : to, caseSensitive: true }, path);
    if (match && (match.params.id === undefined || /^\d+$/.test(match.params.id))) {
      return generatePath(canonical ? to : from, { id: match.params.id ?? null });
    }
  }
  return null;
}

export function canonicalToScreen(pathname: string, search: string) {
  if (!pathname.startsWith(CANONICAL_ROOT)) return null;
  const relative = pathname.slice(CANONICAL_ROOT.length - 1);
  const sede = /^\/sedes\/?$/.test(relative) ? new URLSearchParams(search).get("sede") : null;
  if (sede && /^\d+$/.test(sede)) return `/sedes/${sede}`;
  return mapPath(relative, true);
}

export function screenHref(screen: string, canonical: boolean) {
  if (!canonical) return `${V2_ROOT}${screen}`;
  if (screen.startsWith(CANONICAL_ROOT)) return screen;
  const [, pathname, suffix] = /^([^?#]*)(.*)$/.exec(screen)!;
  const sede = /^sedes\/(\d+)\/?$/.exec(pathname);
  if (sede) {
    const url = new URL(`${CANONICAL_ROOT}sedes/${suffix}`, "http://vpsl.invalid");
    url.searchParams.set("sede", sede[1]);
    return url.pathname + url.search + url.hash;
  }
  const path = mapPath(`/${pathname}`, false);
  return path && path !== "/" ? `${CANONICAL_ROOT.slice(0, -1)}${path}/${suffix}` : CANONICAL_ROOT + suffix;
}
