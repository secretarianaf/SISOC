import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PendingSurvey from "./PendingSurvey";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { runInThisContext } from "node:vm";

const legacyModalScript = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../../../../backends/kernel/static/custom/js/encuestaPendienteModal.js"), "utf8");

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({ crearCliente: () => ({ get, post }), leerCookie: () => "synthetic" }));
const presentation = { user: { username: "synthetic", display_name: "Ana", avatar_initial: "S", role_label: "-" }, footer_version_label: "Versiones", legacy_frame_navigation: [] };
const question = { id: 1, order: 1, text: "¿Continuar?", type: "si_no", required: true, condition: null, options: [] };
const round = { id: 7, title: "Encuesta sintética", description: "Descripción", mode: "obligatoria", anonymous: true, questions: [question], actions: { answer: "/encuestas/responder/7/", postpone: null, dismiss: null } };
const metadata = { presentation, home_variant: "default", messages: [], round };
const modal = { show: vi.fn(), hide: vi.fn(), dispose: vi.fn() };
const createModal = vi.fn((element: HTMLElement) => {
  modal.show.mockImplementation(() => { element.setAttribute("aria-hidden", "false"); element.setAttribute("aria-modal", "true"); });
  return modal;
});
beforeEach(() => {
  vi.resetAllMocks();
  get.mockResolvedValue({ data: metadata });
  Object.assign(window, { bootstrap: { Modal: { getOrCreateInstance: createModal } } });
  const append = document.body.appendChild.bind(document.body);
  vi.spyOn(document.body, "appendChild").mockImplementation(node => {
    const result = append(node);
    if (node instanceof HTMLScriptElement && node.src.endsWith("/static/custom/js/encuestaPendienteModal.js")) {
      runInThisContext(legacyModalScript);
      node.dispatchEvent(new Event("load"));
    }
    return result;
  });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const submit = () => fireEvent.submit(document.getElementById("form-responder-encuesta")!);

describe("source pending survey circuit", () => {
  it("accepts source-valid zero question order and its conditional reference", async () => {
    get.mockResolvedValue({ data: { ...metadata, round: { ...round, questions: [
      { ...question, order: 0 },
      { ...question, id: 2, order: 1, type: "texto_corto", condition: { order: 0, operator: "igual", value: "si" } },
    ] } } });
    render(<PendingSurvey />);
    await screen.findByRole("heading", { name: round.title });
    const conditional = document.querySelector<HTMLInputElement>('[name="respuesta-2"]')!;
    expect(conditional.disabled).toBe(true);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "si" } });
    expect(conditional.disabled).toBe(false);
  });

  it("projects the original home and mandatory modal without an administrative permission", async () => {
    render(<PendingSurvey />);
    await screen.findByRole("heading", { name: round.title });
    expect(get).toHaveBeenCalledWith("web/surveys/pending/", expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(document.querySelector(".inicio-presentacion--default")).not.toBeNull();
    const dialog = document.getElementById("modal-encuesta-pendiente")!;
    expect(dialog.getAttribute("data-bs-backdrop")).toBe("static");
    expect(dialog.getAttribute("data-bs-keyboard")).toBe("false");
    expect(screen.queryByRole("button", { name: "Cerrar" })).toBeNull();
    expect(screen.queryByRole("button", { name: /más tarde|Prefiero/ })).toBeNull();
    expect(modal.show).toHaveBeenCalledOnce();
  });

  it("keeps optional-first controls and existing INET presentation", async () => {
    get.mockResolvedValue({ data: { ...metadata, home_variant: "inet", round: { ...round, mode: "opcional", actions: { ...round.actions, dismiss: "/encuestas/responder/7/descartar/" } } } });
    render(<PendingSurvey />);
    await screen.findByRole("button", { name: "Cerrar" });
    expect(screen.getByAltText("INET Secretaría de Educación").getAttribute("src")).toBe("/static/custom/img/LOGOS-INET-SE_BLANCO.png");
    expect(document.getElementById("modal-encuesta-pendiente")!.hasAttribute("data-bs-keyboard")).toBe(false);
    expect(screen.getByRole("button", { name: "Prefiero no responder" })).toBeDefined();
  });

  it("disables hidden conditional fields and preserves multiple values in URLencoded POST", async () => {
    get.mockResolvedValue({ data: { ...metadata, round: { ...round, questions: [question,
      { ...question, id: 2, order: 2, text: "Varias", type: "opcion_multiple", options: [{ id: 11, value: "a", text: "A" }, { id: 12, value: "b", text: "B" }] },
      { ...question, id: 3, order: 3, text: "Condicional", type: "texto_corto", condition: { order: 1, operator: "igual", value: "si" } },
    ] } } });
    post.mockResolvedValue({ data: { redirect: "/inicio/" } });
    const navigate = vi.fn(); render(<PendingSurvey navigate={navigate} />);
    await screen.findByRole("heading", { name: round.title });
    const conditional = document.querySelector<HTMLInputElement>('[name="respuesta-3"]')!;
    expect(conditional.disabled).toBe(true);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "si" } });
    expect(conditional.disabled).toBe(false);
    fireEvent.change(conditional, { target: { value: "No enviar si está oculta" } });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "no" } });
    fireEvent.click(screen.getByRole("switch", { name: "A" }));
    fireEvent.click(screen.getByRole("switch", { name: "B" }));
    submit(); await waitFor(() => expect(navigate).toHaveBeenCalledWith("/inicio/"));
    const data = post.mock.calls[0][1] as URLSearchParams;
    expect(data).toBeInstanceOf(URLSearchParams);
    expect(data.getAll("respuesta-2")).toEqual(["a", "b"]);
    expect(data.has("respuesta-3")).toBe(false);
    expect(post.mock.calls[0][0]).toBe("web/surveys/7/answer/");
  });

  it.each(["dismiss", "postpone"])("sends only the applicable %s source action", async operation => {
    get.mockResolvedValue({ data: { ...metadata, round: { ...round, mode: operation === "dismiss" ? "opcional" : "postergable", actions: { ...round.actions, [operation]: `/encuestas/responder/7/${operation === "dismiss" ? "descartar" : "mas-tarde"}/` } } } });
    post.mockResolvedValue({ data: { redirect: "/inicio/" } });
    const navigate = vi.fn(); render(<PendingSurvey navigate={navigate} />);
    const button = await screen.findByRole("button", { name: operation === "dismiss" ? "Prefiero no responder" : /Responder más tarde/ });
    fireEvent.click(button); await waitFor(() => expect(navigate).toHaveBeenCalledOnce());
    expect(post.mock.calls[0][0]).toBe(`web/surveys/7/${operation}/`);
  });

  it("performs full navigation for handled native validation redirects, without a local draft", async () => {
    post.mockResolvedValue({ data: { redirect: "/inicio/?error=1" } });
    const navigate = vi.fn(); render(<PendingSurvey navigate={navigate} />);
    await screen.findByRole("heading", { name: round.title }); submit();
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("/inicio/?error=1"));
    expect(document.querySelector("form")).toBeNull();
  });

  it("blocks duplicate/uncertain submission and offers a truthful source reload", async () => {
    let reject!: (error: Error) => void;
    post.mockReturnValue(new Promise((_resolve, fail) => { reject = fail; }));
    render(<PendingSurvey />); await screen.findByRole("heading", { name: round.title });
    submit(); submit(); expect(post).toHaveBeenCalledOnce();
    await act(async () => reject(new Error("Synthetic unavailable")));
    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.getByRole("link", { name: "Volver al inicio" }).getAttribute("href")).toBe("/inicio/");
    expect(screen.getByRole<HTMLButtonElement>("button", { name: "Enviar respuestas" }).disabled).toBe(true);
    submit(); expect(post).toHaveBeenCalledOnce();
  });

  it("rejects an unsafe response destination and ignores abandoned results", async () => {
    const navigate = vi.fn(); post.mockResolvedValue({ data: { redirect: "https://outside.invalid/" } });
    const view = render(<PendingSurvey navigate={navigate} />); await screen.findByRole("heading", { name: round.title }); submit();
    await screen.findByRole("alert"); expect(navigate).not.toHaveBeenCalled(); view.unmount();
    let resolve!: (value: unknown) => void; post.mockReturnValue(new Promise(done => { resolve = done; }));
    const next = render(<PendingSurvey navigate={navigate} />); await screen.findByRole("heading", { name: round.title }); submit(); next.unmount();
    await act(async () => resolve({ data: { redirect: "/inicio/" } }));
    expect(navigate).not.toHaveBeenCalled();
  });

  it("handles higher prerequisites and malformed metadata without exposing a form", async () => {
    get.mockResolvedValueOnce({ status: 403, data: { detail: "Debe completar el requisito de acceso correspondiente.", state: "password_change_required", required_action_url: "/password/first-change/" } });
    const view = render(<PendingSurvey />); await screen.findByRole("heading", { name: "Antes de continuar" });
    expect(document.querySelector("form")).toBeNull(); view.unmount();
    get.mockResolvedValueOnce({ data: { ...metadata, round: { ...round, questions: [{ ...question, type: "unknown" }] } } });
    render(<PendingSurvey />); await screen.findByRole("alert"); expect(document.querySelector("form")).toBeNull();
  });

  it("renders an empty queue with once-only existing feedback", async () => {
    get.mockResolvedValue({ data: { ...metadata, round: null, messages: [{ level: "success", message: "¡Gracias por responder la encuesta!" }] } });
    render(<PendingSurvey />);
    expect(await screen.findByText("¡Gracias por responder la encuesta!")).toBeDefined();
    expect(document.getElementById("modal-encuesta-pendiente")).toBeNull();
  });
});
