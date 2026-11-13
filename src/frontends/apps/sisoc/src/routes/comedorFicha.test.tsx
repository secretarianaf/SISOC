import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { FichaAcordeon, FichaHeaderBar, FichaHero, fichaValid, type FichaData, type FichaHeader } from "./comedorFicha";

const header = (over: Partial<FichaHeader> = {}): FichaHeader => ({
  validar: true, convenio_pnud: null, actividades: null, acompanamiento_territorial: "/comedores/7/relevamiento/listar", historial: "/auditoria/comedores/comedor/7/",
  acciones: { editar: "/comedores/7/editar", responsable_tarjeta: null, eliminar: "/comedores/7/eliminar", equipo_tecnico: { url: "/duplas/7/asignar", label: "Asignar Equipo Técnico" }, comenzar_admision: true },
  convenios: [
    { id: 1, tipo: "Incorporación", creado: "01/10/2026", estado: "Iniciada", vigente_pwa: true, seleccionada: true, url: "/comedores/7?admision_id=1" },
    { id: 2, tipo: "Renovación", creado: "05/11/2026", estado: "-", vigente_pwa: false, seleccionada: false, url: "/comedores/7?admision_id=2" },
  ], ...over,
});
const marcas = (labels: string[], on: string[] = []) => labels.map((label) => ({ label, marcado: on.includes(label) }));
const ficha = (over: Partial<FichaData> = {}): FichaData => ({
  id: 7, nombre: "Comedor Norte", header: header(), messages: [],
  titulo: { conformidad_pendiente: { periodo: "10/2026" }, nombre: "Comedor Norte", validacion: "Validado", programa: "PAC", etiqueta_estado: "Activo", es_caritas: true, inicio_ejecucion: "01/10/2026", plazo_ejecucion: "12 meses" },
  acordeon: {
    ubicacion: { mapa: { tipo: "iframe", src: "https://maps.google.com/maps?q=-27.45,-58.98&output=embed" }, datos: [{ icon: "bi bi-geo", label: "Calle", value: "Mitre" }] },
    responsables: { foto: { url: "/static/custom/img/default.png", webp: null, default: true }, hay_organizacion: true, items: [{ icon: "bi bi-building", label: "Nombre", value: "Org Uno" }],
      firmantes: [{ icon: "bi bi-person-fill", text: "Presidente: Ana" }], avales: [{ icon: "bi bi-shield-check", label: "Aval 1", value: "Beto" }] },
    prestaciones: { colaboradores: "3", dias_por_semana: "5", prestaciones_mensuales: "100", monto_mensual: "2000", dias: ["Lunes", "Martes"], filas: [{ comida: "Desayuno", valores: ["10", "-"] }] },
    relevamientos: { titulo: "Acompañamiento Territorial", pnud: false, donaciones: marcas(["Particulares", "Otros"], ["Otros"]), servicio: marcas(["Vianda"]), espacio: marcas(["Propio"]), actividades_anexo: ["Huerta"] },
  }, ...over,
});

afterEach(cleanup);

