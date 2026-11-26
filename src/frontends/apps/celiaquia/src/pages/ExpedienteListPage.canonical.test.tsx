import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { CanonicalExpedientesList } from "../canonicalExpedientes";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const data = {
  version: 1, title: "Mis Expedientes", create_url: "/celiaquia/expedientes/nuevo/",
  show_tecnicos: false, show_excel: false, show_audit: false, tecnicos: [],
  filters: { fields: [{ name: "id", label: "ID", type: "number" }], operators: { number: ["eq", "gt"] }, defaultOperators: { number: "eq" } },
  rows: [{ id: 7, numero: "EX-SYNTHETIC", fecha: "2026-11-24T12:00:00Z", provincia: "Chaco", estado: "Creado", subsanar: 2, subsanado: 0, tecnicos: [], can_assign: false, excel: null,
    urls: { detail: "/celiaquia/expedientes/7/", assign: "/celiaquia/expedientes/7/asignar-tecnico/" },
    actions: [{ label: "Editar", url: "/celiaquia/expedientes/7/editar/", method: "GET" }] }],
};

it("keeps canonical query and native action links without requesting the V2 list", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/?q=EX&filters=%7B%22logic%22%3A%22AND%22%2C%22items%22%3A%5B%5D%7D");
  const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => data });
  vi.stubGlobal("fetch", fetcher);
  render(<CanonicalExpedientesList />);
  expect((await screen.findByRole("link", { name: "Editar" })).getAttribute("href")).toBe("/celiaquia/expedientes/7/editar/");
  expect(screen.getByRole("link", { name: "Nuevo expediente" }).getAttribute("href")).toBe("/celiaquia/expedientes/nuevo/");
  expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("EX");
  expect(fetcher.mock.calls[0][0]).toBe(window.location.pathname + window.location.search);
  expect(fetcher.mock.calls[0][1].headers.Accept).toBe("application/json");
  expect(screen.queryByText("Técnico")).toBeNull();
  expect(screen.getByText("2 a subsanar")).toBeTruthy();
});

it("does not invent forbidden actions or truncate native rows", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...data, create_url: null, rows: Array.from({ length: 27 }, (_, i) => ({ ...data.rows[0], id: i + 1, numero: `EX-${i}`, actions: [] })) }) }));
  render(<CanonicalExpedientesList />);
  await screen.findByText("EX-26");
  expect(screen.queryByRole("link", { name: "Editar" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Nuevo expediente" })).toBeNull();
  expect(screen.getAllByRole("link", { name: "Ver" })).toHaveLength(27);
});
