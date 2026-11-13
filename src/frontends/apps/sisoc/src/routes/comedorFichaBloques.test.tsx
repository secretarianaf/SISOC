import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { CertificacionesCard, FichaBloques, bloquesValid, certificacionesValid } from "./comedorFichaBloques";
import { bloquesFixture } from "./comedorFichaFixtures";

afterEach(cleanup);

describe("Comedor ficha: lower cards", () => {
  it("validates the certifications block", () => {
    const { certificaciones } = bloquesFixture();
    expect(certificacionesValid(certificaciones)).toBe(true);
    expect(bloquesValid({ ...bloquesFixture() })).toBe(true);
    expect(certificacionesValid({ ...certificaciones, historial: "https://evil.example/" })).toBe(false);
    expect(certificacionesValid({ ...certificaciones, items: [{ id: 1 }] })).toBe(false);
    expect(certificacionesValid({ ...certificaciones, items: [{ ...certificaciones.items[0], pdf: "//x" }] })).toBe(false);
    expect(bloquesValid({})).toBe(false);
  });

  it("certifications card: native title, columns, badges, links and the history button", () => {
    render(<FichaBloques data={bloquesFixture()} />);
    expect(screen.getByRole("heading", { name: "Certificaciones Mensuales de Prestaciones" })).toBeTruthy();
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Período", "Usuario generador", "Estado Conformidad", "Fecha de certificación", "Ver PDF"]);
    expect(screen.getByText("Conforme").className).toBe("badge bg-success");
    expect(screen.getByText("No conforme").className).toBe("badge bg-danger");
    const pdf = screen.getByRole("link", { name: "Ver PDF" });
    expect(pdf.getAttribute("href")).toBe("/comedores/7/certificaciones-prestaciones/2/pdf/");
    expect(pdf.getAttribute("target")).toBe("_blank");
    expect(pdf.getAttribute("rel")).toBe("noopener");
    expect(screen.getByText("No disponible").className).toBe("text-muted");
    expect(screen.getByRole("link", { name: "Ver historial completo" }).getAttribute("href")).toBe("/comedores/7/certificaciones-prestaciones/");
    expect(document.querySelector(".card-tools")!.textContent).toBe("Ver historial completo ");
  });

  it("without certifications it shows the native empty row", () => {
    render(<CertificacionesCard data={{ historial: "/h/", items: [] }} />);
    expect(screen.getByText("No hay certificaciones mensuales registradas.").getAttribute("colspan")).toBe("5");
  });

  it("the collapse button hides the body and swaps the icon, as AdminLTE", () => {
    render(<CertificacionesCard data={bloquesFixture().certificaciones} />);
    const button = document.querySelector<HTMLButtonElement>('[data-card-widget="collapse"]')!;
    fireEvent.click(button);
    expect(document.querySelector(".card")!.classList.contains("collapsed-card")).toBe(true);
    expect(document.querySelector<HTMLElement>(".card-body")!.style.display).toBe("none");
    expect(button.querySelector("i")!.className).toBe("fas fa-plus");
    fireEvent.click(button);
    expect(document.querySelector<HTMLElement>(".card-body")!.style.display).toBe("");
  });
});
