import { describe, expect, it } from "vitest";
import { route } from "./App";
import { screenHref } from "./canonicalRoutes";

describe("navegación de VPSL", () => {
  it("resuelve las pantallas principales en /v2/vpsl/", () => {
    expect(route("/v2/vpsl/")).toEqual({ kind: "itinerarios" });
    expect(route("/v2/vpsl/sedes/12/")).toEqual({ kind: "sede", id: 12 });
    expect(route("/v2/vpsl/jornadas/41/")).toEqual({ kind: "jornada", id: 41 });
    expect(route("/v2/vpsl/forms/registro-create/41/")).toEqual({ kind: "form", formKind: "registro-create", id: 41 });
  });
});

describe("URLs canónicas", () => {
  it.each([
    ["/ver-para-ser-libre/crear/", { kind: "nuevo" }],
    ["/ver-para-ser-libre/sedes/crear/", { kind: "form", formKind: "sede-create", id: 0 }],
    ["/ver-para-ser-libre/sedes/7/editar/", { kind: "form", formKind: "sede-edit", id: 7 }],
    ["/ver-para-ser-libre/7/jornadas/crear/", { kind: "form", formKind: "jornada-create", id: 7 }],
    ["/ver-para-ser-libre/jornadas/7/checklist/crear/", { kind: "form", formKind: "checklist", id: 7 }],
    ["/ver-para-ser-libre/jornadas/7/registros/crear/", { kind: "form", formKind: "registro-create", id: 7 }],
    ["/ver-para-ser-libre/registros/7/editar/", { kind: "form", formKind: "registro-edit", id: 7 }],
    ["/ver-para-ser-libre/laboratorio/7/editar/", { kind: "form", formKind: "laboratorio", id: 7 }],
    ["/ver-para-ser-libre/jornadas/7/cierre/crear/", { kind: "form", formKind: "cierre", id: 7 }],
    ["/ver-para-ser-libre/registros/7/eliminar/", { kind: "delete", formKind: "eliminar-registro", id: 7 }],
    ["/ver-para-ser-libre/jornadas/7/exportar/", { kind: "not-found" }],
    ["/ver-para-ser-libre/jornadas/no-es-un-id/", { kind: "not-found" }],
  ])("clasifica %s sin absorber descargas ni rutas desconocidas", (path, expected) => {
    expect(route(path)).toEqual(expected);
  });

  it("usa la URL de sedes para consultar el detalle que no tenía pantalla nativa separada", () => {
    expect(route("/ver-para-ser-libre/sedes/", "?sede=7")).toEqual({ kind: "sede", id: 7 });
    expect(route("/ver-para-ser-libre/sedes/", "?sede=no-es-un-id")).toEqual({ kind: "sedes" });
  });
});


it("conserva la query y el fragmento al convertir el enlace a edición canónica", () => {
  const screen = "forms/itinerario-edit/8/?ref=lista#contacto";
  expect(screenHref(screen, true)).toBe("/ver-para-ser-libre/8/editar/?ref=lista#contacto");
  expect(screenHref(screen, false)).toBe("/v2/vpsl/" + screen);
});
