import { describe, expect, it, vi } from "vitest";
import { findRoute, ROUTES, SHELL_ROUTES } from "./index";

vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: vi.fn(), post: vi.fn() })),
  leerCookie: vi.fn(() => ""),
  mensajeDeError: vi.fn(() => ""),
  SinPermiso: class SinPermiso extends Error {},
}));

function shellRoute(pathname: string) {
  for (const route of SHELL_ROUTES) {
    const params = route.match(pathname);
    if (params !== null) return { name: route.name, params, title: route.title(params), listPath: route.listPath };
  }
  return null;
}

describe("route registry", () => {
  it.each([
    ["/grupos/", "groups", { mode: "list" }],
    ["/grupos/crear/", "groups", { mode: "create" }],
    ["/grupos/editar/7/", "groups", { mode: "edit", id: "7" }],
    ["/inicio/", "inicio", {}],
    ["/", "login", {}],
    ["/login/", "login", {}],
    ["/password/first-change/", "required-password", {}],
    ["/mi-cuenta/", "account", { mode: "account" }],
    ["/mi-cuenta/confirmar/", "account", { mode: "confirm" }],
    ["/password_change/", "password-change", { mode: "form" }],
    ["/password_change/done/", "password-change", { mode: "done" }],
    ["/password_reset/", "password-reset", { mode: "request" }],
    ["/password_reset/done/", "password-reset", { mode: "done" }],
    ["/reset/done/", "password-reset", { mode: "complete" }],
    ["/reset/MQ/set-password/", "password-reset", { mode: "confirm", uidb64: "MQ" }],
    ["/password/reset/confirm/MQ/set-password/", "password-reset", { mode: "confirm", uidb64: "MQ" }],
    ["/reset/MQ/synthetic-reset-token/", "password-reset", { mode: "confirm", uidb64: null }],
    ["/usuarios/importar/", "user-import", { mode: "form" }],
    ["/usuarios/importar/lotes/12/", "user-import", { mode: "job", id: "12" }],
    ["/usuarios/importar/lotes/x/", "business", {}],
    ["/usuarios/importar", "business", {}],
    ["/usuarios/credenciales-masivas/", "bulk-credentials", { mode: "form" }],
    ["/usuarios/credenciales-masivas/lotes/7/", "bulk-credentials", { mode: "job", id: "7" }],
    ["/usuarios/credenciales-masivas/lotes/7/reanudar/", "business", {}],
    ["/usuarios/credenciales-masivas", "business", {}],
    ["/grupos", "business", {}],
    ["/grupos/editar/x/", "business", {}],
    ["/mi-cuenta", "business", {}],
    ["/v2/sisoc/insumos/", "business", {}],
    ["/otra/ruta/", "business", {}],
  ])("resolves %s to the %s route", (pathname, name, params) => {
    const found = findRoute(pathname);
    expect(found?.route.name).toBe(name);
    expect(found?.params).toEqual(params);
  });

  it("keeps the business catch-all last so identity paths cannot fall through to it", () => {
    expect(ROUTES.at(-1)?.name).toBe("business");
    expect(ROUTES.slice(0, -1).every((route) => route.match("/v2/sisoc/insumos/") === null)).toBe(true);
    expect(new Set(ROUTES.map((route) => route.name)).size).toBe(ROUTES.length);
  });

  it.each([
    ["/v2/sisoc/insumos/categorias/", "insumos-categorias", "Categorías de insumos", { action: undefined, id: undefined }],
    ["/v2/sisoc/insumos/categorias/crear", "insumos-categorias", "Nueva categoría", { action: "crear", id: undefined }],
    ["/v2/sisoc/insumos/categorias/4/editar", "insumos-categorias", "Editar categoría", { action: "editar", id: "4" }],
    ["/v2/sisoc/insumos/categorias/4/eliminar", "insumos-categorias", "Eliminar categoría", { action: "eliminar", id: "4" }],
    ["/v2/sisoc/insumos/categorias/crear/", "insumos-categorias", "Categorías de insumos", { action: undefined, id: undefined }],
    ["/v2/sisoc/insumos/crear/", "insumos", "Nuevo insumo", { action: "crear", id: undefined }],
    ["/v2/sisoc/insumos/crear", "insumos", "Nuevo insumo", { action: "crear", id: undefined }],
    ["/v2/sisoc/insumos/9/editar/", "insumos", "Editar insumo", { action: "editar", id: "9" }],
    ["/v2/sisoc/insumos/9/eliminar", "insumos", "Eliminar insumo", { action: "eliminar", id: "9" }],
    ["/v2/sisoc/insumos/", "insumos", "Insumos", { action: undefined, id: undefined }],
    ["/otra/ruta/", "insumos", "Insumos", { action: undefined, id: undefined }],
  ])("resolves the in-shell path %s to %s with its legacy title", (pathname, name, title, params) => {
    const found = shellRoute(pathname);
    expect(found?.name).toBe(name);
    expect(found?.title).toBe(title);
    expect(found?.params).toEqual(params);
    expect(found?.listPath).toBe(name === "insumos" ? "/v2/sisoc/insumos/" : "/v2/sisoc/insumos/categorias/");
  });
});
