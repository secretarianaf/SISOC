import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { navigation } from "./userImport";
import { usuariosRoute } from "./usuarios";
import { usuariosNavigation } from "./usuariosList";
import { setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
  mensajeDeError: vi.fn(() => "Error de prueba"),
  SinPermiso: class SinPermiso extends Error {},
}));

const presentation = { user: { username: "synthetic", display_name: "Ana", avatar_initial: "A", role_label: "-" }, footer_version_label: "Versiones", legacy_frame_navigation: [] };
const column = (key: string, title: string, active = true) => ({ key, title, active, required: false, default: active });
const action = (label: string, url: string, type: string, icon: string) => ({ label, url, type, icon });
const listData = (extra = {}) => ({
  filters_config: { fields: [{ name: "username", label: "Usuario", type: "text" }, { name: "email", label: "Email", type: "text" }] },
  favorites: { section: "usuarios", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" },
  urls: { list: "/usuarios/", reset: "/usuarios/", add: "/usuarios/crear/", export: "/usuarios/exportar/" },
  show_add_button: true,
  additional_buttons: [{ label: "GESTOR DE USUARIOS", url: "/usuarios/importar/", class: "btn btn-lg btn-primary", title: "Importar usuarios masivamente desde Excel" }],
  can_export: true,
  columns: { list_key: "usuarios_list", endpoint: "/ajax/columnas-preferencias/", modal_id: "column-config-modal-usuarios_list", script_id: "column-config-usuarios_list",
    available: [column("first_name", "Nombre"), column("username", "Username")], active: ["first_name", "username"], defaults: ["first_name", "username"] },
  headers: [{ title: "Nombre", width: "12%", sortable: true, sort_key: "first_name" }, { title: "Username", width: "10%", sortable: true, sort_key: "username" }],
  results: [
    { id: 7, cells: ["Zoe", "zoe_user"], actions: [action("Editar", "/usuarios/editar/7/", "primary", "edit"), action("Desactivar", "/usuarios/borrar/7/", "danger", "trash-alt")] },
    { id: 8, cells: ["Ana", "ana_user"], actions: [action("Editar", "/usuarios/editar/8/", "primary", "edit"), action("Activar", "/usuarios/activar/8/", "success", "check-circle")] },
  ],
  page: { is_paginated: true, number: 1, count: 30, previous: null, next: 2, range: [1, 2], query_without_page: "filters=%7B%7D&" },
  messages: [],
  presentation,
  ...extra,
});
const stateData = (extra = {}) => ({
  title: "Desactivar Usuario", message: "¿Estás seguro que deseas desactivar el usuario", object_name: "ZOE_USER",
  confirm_text: "Desactivar", confirm_class: "btn-danger", cancel_url: "/usuarios/", presentation, ...extra,
});

let assign: ReturnType<typeof vi.spyOn>;
let exportAssign: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
  exportAssign = vi.spyOn(usuariosNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  assign.mockRestore();
  exportAssign.mockRestore();
  webGet.mockReset();
  webPost.mockReset();
  window.history.replaceState(null, "", "/");
});

async function openList(data = listData(), search = "") {
  window.history.replaceState(null, "", `/usuarios/${search}`);
  webGet.mockResolvedValue({ status: 200, data });
  render(<App />);
  return screen.findByRole("heading", { name: "Buscar Usuario" });
}

