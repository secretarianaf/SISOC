import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import {
  aporteResult, CdfCard, CdfMonto, CeliaquiaCard, ColaboracionesCard, ComedoresCard, PwaBadges, PwaFilas, VatCard, type AporteState,
} from "./ciudadano360Aportes";
import { fichaValid } from "./ciudadano360";
import { fichaExtra } from "./ciudadano360Fixtures";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const ok = (secciones: Record<string, unknown>): AporteState => ({ status: "ok", secciones });
const UNAVAILABLE: AporteState = { status: "unavailable" };
const LOADING: AporteState = { status: "loading" };
const comedor = { id: 5, nombre: "Comedor Uno", url: "/comedores/5/" };
const comedores = {
  comedores: {
    nomina_actual: { estado: "activo", comedor: { ...comedor, tipo_texto: "Tipo A", provincia_texto: "Prov A", municipio_texto: "-" }, fecha_texto: "01/03/2026" },
    historial: [
      { estado: "activo", comedor, fecha_texto: "01/03/2026" },
      { estado: "baja", comedor: null, fecha_texto: "05/01/2026" },
    ],
  },
  comedores_colaboraciones: [{ comedor, fecha_alta_texto: "03/02/2026", fecha_baja_texto: "-", actividades: ["Cocina", "Limpieza"] }],
};
const vat = {
  vat: {
    programas: [{
      nombre: "Alfa", voucher_badge: { tipo: "referencia", estado_display: "Agotado" }, voucher: { id: 3, url: "/vat/vouchers/3/", estado_display: "Agotado" },
      creditos_totales: 10, creditos_actuales: 0, cursos_asignados: 2, asistencias_presentes: 2, asistencias_registradas: 3,
      inscripciones: [{ curso_texto: "Electricista", comision: { id: 1, codigo: "COM-1", url: "/vat/comisiones/1/" }, estado_display: "Inscripta",
        asistencias_presentes: 2, asistencias_registradas: 3, asistencia_porcentaje: 67, url: "/vat/inscripciones/1/" }],
      inscripciones_oferta: [{ curso_texto: "-", comision: { id: 2, codigo: "COM-2", url: "/vat/comisiones/2/" }, estado_display: "Inscrito", url: "/vat/io/2/" }],
    }],
  },
};

afterEach(() => cleanup());

describe("aporteResult (C2 availability)", () => {
  const good = { aporte: "pwa", secciones: { pwa: { pertenece_comunidad_indigena: false, situacion_calle: true, persona_con_celiaquia: false } } };
  it("accepts a 200 with the expected sections", () => {
    expect(aporteResult("pwa", 200, good).status).toBe("ok");
  });
  it.each([[404, {}], [500, {}], [503, { detail: "x", codigo: "aporte_no_disponible" }], [403, { detail: "Sin permiso" }], [200, "<html>"],
    [200, { aporte: "pwa", secciones: {} }], [200, { aporte: "vat", secciones: good.secciones }], [200, { aporte: "pwa", secciones: { pwa: { situacion_calle: true } } }]])(
    "status %s is unavailable", (status, data) => {
      expect(aporteResult("pwa", status as number, data).status).toBe("unavailable");
    });
  it("a 403 with a web prerequisite is the standard access flow", () => {
    const state = aporteResult("pwa", 403, { detail: "x", state: "password_change_required", required_action_url: "/password/change/" });
    expect(state.status).toBe("forbidden");
  });
});

