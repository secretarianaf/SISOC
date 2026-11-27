import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ComedorValidacion, { comedorValidacionNavigation, validacionValid } from "./comedorValidacion";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/comedores/7/validacion/";
const POST = "web/comedores/comedores/7/validar/";
const data = (over: Record<string, unknown> = {}) => ({
  id: 7, puede_validar: true,
  opciones: [{ value: "sin_movimiento", label: "Sin movimiento" }, { value: "otro", label: "Otros" }],
  urls: { ficha: "/comedores/7" }, ...over,
});

function Host({ onClose = () => undefined }: { onClose?: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>Abrir</button>
      <ComedorValidacion comedorId={7} open={open} onClose={() => { setOpen(false); onClose(); }} />
    </>
  );
}

let assign: ReturnType<typeof vi.spyOn>;
let alert: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  vi.clearAllMocks();
  webGet.mockResolvedValue({ status: 200, data: data() });
  assign = vi.spyOn(comedorValidacionNavigation, "assign").mockImplementation(() => undefined);
  alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); alert.mockRestore(); });

const open = async () => {
  fireEvent.click(screen.getByRole("button", { name: "Abrir" }));
  await screen.findByText("Seleccione una opción para validar el comedor:");
};
const pickMotivos = (...labels: string[]) => {
  for (const label of labels) {
    fireEvent.mouseDown(document.querySelector(".select2-selection") as HTMLElement);
    fireEvent.click(screen.getByRole("option", { name: label }));
  }
};

