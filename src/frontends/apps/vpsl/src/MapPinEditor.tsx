import { useEffect, useId, useRef, useState } from "react";
import { Alert, Button } from "@mui/material";
import { leerCookie } from "@sisoc/api";

const resources = new Map<string, Promise<void>>();
function script(src: string, integrity?: string) {
  if (!resources.has(src)) resources.set(src, new Promise<void>((resolve, reject) => {
    const element = document.createElement("script");
    element.src = src;
    if (integrity) { element.integrity = integrity; element.crossOrigin = "anonymous"; }
    element.onload = () => resolve();
    element.onerror = () => { resources.delete(src); reject(new Error("No se pudo cargar el mapa. Podés ingresar las coordenadas manualmente.")); };
    document.head.appendChild(element);
  }));
  return resources.get(src)!;
}
function style(href: string) {
  if ([...document.querySelectorAll<HTMLLinkElement>("link[rel=stylesheet]")].some(link => link.getAttribute("href") === href)) return;
  const link = document.createElement("link"); link.rel = "stylesheet"; link.href = href; document.head.appendChild(link);
}

type Props = { latitude: string; longitude: string; address?: { domicilio: string; provincia: string; localidad: string }; onChange: (latitude: string, longitude: string) => void };
export function MapPinEditor({ latitude, longitude, address, onChange }: Props) {
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const lat = useRef<HTMLInputElement>(null);
  const lon = useRef<HTMLInputElement>(null);
  const callback = useRef(onChange);
  const [error, setError] = useState("");
  useEffect(() => { callback.current = onChange; }, [onChange]);
  useEffect(() => {
    if (!lat.current || !lon.current) return;
    lat.current.value = latitude; lon.current.value = longitude;
    lat.current.dispatchEvent(new Event("change", { bubbles: true }));
  }, [latitude, longitude]);
  useEffect(() => {
    let active = true;
    const element = root.current;
    const latitudeInput = lat.current;
    const longitudeInput = lon.current;
    const update = () => callback.current(latitudeInput?.value || "", longitudeInput?.value || "");
    latitudeInput?.addEventListener("input", update);
    longitudeInput?.addEventListener("input", update);
    style("https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css");
    style("/static/custom/css/mapPinEditor.css");
    script("https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js", "sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH")
      .then(() => script("/static/custom/js/mapPinEditor.js?v=2778-6"))
      .then(() => { if (active) document.dispatchEvent(new Event("pin:init")); })
      .catch(reason => { if (active) setError(String(reason.message)); });
    return () => {
      active = false;
      latitudeInput?.removeEventListener("input", update);
      longitudeInput?.removeEventListener("input", update);
      element?.dispatchEvent(new Event("pin:destroy"));
    };
  }, []);
  return <div className="wide" ref={root} data-pin-editor data-always-visible="true"
    data-latitude-field={`${id}-lat`} data-longitude-field={`${id}-lon`} data-generic-search="true"
    data-search-url={address?.provincia ? "/ajax/ubicacion/previsualizar/" : ""}
    data-address-fields={`${id}-address,${id}-province,${id}-locality`}>
    {error && <Alert severity="error">{error}</Alert>}
    <input ref={lat} id={`${id}-lat`} type="hidden" defaultValue={latitude} />
    <input ref={lon} id={`${id}-lon`} type="hidden" defaultValue={longitude} />
    <input id={`${id}-address`} type="hidden" data-name="domicilio" value={address?.domicilio || ""} readOnly />
    <input id={`${id}-province`} type="hidden" data-name="provincia" value={address?.provincia || ""} readOnly />
    <input id={`${id}-locality`} type="hidden" data-name="localidad" value={address?.localidad || ""} readOnly />
    <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") || ""} readOnly />
    <Button type="button" variant="outlined" data-pin-start>{address ? "Buscar dirección en el mapa" : "Centrar en las coordenadas"}</Button>
    <div data-pin-panel>
      <p>Arrastrá el pin para ajustar la ubicación. El domicilio se conserva; guardá el formulario para confirmar.</p>
      <div className="map-pin-editor" data-pin-map aria-label="Mapa para ajustar la ubicación" />
      <div className="form-actions">
        <Button type="button" variant="outlined" data-pin-center>Colocar pin en el centro del mapa</Button>
        <Button type="button" variant="outlined" data-pin-cancel>Descartar ajuste del pin</Button>
      </div>
    </div>
    <p role="status" aria-live="polite" data-pin-status />
  </div>;
}
