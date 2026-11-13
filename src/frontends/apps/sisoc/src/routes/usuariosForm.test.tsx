import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { navigation } from "./userImport";
import { UsuarioFormContent, territorialTransport, type UsuarioFormData } from "./usuariosForm";
import { setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
  mensajeDeError: vi.fn(() => "Error de prueba"),
  SinPermiso: class SinPermiso extends Error {},
}));

const presentation = { user: { username: "synthetic", display_name: "Ana", avatar_initial: "A", role_label: "-" }, footer_version_label: "Versiones", legacy_frame_navigation: [] };
type Spec = Record<string, unknown>;
const f = (name: string, kind: string, label: string, extra: Spec = {}) => ({ name, kind, label, required: false, disabled: false, help_text: "", max_length: null, value: kind === "boolean" ? false : kind === "multiselect" ? [] : "", ...extra });
const formData = (extra: Spec = {}) => ({
  mode: "create", title: "Usuarios", object: null,
  sections: [
    { key: "personal", fields: [f("first_name", "text", "Nombre", { max_length: 150 }), f("last_name", "text", "Apellido"), f("dni", "text", "DNI"), f("cuil", "text", "CUIL"),
      f("tipo_usuario", "radio", "Tipo de usuario", { required: true, choices: [{ value: "interno", label: "Interno" }, { value: "externo", label: "Externo" }] })] },
    { key: "access", fields: [f("username", "text", "Nombre de usuario", { required: true }), f("email", "email", "Dirección de email"), f("password", "password", "Contraseña", { required: true })] },
    { key: "datacalle", fields: [f("es_relevador_calle", "boolean", "Habilitar acceso a SISOC - Mobile DataCalle"), f("datacalle_rol", "select", "Rol en DataCalle", { choices: [{ value: "", label: "---------" }, { value: "entrevistador", label: "Relevador" }] }), f("provincias_datacalle", "multiselect", "Provincias", { choices: [] })] },
    { key: "permissions", fields: [f("groups", "multiselect", "Grupos", { choices: [{ value: "5", label: "Grupo cinco" }] }), f("rol", "text", "Rol (descriptivo)")] },
    { key: "territorial", fields: [f("es_usuario_provincial", "boolean", "Es usuario provincial"), f("provincia", "select", "Provincia", { choices: [{ value: "", label: "---------" }, { value: "2", label: "Provincia dos" }] }), f("territorial_scopes", "hidden", "Alcances territoriales", { value: "[]" })] },
    { key: "delegation", fields: [f("user_permissions", "multiselect", "Permisos directos", { choices: [] }), f("acceso_web", "boolean", "Acceso SISOC web", { value: true }), f("acceso_siis", "boolean", "Acceso SIIS", { disabled: true })] },
  ],
  identity_present: ["es_relevador_calle", "groups", "es_usuario_provincial", "acceso_web"],
  errors: {}, comedores: { sections: [], runtime_required: true },
  territorial: { initial: [], municipios_url: "/ajax/load-municipios/", localidades_url: "/ajax/load-localidades/" },
  urls: { cancel: "/usuarios/" }, submit_text: "Confirmar", credential: null, messages: [], presentation, ...extra,
});

let assign: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); webGet.mockReset(); webPost.mockReset(); window.history.replaceState(null, "", "/"); });

async function open(data = formData(), path = "/usuarios/crear/") {
  const id = path.match(/editar\/([0-9]+)/)?.[1];
  render(<UsuarioFormContent data={data as unknown as UsuarioFormData} endpoint={id ? `web/users/${id}/edit/` : "web/users/create/"} onForbidden={() => undefined} />);
  return screen.findByRole("button", { name: /Confirmar/ });
}
const posted = () => webPost.mock.calls[0][1] as URLSearchParams;