describe("cards", () => {
  it("Comedores shows the current nomina, the badge, the history and links", () => {
    render(<ComedoresCard state={ok(comedores)} />);
    expect(screen.getByRole("heading", { name: /Comedores\s+Activo/ })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Comedor Uno" })[0].getAttribute("href")).toBe("/comedores/5/");
    expect(screen.getByText("Historial de Comedores")).toBeTruthy();
    expect(screen.getAllByText("Baja").length).toBe(1);
    expect(screen.getByText("Tipo A")).toBeTruthy();
  });
  it("Comedores without nominas shows the native empty text, and a failure only 'No disponible' without badge", () => {
    render(<ComedoresCard state={ok({ comedores: { nomina_actual: null, historial: [] }, comedores_colaboraciones: [] })} />);
    expect(screen.getByText("No hay registros de comedores.")).toBeTruthy();
    cleanup();
    render(<ComedoresCard state={UNAVAILABLE} />);
    expect(screen.getByText("No disponible")).toBeTruthy();
    expect(screen.queryByText("Activo")).toBeNull();
    expect(screen.queryByText("No hay registros de comedores.")).toBeNull();
  });
  it("Colaboraciones draws nothing when empty, loading or failed", () => {
    for (const state of [ok({ ...comedores, comedores_colaboraciones: [] }), LOADING, UNAVAILABLE]) {
      const { container } = render(<ColaboracionesCard state={state} />);
      expect(container.textContent).toBe("");
      cleanup();
    }
    const { container } = render(<ColaboracionesCard state={ok(comedores)} />);
    expect(screen.getByText("Colaboraciones en comedores")).toBeTruthy();
    expect(container.textContent).toContain("Cocina , Limpieza");
  });
  it("PWA rows say Sí/No, never No when the provider failed; badges only for true values", () => {
    const state = ok({ pwa: { pertenece_comunidad_indigena: false, situacion_calle: true, persona_con_celiaquia: false } });
    const rows = render(<PwaFilas state={state} />);
    expect(rows.container.textContent).toBe("Pueblo originario:NoSituación de calle:SíPersona con Celiaquía:No");
    cleanup();
    const badges = render(<PwaBadges state={state} />);
    expect(badges.container.textContent).toContain("Situación de calle");
    expect(badges.container.textContent).not.toContain("Celiaquía");
    cleanup();
    const failed = render(<PwaFilas state={UNAVAILABLE} />);
    expect(failed.container.textContent).toBe("Pueblo originario:No disponibleSituación de calle:No disponiblePersona con Celiaquía:No disponible");
    expect(failed.container.textContent).not.toMatch(/:No(?!\s*d)/);
    cleanup();
    expect(render(<PwaBadges state={UNAVAILABLE} />).container.textContent).toBe("");
  });
  it("Celiaquia keeps the always-on Activo badge and its source labels; empty and failed states", () => {
    const legajo = { estado_expediente: "E1", estado_legajo: "Aprobado", resultado_cruce: "Match", estado_cupo: "Dentro", es_titular_activo: true, revision_tecnica: "Subsanar" };
    render(<CeliaquiaCard state={ok({ celiaquia: { legajo_actual: legajo, historial: [{ estado_legajo: "Aprobado", estado_cupo: "Dentro", creado_en_texto: "01/03/2026 22:30" }, { estado_legajo: "x", estado_cupo: "y", creado_en_texto: "05/01/2026 12:00" }] } })} />);
    expect(screen.getByText("Titular Activo").nextElementSibling?.textContent).toBe("Si");
    expect(screen.getByText("Revision Tecnico")).toBeTruthy();
    expect(screen.getByText("Historial de Expedientes")).toBeTruthy();
    cleanup();
    render(<CeliaquiaCard state={ok({ celiaquia: { legajo_actual: null, historial: [] } })} />);
    expect(screen.getByText("Activo")).toBeTruthy();
    expect(screen.getByText("No hay expedientes de celiaquía registrados.")).toBeTruthy();
    cleanup();
    render(<CeliaquiaCard state={UNAVAILABLE} />);
    expect(screen.queryByText("Activo")).toBeNull();
    expect(screen.getByText("No disponible")).toBeTruthy();
  });
  it("VAT shows programs, badges, links, percentage and the empty / failed texts", () => {
    render(<VatCard state={ok(vat)} />);
    expect(screen.getByText("1 programa")).toBeTruthy();
    expect(screen.getByText("Voucher agotado")).toBeTruthy();
    expect(screen.getByRole("link", { name: "#3" }).getAttribute("href")).toBe("/vat/vouchers/3/");
    expect(screen.getByText("(67%)")).toBeTruthy();
    expect(screen.getByRole("link", { name: "COM-2" }).getAttribute("href")).toBe("/vat/comisiones/2/");
    expect(screen.getAllByRole("link", { name: "Ver inscripción" }).length).toBe(2);
    cleanup();
    render(<VatCard state={ok({ vat: { programas: [] } })} />);
    expect(screen.getByText("No hay registros VAT para este ciudadano.")).toBeTruthy();
    cleanup();
    render(<VatCard state={UNAVAILABLE} />);
    expect(screen.getByText("No disponible")).toBeTruthy();
    expect(screen.queryByText("No hay registros VAT para este ciudadano.")).toBeNull();
  });
  it("CDF shows the table with state badges, the empty text; the amount is the server text or 'No disponible'", () => {
    const secciones = { centrodefamilia: [{ centro_nombre: "Centro Uno", actividad_nombre: "Yoga", estado: "lista_espera", fecha_registro_texto: "04/03/2026" }], centrodefamilia_monto: { total: "0", total_texto: "$0,00" } };
    render(<><CdfCard state={ok(secciones)} /><p data-testid="m"><CdfMonto state={ok(secciones)} /></p></>);
    expect(screen.getByText("Lista Espera")).toBeTruthy();
    expect(screen.getByTestId("m").textContent).toBe("$0,00");
    cleanup();
    render(<CdfCard state={ok({ ...secciones, centrodefamilia: [] })} />);
    expect(screen.getByText("No hay participaciones registradas.")).toBeTruthy();
    cleanup();
    render(<><CdfCard state={UNAVAILABLE} /><p data-testid="m"><CdfMonto state={UNAVAILABLE} /></p></>);
    expect(screen.getByTestId("m").textContent).toBe("No disponible");
    expect(screen.queryByText("$0.00")).toBeNull();
  });
  it("loading shows only the indicator", () => {
    render(<VatCard state={LOADING} />);
    expect(screen.getByRole("status").textContent).toBe("Cargando…");
  });
});

describe("Ciudadano 360 route", () => {
  const ficha = (aportes: unknown[]) => ({
    id: 7, nombre: "Ana", apellido: "Aporte", tipo_documento_texto: "DNI", numero_documento: "30111222", pais_emisor: null, identificador_interno: null, aportes, ...fichaExtra(),
  });
  const entry = (aporte: string, secciones: string[]) => ({ aporte, secciones, url: `/api/web/x/ciudadanos/7/aportes/${aporte}/` });
  function serve(aportes: unknown[], byAporte: Record<string, { status: number; data: unknown } | "reject">) {
    webGet.mockImplementation((url: string) => {
      if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
      if (url === "web/ciudadanos/7/") return Promise.resolve({ data: ficha(aportes), status: 200 });
      const key = /aportes\/([a-z]+)\//.exec(url)?.[1] ?? "";
      const reply = byAporte[key];
      return reply === "reject" ? Promise.reject(new Error("network")) : Promise.resolve(reply);
    });
  }
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
    setViewport(false);
    window.history.replaceState({}, "", "/ciudadanos/ver/7");
  });

  it("owns only /ciudadanos/ver/<pk>", () => {
    expect(findRoute("/ciudadanos/ver/7")?.route.name).toBe("ciudadano-360");
    expect(findRoute("/ciudadanos/ver/7/")?.route.name).not.toBe("ciudadano-360");
    expect(fichaValid(ficha([]))).toBe(true);
    expect(fichaValid({ ...ficha([]), aportes: [{ aporte: "pwa", secciones: [], url: "http://evil/" }] })).toBe(false);
  });

  it("loads every aporte on its own: one down shows 'No disponible', the others render", async () => {
    serve([entry("pwa", ["pwa", "pwa_badges"]), entry("vat", ["vat"]), entry("celiaquia", ["celiaquia"])], {
      pwa: { status: 200, data: { aporte: "pwa", secciones: { pwa: { pertenece_comunidad_indigena: false, situacion_calle: true, persona_con_celiaquia: false } } } },
      vat: { status: 200, data: { aporte: "vat", secciones: { vat: { programas: [] } } } },
      celiaquia: "reject",
    });
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: /Ana Aporte/ })).toBeTruthy();
    await waitFor(() => expect(screen.getByText("No hay registros VAT para este ciudadano.")).toBeTruthy());
    expect(within(screen.getByRole("heading", { level: 1, name: /Ana Aporte/ })).getByText("Situación de calle")).toBeTruthy();
    await waitFor(() => expect(screen.getByText("No disponible")).toBeTruthy());
    expect(webGet).toHaveBeenCalledWith("web/x/ciudadanos/7/aportes/vat/", expect.objectContaining({ validateStatus: expect.any(Function) }));
  });

  it("does not draw an aporte the server did not list", async () => {
    serve([entry("vat", ["vat"])], { vat: { status: 200, data: { aporte: "vat", secciones: { vat: { programas: [] } } } } });
    render(<App />);
    await waitFor(() => expect(screen.getByText("No hay registros VAT para este ciudadano.")).toBeTruthy());
    expect(screen.queryByText("Comedores")).toBeNull();
    // The program card is part of the page; only its amount comes from the provider (native default `$0.00`).
    expect(document.querySelector(".programa-card.centro-familia .monto")?.textContent).toBe("$0.00");
  });

  it("a pending web requirement from a provider shows the standard access screen", async () => {
    serve([entry("vat", ["vat"])], { vat: { status: 403, data: { detail: "x", state: "password_change_required", required_action_url: "/password/change/" } } });
    render(<App />);
    expect(await screen.findByText("Antes de continuar")).toBeTruthy();
  });
});
