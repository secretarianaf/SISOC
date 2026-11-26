import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import Select2, { type Choice, type Select2Props } from "./select2";

const CHOICES: Choice[] = [{ value: "", label: "Elegí" }, { value: "1", label: "Álamo" }, { value: "2", label: "Berro" }, { value: "3", label: "Cedro" }];

function Harness({ initial = [], onValue, ...rest }: { initial?: string[]; onValue?: (v: string[]) => void } & Partial<Select2Props>) {
  const [value, setValue] = useState(initial);
  return <>
    <input aria-label="antes" />
    <Select2 id="s" name="s" choices={CHOICES} noResults="Sin resultados" selectClassName="form-select" {...rest} value={value}
      onChange={(v) => { setValue(v); onValue?.(v); }} />
    <input aria-label="despues" />
  </>;
}
const box = () => document.querySelector(".select2-selection") as HTMLElement;
const dropdownSearch = () => document.querySelector(".select2-search--dropdown input") as HTMLInputElement;
const inlineSearch = () => document.querySelector(".select2-search__field") as HTMLInputElement;
const optionTexts = () => [...document.querySelectorAll(".select2-results__option")].map((o) => o.textContent);

afterEach(cleanup);

describe("Select2 hidden select", () => {
  it("keeps the native select as the form value owner with the given classes and attributes", () => {
    render(<Harness multiple invalid selectClassName="form-control x" selectProps={{ "data-role": "select2", required: true, "aria-describedby": "h" }} initial={["2"]} />);
    const select = document.getElementById("s") as HTMLSelectElement;
    expect(select.className).toBe("form-control x is-invalid select2-hidden-accessible");
    expect(select.multiple).toBe(true);
    expect(select.getAttribute("aria-invalid")).toBe("true");
    expect(select.getAttribute("data-role")).toBe("select2");
    expect(select.required).toBe(true);
    expect([...select.selectedOptions].map((o) => o.value)).toEqual(["2"]);
  });
});

