import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ComedoresSection, comedoresSectionValid, ProyectosSection, proyectosSectionValid, RegionSection, regionSectionValid, type ComedoresSection as Comedores, type ProyectosSection as Proyectos, type RegionSection as Region } from "./organizacionLegajoDatos";

afterEach(cleanup);

describe("Legajo región section", () => {
  const region = (over: Partial<Region> = {}): Region => ({
    kind: "region", can_manage: true, edit_url: "/organizaciones/editar/8#abordaje-card", has_data: true, region: "Región Sintética", subzona: "-", territorials: ["Pérez, Ana (ana.t)", "solo.usuario"], ...over,
  });

  it("renders region, subzona, the old territoriales and the edit link", () => {
    render(<RegionSection section={region()} />);
    expect(screen.getByRole("heading", { level: 5, name: "Datos de Región" })).toBeTruthy();
    expect(screen.getByText("Común a Línea Secos y Línea Tradicional")).toBeTruthy();
    expect(screen.getByText("Región:").nextElementSibling?.textContent).toBe("Región Sintética");
    expect(screen.getByText("Subzona:").nextElementSibling?.textContent).toBe("-");
    expect(screen.getByRole("link", { name: "Editar datos de región" }).getAttribute("href")).toBe("/organizaciones/editar/8#abordaje-card");
    expect(screen.getByRole("heading", { level: 6, name: "Territoriales anteriores sin proyecto" })).toBeTruthy();
    expect(screen.getByText("Pérez, Ana (ana.t)").className).toBe("badge-territorial");
    expect(screen.getByText(/Asignados a la organización antes de que los territoriales/)).toBeTruthy();
  });

  it("shows the empty block with the complete link only for managers", () => {
    const { unmount } = render(<RegionSection section={region({ has_data: false, territorials: [] })} />);
    expect(screen.getByText("Faltan Región y Subzona.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "+ Completar región" }).getAttribute("href")).toBe("/organizaciones/editar/8#abordaje-card");
    expect(screen.queryByText("Territoriales anteriores sin proyecto")).toBeNull();
    unmount();
    render(<RegionSection section={region({ has_data: false, can_manage: false, edit_url: null, territorials: [] })} />);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("validates the payload", () => {
    expect(regionSectionValid(region())).toBe(true);
    expect(regionSectionValid({ ...region(), territorials: "x" })).toBe(false);
    expect(regionSectionValid({ ...region(), edit_url: "https://evil.example/" })).toBe(false);
    expect(regionSectionValid({ ...region(), kind: "otra" })).toBe(false);
  });
});

describe("Legajo proyectos section", () => {
  const proyectos = (over: Partial<Proyectos> = {}): Proyectos => ({
    kind: "proyectos", title: "Proyectos · Línea Secos", color: "secos", can_manage: true, edit_url: "/organizaciones/editar/8#abordaje-card", total: 2,
    rows: [{ id: 1, code: "A-1", territorials: [] }, { id: 2, code: "B-2", territorials: ["Territ, Uno (pt.uno)", "otro.t"] }], ...over,
  });

  it("renders the title with its total, the rows, the badges and the edit link", () => {
    render(<ProyectosSection section={proyectos()} />);
    expect(screen.getByRole("heading", { level: 5 }).textContent).toBe("Proyectos · Línea Secos 2 Total");
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Código de Proyecto", "Territoriales", "Estado"]);
    expect(screen.getByText("A-1").className).toContain("bg-primary");
    expect(screen.getByText("Sin territorial").className).toContain("badge-pendiente");
    expect(screen.getByText("Territ, Uno (pt.uno)").className).toBe("badge-territorial");
    expect(screen.getAllByText("Activo")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Editar proyectos" }).getAttribute("href")).toBe("/organizaciones/editar/8#abordaje-card");
    expect(screen.getByText("Cada proyecto pertenece a una sola línea y tiene sus propios territoriales.")).toBeTruthy();
  });

  it("shows the empty text without the edit link and validates the payload", () => {
    render(<ProyectosSection section={proyectos({ rows: [], total: 0, can_manage: false, edit_url: null })} />);
    expect(screen.getByText("No hay proyectos activos.")).toBeTruthy();
    expect(screen.queryByRole("link")).toBeNull();
    expect(proyectosSectionValid(proyectos())).toBe(true);
    expect(proyectosSectionValid({ ...proyectos(), rows: [{ id: 1 }] })).toBe(false);
    expect(proyectosSectionValid({ ...proyectos(), total: "2" })).toBe(false);
  });
});

describe("Legajo comedores section", () => {
  const row = (over: Record<string, unknown> = {}) => ({
    id: 1, name: "Comedor Uno", url: "/comedores/1", caritas: false, type: "Comedor", code: "COD-7", program: "Alimentar", province: "Prov", municipality: "Muni", locality: "Loc",
    address: "Mitre 120", referent: "Ana Pérez", validation: "ok", ...over,
  });
  const comedores = (over: Partial<Comedores> = {}): Comedores => ({
    kind: "comedores", title: "Comedores", color: "sin", show_code: true, show_program: true, total: 3,
    rows: [row(), row({ id: 2, name: "Dos", caritas: true, code: null, referent: null, validation: "no" }), row({ id: 3, name: "Tres", validation: "pending" })], ...over,
  } as Comedores);

  it("renders the table with the optional columns, badges and links", () => {
    render(<ComedoresSection section={comedores()} />);
    expect(screen.getByRole("heading", { level: 5 }).textContent).toBe("Comedores 3 Total");
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent)).toEqual(
      ["Nombre", "Tipo", "Código de Proyecto", "Programa", "Ubicación", "Dirección", "Referente", "¿Fue Validado?", "Acciones"]);
    expect(screen.getByRole("link", { name: "Comedor Uno" }).getAttribute("href")).toBe("/comedores/1");
    expect(screen.getAllByRole("link", { name: /Ver/ })).toHaveLength(3);
    expect(screen.getAllByText("COD-7")[0].className).toContain("bg-primary");
    expect(screen.getByText(/CARITAS/).className).toContain("badge-caritas");
    expect(screen.getAllByText("Muni / Loc", { selector: ".small-ubicacion-sub" })).toHaveLength(3);
    expect(screen.getByText(/^Validado$/).className).toContain("badge-ok");
    expect(screen.getByText(/No Validado/).className).toContain("badge-no");
    expect(screen.getByText(/Pendiente/).className).toContain("badge-pendiente");
  });

  it("drops the optional columns, shows the empty text and validates the payload", () => {
    const { unmount } = render(<ComedoresSection section={comedores({ show_code: false, show_program: false })} />);
    expect(screen.getAllByRole("columnheader")).toHaveLength(7);
    unmount();
    render(<ComedoresSection section={comedores({ rows: [], total: 0 })} />);
    expect(screen.getByText("No hay comedores asociados en este programa.")).toBeTruthy();
    expect(comedoresSectionValid(comedores())).toBe(true);
    expect(comedoresSectionValid({ ...comedores(), rows: [row({ validation: "x" })] })).toBe(false);
    expect(comedoresSectionValid({ ...comedores(), rows: [row({ url: "https://evil.example/" })] })).toBe(false);
  });
});