describe("user form", () => {
  it("draws the native cards in order", async () => {
    await open();
    expect(Array.from(document.querySelectorAll(".card-header h5"), (n) => n.textContent)).toEqual(["Datos Personales", "Datos de Acceso", "Acceso SISOC - Mobile DataCalle", "Permisos y Roles", "Alcance territorial", "Administración de accesos"]);
    expect(screen.getByLabelText(/Contraseña/, { selector: "input" }).getAttribute("type")).toBe("password");
    expect(document.getElementById("relevador-calle-detalle-wrapper")!.style.display).toBe("none");
    expect((screen.getByLabelText("Acceso SIIS") as HTMLInputElement).disabled).toBe(true);
  });

  it("shows and posts to the edit transport, the temporary credential only when it is projected", async () => {
    await open(formData({ mode: "edit", object: { id: 7, username: "u" }, credential: { temporary_password: "Temporal-1" } }), "/usuarios/editar/7/");
    fireEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe("web/users/7/edit/");
    expect(screen.getByText("Temporal-1")).toBeTruthy();
  });

  it("toggles the password and the detail cards like the native scripts", async () => {
    await open();
    const password = screen.getByLabelText(/Contraseña/, { selector: "input" });
    fireEvent.click(screen.getByRole("button", { name: "Mostrar la contraseña" }));
    expect(password.getAttribute("type")).toBe("text");
    expect(screen.getByRole("button", { name: "Ocultar la contraseña" }).getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(screen.getByLabelText("Habilitar acceso a SISOC - Mobile DataCalle"));
    expect(document.getElementById("relevador-calle-detalle-wrapper")!.style.display).toBe("");
  });

  it("posts the enabled controls with the present markers and follows the native redirect", async () => {
    await open();
    fireEvent.change(screen.getByLabelText(/Nombre de usuario/), { target: { value: "ada" } });
    fireEvent.change(screen.getByLabelText(/Contraseña/, { selector: "input" }), { target: { value: "Clave-123" } });
    fireEvent.click(screen.getByLabelText("Interno"));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/usuarios/" } });
    fireEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/usuarios/"));
    const body = posted();
    expect(webPost.mock.calls[0][0]).toBe("web/users/create/");
    expect(body.get("username")).toBe("ada");
    expect(body.get("password")).toBe("Clave-123");
    expect(body.get("tipo_usuario")).toBe("interno");
    expect(body.get("acceso_web")).toBe("on");
    expect(body.has("acceso_siis")).toBe(false);
    expect(body.has("es_relevador_calle")).toBe(false);
    expect(body.get("territorial_scopes")).toBe("[]");
    expect(body.getAll("_identity_present")).toEqual(["es_relevador_calle", "groups", "es_usuario_provincial", "acceso_web"]);
  });

  it("re-renders the bound values and the native errors after a rejected post, and sends once", async () => {
    await open();
    fireEvent.change(screen.getByLabelText(/Nombre de usuario/), { target: { value: "ada" } });
    const rejected = formData({ errors: { username: [{ message: "Ya existe un usuario con este nombre de usuario.", code: "unique" }] } });
    (rejected.sections[1].fields[0] as Spec).value = "ada";
    webPost.mockRejectedValue({ response: { status: 400, data: rejected } });
    fireEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    expect(await screen.findByText("Ya existe un usuario con este nombre de usuario.")).toBeTruthy();
    expect((screen.getByLabelText(/Nombre de usuario/) as HTMLInputElement).value).toBe("ada");
    expect(screen.getByLabelText(/Nombre de usuario/).classList.contains("is-invalid")).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("reports an unconfirmed outcome and never resends", async () => {
    await open();
    webPost.mockResolvedValue({ status: 200, data: {} });
    fireEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado.");
    expect((screen.getByRole("button", { name: /Confirmar/ }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("builds the territorial scopes through cascaded options and posts them as JSON", async () => {
    const options = vi.spyOn(territorialTransport, "options").mockImplementation(async (_url, key) => (key === "provincia_id" ? [{ id: 9, nombre: "Municipio nueve" }] : [{ id: 4, nombre: "Localidad cuatro" }]));
    await open();
    fireEvent.click(screen.getByLabelText("Es usuario provincial"));
    fireEvent.click(screen.getByRole("button", { name: /Agregar alcance/ }));
    const panel = document.getElementById("territorial-scopes-panel") as HTMLElement;
    const choose = async (label: string, option: string) => {
      fireEvent.mouseDown(within(panel).getByLabelText(label, { selector: "select" }).parentElement!.querySelector(".select2-selection")!);
      fireEvent.click(await screen.findByRole("option", { name: option }));
    };
    await choose("Provincia", "Provincia dos");
    await waitFor(() => expect(options).toHaveBeenCalledWith("/ajax/load-municipios/", "provincia_id", "2"));
    await choose("Municipio", "Municipio nueve");
    await waitFor(() => expect(options).toHaveBeenCalledWith("/ajax/load-localidades/", "municipio_id", "9"));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/usuarios/" } });
    fireEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    await waitFor(() => expect(assign).toHaveBeenCalled());
    expect(JSON.parse(posted().get("territorial_scopes") as string)).toEqual([{ provincia_id: "2", municipio_id: "9", localidad_id: null }]);
    options.mockRestore();
  });
});