describe("Comedor validation modals (CO07.03)", () => {
  it("validates the payload the server sends", () => {
    expect(validacionValid(data())).toBe(true);
    expect(validacionValid(data({ urls: { ficha: "https://externo.example/" } }))).toBe(false);
    expect(validacionValid(data({ puede_validar: "si" }))).toBe(false);
  });

  it("renders nothing until opened, then the native first modal with its texts", async () => {
    render(<Host />);
    expect(document.querySelector("#modalValidacion")).toBeNull();
    await open();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    expect(screen.getByText("Validación del Comedor", { selector: "h5" })).toBeTruthy();
    for (const name of ["Validar", "No Validar", "Cancelar", "Close"]) expect(screen.getByRole("button", { name })).toBeTruthy();
    expect(webPost).not.toHaveBeenCalled();
  });

  it("posts accion=validar with the ficha as next and follows the redirect", async () => {
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/comedores/7" } });
    render(<Host />);
    await open();
    fireEvent.click(screen.getByRole("button", { name: "Validar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(POST);
    expect(Object.fromEntries(body as URLSearchParams)).toEqual({ accion: "validar", next: "/comedores/7" });
  });

  it("cancel closes without posting, in both modals", async () => {
    const closed = vi.fn();
    render(<Host onClose={closed} />);
    await open();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(document.querySelector("#modalValidacion")).toBeNull();
    await open();
    fireEvent.click(screen.getByRole("button", { name: "No Validar" }));
    expect(await screen.findByText("Motivos de No Validación", { selector: "h5" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(closed).toHaveBeenCalledTimes(2);
    expect(webPost).not.toHaveBeenCalled();
  });

  it("No Validar without a reason alerts the native text and posts nothing", async () => {
    render(<Host />);
    await open();
    fireEvent.click(screen.getByRole("button", { name: "No Validar" }));
    fireEvent.click(await screen.findByRole("button", { name: "No Validar" }));
    expect(alert).toHaveBeenCalledWith("Debe seleccionar al menos una opción.");
    expect(webPost).not.toHaveBeenCalled();
  });

  it("«Otros» shows the comment, requires it, and posts the options with it", async () => {
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/comedores/7" } });
    render(<Host />);
    await open();
    fireEvent.click(screen.getByRole("button", { name: "No Validar" }));
    await screen.findByText("Motivos de No Validación", { selector: "h5" });
    expect(document.getElementById("comentarioDiv")?.className).toContain("d-none");
    pickMotivos("Sin movimiento", "Otros");
    expect(document.getElementById("comentarioDiv")?.className).not.toContain("d-none");
    fireEvent.click(screen.getAllByRole("button", { name: "No Validar" }).at(-1)!);
    expect(alert).toHaveBeenCalledWith('El comentario es obligatorio cuando selecciona "Otro".');
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(document.getElementById("comentario") as HTMLTextAreaElement, { target: { value: "detalle" } });
    fireEvent.click(screen.getAllByRole("button", { name: "No Validar" }).at(-1)!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
    const body = webPost.mock.calls[0][1] as URLSearchParams;
    expect(body.getAll("opciones")).toEqual(["sin_movimiento", "otro"]);
    expect(body.get("accion")).toBe("no_validar");
    expect(body.get("comentario")).toBe("detalle");
    expect(body.get("next")).toBe("/comedores/7");
  });

  it("the second modal shows without modal-open or the scroll lock (Bootstrap drops them when the first finishes hiding) and brings the select2 styles", async () => {
    render(<Host />);
    await open();
    await waitFor(() => {
      expect(document.body.classList.contains("modal-open")).toBe(true);
      expect(document.body.style.overflow).toBe("hidden");
    });
    fireEvent.click(screen.getByRole("button", { name: "No Validar" }));
    await screen.findByText("Motivos de No Validación", { selector: "h5" });
    await waitFor(() => {
      expect(document.body.classList.contains("modal-open")).toBe(false);
      expect(document.body.style.overflow).toBe("");
    });
    expect([...document.querySelectorAll("link[rel=stylesheet]")].map((l) => l.getAttribute("href"))).toEqual([
      "https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css", "/static/custom/css/select2_theme.css",
    ]);
  });

  it("the select2 sheets load with the first modal, so the motivos box is laid out with them (an empty inline list laid out before them keeps no line height)", async () => {
    render(<Host />);
    const sheets = () => [...document.querySelectorAll("link[rel=stylesheet]")].map((l) => l.getAttribute("href"));
    expect(sheets()).toEqual([]);
    await open();
    expect(sheets()).toEqual([
      "https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css", "/static/custom/css/select2_theme.css",
    ]);
    expect(document.querySelector(".select2-selection")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "No Validar" }));
    await screen.findByText("Motivos de No Validación", { selector: "h5" });
    expect(sheets()).toHaveLength(2);
  });

  it("drops the comment when «Otros» is unselected, as the native toggle does", async () => {
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/comedores/7" } });
    render(<Host />);
    await open();
    fireEvent.click(screen.getByRole("button", { name: "No Validar" }));
    await screen.findByText("Motivos de No Validación", { selector: "h5" });
    pickMotivos("Otros");
    fireEvent.change(document.getElementById("comentario") as HTMLTextAreaElement, { target: { value: "x" } });
    pickMotivos("Otros");
    pickMotivos("Sin movimiento");
    fireEvent.click(screen.getAllByRole("button", { name: "No Validar" }).at(-1)!);
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect((webPost.mock.calls[0][1] as URLSearchParams).get("comentario")).toBe("");
  });

  it("an uncertain POST shows an error and does not navigate", async () => {
    webPost.mockRejectedValue(new Error("network"));
    render(<Host />);
    await open();
    fireEvent.click(screen.getByRole("button", { name: "Validar" }));
    expect(await screen.findByText(/No se pudo registrar la validación/)).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });

  it("without the server capability no modal is ever shown", async () => {
    webGet.mockResolvedValue({ status: 200, data: data({ puede_validar: false, opciones: [] }) });
    render(<Host />);
    fireEvent.click(screen.getByRole("button", { name: "Abrir" }));
    expect(await screen.findByText(/No se pudo cargar la validación/)).toBeTruthy();
    expect(document.querySelector("#modalValidacion")).toBeNull();
    expect(webPost).not.toHaveBeenCalled();
  });
});