describe("Select2 single", () => {
  it("shows the placeholder, hides the empty choice, filters ignoring accents and picks", () => {
    const seen = vi.fn();
    render(<Harness placeholder="Elegí" hideEmptyChoice clearTrigger="mousedown" onValue={seen} />);
    expect(document.querySelector(".select2-selection__placeholder")?.textContent).toBe("Elegí");
    fireEvent.mouseDown(box());
    expect(optionTexts()).toEqual(["Álamo", "Berro", "Cedro"]);
    expect(document.activeElement).toBe(dropdownSearch());
    fireEvent.change(dropdownSearch(), { target: { value: "alamo" } });
    expect(optionTexts()).toEqual(["Álamo"]);
    fireEvent.change(dropdownSearch(), { target: { value: "zzz" } });
    expect(optionTexts()).toEqual(["Sin resultados"]);
    fireEvent.change(dropdownSearch(), { target: { value: "ber" } });
    fireEvent.click(screen.getByRole("option", { name: "Berro" }));
    expect(seen).toHaveBeenLastCalledWith(["2"]);
    expect(document.querySelector(".select2-dropdown")).toBeNull();
    expect(document.activeElement).toBe(box());
    // The clear cross empties the value and keeps the dropdown closed.
    fireEvent.mouseDown(document.querySelector(".select2-selection__clear")!);
    expect(seen).toHaveBeenLastCalledWith([]);
    expect(document.querySelector(".select2-dropdown")).toBeNull();
  });

  it("has no clear cross unless the option asks for it", () => {
    render(<Harness initial={["1"]} />);
    expect(document.querySelector(".select2-selection__clear")).toBeNull();
  });

  it("Escape closes with the term reset and refocuses the box; Tab closes without moving focus", () => {
    render(<Harness placeholder="Elegí" hideEmptyChoice />);
    fireEvent.mouseDown(box());
    fireEvent.keyDown(dropdownSearch(), { key: "Escape" });
    expect(document.querySelector(".select2-dropdown")).toBeNull();
    expect(document.activeElement).toBe(box());
    fireEvent.keyDown(box(), { key: "Enter" });
    expect(document.querySelector(".select2-dropdown")).not.toBeNull();
    expect(fireEvent.keyDown(dropdownSearch(), { key: "Tab" })).toBe(true);
    expect(document.querySelector(".select2-dropdown")).toBeNull();
  });

  it("singleFocus=selection keeps focus on the box and follows the native keys", () => {
    render(<Harness placeholder="Elegí" hideEmptyChoice singleFocus="selection" />);
    box().focus();
    fireEvent.keyDown(box(), { key: "ArrowDown" });
    expect(document.querySelector(".select2-dropdown")).toBeNull();
    fireEvent.keyDown(box(), { key: "ArrowDown", altKey: true });
    expect(document.querySelector(".select2-dropdown")).not.toBeNull();
    expect(document.activeElement).toBe(box());
    fireEvent.keyDown(box(), { key: "ArrowDown" });
    fireEvent.keyDown(box(), { key: "Enter" });
    expect((document.getElementById("s") as HTMLSelectElement).value).toBe("2");
    expect(document.activeElement).toBe(box());
    fireEvent.keyDown(box(), { key: " " });
    expect(document.querySelector(".select2-results__option--highlighted")?.textContent).toBe("Berro");
    fireEvent.keyDown(box(), { key: "ArrowUp", altKey: true });
    expect(document.querySelector(".select2-dropdown")).toBeNull();
    expect(document.activeElement).toBe(box());
    fireEvent.keyDown(box(), { key: "Enter" });
    fireEvent.keyDown(box(), { key: "Escape" });
    expect(document.querySelector(".select2-dropdown")).toBeNull();
  });

  it("a disabled select neither opens nor answers keys", () => {
    render(<Harness placeholder="Elegí" hideEmptyChoice disabled />);
    expect(document.querySelector(".select2-container--disabled")).not.toBeNull();
    expect(box().tabIndex).toBe(-1);
    fireEvent.mouseDown(box());
    fireEvent.keyDown(box(), { key: "Enter" });
    expect(document.querySelector(".select2-dropdown")).toBeNull();
    expect((document.getElementById("s") as HTMLSelectElement).disabled).toBe(true);
  });

  it("places the dropdown inside dropdownParent and shows nothing while it is null", () => {
    const parent = document.createElement("div");
    document.body.append(parent);
    const { rerender } = render(<Harness placeholder="Elegí" dropdownParent={null} />);
    fireEvent.mouseDown(box());
    expect(document.querySelector(".select2-dropdown")).toBeNull();
    rerender(<Harness placeholder="Elegí" dropdownParent={parent} />);
    expect(parent.querySelector(".select2-dropdown")).not.toBeNull();
    parent.remove();
  });

  // #2954: con un dropdownParent estático, el `position: absolute` del desplegable se
  // mide desde el primer ancestro posicionado, no desde el padre.
  const rect = (top: number, left: number, height = 0, width = 0) =>
    ({ top, left, bottom: top + height, right: left + width, height, width, x: left, y: top, toJSON: () => ({}) }) as DOMRect;
  const abrirConPadre = (parent: HTMLElement, base: HTMLElement) => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      if (this === base) return rect(100, 50);
      if (this === parent) return rect(262, 200);
      if (this.classList.contains("select2-container")) return rect(262, 200, 38, 300);
      return rect(0, 0);
    });
    render(<Harness placeholder="Elegí" dropdownParent={parent} />);
    fireEvent.mouseDown(box());
    return parent.querySelector(".select2-container--open") as HTMLElement;
  };

  it("measures a static dropdownParent from its positioned ancestor", () => {
    const base = document.createElement("div");
    base.style.position = "relative";
    const parent = document.createElement("div");
    base.append(parent);
    document.body.append(base);
    Object.defineProperty(parent, "offsetParent", { configurable: true, get: () => base });
    const abierto = abrirConPadre(parent, base);
    expect([abierto.style.top, abierto.style.left]).toEqual(["200px", "150px"]);
    vi.restoreAllMocks();
    base.remove();
  });

  it("opening focuses the dropdown search without scrolling the page", () => {
    const focus = vi.spyOn(HTMLElement.prototype, "focus");
    render(<Harness placeholder="Elegí" />);
    fireEvent.mouseDown(box());
    const call = focus.mock.instances.findIndex((el) => el === dropdownSearch());
    expect(call).toBeGreaterThanOrEqual(0);
    expect(focus.mock.calls[call][0]).toEqual({ preventScroll: true });
    vi.restoreAllMocks();
  });

  it("measures a positioned dropdownParent from itself", () => {
    const parent = document.createElement("div");
    parent.style.position = "relative";
    document.body.append(parent);
    const abierto = abrirConPadre(parent, document.createElement("div"));
    expect([abierto.style.top, abierto.style.left]).toEqual(["38px", "0px"]);
    vi.restoreAllMocks();
    parent.remove();
  });
});