describe("Comedor ficha: hero and accordion", () => {
  it("validates the API payload", () => {
    expect(fichaValid(ficha())).toBe(true);
    expect(fichaValid({ ...ficha(), header: { ...header(), convenios: [{ id: "x" }] } })).toBe(false);
    expect(fichaValid(null)).toBe(false);
  });

  it("title card: pending conformity, validation, program, CARITAS and dates", () => {
    render(<FichaHero data={ficha()} />);
    expect(screen.getByText(/Pendiente la conformidad de prestaciones del periodo 10\/2026\./)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Comedor Norte \|/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Validado" }).className).toBe("btn btn-sm btn-success mb-2");
    expect(screen.getByRole("button", { name: "PAC" })).toBeTruthy();
    expect(screen.getByText("CARITAS")).toBeTruthy();
    expect(screen.getByText("12 meses")).toBeTruthy();
    cleanup();
    render(<FichaHero data={ficha({ titulo: { ...ficha().titulo, conformidad_pendiente: null, validacion: "Pendiente", es_caritas: false, inicio_ejecucion: null } })} />);
    expect(screen.queryByText(/Pendiente la conformidad/)).toBeNull();
    expect(screen.getByRole("button", { name: "Validación Pendiente" })).toBeTruthy();
    expect(screen.getByText("Sin información")).toBeTruthy();
    expect(screen.queryByText("CARITAS")).toBeNull();
  });

  it("header: links by flag, the Acciones menu and the convenio selector", () => {
    render(<FichaHeaderBar header={header()} />);
    expect(screen.getByRole("link", { name: /Acompañamiento Territorial/ }).getAttribute("href")).toBe("/comedores/7/relevamiento/listar");
    expect(screen.getByRole("link", { name: /Historial/ }).getAttribute("href")).toBe("/auditoria/comedores/comedor/7/");
    // The actions of later units are drawn only when their handler exists: nothing inert.
    expect(screen.queryByText("Validar")).toBeNull();
    expect(screen.queryByText("Comenzar Admisión")).toBeNull();
    const acciones = screen.getByRole("button", { name: /Acciones/ });
    expect(acciones.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(acciones);
    expect(acciones.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("link", { name: /Editar/ }).getAttribute("href")).toBe("/comedores/7/editar");
    expect(screen.getByRole("link", { name: /Eliminar/ }).getAttribute("href")).toBe("/comedores/7/eliminar");
    expect(screen.getByRole("link", { name: /Asignar Equipo Técnico/ })).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(acciones.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(screen.getByRole("button", { name: /Seleccionar Convenio/ }));
    const activo = screen.getByRole("link", { name: /Incorporación/ });
    expect(activo.className).toContain("active");
    expect(activo.getAttribute("href")).toBe("/comedores/7?admision_id=1");
    expect(screen.getByRole("link", { name: /Renovación/ }).textContent).toContain("05/11/2026 · -");
  });

  it("header: the validation and admission actions work when the page wires them", () => {
    const onValidar = vi.fn(), onComenzar = vi.fn();
    render(<FichaHeaderBar header={header()} onValidar={onValidar} onComenzarAdmision={onComenzar} />);
    fireEvent.click(screen.getByRole("link", { name: /Validar/ }));
    expect(onValidar).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: /Acciones/ }));
    fireEvent.click(screen.getByRole("button", { name: /Comenzar Admisión/ }));
    expect(onComenzar).toHaveBeenCalledTimes(1);
  });

  it("header: without convenios the selector says so", () => {
    render(<FichaHeaderBar header={header({ convenios: [] })} />);
    fireEvent.click(screen.getByRole("button", { name: /Seleccionar Convenio/ }));
    expect(screen.getByText("Sin Convenios")).toBeTruthy();
  });

  it("accordion: the first panel is open, a click opens another and an open one stays open", () => {
    Object.defineProperty(window, "innerWidth", { value: 1280, configurable: true });
    render(<FichaAcordeon data={ficha().acordeon} />);
    const panels = () => [...document.querySelectorAll(".accordion-panel")].map((p) => p.classList.contains("open"));
    expect(panels()).toEqual([true, false, false, false]);
    fireEvent.click(screen.getByText("Prestaciones", { selector: ".accordion-header" }));
    expect(panels()).toEqual([false, false, true, false]);
    fireEvent.click(screen.getByText("Prestaciones", { selector: ".accordion-header" }));
    expect(panels()).toEqual([false, false, true, false]);
    expect(screen.getByText("Colaboradores")).toBeTruthy();
    expect(document.getElementById("legajo-actividades-pnud")).toBeTruthy();
  });

  it("accordion on a phone toggles each panel", () => {
    Object.defineProperty(window, "innerWidth", { value: 400, configurable: true });
    render(<FichaAcordeon data={ficha().acordeon} />);
    fireEvent.click(screen.getByText("Responsables"));
    fireEvent.click(screen.getByText("Ubicación"));
    expect([...document.querySelectorAll(".accordion-panel")].map((p) => p.classList.contains("open"))).toEqual([false, true, false, false]);
  });

  it("panels: map, data rows, responsables, prestaciones table and territorial marks", () => {
    Object.defineProperty(window, "innerWidth", { value: 1280, configurable: true });
    render(<FichaAcordeon data={ficha().acordeon} />);
    expect(document.querySelector("iframe")!.getAttribute("src")).toBe("https://maps.google.com/maps?q=-27.45,-58.98&output=embed");
    expect(screen.getByText("Calle:").closest("p")!.textContent).toBe("Calle: Mitre");
    expect(screen.getByText("Firmantes")).toBeTruthy();
    expect(screen.getByText("Aval 1:")).toBeTruthy();
    expect((document.querySelector(".comedor-photo") as HTMLImageElement).alt).toBe("Imagen del comedor");
    expect(screen.getByRole("row", { name: /Desayuno 10 -/ })).toBeTruthy();
    const otros = screen.getByText("Otros");
    expect(otros.querySelector("i")!.className).toBe("bi bi-check-circle-fill text-white me-2");
    expect(screen.getByText("Particulares").querySelector("i")!.className).toBe("bi bi-circle text-white me-2");
    expect(screen.getByText("Huerta")).toBeTruthy();
  });

  it("without map data, organization or activities the native empty texts show", () => {
    const base = ficha();
    const sin = ficha({ acordeon: { ...base.acordeon, ubicacion: { mapa: { tipo: "vacio", src: null }, datos: [] },
      responsables: { ...base.acordeon.responsables, hay_organizacion: false },
      relevamientos: { titulo: "Actividades", pnud: true, agregar: "/pwa/7/actividades/crear", actividades: [], puede_gestionar: true } } });
    render(<FichaAcordeon data={sin.acordeon} />);
    expect(screen.getByText("No hay coordenadas ni datos suficientes para cargar el mapa.")).toBeTruthy();
    expect(screen.getByText("No hay una organizacion vinculada para mostrar responsables.")).toBeTruthy();
    expect(screen.getByText("No hay actividades cargadas para este espacio.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Agregar actividad" }).getAttribute("href")).toBe("/pwa/7/actividades/crear");
  });

  it("PNUD activities: table with details and the edit link only for active ones", () => {
    const base = ficha();
    const actividad = (id: number, activo: boolean) => ({ id, categoria: "Salud", actividad: "Taller", dia: "Lunes", horario: "10 a 12", responsable: "Ana", vigencia: "6 meses", inscriptos: "4", activo,
      detalle: [["Hora inicio", "10:00"]] as [string, string][], editar: activo ? `/pwa/7/actividades/${id}/editar` : null });
    const pnud = ficha({ acordeon: { ...base.acordeon, relevamientos: { titulo: "Actividades", pnud: true, agregar: null, puede_gestionar: true, actividades: [actividad(1, true), actividad(2, false)] } } });
    render(<FichaAcordeon data={pnud.acordeon} />);
    expect(screen.getAllByRole("link", { name: "Editar" })).toHaveLength(1);
    expect(screen.getByText("Activa")).toBeTruthy();
    expect(screen.getByText("Inactiva")).toBeTruthy();
    expect(screen.getAllByText("Ver detalles")).toHaveLength(2);
  });
});
