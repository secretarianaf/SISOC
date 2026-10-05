import { describe, expect, it } from "vitest";
import { route } from "./App";

describe("navegación de VPSL", () => {
  it("resuelve las pantallas principales en /v2/vpsl/", () => {
    expect(route("/v2/vpsl/")).toEqual({ kind: "itinerarios" });
    expect(route("/v2/vpsl/sedes/12/")).toEqual({ kind: "sede", id: 12 });
    expect(route("/v2/vpsl/jornadas/41/")).toEqual({ kind: "jornada", id: 41 });
    expect(route("/v2/vpsl/forms/registro-create/41/")).toEqual({ kind: "form", formKind: "registro-create", id: 41 });
  });
});
