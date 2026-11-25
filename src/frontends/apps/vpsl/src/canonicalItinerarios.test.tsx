// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { CanonicalSedesFilters } from "./canonicalSedes";
import { CanonicalItinerariosFilters } from "./canonicalItinerarios";

afterEach(cleanup);

it.each(["sedes", "itinerarios"])("submits the native null empty-mode token for %s instead of an unsupported synonym", (family) => {
  const onApply = vi.fn();
  const filters = JSON.stringify({ logic: "AND", items: [{ field: "nombre", op: "empty", value: "" }] });
  const config = { fields: [{ name: "nombre", type: "text", label: "Nombre" }], operators: { text: ["empty"] } };
  render(family === "sedes" ? <CanonicalSedesFilters search={`?filters=${encodeURIComponent(filters)}`} config={config} onApply={onApply} /> : <CanonicalItinerariosFilters search={`?filters=${encodeURIComponent(filters)}`} data={{ count: 0, results: [], next: null, previous: null, page: 1, pages: 1, page_size: 10, provincias: [], provincia_restringida: null, estados: [], filters_config: config }} onApply={onApply} />);
  fireEvent.mouseDown(screen.getByRole("combobox", { name: "Vacío del filtro 1" }));
  fireEvent.click(screen.getByRole("option", { name: "Solo nulo" }));
  fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
  const payload = JSON.parse(onApply.mock.calls[0][0].get("filters"));
  expect(payload.items[0].empty_mode).toBe("null");
});