describe("Select2 multiple", () => {
  it("termHandling=keep: a pick closes, Enter on a chosen option only closes, Backspace moves the last choice into the search", () => {
    const seen = vi.fn();
    render(<Harness multiple placeholder="Técnicos" termHandling="keep" enterOnSelected="close" removeOpensResults focusMarker="search" clearTrigger="click" outsideClick="results" onValue={seen} />);
    fireEvent.mouseDown(box());
    expect(document.activeElement).toBe(inlineSearch());
    fireEvent.click(screen.getByRole("option", { name: "Cedro" }));
    expect(seen).toHaveBeenLastCalledWith(["3"]);
    expect(document.querySelector(".select2-dropdown")).toBeNull();
    expect(inlineSearch().placeholder).toBe("");
    fireEvent.keyDown(inlineSearch(), { key: "ArrowDown" });
    expect(document.querySelector(".select2-results__option--highlighted")?.textContent).toBe("Cedro");
    seen.mockClear();
    fireEvent.keyDown(inlineSearch(), { key: "Enter" });
    expect(seen).not.toHaveBeenCalled();
    expect(document.querySelector(".select2-dropdown")).toBeNull();
    fireEvent.keyDown(inlineSearch(), { key: "Backspace" });
    expect(seen).toHaveBeenLastCalledWith([]);
    expect(inlineSearch().value).toBe("Cedro");
    expect(document.querySelector(".select2-dropdown")).not.toBeNull();
  });

  it("termHandling=reset: Enter on a chosen option removes it", () => {
    const seen = vi.fn();
    render(<Harness multiple initial={["3"]} onValue={seen} />);
    fireEvent.keyDown(inlineSearch(), { key: "ArrowDown" });
    expect(document.querySelector(".select2-results__option--highlighted")?.textContent).toBe("Cedro");
    fireEvent.keyDown(inlineSearch(), { key: "Enter" });
    expect(seen).toHaveBeenLastCalledWith([]);
  });

  it("removeOpensResults decides whether the chip cross opens the results", () => {
    const first = render(<Harness multiple initial={["1", "2"]} removeOpensResults />);
    fireEvent.click(document.querySelectorAll(".select2-selection__choice__remove")[0]);
    expect(document.querySelector(".select2-dropdown")).not.toBeNull();
    first.unmount();
    render(<Harness multiple initial={["1", "2"]} />);
    fireEvent.click(document.querySelectorAll(".select2-selection__choice__remove")[0]);
    expect(document.querySelector(".select2-dropdown")).toBeNull();
  });

  it("focusMarker marks the container for the chosen element only", () => {
    const first = render(<Harness multiple focusMarker="search" />);
    fireEvent.focus(inlineSearch());
    expect(document.querySelector(".select2-container--focus")).not.toBeNull();
    first.unmount();
    render(<Harness multiple focusMarker="none" />);
    fireEvent.focus(inlineSearch());
    expect(document.querySelector(".select2-container--focus")).toBeNull();
  });

  it("outsideClick=results closes on the dropdown frame, dropdown does not", () => {
    for (const mode of ["results", "dropdown"] as const) {
      const view = render(<Harness multiple outsideClick={mode} />);
      fireEvent.mouseDown(box());
      fireEvent.mouseDown(document.querySelector(".select2-dropdown")!);
      expect(document.querySelector(".select2-dropdown") === null).toBe(mode === "results");
      view.unmount();
    }
  });

  it("clearTrigger=click empties the value", () => {
    const seen = vi.fn();
    render(<Harness multiple initial={["1"]} clearTrigger="click" onValue={seen} />);
    fireEvent.click(document.querySelector(".select2-selection__clear")!);
    expect(seen).toHaveBeenLastCalledWith([]);
  });
});

describe("Select2 remote source", () => {
  const EMPTY: Choice[] = [{ value: "", label: "---------" }];
  const REMOTE = { url: "/vat/ajax/ciudadanos-buscar/", delay: 0, minimumInputLength: 3 };
  const respond = (body: unknown, ok = true) => vi.fn(() => Promise.resolve({ ok, status: ok ? 200 : 500, json: () => Promise.resolve(body) }));
  afterEach(() => vi.unstubAllGlobals());

  it("asks for the minimum characters, searches like the AjaxAdapter and keeps the picked option", async () => {
    const fetchMock = respond({ results: [{ id: 7, text: "Pérez, Ana (12345678)" }] });
    vi.stubGlobal("fetch", fetchMock);
    const seen = vi.fn();
    render(<Harness choices={EMPTY} hideEmptyChoice placeholder="Buscar por DNI" remote={REMOTE} onValue={seen} />);
    fireEvent.mouseDown(box());
    expect(optionTexts()).toEqual(["Please enter 3 or more characters"]);
    fireEvent.change(dropdownSearch(), { target: { value: "12" } });
    expect(optionTexts()).toEqual(["Please enter 1 or more characters"]);
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.change(dropdownSearch(), { target: { value: "123" } });
    expect(optionTexts()).toEqual(["Searching…"]);
    fireEvent.click(await screen.findByRole("option", { name: "Pérez, Ana (12345678)" }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]).toEqual(["/vat/ajax/ciudadanos-buscar/?term=123&_type=query&q=123", expect.objectContaining({ credentials: "same-origin" })]);
    expect(seen).toHaveBeenLastCalledWith(["7"]);
    expect(document.querySelector(".select2-selection__rendered")?.textContent).toBe("Pérez, Ana (12345678)");
    expect((document.getElementById("s") as HTMLSelectElement).value).toBe("7");
  });

  it("shows the empty and the failed search with the Select2 messages", async () => {
    vi.stubGlobal("fetch", respond({ results: [] }));
    render(<Harness choices={EMPTY} hideEmptyChoice noResults="No results found" remote={REMOTE} />);
    fireEvent.mouseDown(box());
    fireEvent.change(dropdownSearch(), { target: { value: "999" } });
    expect(await screen.findByText("No results found")).toBeTruthy();
    vi.stubGlobal("fetch", respond({}, false));
    fireEvent.change(dropdownSearch(), { target: { value: "9999" } });
    expect(await screen.findByText("The results could not be loaded.")).toBeTruthy();
  });
});