describe("user list", () => {
  it("reads only its own transport (with the query) and renders the native list", async () => {
    await openList(listData(), "?page=2&filters=%7B%7D");
    expect(webGet).toHaveBeenCalledTimes(1);
    expect(webGet).toHaveBeenCalledWith("web/users/list/?page=2&filters=%7B%7D", expect.any(Object));
    await waitFor(() => expect(document.title).toBe("SISOC - Usuarios"));
    expect(screen.getAllByRole("columnheader").map((th) => th.textContent?.trim())).toEqual(["Nombre", "Username", "Acciones"]);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getAllByRole("cell").slice(0, 2).map((td) => td.textContent))).toEqual([["Zoe", "zoe_user"], ["Ana", "ana_user"]]);
    expect(screen.getByRole("link", { name: /Desactivar/ }).getAttribute("href")).toBe("/usuarios/borrar/7/");
    expect(screen.getByRole("link", { name: /Activar/ }).getAttribute("href")).toBe("/usuarios/activar/8/");
    expect(screen.getAllByRole("link", { name: /Editar/ }).map((a) => a.getAttribute("href"))).toEqual(["/usuarios/editar/7/", "/usuarios/editar/8/"]);
    expect(screen.getByRole("link", { name: /Agregar/ }).getAttribute("href")).toBe("/usuarios/crear/");
    expect(screen.getByRole("link", { name: "GESTOR DE USUARIOS" }).getAttribute("href")).toBe("/usuarios/importar/");
    expect(screen.getByText("Se encontraron 30 resultados")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?filters=%7B%7D&page=2");
  });

  it("renders only the controls the server allowed", async () => {
    await openList(listData({ can_export: false, show_add_button: false, additional_buttons: [] }));
    expect(screen.queryByRole("button", { name: /Exportar búsqueda/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Agregar/ })).toBeNull();
    expect(screen.queryByRole("link", { name: "GESTOR DE USUARIOS" })).toBeNull();
  });

  it("shows the native empty notice and server messages", async () => {
    await openList(listData({ results: [], messages: [{ message: "Usuario desactivado correctamente.", level: "success" }] }));
    expect(screen.getByText("No hay usuarios disponibles.").getAttribute("colspan")).toBe("3");
    expect(await screen.findByText("Usuario desactivado correctamente.")).toBeTruthy();
  });

  it("sorts rows locally and exports the query plus the active sort through the native URL", async () => {
    await openList(listData(), "?page=2");
    fireEvent.click(screen.getByRole("columnheader", { name: /Nombre/ }));
    expect(screen.getAllByRole("row").slice(1).map((row) => within(row).getAllByRole("cell")[0].textContent)).toEqual(["Ana", "Zoe"]);
    fireEvent.click(screen.getByRole("button", { name: /Exportar búsqueda/ }));
    expect(exportAssign).toHaveBeenCalledWith("/usuarios/exportar/?page=2&sort=first_name&direction=asc");
  });

  it("shows the prerequisite on a 403 and an error for an unexpected payload", async () => {
    window.history.replaceState(null, "", "/usuarios/");
    webGet.mockResolvedValue({ status: 403, data: { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" } });
    const view = render(<App />);
    expect(await screen.findByRole("link", { name: "Continuar en SISOC" })).toBeTruthy();
    view.unmount();
    webGet.mockResolvedValue({ status: 200, data: { results: [] } });
    render(<App />);
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar el listado de usuarios.");
  });
});

async function openState(mode: "borrar" | "activar", data = stateData()) {
  window.history.replaceState(null, "", `/usuarios/${mode}/7/`);
  webGet.mockResolvedValue({ status: 200, data });
  render(<App />);
  return screen.findByRole("button", { name: data.confirm_text });
}

describe("user state confirmation", () => {
  it("reads the object through its own endpoint and renders the native confirmation", async () => {
    await openState("borrar");
    expect(webGet).toHaveBeenCalledWith("web/users/7/deactivate/", expect.any(Object));
    expect(document.querySelector(".error-content h3")?.textContent).toBe(" Desactivar Usuario");
    expect(document.querySelector(".error-content p")?.textContent).toBe("¿Estás seguro que deseas desactivar el usuario ZOE_USER?");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/usuarios/");
    expect(webPost).not.toHaveBeenCalled();
  });

  it("uses the activate endpoint and its native copy", async () => {
    await openState("activar", stateData({ title: "Activar Usuario", message: "¿Estás seguro que deseas activar el usuario", confirm_text: "Activar", confirm_class: "btn-success" }));
    expect(webGet).toHaveBeenCalledWith("web/users/7/activate/", expect.any(Object));
    expect(screen.getByRole("button", { name: "Activar" }).className).toContain("btn-success");
  });

  it("posts once without a body and goes back to the list on the confirmed redirect", async () => {
    const button = await openState("borrar");
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/usuarios/" } });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/usuarios/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/users/7/deactivate/");
    expect(String(webPost.mock.calls[0][1])).toBe("");
  });

  it("reports an unconfirmed outcome and never resends", async () => {
    const button = await openState("borrar");
    webPost.mockRejectedValue(Object.assign(new Error("network"), { response: { status: 500, data: {} } }));
    fireEvent.click(button);
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado");
    expect((button as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(button);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(assign).not.toHaveBeenCalled();
  });

  it("does not follow an unexpected redirect target", async () => {
    const button = await openState("borrar");
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "https://example.invalid/" } });
    fireEvent.click(button);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });

  it("shows the prerequisite when the POST is refused", async () => {
    const button = await openState("borrar");
    webPost.mockResolvedValue({ status: 403, data: { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" } });
    fireEvent.click(button);
    expect(await screen.findByRole("link", { name: "Continuar en SISOC" })).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });

  it("shows a load error when the user cannot be read", async () => {
    window.history.replaceState(null, "", "/usuarios/borrar/7/");
    webGet.mockRejectedValue(new Error("404"));
    render(<App />);
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar el usuario.");
  });
});

describe("usuarios route", () => {
  it("claims only the list and the two state steps", () => {
    expect(usuariosRoute.match("/usuarios/")).toEqual({ mode: "list" });
    expect(usuariosRoute.match("/usuarios/borrar/12/")).toEqual({ mode: "deactivate", id: "12" });
    expect(usuariosRoute.match("/usuarios/activar/12/")).toEqual({ mode: "activate", id: "12" });
    for (const other of ["/usuarios/importar/", "/usuarios/crear/", "/usuarios/editar/1/", "/usuarios/borrar/x/", "/usuarios/exportar/", "/usuarios"]) {
      expect(usuariosRoute.match(other)).toBeNull();
    }
  });
});
