import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { centroDetalleNavigation } from "./cdiCentroDetalle";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const item = (icon: string, label: string, value: string) => ({ icon, label, value });
const usuario = (id: number, over: Record<string, unknown> = {}) => ({
  id, username: `ref${id}`, responsable: id === 1, nombre: `Ref ${id}`, email: `ref${id}@x.test`, estado: "activo", motivo: "",
  password: { kind: "value", value: `Temp-${id}` },
  acciones: id === 1 ? null : { activo: true, usuario: `Ref ${id}`, url: `/api/web/cdi/centros/7/usuarios/${id}/estado/` },
  ...over,
});
const detalle = (over: Record<string, unknown> = {}) => ({
  centro: { id: 7, nombre: "CDI Girasoles", codigo_cdi: "CDI-7", lista_url: "/centrodeinfancia/listar", estado: "activo", estado_display: "Activo" },
  hero: { nomina: 3, trabajadores: 1, formularios: null, anio_inicio: "2019" },
  header: {
    nomina_url: "/centrodeinfancia/7/nomina/", historial_url: "/audittrail/log/centrodeinfancia/centrodeinfancia/7/",
    generar_usuario_url: "/centrodeinfancia/7/generar-usuario/", editar_url: "/centrodeinfancia/editar/7", eliminar_url: "/centrodeinfancia/eliminar/7", estado_url: null,
  },
  general: [item("bi-diagram-3", "Organización", "Fundación Sol"), item("bi-map", "Provincia", "Mendoza")],
  mapa: null,
  referente: { nombre: "Rosa   Pérez", items: [item("bi-phone", "Teléfono", "261777")] },
  funcionamiento: { items: [item("bi-calendar3", "Meses de funcionamiento", "Enero, Febrero")], horarios: [{ dia: "Lunes", apertura: "08:00", cierre: "16:30" }] },
  usuarios: { credenciales: true, administrar: true, generar_url: "/centrodeinfancia/7/generar-usuario/", columnas: 6, filas: [usuario(1), usuario(2), usuario(3, { estado: "suspendido", motivo: "Licencia", acciones: { activo: false, usuario: "Ref 3", url: "/api/web/cdi/centros/7/usuarios/3/estado/" } })] },
  nomina: { asistencia_url: null, ver_url: "/centrodeinfancia/7/nomina/", hombres: 1, mujeres: 2, x: 0, menores: 3 },
  trabajadores: {
    crear_url: "/centrodeinfancia/7/trabajadores/crear/",
    filas: [
      { id: 5, nombre: "Gómez, Lucía", subcomponente: "PFPI", funcion: "Docente", fecha_carga: "1 Set. 2026", ver: "/centrodeinfancia/7/trabajadores/5/ver/", editar: "/centrodeinfancia/7/trabajadores/5/editar/", eliminar: "/api/web/cdi/centros/7/trabajadores/5/eliminar/" },
      { id: 6, nombre: "Pérez, Ana", subcomponente: "-", funcion: "-", fecha_carga: "-", ver: "/centrodeinfancia/7/trabajadores/6/ver/", editar: null, eliminar: null },
    ],
  },
  formularios: null,
  calidad: null,
  observaciones: {
    filas: [{ id: 9, fecha: "01/10/2026 10:00", observador: "Obs <b>", texto: "Texto", ver: "/centrodeinfancia/observacion/9/" }],
    paginated: true, number: 1, previous: null, next: 2, range: [1, 2], count: 7, query_prefix: "otro=a&",
    crear_url: "/api/web/cdi/centros/7/observaciones/crear/", campo: { label: "Observación", rows: 4, placeholder: "Describa la observación" },
  },
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path = "/centrodeinfancia/detalle/7") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  vi.spyOn(centroDetalleNavigation, "go").mockImplementation(() => undefined);
  vi.spyOn(window, "alert").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDI centre detail route", () => {
  it("owns only the native detail path", () => {
    expect(findRoute("/centrodeinfancia/detalle/7")?.route.name).toBe("cdi-centro-detalle");
    for (const other of ["/centrodeinfancia/detalle/7/", "/centrodeinfancia/detalle/0", "/centrodeinfancia/detalle/x", "/centrodeinfancia/editar/7"]) {
      expect(findRoute(other)?.route.name).not.toBe("cdi-centro-detalle");
    }
  });

  it("keeps the page query, draws hero, header actions and the folder with its side tabs", async () => {
    serve(detalle());
    setup("/centrodeinfancia/detalle/7?observaciones_page=1");
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/7/?observaciones_page=1", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Centro de Desarrollo Infantil: CDI Girasoles"));
    expect(Array.from(document.querySelectorAll(".cdi-hero-stat")).map((s) => s.textContent)).toEqual(["3Nómina", "1Trabajadores", "2019Año de inicio"]);
    expect(screen.getByRole("link", { name: "Ver Nómina" }).getAttribute("href")).toBe("/centrodeinfancia/7/nomina/");
    expect(screen.getByRole("link", { name: "Historial" })).toBeDefined();
    const left = document.getElementById("cdiTabsLeft") as HTMLElement;
    const right = document.getElementById("cdiTabsRight") as HTMLElement;
    expect(within(left).getAllByRole("tab").map((t) => t.textContent)).toEqual(["Información general"]);
    expect(within(right).getAllByRole("tab").map((t) => t.textContent)).toEqual(["Funcionamiento", "Usuarios del centro"]);
    expect(document.querySelector('[data-panel="general"]')?.className).toBe("cdi-panel is-active");
    expect(screen.getByText("No hay datos suficientes para cargar el mapa.")).toBeDefined();
    expect(screen.getByText("Lunes: 08:00 a 16:30")).toBeDefined();
    fireEvent.click(within(right).getByRole("tab", { name: "Funcionamiento" }));
    expect(within(left).getAllByRole("tab").map((t) => t.textContent)).toEqual(["Información general", "Funcionamiento"]);
    expect(document.querySelector('[data-panel="funcionamiento"]')?.className).toBe("cdi-panel is-active");
    expect(document.querySelector('[data-panel="general"]')?.className).toBe("cdi-panel");
  });

  it("opens the tab named by the hash and shows the credential rule per row", async () => {
    serve(detalle({ usuarios: { ...detalle().usuarios, filas: [usuario(1), usuario(2, { password: { kind: "unavailable", value: "" }, acciones: null }), usuario(3, { password: { kind: "changed", value: "" }, estado: "baja", motivo: "Fin", acciones: null })] } }));
    setup("/centrodeinfancia/detalle/7#usuarios");
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    expect(document.querySelector('[data-panel="usuarios"]')?.className).toBe("cdi-panel is-active");
    const rows = within(document.querySelector('[data-panel="usuarios"]') as HTMLElement).getAllByRole("row").slice(1);
    expect(rows[0].textContent).toBe("ref1 ResponsableRef 1ref1@x.testActivoTemp-1—");
    expect(rows[1].textContent).toBe("ref2Ref 2ref2@x.testActivoNo disponible—");
    expect(rows[2].textContent).toBe("ref3Ref 3ref3@x.testBajaYa cambiada—");
    expect(within(rows[2]).getByText("Baja").getAttribute("title")).toBe("Motivo: Fin");
    window.history.replaceState({}, "", "/");
  });

  it("suspends a user through the native write: one POST with accion and motivo, then the native redirect", async () => {
    serve(detalle());
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    fireEvent.click(within(document.getElementById("cdiTabsRight") as HTMLElement).getByRole("tab", { name: "Usuarios del centro" }));
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/detalle/7#usuarios" }, status: 200 });
    fireEvent.click(screen.getAllByRole("button", { name: "Suspender" })[0]);
    const modal = document.getElementById("modalEstadoUsuario") as HTMLElement;
    expect(within(modal).getByText("¿Suspender a Ref 2? No va a poder ingresar al centro hasta que se lo reactive.")).toBeDefined();
    const motivo = within(modal).getByLabelText("Motivo *") as HTMLTextAreaElement;
    expect(motivo.required).toBe(true);
    fireEvent.change(motivo, { target: { value: "Licencia" } });
    fireEvent.submit(modal.querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(centroDetalleNavigation.go).toHaveBeenCalledWith("/centrodeinfancia/detalle/7#usuarios"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/cdi/centros/7/usuarios/2/estado/");
    expect((body as URLSearchParams).toString()).toBe("accion=suspender&motivo=Licencia");
  });

  it("shows the CDI status and, only with estado_url, the Estado button that posts the chosen value once (#2945)", async () => {
    const base = detalle();
    serve(detalle({ centro: { ...base.centro, estado: "pendiente", estado_display: "Pendiente" } }));
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    expect(document.getElementById("cdiEstadoPill")?.className).toBe("cdf-pill cdf-pill--gold");
    expect(document.getElementById("cdiEstadoPill")?.textContent).toBe("Pendiente");
    expect(screen.queryByRole("button", { name: "Estado" })).toBeNull();
    cleanup();

    serve(detalle({ header: { ...base.header, estado_url: "/api/web/cdi/centros/7/estado/" } }));
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    expect(document.getElementById("cdiEstadoPill")?.className).toBe("cdf-pill cdf-pill--success");
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/detalle/7" }, status: 200 });
    fireEvent.click(screen.getByRole("button", { name: "Estado" }));
    const modal = document.getElementById("modalEstadoCentro") as HTMLElement;
    expect((within(modal).getByLabelText("Activo") as HTMLInputElement).checked).toBe(true);
    fireEvent.click(within(modal).getByLabelText("Baja"));
    fireEvent.submit(modal.querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(centroDetalleNavigation.go).toHaveBeenCalledWith("/centrodeinfancia/detalle/7"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/cdi/centros/7/estado/");
    expect((body as URLSearchParams).toString()).toBe("estado=baja");
  });

  it("hides the workers counter and card when the Fuerza de Trabajo rule denies them (#2943)", async () => {
    const base = detalle();
    serve(detalle({ hero: { ...base.hero, trabajadores: null }, trabajadores: null }));
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    const stats = document.querySelector(".cdi-hero-stats") as HTMLElement;
    expect(within(stats).queryByText("Trabajadores")).toBeNull();
    expect(within(stats).getByText("Nómina")).toBeDefined();
    expect(document.getElementById("tablaTrabajadores")).toBeNull();
    expect(document.getElementById("trabajadorSearch")).toBeNull();
    expect(screen.queryByRole("link", { name: "Agregar trabajador" })).toBeNull();
  });

  it("reactivate needs no reason and a rejected write is announced without retrying", async () => {
    serve(detalle());
    setup("/centrodeinfancia/detalle/7#usuarios");
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    webPost.mockResolvedValue({ data: { detail: "No tiene permisos para esta acción." }, status: 403 });
    fireEvent.click(screen.getByRole("button", { name: "Reactivar" }));
    const modal = document.getElementById("modalEstadoUsuario") as HTMLElement;
    expect((within(modal).getByLabelText("Motivo *") as HTMLTextAreaElement).required).toBe(false);
    expect(document.getElementById("usuarioEstadoMotivoGrupo")?.hidden).toBe(true);
    fireEvent.submit(modal.querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith("No tiene permisos para esta acción."));
    expect(centroDetalleNavigation.go).not.toHaveBeenCalled();
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][1].toString()).toBe("accion=reactivar&motivo=");
    window.history.replaceState({}, "", "/");
  });

  it("filters workers client-side and confirms a soft delete with one POST", async () => {
    serve(detalle());
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    fireEvent.change(screen.getByPlaceholderText("Buscar trabajador…"), { target: { value: "pérez" } });
    const rows = within(document.getElementById("tablaTrabajadores") as HTMLElement).getAllByRole("row", { hidden: true }).slice(1);
    expect(rows.map((r) => r.hidden)).toEqual([true, false]);
    expect(within(rows[1]).queryByRole("button", { name: "Eliminar" })).toBeNull();
    fireEvent.change(screen.getByPlaceholderText("Buscar trabajador…"), { target: { value: "" } });
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/detalle/7" }, status: 200 });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    const modal = document.getElementById("modalEliminarTrabajador") as HTMLElement;
    expect(within(modal).getByText("Gómez, Lucía").tagName).toBe("STRONG");
    fireEvent.click(within(modal).getByRole("button", { name: "Cancelar" }));
    expect(document.getElementById("modalEliminarTrabajador")).toBeNull();
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    fireEvent.submit((document.getElementById("modalEliminarTrabajador") as HTMLElement).querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(centroDetalleNavigation.go).toHaveBeenCalledWith("/centrodeinfancia/detalle/7"));
    expect(webPost.mock.calls[0][0]).toBe("web/cdi/centros/7/trabajadores/5/eliminar/");
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("creates an observation from the modal and shows a rejected one inline", async () => {
    serve(detalle());
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    const table = screen.getByText("Texto").closest("table") as HTMLElement;
    expect(within(table).getAllByRole("row")[1].textContent).toBe("01/10/2026 10:00Obs <b>TextoVer");
    expect(screen.getByText("Se encontraron 7 resultados")).toBeDefined();
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?otro=a&observaciones_page=2");
    fireEvent.click(screen.getByRole("button", { name: "Agregar observación" }));
    const modal = document.getElementById("modalObservacion") as HTMLElement;
    const area = within(modal).getByLabelText("Observación") as HTMLTextAreaElement;
    expect(area.placeholder).toBe("Describa la observación");
    webPost.mockResolvedValueOnce({ data: { errors: { observacion: [{ message: "Este campo es requerido." }] } }, status: 400 });
    fireEvent.change(area, { target: { value: "  " } });
    fireEvent.submit(modal.querySelector("form") as HTMLFormElement);
    await screen.findByText("Este campo es requerido.");
    expect(centroDetalleNavigation.go).not.toHaveBeenCalled();
    webPost.mockResolvedValueOnce({ data: { ok: true, redirect: "/centrodeinfancia/detalle/7" }, status: 200 });
    fireEvent.change(area, { target: { value: "Visita" } });
    fireEvent.submit(modal.querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(centroDetalleNavigation.go).toHaveBeenCalledWith("/centrodeinfancia/detalle/7"));
    expect(webPost.mock.calls[1][0]).toBe("web/cdi/centros/7/observaciones/crear/");
    expect((webPost.mock.calls[1][1] as URLSearchParams).toString()).toBe("observacion=Visita&next=%2Fcentrodeinfancia%2Fdetalle%2F7");
  });

  it("omits the results line when the page has no rows, like the native component", async () => {
    serve(detalle({ observaciones: { ...detalle().observaciones, filas: [], paginated: false, next: null, range: [1], count: null } }));
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    expect(screen.getByText("Sin observaciones registradas.")).toBeDefined();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("opens and closes the Acciones menu with the keyboard", async () => {
    serve(detalle());
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    const button = screen.getByRole("button", { name: "Acciones" });
    expect(button.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(button);
    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getAllByRole("link", { name: "Generar usuario" })).toHaveLength(2);
    expect(within(document.querySelector(".dropdown-menu") as HTMLElement).getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/centrodeinfancia/editar/7");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(button.getAttribute("aria-expanded")).toBe("false");
  });

  it("shows access and missing states", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "x" }, status: 404 }));
    setup();
    await screen.findByText("No se encontró la página.");
  });
});
