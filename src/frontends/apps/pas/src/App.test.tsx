import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { documentFor } from "./page";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the generic confirmation without identifiers or redirects", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<App pathname="/pas/ddjj/confirmacion" />);

    expect(screen.getByRole("heading", { name: "Declaración Jurada enviada con éxito" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "OK" })).toBeTruthy();
    expect(document.querySelector("main")!.className).toBe("pas-ddjj-modal-card is-success");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("uses the native document title and body class of each template", () => {
    expect(documentFor("/pas/ddjj/confirmacion")).toEqual({
      title: "Declaración Jurada enviada · SISOC",
      bodyClass: "pas-ddjj-public pas-ddjj-success-page",
    });
    expect(documentFor("/pas/ddjj/formulario/00005a50-0000-4000-8000-000000000001")).toEqual({
      title: "Declaración Jurada PAS",
      bodyClass: "pas-ddjj-public",
    });
  });

  it("renders nothing and requests nothing for unknown paths", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<App pathname="/pas/ddjj/otra" />);
    expect(container.innerHTML).toBe("");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
