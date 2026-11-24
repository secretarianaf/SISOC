export const INSUMOS_CANONICAL_LIST = "/insumos/";
export const INSUMOS_PREVIEW_LIST = "/v2/sisoc/insumos/";

export function isCanonicalInsumosPath(pathname: string): boolean {
  return pathname === "/insumos" || pathname.startsWith(INSUMOS_CANONICAL_LIST);
}

export function insumosListPath(pathname: string, categories = false): string {
  const list = isCanonicalInsumosPath(pathname) ? INSUMOS_CANONICAL_LIST : INSUMOS_PREVIEW_LIST;
  return categories ? `${list}categorias/` : list;
}

export function insumoActionPath(pathname: string, action: string): string {
  const trailingSlash = isCanonicalInsumosPath(pathname) ? "" : "/";
  return `${insumosListPath(pathname)}${action}${trailingSlash}`;
}
