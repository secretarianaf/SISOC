// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import type { InetItem } from "@sisoc/api";
import { CenterPanel } from "./DetailPanels";
import { ThemeProvider } from "@mui/material";
import { getTheme } from "@sisoc/ui";

afterEach(cleanup);
const center = { nombre: "CFP 3", cue: "3", provincia: "Buenos Aires", localidad: "Tolosa", detalle: [{ label: "Domicilio de actividades", value: "7 & 123" }] } as InetItem;
function show(item: InetItem) {
  return render(<ThemeProvider theme={getTheme()}><CenterPanel item={item} /></ThemeProvider>);
}

describe("Mapa del CFP", () => {
  it("carga un mapa con el domicilio y territorio del centro, codificados", () => {
    show(center);
    const map = screen.getByTitle("Mapa de la sede: CFP 3");
    const url = new URL(map.getAttribute("src")!);
    expect(url.origin).toBe("https://www.google.com");
    expect(url.searchParams.get("q")).toBe("7 & 123, Tolosa, Buenos Aires, Argentina");
    expect(url.searchParams.get("output")).toBe("embed");
  });
  it("prioriza la calle y altura entregadas por la API", () => {
    show({ ...center, detalle: [...center.detalle, { label: "Domicilio mapa", value: "Calle 8 456" }] });
    expect(new URL(screen.getByTitle("Mapa de la sede: CFP 3").getAttribute("src")!).searchParams.get("q")).toBe("Calle 8 456, Tolosa, Buenos Aires, Argentina");
  });
  it.each([{ ...center, detalle: [] }, { ...center, localidad: "" }, { ...center, provincia: "" }])("no muestra un mapa engañoso cuando falta domicilio o territorio", (item) => {
    show(item);
    expect(screen.queryByTitle("Mapa de la sede: CFP 3")).toBeNull();
    expect(screen.getByText("Sin datos suficientes para mostrar el mapa")).toBeDefined();
  });
});
