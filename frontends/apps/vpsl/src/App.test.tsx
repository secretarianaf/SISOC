// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { get } from "./api";

vi.mock("./api", async (importOriginal) => ({
  ...await importOriginal<typeof import("./api")>(), get: vi.fn(),
}));

afterEach(() => { cleanup(); vi.resetAllMocks(); localStorage.clear(); });

function show(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);
}

const session = { username: "Provincia", can_view_itinerarios: true, can_view_sedes: true, permissions: {}, can_export: false };

it.each(["light", "dark"])("presenta subsanación y cartas en modo %s", async (mode) => {
  localStorage.setItem("app.theme", mode);
  vi.mocked(get).mockImplementation(async (path) => path === "/session/" ? session : {
    id: 1, codigo: "VPSL-1", provincia: "Buenos Aires", estado: "en_subsanacion", estado_label: "En subsanación",
    fecha_inicio: "2026-10-01", fecha_fin: "2026-10-03", referente: "Ana", referente_telefono: "123456",
    referente_email: "ana@example.com", subsanacion_observaciones: "Reemplazar la carta sin firma.",
    carta_archivo_url: "/media/carta.pdf", carta_archivo_estado: "subsanar", jornadas: [],
  });
  show("/v2/vpsl/itinerarios/1/");
  expect(await screen.findByText(/Reemplazar la carta sin firma/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Ver carta adjunta" }).getAttribute("href")).toBe("/media/carta.pdf");
  expect(screen.getByText("ana@example.com")).toBeTruthy();
});

it("pagina registros y presenta evidencias y actas del cierre", async () => {
  vi.mocked(get).mockImplementation(async (path) => {
    if (path === "/session/") return session;
    if (path.includes("/registros/")) return {
      count: 2, next: path.includes("page=1") ? "page=2" : null, previous: path.includes("page=2") ? "page=1" : null,
      results: [{ id: path.includes("page=2") ? 2 : 1, dni: path.includes("page=2") ? "22222222" : "11111111", nombre: "Ana", apellido: "Perez", numero_acta: "1", resultado: "No requiere", graduacion_izquierda: "", graduacion_derecha: "" }],
    };
    if (path.includes("/laboratorio/")) return { count: 0, results: [], next: null, previous: null };
    return {
      id: 1, itinerario_id: 1, fecha: "2026-10-01", sede: "Escuela", estado: "habilitada", estado_label: "Habilitada",
      checklist: [{ item: "electricidad", descripcion: "Electricidad", cumple: true, evidencia_url: "/media/evidencia.pdf", historial: [] }],
      cierre: { responsable: "Ana", consistente: true, atenciones: 2, lentes: 0, casos: 0, acta_adjunta_url: "/media/acta.pdf", historial: [] },
    };
  });
  show("/v2/vpsl/jornadas/1/");
  await screen.findByText("11111111");
  expect(screen.getByRole("link", { name: "Ver evidencia" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Descargar acta de cierre" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));
  expect(await screen.findByText("22222222")).toBeTruthy();
  expect(screen.queryByText("11111111")).toBeNull();
});
