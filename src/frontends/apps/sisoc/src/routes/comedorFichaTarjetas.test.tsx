import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { TarjetasFila, tarjetasValid, type MesEjecucion, type Transacciones } from "./comedorFichaTarjetas";
import { FichaTablero, tableroValid } from "./comedorFichaTablero";
import { tableroFixture } from "./comedorFichaFixtures";

afterEach(cleanup);

const transacciones: Transacciones = { periodo: "2026-09", movimientos: "14", transferido: "$12.000", gastado: "$1.500", saldo: "$0", detalle: "/comedores/7/transacciones" };
const mes: MesEjecucion = {
  expediente: { convenio: "ex-c-1", pago: "Sin información", prestaciones: "15", monto: "$1.235", mes_pago: "Octubre", ano: "2026", mes_ejecucion: "Sin información" },
  ver_mas: "/expedientespagos/expedientespagos/7/",
};

describe("Comedor ficha: transactions and execution month cards", () => {
  it("draws nothing when the page draws neither card", () => {
    const { container } = render(<TarjetasFila data={{ transacciones: null, mes_ejecucion: null }} />);
    expect(container.innerHTML).toBe("");
    cleanup();
    expect(render(<TarjetasFila data={{}} />).container.innerHTML).toBe("");
  });

  it("transactions card: native title, the five lines in order and the link", () => {
    render(<TarjetasFila data={{ transacciones }} />);
    expect(screen.getByText("Transacciones - Nación Servicios")).toBeTruthy();
    const lines = [...document.querySelectorAll("#card-transacciones p")].map((p) => p.textContent);
    expect(lines).toEqual(["Período: 2026-09", "Movimientos: 14", "Transferido: $12.000", "Gastado: $1.500", "Saldo Cereado: $0"]);
    expect(screen.getByRole("link", { name: "Ver detalles" }).getAttribute("href")).toBe("/comedores/7/transacciones");
    expect(document.querySelector(".row.mt-3 > .col-12.col-lg-6.mb-3.mb-lg-0")).toBeTruthy();
  });

  it("execution month card with an expediente: uppercase expedientes and the link", () => {
    render(<TarjetasFila data={{ mes_ejecucion: mes }} />);
    expect(screen.getByText("ex-c-1").className).toBe("text-uppercase");
    const lines = [...document.querySelectorAll("#card-mes-ejecucion p")].map((p) => p.textContent);
    expect(lines[2]).toBe("Cantidad de prestaciones: 15");
    expect(lines[3]).toBe("Monto total de prestaciones: $1.235");
    expect(lines).toHaveLength(7);
    expect(screen.getByRole("link", { name: "Ver más" }).getAttribute("href")).toBe("/expedientespagos/expedientespagos/7/");
    // Alone in the row it is pushed to the right, as in the template.
    expect(document.querySelector(".col-lg-6.ms-lg-auto")).toBeTruthy();
  });

  it("execution month card without expediente shows the native notice and keeps the link", () => {
    render(<TarjetasFila data={{ transacciones, mes_ejecucion: { expediente: null, ver_mas: mes.ver_mas } }} />);
    expect(screen.getByText("No hay expedientes de pago cargados para este comedor.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver más" })).toBeTruthy();
    expect(document.querySelector(".ms-lg-auto")).toBeNull();
  });

  it("validates the optional keys and the board renders them through the rows slot", () => {
    expect(tarjetasValid({})).toBe(true);
    expect(tarjetasValid({ transacciones, mes_ejecucion: mes })).toBe(true);
    expect(tarjetasValid({ transacciones: { periodo: 1 } })).toBe(false);
    expect(tarjetasValid({ mes_ejecucion: { expediente: null, ver_mas: "https://evil.example/" } })).toBe(false);
    expect(tableroValid(tableroFixture({ transacciones, mes_ejecucion: mes }))).toBe(true);
    expect(tableroValid(tableroFixture({ transacciones: { ...transacciones, detalle: "//x" } }))).toBe(false);
    render(<FichaTablero data={tableroFixture({ transacciones })} rows={<TarjetasFila data={{ transacciones }} />} />);
    expect(document.getElementById("card-transacciones")).toBeTruthy();
  });
});
