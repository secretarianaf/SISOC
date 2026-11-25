import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import Groups from "./Groups";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({ crearCliente: () => ({ get, post }), leerCookie: () => "synthetic" }));
const presentation = { user: { username: "synthetic", display_name: "Ana", avatar_initial: "A", role_label: "-" }, footer_version_label: "Versiones", legacy_frame_navigation: [] };
const metadata = { title: "Crear grupo", submit_text: "Crear grupo", presentation, errors: {}, initial: { name: "", permissions: [] }, fields: [
  { name: "name", label: "Nombre", required: true, max_length: 150, help_text: "" },
  { name: "permissions", label: "Permisos (roles)", required: false, help_text: "Permisos del grupo.", choices: [{ id: 1, label: "Autenticación | grupo | Can view group" }, { id: 2, label: "Autenticación | grupo | Can change group" }] },
] };
beforeEach(() => { vi.resetAllMocks(); vi.spyOn(window, "scrollTo").mockImplementation(() => undefined); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("renders React-owned dual controls without loading the guarded Admin catalog", async () => {
  get.mockResolvedValue({ data: metadata }); render(<Groups mode="create" />);
  await screen.findByLabelText(/Nombre/);
  expect(document.querySelectorAll(".selector select")).toHaveLength(2);
  expect(document.querySelector('script[src*="jsi18n"]')).toBeNull();
  expect(screen.getByText("Choose all")).toBeTruthy();
  expect(screen.getByText("Permisos disponibles")).toBeTruthy();
  expect(get.mock.calls[0][0]).toBe("web/groups/create/");
});

it("filters and transfers permissions, then posts all chosen IDs once", async () => {
  get.mockResolvedValue({ data: metadata }); post.mockResolvedValue({ data: { ok: true, redirect: "/grupos/" } });
  const navigate = vi.fn(); render(<Groups mode="create" navigate={navigate} />);
  fireEvent.change(await screen.findByLabelText(/Nombre/), { target: { value: "Nuevo" } });
  fireEvent.change(screen.getByPlaceholderText("Filtro"), { target: { value: "change" } });
  fireEvent.click(screen.getByText("Choose all"));
  expect(document.querySelector<HTMLSelectElement>("#id_permissions_to")!.options).toHaveLength(1);
  fireEvent.submit(document.querySelector("form")!);
  await waitFor(() => expect(navigate).toHaveBeenCalledWith("/grupos/"));
  const body = post.mock.calls[0][1] as URLSearchParams;
  expect(body.get("name")).toBe("Nuevo"); expect(body.getAll("permissions")).toEqual(["2"]); expect(post).toHaveBeenCalledOnce();
});

it("preserves edit selection and can remove all without a permissions value", async () => {
  get.mockResolvedValue({ data: { ...metadata, initial: { name: "Editado", permissions: ["1"] } } });
  post.mockResolvedValue({ data: { ok: true, redirect: "/grupos/" } });
  render(<Groups mode="edit" id="7" navigate={vi.fn()} />); await screen.findByLabelText(/Nombre/);
  expect(get.mock.calls[0][0]).toBe("web/groups/7/edit/");
  expect(document.querySelector<HTMLSelectElement>("#id_permissions_to")!.options[0].value).toBe("1");
  fireEvent.click(screen.getByText("Remove all")); fireEvent.submit(document.querySelector("form")!);
  await waitFor(() => expect(post).toHaveBeenCalledOnce()); expect(post.mock.calls[0][1].getAll("permissions")).toEqual([]);
});

it("lists initially chosen permissions in catalog order like the native widget", async () => {
  get.mockResolvedValue({ data: { ...metadata, initial: { name: "Editado", permissions: ["2", "1"] } } });
  render(<Groups mode="edit" id="7" />); await screen.findByLabelText(/Nombre/);
  expect(Array.from(document.querySelector<HTMLSelectElement>("#id_permissions_to")!.options, o => o.value)).toEqual(["1", "2"]);
});

it("restores invalid-response chosen permissions in catalog order", async () => {
  get.mockResolvedValue({ data: metadata });
  post.mockRejectedValue({ response: { status: 400, data: { ...metadata, initial: { name: "", permissions: ["2", "1"] }, errors: { name: [{ message: "Este campo es obligatorio.", code: "required" }] } } } });
  render(<Groups mode="create" />); await screen.findByLabelText(/Nombre/);
  fireEvent.submit(document.querySelector("form")!);
  await screen.findByText("Este campo es obligatorio.");
  expect(Array.from(document.querySelector<HTMLSelectElement>("#id_permissions_to")!.options, o => o.value)).toEqual(["1", "2"]);
  expect(document.querySelector("#id_permissions_remove_all_link")!.classList.contains("active")).toBe(true);
  expect(document.querySelector("#id_permissions_add_all_link")!.classList.contains("active")).toBe(false);
});

it("keeps source filter Enter transfer and append ordering without submitting", async () => {
  get.mockResolvedValue({ data: metadata }); render(<Groups mode="create" />);
  const filter = await screen.findByPlaceholderText("Filtro");
  fireEvent.change(filter, { target: { value: "change" } }); fireEvent.keyDown(filter, { key: "Enter" });
  expect(Array.from(document.querySelector<HTMLSelectElement>("#id_permissions_to")!.options, o => o.value)).toEqual(["2"]);
  fireEvent.change(filter, { target: { value: "" } }); fireEvent.keyDown(filter, { key: "Enter" });
  expect(Array.from(document.querySelector<HTMLSelectElement>("#id_permissions_to")!.options, o => o.value)).toEqual(["2", "1"]);
  expect(post).not.toHaveBeenCalled();
});

it("preserves the next available selected row after a filter transfer", async () => {
  get.mockResolvedValue({ data: metadata }); render(<Groups mode="create" />);
  const filter = await screen.findByPlaceholderText("Filtro"); fireEvent.keyDown(filter, { key: "Enter" });
  expect(Array.from(document.querySelector<HTMLSelectElement>("#id_permissions_from")!.selectedOptions, o => o.value)).toEqual(["2"]);
  expect(document.querySelector("#id_permissions_add_link")!.classList.contains("active")).toBe(false);
});

it("keeps native chooser icon state stale after filter keyboard moves until a selection change", async () => {
  get.mockResolvedValue({ data: metadata }); render(<Groups mode="create" />);
  const link = (id: string) => document.querySelector(`#id_permissions_${id}_link`)!.classList.contains("active");
  const filter = await screen.findByPlaceholderText("Filtro");
  expect([link("add"), link("remove"), link("add_all"), link("remove_all")]).toEqual([false, false, true, false]);
  fireEvent.keyDown(filter, { key: "Enter" });
  expect([link("add"), link("remove"), link("add_all"), link("remove_all")]).toEqual([false, false, true, false]);
  fireEvent.click(screen.getByText("Choose"));
  expect(Array.from(document.querySelector<HTMLSelectElement>("#id_permissions_to")!.options, o => o.value)).toEqual(["1"]);
  fireEvent.change(document.querySelector<HTMLSelectElement>("#id_permissions_from")!);
  expect([link("add"), link("remove"), link("add_all"), link("remove_all")]).toEqual([true, false, true, true]);
  fireEvent.click(screen.getByText("Choose"));
  expect(Array.from(document.querySelector<HTMLSelectElement>("#id_permissions_to")!.options, o => o.value)).toEqual(["1", "2"]);
  expect([link("add"), link("remove"), link("add_all"), link("remove_all")]).toEqual([false, false, false, true]);
});

it("retains native topbar spacing without export authorization", async () => {
  get.mockResolvedValue({ data: { presentation, query: "", messages: [], can_export: false, items: [], columns: { list_key: "grupos_list", endpoint: "/ajax/columnas-preferencias/", active: ["name"], defaults: ["name"], available: [{ key: "name", title: "Nombre", active: true, required: false, default: true }] } } });
  render(<Groups mode="list" />); await screen.findByText("No hay grupos disponibles.");
  expect(document.querySelector(".poncho-topbar")).not.toBeNull();
  expect(screen.queryByRole("button", { name: "Exportar búsqueda" })).toBeNull();
});

it("prepares asynchronous list wrappers and updates native scroll hints without fixed shadows", async () => {
  get.mockResolvedValue({ data: { presentation, query: "", messages: [], can_export: false, items: [], columns: { list_key: "grupos_list", endpoint: "/ajax/columnas-preferencias/", active: ["name"], defaults: ["name"], available: [{ key: "name", title: "Nombre", active: true, required: false, default: true }] } } });
  const view = render(<Groups mode="list" />);
  const container = (await screen.findByRole("table")).parentElement!;
  expect(container.classList.contains("poncho-scroll")).toBe(true);
  expect(container.closest(".card-body")?.classList.contains("poncho-scroll")).toBe(true);
  Object.defineProperties(container, {
    clientWidth: { configurable: true, value: 300 },
    scrollWidth: { configurable: true, value: 900 },
    scrollLeft: { configurable: true, writable: true, value: 0 },
  });
  fireEvent.resize(window);
  expect(container.classList.contains("poncho-scroll--der")).toBe(true);
  expect(container.classList.contains("poncho-scroll--izq")).toBe(false);
  container.scrollLeft = 100; fireEvent.scroll(container);
  expect(container.classList.contains("poncho-scroll--izq")).toBe(true);
  expect(container.classList.contains("poncho-scroll--der")).toBe(true);
  container.scrollLeft = 600; fireEvent.scroll(container);
  expect(container.classList.contains("poncho-scroll--der")).toBe(false);
  Object.defineProperty(container, "scrollWidth", { configurable: true, value: 301 });
  fireEvent.resize(window);
  expect(container.classList.contains("poncho-scroll--izq")).toBe(false);
  expect(container.classList.contains("poncho-scroll--der")).toBe(false);
  view.unmount(); fireEvent.resize(window); fireEvent.scroll(container);
  expect(post).not.toHaveBeenCalled();
});

it("shows native invalid errors and retains bound values without inventing autofocus", async () => {
  get.mockResolvedValue({ data: metadata }); post.mockRejectedValue({ response: { status: 400, data: { ...metadata, initial: { name: "EXISTING", permissions: [] }, errors: { name: [{ message: "Ya existe un grupo con ese nombre.", code: "" }] } } } });
  render(<Groups mode="create" />); await screen.findByLabelText(/Nombre/); fireEvent.submit(document.querySelector("form")!);
  await screen.findByText("Ya existe un grupo con ese nombre."); expect((screen.getByLabelText(/Nombre/) as HTMLInputElement).value).toBe("EXISTING");
  expect(document.activeElement).not.toBe(screen.getByLabelText(/Nombre/));
});

it("blocks uncertain resubmission and does not claim success or follow foreign destinations", async () => {
  get.mockResolvedValue({ data: metadata }); post.mockResolvedValue({ data: { ok: true, redirect: "https://example.invalid" } });
  const navigate = vi.fn(); render(<Groups mode="create" navigate={navigate} />); await screen.findByLabelText(/Nombre/); fireEvent.submit(document.querySelector("form")!);
  await screen.findByRole("alert"); fireEvent.submit(document.querySelector("form")!); expect(post).toHaveBeenCalledOnce(); expect(navigate).not.toHaveBeenCalled();
});

it("renders the source list, columns, edit links and original export route", async () => {
  get.mockResolvedValue({ data: { presentation, query: "", messages: [], can_export: true, items: [{ id: 7, name: "Grupo", permissions_count: 2 }], columns: { list_key: "grupos_list", endpoint: "/ajax/columnas-preferencias/", active: ["name", "permissions_count"], defaults: ["name", "permissions_count"], available: [{ key: "name", title: "Nombre", active: true, required: false, default: true }, { key: "permissions_count", title: "Permisos", active: true, required: false, default: true }, { key: "id", title: "ID", active: false, required: false, default: false }] } } });
  render(<Groups mode="list" />); await screen.findByText("Grupo");
  expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/grupos/editar/7/");
  expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/grupos/crear/");
  expect(screen.getByRole("button", { name: "Exportar búsqueda" }).getAttribute("data-url")).toBe("/grupos/exportar/");
  fireEvent.click(screen.getByRole("button", { name: "Configurar columnas" }));
  expect(screen.getByText("Columnas visibles")).toBeTruthy();
});

it("keeps permission denial separate from loading errors", async () => {
  get.mockResolvedValue({ status: 403, data: { detail: "Denegado" } }); render(<Groups mode="create" />);
  await waitFor(() => expect(document.querySelector("form")).toBeNull());
  await waitFor(() => expect(screen.queryByText("Cargando grupos…")).toBeNull());
});
