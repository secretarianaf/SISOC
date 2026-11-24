import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ColumnModal, Filters, Pagination, ServerSortHeader, type FiltersConfig } from "./listControls";

vi.mock("@sisoc/api", () => ({ leerCookie: vi.fn(() => "synthetic-csrf-token") }));

const favorites = { section: "s", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" };
const config: FiltersConfig = {
  fields: [
    { name: "nombre", label: "Nombre", type: "text" },
    { name: "id", label: "ID", type: "number" },
    { name: "fecha", label: "Fecha", type: "date" },
    { name: "estado", label: "Estado", type: "choice", choices: [{ value: "iniciada", label: "Iniciada" }, { value: "cerrada", label: "Cerrada" }] },
    { name: "activo", label: "Activo", type: "boolean" },
  ],
};
const campo = (i = 0) => document.querySelectorAll<HTMLSelectElement>('[data-rol="campo"]')[i];
const valor = (i = 0) => document.querySelectorAll<HTMLInputElement>('[data-rol="valor"]')[i];
const valorSelect = (i = 0) => document.querySelectorAll<HTMLSelectElement>('[data-rol="valor-select"]')[i];
function serialized() {
  const form = document.getElementById("filters-form") as HTMLFormElement;
  form.addEventListener("submit", (e) => e.preventDefault());
  fireEvent.submit(form);
  return JSON.parse((document.getElementById("filters-input") as HTMLInputElement).value);
}

describe("Filters (advanced_filters.js)", () => {
  afterEach(() => { cleanup(); window.history.replaceState({}, "", "/"); });

  it("types the value input by field: number with step 1, date, text", () => {
    render(<Filters config={config} action="/lista/" favorites={favorites} />);
    expect([valor().type, valor().getAttribute("step")]).toEqual(["text", null]);
    fireEvent.change(campo(), { target: { value: "id" } });
    expect([valor().type, valor().getAttribute("step")]).toEqual(["number", "1"]);
    fireEvent.change(campo(), { target: { value: "fecha" } });
    expect(valor().type).toBe("date");
  });

  it("shows choice fields as a select starting on the first choice, without an empty option", () => {
    render(<Filters config={config} action="/lista/" favorites={favorites} />);
    fireEvent.change(campo(), { target: { value: "estado" } });
    expect(valorSelect().hidden).toBe(false);
    expect(valor().hidden).toBe(true);
    expect([...valorSelect().options].map((o) => o.textContent)).toEqual(["Iniciada", "Cerrada"]);
    expect(valorSelect().value).toBe("iniciada");
    expect(serialized()).toEqual({ logic: "AND", items: [{ field: "estado", op: "eq", value: "iniciada" }] });
  });

  it("offers Sí/No for boolean fields and keeps an unknown prefilled value", () => {
    window.history.replaceState({}, "", `/lista/?filters=${encodeURIComponent(JSON.stringify({ items: [{ field: "activo", value: "false" }, { field: "estado", value: "otra" }] }))}`);
    render(<Filters config={config} action="/lista/" favorites={favorites} />);
    expect([...valorSelect(0).options].map((o) => o.textContent)).toEqual(["Sí", "No"]);
    expect(valorSelect(0).value).toBe("false");
    expect([...valorSelect(1).options].map((o) => o.value)).toEqual(["iniciada", "cerrada", "otra"]);
    expect(serialized().items).toEqual([{ field: "activo", op: "eq", value: "false" }, { field: "estado", op: "eq", value: "otra" }]);
  });

  it("adds and removes rows; only later rows show «- Filtro»", () => {
    render(<Filters config={{ ...config, defaultField: "nombre" }} action="/lista/" favorites={favorites} />);
    fireEvent.click(screen.getByRole("button", { name: "Filtro" }));
    expect(campo(1).value).toBe("nombre");
    expect(valor(1).placeholder).toBe("Buscar por filtro 2");
    const quitar = document.querySelectorAll<HTMLButtonElement>('[data-rol="quitar"]');
    expect([quitar[0].hidden, quitar[1].hidden]).toEqual([true, false]);
    fireEvent.change(valor(0), { target: { value: "  Norte " } });
    fireEvent.click(quitar[1]);
    expect(document.querySelectorAll(".poncho-search--row")).toHaveLength(1);
    expect(serialized().items).toEqual([{ field: "nombre", op: "contains", value: "Norte" }]);
  });
});

describe("ColumnModal (column_config.js)", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
  const columns = {
    list_key: "k", endpoint: "/ajax/columnas-preferencias/", modal_id: "m", script_id: "s", active: ["a"], defaults: ["a"],
    available: [{ key: "a", title: "Nombre", active: true, required: true, default: true }, { key: "b", title: "Estado", active: false, required: false, default: false }],
  };

  it("marks required columns, traps Tab and reloads after saving", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const reload = vi.fn();
    render(<ColumnModal columns={columns} close={vi.fn()} reload={reload} />);
    expect(screen.getByText("Obligatoria").className).toBe("badge bg-secondary ms-2");
    await waitFor(() => expect(document.body.classList.contains("modal-open")).toBe(true));
    const guardar = screen.getByRole("button", { name: "Guardar" });
    guardar.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Cerrar" }));
    fireEvent.click(screen.getByLabelText("Estado"));
    fireEvent.click(guardar);
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    expect(JSON.parse((fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1].body as string)).toEqual({ list_key: "k", columns: ["a", "b"] });
  });
});

describe("ServerSortHeader and Pagination", () => {
  afterEach(() => cleanup());

  it("links the header to the server ordering with its direction icon", () => {
    render(<ServerSortHeader title="Nombre" url="?ordering=-nombre" direction="asc" />);
    const link = screen.getByRole("link", { name: "Nombre" });
    expect(link.getAttribute("href")).toBe("?ordering=-nombre");
    expect(link.querySelector("i")!.className).toBe("fas fa-sort-up");
  });

  it("renders pagination.html with custom labels, gaps and an optional count", () => {
    const { rerender } = render(<Pagination paginated number={2} previous={1} next={null} range={[1, 2, "…", 9]} href={(n) => `?q=x&page=${n}`} count={90} prevText="Anterior" nextText="Siguiente" />);
    expect([...document.querySelectorAll(".page-item")].map((li) => `${li.className}|${li.textContent}|${li.querySelector("a")!.getAttribute("href")}`)).toEqual([
      "page-item|Anterior|?q=x&page=1", "page-item |1|?q=x&page=1", "page-item active|2|?q=x&page=2", "page-item disabled|...|#", "page-item |9|?q=x&page=9", "page-item disabled|Siguiente|#",
    ]);
    expect(screen.getByText("Se encontraron 90 resultados")).toBeTruthy();
    rerender(<Pagination paginated={false} number={1} previous={null} next={null} range={[]} href={(n) => `?page=${n}`} count={null} />);
    expect(document.querySelector(".mt-2")!.innerHTML).toBe("");
  });
});
