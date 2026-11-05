// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import { MapPinEditor } from "./MapPinEditor";

afterEach(cleanup);
it("comunica coordenadas sin cambiar domicilio y libera el mapa al salir", async () => {
  const update = vi.fn();
  const initialized = vi.fn();
  document.addEventListener("pin:init", initialized);
  const { container, unmount } = render(<form><MapPinEditor latitude="-34" longitude="-58" address={{ domicilio: "Calle 123", provincia: "Buenos Aires", localidad: "La Plata" }} onChange={update} /></form>);
  const root = container.querySelector<HTMLElement>("[data-pin-editor]")!;
  const lat = document.getElementById(root.dataset.latitudeField!) as HTMLInputElement;
  const lon = document.getElementById(root.dataset.longitudeField!) as HTMLInputElement;
  const destroy = vi.fn(); root.addEventListener("pin:destroy", destroy);
  fireEvent.load(document.querySelector<HTMLScriptElement>('script[src*="leaflet.js"]')!);
  await waitFor(() => expect(document.querySelector('script[src*="mapPinEditor.js"]')).not.toBeNull());
  fireEvent.load(document.querySelector('script[src*="mapPinEditor.js"]')!);
  await waitFor(() => expect(initialized).toHaveBeenCalled());
  lat.value = "-34.123456"; lon.value = "-58.123456";
  fireEvent.input(lat);
  expect(update).toHaveBeenCalledWith("-34.123456", "-58.123456");
  expect((root.querySelector('[data-name="domicilio"]') as HTMLInputElement).value).toBe("Calle 123");
  const formData = new FormData(container.querySelector("form")!);
  expect(formData.has("latitud")).toBe(false);
  expect(formData.has("provincia")).toBe(false);
  unmount(); expect(destroy).toHaveBeenCalledOnce();
  document.removeEventListener("pin:init", initialized);
});
