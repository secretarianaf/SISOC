import entryHtml from "../index.html?raw";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import InsumosToast, { InsumosToastList } from "./InsumosToast";

const shellStyles = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "shell.css"), "utf8");


afterEach(() => { cleanup(); vi.useRealTimers(); });

it.each(["error", "warning", "info"] as const)("preserves the source %s notification level", (level) => {
  render(<InsumosToast message="Aviso existente" level={level} />);
  expect(screen.getByRole("status").classList.contains(`toast-${level}`)).toBe(true);
});

it("stacks consumed notices in one native container without changing the default success style", () => {
  render(<InsumosToastList messages={[{ message: "Guardado" }, { message: "Aviso", level: "warning" }]} />);
  expect(document.querySelectorAll("#toast-container")).toHaveLength(1);
  const notices = screen.getAllByRole("status");
  expect(notices).toHaveLength(2);
  expect(notices[0].classList.contains("toast-warning")).toBe(true);
  expect(notices[1].classList.contains("toast-success")).toBe(true);
  expect(notices[0].parentElement).toBe(notices[1].parentElement);
});

it("loads native notification styles before the theme without reinserting them after it", () => {
  const html = entryHtml;
  const nativeStyles = "https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.css";
  const nativeIndex = html.indexOf(nativeStyles);
  expect(nativeIndex).toBeGreaterThan(-1);
  expect(nativeIndex).toBeLessThan(html.indexOf("/static/dist/css/adminlte.css"));
  render(<InsumosToast message="Insumo creado correctamente." />);
  expect(document.querySelector(`link[href="${nativeStyles}"]`)).toBeNull();
});

it("preserves the native notification opacity while keeping its Bootstrap toast visible", () => {
  const styles = document.createElement("style");
  // Minimal independent contract from the pinned native Toastr stylesheet.
  styles.textContent = '#toast-container > div { opacity: .8; }' + shellStyles;
  document.head.append(styles);
  try {
    render(<InsumosToast message="Insumo creado correctamente." />);
    const toast = getComputedStyle(screen.getByRole("status"));
    expect(toast.display).toBe("block");
    expect(toast.opacity).toBe("0.8");
  } finally {
    styles.remove();
  }
});


it("shows operation feedback at the legacy bottom-right position and dismisses it after the native timeout", () => {
  vi.useFakeTimers();
  const view = render(<InsumosToast message="Insumo creado correctamente." />);
  expect(screen.getByRole("status").textContent).toBe("Insumo creado correctamente.");
  expect(screen.getByRole("status").parentElement?.className).toBe("toast-bottom-right");
  act(() => vi.advanceTimersByTime(5000));
  expect(screen.getByRole("status").className).toContain("sisoc-toast-hiding");
  act(() => vi.advanceTimersByTime(1000));
  expect(screen.queryByRole("status")).toBeNull();
  view.unmount();
  expect(vi.getTimerCount()).toBe(0);
});

it("pauses while hovered and clears all timers on unmount", () => {
  vi.useFakeTimers();
  const view = render(<InsumosToast message="Insumo actualizado correctamente." />);
  fireEvent.mouseEnter(screen.getByRole("status"));
  act(() => vi.advanceTimersByTime(6000));
  expect(screen.getByRole("status").className).not.toContain("sisoc-toast-hiding");
  fireEvent.mouseLeave(screen.getByRole("status"));
  act(() => vi.advanceTimersByTime(1000));
  expect(screen.getByRole("status").className).toContain("sisoc-toast-hiding");
  view.unmount();
  expect(vi.getTimerCount()).toBe(0);
});
