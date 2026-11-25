import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import InspSelect2, { type InspOption } from "./InspSelect2";

const OPTIONS: InspOption[] = [
  { id: 3, text: "Castelar", detalle: "Morón" },
  { id: 2, text: "Ramos Mejía", detalle: "La Matanza" },
  { id: 1, text: "San Justo", detalle: "La Matanza" },
];

function setup(initial: InspOption | null = null, minimum = 0) {
  const search = vi.fn(async () => ({ results: OPTIONS }));
  const onChange = vi.fn();
  render(
    <form onChange={onChange}>
      <input aria-label="antes" />
      <InspSelect2 id="loc" name="localidad" placeholder="Buscá la localidad" minimum={minimum} initial={initial} search={search} autoSubmit={false} />
      <input aria-label="después" />
    </form>,
  );
  const box = screen.getByRole("combobox");
  const container = box.closest<HTMLElement>(".select2-container")!;
  const hidden = document.getElementById("loc") as HTMLSelectElement;
  return { box, container, hidden, search, onChange };
}

const results = () => document.getElementById("select2-loc-results");
const highlighted = () => document.querySelector(".select2-results__option--highlighted")?.textContent;

describe("InspSelect2 focus and keyboard parity with native Select2 4.1", () => {
  afterEach(() => cleanup());

  it("keeps focus on the selection box when the dropdown opens with the mouse", async () => {
    const { box, container } = setup();
    fireEvent.mouseDown(box);
    expect(await within(results()!).findAllByRole("option")).toHaveLength(3);
    await waitFor(() => expect(document.activeElement).toBe(box));
    expect(container.className).toContain("select2-container--open");
    await waitFor(() => expect(container.className).toContain("select2-container--focus"));
  });

  it("closes on Tab without selecting, keeps focus on the box and blocks the focus move", async () => {
    const { box, hidden } = setup();
    fireEvent.mouseDown(box);
    await within(results()!).findAllByRole("option");
    expect(fireEvent.keyDown(box, { key: "Tab" })).toBe(false);
    expect(results()).toBeNull();
    expect(document.activeElement).toBe(box);
    expect(hidden.value).toBe("");
  });

  it("opens only with Enter, Space or Alt+ArrowDown, as native single selects", async () => {
    const { box } = setup();
    box.focus();
    fireEvent.keyDown(box, { key: "ArrowDown" });
    fireEvent.keyDown(box, { key: "ArrowUp" });
    expect(results()).toBeNull();
    for (const key of [{ key: "Enter" }, { key: " " }, { key: "ArrowDown", altKey: true }]) {
      fireEvent.keyDown(box, key);
      expect(results()).not.toBeNull();
      expect(document.activeElement).toBe(box);
      fireEvent.keyDown(box, { key: "Escape" });
      expect(results()).toBeNull();
      expect(document.activeElement).toBe(box);
    }
  });

  it("starts the highlight on the selected option and selects with arrows and Enter from the box", async () => {
    const { box, hidden, onChange } = setup({ id: 1, text: "San Justo" });
    fireEvent.mouseDown(box);
    await within(results()!).findAllByRole("option");
    await waitFor(() => expect(highlighted()).toBe("San JustoLa Matanza"));
    fireEvent.keyDown(box, { key: "ArrowUp" });
    expect(highlighted()).toBe("Ramos MejíaLa Matanza");
    fireEvent.keyDown(box, { key: "Enter" });
    expect(results()).toBeNull();
    expect(document.activeElement).toBe(box);
    await waitFor(() => expect(hidden.value).toBe("2"));
    await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
  });

  it("returns focus to the box when Tab leaves the search field", async () => {
    const { box, container } = setup();
    fireEvent.mouseDown(box);
    const field = document.querySelector<HTMLInputElement>(".select2-search__field")!;
    field.focus();
    await waitFor(() => expect(container.className).not.toContain("select2-container--focus"));
    fireEvent.change(field, { target: { value: "San" } });
    expect(fireEvent.keyDown(field, { key: "Tab" })).toBe(false);
    expect(results()).toBeNull();
    expect(document.activeElement).toBe(box);
    await waitFor(() => expect(container.className).toContain("select2-container--focus"));
  });

  it("clears and opens the dropdown with focus on the box", async () => {
    const { box, hidden, onChange } = setup({ id: 1, text: "San Justo" });
    fireEvent.mouseDown(screen.getByRole("button", { name: "Remove all items" }));
    expect(results()).not.toBeNull();
    expect(document.activeElement).toBe(box);
    await waitFor(() => expect(hidden.value).toBe(""));
    await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
  });

  it("closes on an outside click without stealing focus and empties the search", async () => {
    const { box } = setup();
    fireEvent.mouseDown(box);
    const field = document.querySelector<HTMLInputElement>(".select2-search__field")!;
    fireEvent.change(field, { target: { value: "Ra" } });
    const after = screen.getByLabelText("después");
    after.focus();
    fireEvent.mouseDown(after);
    expect(results()).toBeNull();
    expect(document.activeElement).toBe(after);
    fireEvent.mouseDown(box);
    expect(document.querySelector<HTMLInputElement>(".select2-search__field")!.value).toBe("");
  });

  it("does not fire change when the selected option is chosen again", async () => {
    const { box, hidden, onChange } = setup({ id: 1, text: "San Justo" });
    fireEvent.mouseDown(box);
    await within(results()!).findAllByRole("option");
    await waitFor(() => expect(highlighted()).toBe("San JustoLa Matanza"));
    fireEvent.keyDown(box, { key: "Enter" });
    expect(results()).toBeNull();
    expect(hidden.value).toBe("1");
    expect(onChange).not.toHaveBeenCalled();
  });
});
