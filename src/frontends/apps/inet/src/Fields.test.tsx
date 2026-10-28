// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { inetGet, type InetField } from "@sisoc/api";
import { Field } from "./Fields";

vi.mock("@sisoc/api", async (original) => ({ ...await original<typeof import("@sisoc/api")>(), inetGet: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("conserva la localidad seleccionada sin recargar opciones al editar un campo independiente", async () => {
  vi.mocked(inetGet).mockResolvedValue({ count: 1, next: null, previous: null, results: [{ value: "2824", label: "Catamarca" }] });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const field: InetField = { name: "localidad", label: "Localidad", kind: "select", required: true, disabled: false, help_text: "", value: "2824", options: [], remote_options: true };
  const view = (nombre: string) => <QueryClientProvider client={client}><Field field={field} value="2824" values={{ municipio: "194", nombre, localidad: "2824" }} optionsPath="centros/options/" onChange={() => undefined} /></QueryClientProvider>;
  const { rerender } = render(view("Centro"));
  await waitFor(() => expect((screen.getByRole("combobox", { name: "Localidad" }) as HTMLInputElement).value).toBe("Catamarca"));
  expect(inetGet).toHaveBeenCalledTimes(1);
  rerender(view("Centro editado"));
  expect((screen.getByRole("combobox", { name: "Localidad" }) as HTMLInputElement).value).toBe("Catamarca");
  expect(inetGet).toHaveBeenCalledTimes(1);
  expect(vi.mocked(inetGet).mock.calls[0][0]).toContain("municipio=194");
  expect(vi.mocked(inetGet).mock.calls[0][0]).not.toContain("nombre=");
});
