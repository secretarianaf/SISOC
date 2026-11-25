import { useEffect, useRef } from "react";

/**
 * `components/map_pin_editor.html` of the CDI centre form (always visible, address search), driven by
 * the shared engine (`mapPinEditor.js`, `pin:init` / `pin:destroy`). The latitude and longitude inputs
 * stay uncontrolled: the engine writes them straight into the DOM, like the native page.
 */
const loaded = new Map<string, Promise<void>>();

/** Like the native page, the engine loads even when Leaflet does not (the promise always settles). */
function loadScript(src: string, integrity?: string) {
  if (!loaded.has(src)) loaded.set(src, new Promise<void>((resolve) => {
    const element = document.createElement("script");
    element.src = src;
    if (integrity) { element.integrity = integrity; element.crossOrigin = "anonymous"; }
    element.onload = () => resolve();
    element.onerror = () => { loaded.delete(src); resolve(); };
    document.head.appendChild(element);
  }));
  return loaded.get(src)!;
}

const LEAFLET = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js";
const LEAFLET_SRI = "sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH";

export default function CentroMapa({ searchUrl }: { searchUrl: string }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let active = true;
    const element = root.current;
    loadScript(LEAFLET, LEAFLET_SRI)
      .then(() => loadScript("/static/custom/js/mapPinEditor.js?v=2778-6"))
      .then(() => { if (active) document.dispatchEvent(new Event("pin:init")); });
    return () => { active = false; element?.querySelector("[data-pin-editor]")?.dispatchEvent(new Event("pin:destroy")); };
  }, []);
  return (
    <div ref={root}>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossOrigin="anonymous" />
      <link rel="stylesheet" href="/static/custom/css/mapPinEditor.css" />
      <div data-pin-editor="" data-always-visible="true" data-latitude-field="id_latitud" data-longitude-field="id_longitud" data-preview-frame=""
        data-generic-search="true" data-search-url={searchUrl} data-location-url="" data-address-fields="id_calle,id_numero,id_provincia,id_municipio,id_localidad">
        <button type="button" className="btn btn-secondary mb-2" data-pin-start="">Buscar dirección en el mapa</button>
        <div data-pin-panel="">
          <p>Arrastrá el pin hasta la ubicación correcta. El domicilio escrito se conserva. Los cambios se guardan al guardar el formulario.</p>
          <div className="map-pin-editor" data-pin-map="" aria-label="Mapa para ajustar la ubicación" />
          <div className="d-flex flex-wrap gap-2 my-2">
            <button type="button" className="btn btn-secondary" data-pin-center="">Colocar pin en el centro del mapa</button>{" "}
            <button type="button" className="btn btn-secondary" data-pin-cancel="">Descartar ajuste del pin</button>
          </div>
        </div>
        <p className="text-muted" role="status" aria-live="polite" data-pin-status="" />
      </div>
    </div>
  );
}
