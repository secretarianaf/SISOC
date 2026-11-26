/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen and validator live here with the route. */
import { useEffect, useMemo, useRef, useState } from "react";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { Filters, filtersConfigValid, type Favorites, type FiltersConfig } from "./cdfFilters";
import { integer, internal, messagesValid, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import { favoritesValid, SearchActions } from "./dispositivosShared";

/**
 * DS01.01 (contract DS01-DS02, #2785): `dispositivos_map.html` with the
 * behaviour of `dispositivosMap.js`. Leaflet 1.9.4 from the same CDN and SRI;
 * devices without a saved location are looked up one by one through
 * `/api/web/dispositivos/<pk>/ubicacion/`, stopping after the first
 * `unavailable`. Location-state filters stay client-side.
 */
const API = "web/dispositivos/mapa/";
const LEAFLET_CSS = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css";
const LEAFLET_CSS_SRI = "sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H";
const LEAFLET_JS = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js";
const LEAFLET_JS_SRI = "sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH";
const PAGE_SIZE = 15;
const TIMEOUT_MS = 20000;
const LABELS: Record<string, string> = {
  located: "Ubicado", ambiguous: "Dirección ambigua", not_found: "Sin coincidencia", unavailable: "Servicio no disponible",
};

type Location = { status: string; lat?: number; lon?: number };
type Device = {
  id: number; name: string; type: string; province_id: number | null; province: string; representative: string; phone: string;
  address: string; detail_url: string; location_url: string; location: Location | null; municipio: string; street: string;
};
type StateFilter = { field: string; op: "eq" | "ne"; value: string };
export type MapaData = {
  titulo: string; devices: Device[]; provinces: { id: number; nombre: string }[]; filters_config: FiltersConfig; favorites: Favorites;
  location_filters: StateFilter[]; initial_device: number | ""; urls: { list: string; reset: string }; messages: CdfMessage[];
};

const locationValid = (v: unknown): v is Location | null => v === null || (record(v) && text(v.status));
const deviceValid = (d: unknown): d is Device => record(d) && integer(d.id) &&
  ["name", "type", "province", "representative", "phone", "address", "municipio", "street"].every((k) => text(d[k])) &&
  (d.province_id === null || integer(d.province_id)) && internal(d.detail_url) && internal(d.location_url) && locationValid(d.location);

export function mapaValid(v: unknown): v is MapaData {
  return record(v) && text(v.titulo) && Array.isArray(v.devices) && v.devices.every(deviceValid) &&
    Array.isArray(v.provinces) && filtersConfigValid(v.filters_config) && favoritesValid(v.favorites) &&
    Array.isArray(v.location_filters) && v.location_filters.every((f) => record(f) && text(f.value) && (f.op === "eq" || f.op === "ne")) &&
    (v.initial_device === "" || integer(v.initial_device)) && record(v.urls) && internal(v.urls.list) && internal(v.urls.reset) &&
    messagesValid(v.messages);
}

// --- Leaflet (CDN, global `L`) ------------------------------------------------

/* Minimal surface of the Leaflet global used here. */
type LatLng = unknown;
type LMarker = { getLatLng(): LatLng; openPopup(): void; bindPopup(e: HTMLElement): LMarker; addTo(g: unknown): LMarker; on(ev: string, fn: () => void): void };
type LGroup = { addTo(m: unknown): LGroup; getLayers(): unknown[]; getBounds(): unknown; hasLayer(l: unknown): boolean; addLayer(l: unknown): void; removeLayer(l: unknown): void };
type LMap = { setView(c: unknown, z: number): LMap; fitBounds(b: unknown, o: unknown): void; on(ev: string, fn: () => void): void; closePopup(): void; remove(): void };
type Leaflet = {
  map(e: HTMLElement): LMap; tileLayer(u: string, o: unknown): { addTo(m: LMap): void }; featureGroup(): LGroup;
  divIcon(o: unknown): unknown; marker(c: [number, number], o: unknown): LMarker;
};
const leafletGlobal = () => (window as unknown as { L?: Leaflet }).L;

let leafletLoad: Promise<Leaflet | null> | null = null;
/** Same tags as the native template: the stylesheet in the content, the script with SRI. */
export function loadLeaflet(): Promise<Leaflet | null> {
  const present = leafletGlobal();
  if (present) return Promise.resolve(present);
  if (!leafletLoad) leafletLoad = new Promise((resolve) => {
    const element = document.createElement("script");
    element.src = LEAFLET_JS;
    element.integrity = LEAFLET_JS_SRI;
    element.crossOrigin = "anonymous";
    element.onload = () => resolve(leafletGlobal() ?? null);
    element.onerror = () => { leafletLoad = null; element.remove(); resolve(null); };
    document.body.appendChild(element);
  });
  return leafletLoad;
}
export const resetLeafletForTests = () => { leafletLoad = null; };

async function lookup(url: string): Promise<Location> {
  try {
    const response = await fetch(url, { credentials: "same-origin", signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (response.ok) return (await response.json()) as Location;
  } catch { /* The list keeps the address even when the service fails. */ }
  return { status: "unavailable" };
}

function pageItems(current: number, count: number) {
  const items: { label: string; page: number; disabled: boolean; active: boolean }[] = [];
  items.push({ label: "Volver", page: current - 1, disabled: current === 1, active: false });
  let previous = 0;
  for (let page = 1; page <= count; page += 1) {
    if (page !== 1 && page !== count && Math.abs(page - current) > 2) continue;
    if (previous && page - previous > 1) items.push({ label: "…", page: current, disabled: true, active: false });
    items.push({ label: String(page), page, disabled: false, active: page === current });
    previous = page;
  }
  items.push({ label: "Continuar", page: current + 1, disabled: current === count, active: false });
  return items;
}

export function MapaContent({ data }: { data: MapaData }) {
  const { devices } = data;
  const container = useRef<HTMLDivElement>(null);
  const { cardRef, tableRef, classes } = useLegacyScrollHints(String(devices.length));
  const [mode, setMode] = useState<"loading" | "failed" | "ready">("loading");
  const [statusText, setStatusText] = useState(`${devices.length} dispositivos para cargar.`);
  const [locations, setLocations] = useState<Record<string, string>>(() => Object.fromEntries(devices.map((d) => [String(d.id), "pending"])));
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [focusable, setFocusable] = useState<Record<string, boolean>>({});
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const leaflet = useRef<{ L: Leaflet; map: LMap; group: LGroup; markers: Map<string, LMarker>; userSelected: boolean } | null>(null);
  const focusRef = useRef<(id: string) => void>(() => undefined);

  const filtered = useMemo(() => devices.filter((d) => data.location_filters.every((f) => (f.op === "ne"
    ? locations[String(d.id)] !== f.value : locations[String(d.id)] === f.value))), [devices, data.location_filters, locations]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const offset = (current - 1) * PAGE_SIZE;
  const pageIds = new Set(filtered.slice(offset, offset + PAGE_SIZE).map((d) => String(d.id)));
  const matchedKey = filtered.map((d) => d.id).join(",");
  const ready = mode === "ready";
  const fitAll = useRef<() => void>(() => undefined);
  // Latest location states, written by the lookup loop before React renders them.
  const statusRef = useRef<Record<string, string>>(locations);
  /** `selectRow()`: the selected row's page becomes the current one. */
  const selectRow = (id: string) => {
    const now = statusRef.current;
    const visible = devices.filter((d) => data.location_filters.every((f) => (f.op === "ne"
      ? now[String(d.id)] !== f.value : now[String(d.id)] === f.value)));
    const index = visible.findIndex((d) => String(d.id) === id);
    if (index >= 0) setPage(Math.floor(index / PAGE_SIZE) + 1);
    setSelected(id);
  };
  const matchedIds = new Set(matchedKey.split(","));
  const activeRow = selected && matchedIds.has(selected) ? selected : null;
  const markerCount = Object.keys(focusable).filter((id) => matchedIds.has(id)).length;

  // Marker visibility follows the client filters, as `applyFilters()` does.
  useEffect(() => {
    const state = leaflet.current;
    if (!state) return;
    const matched = new Set(matchedKey.split(","));
    for (const [id, marker] of state.markers) {
      if (matched.has(id) && !state.group.hasLayer(marker)) state.group.addLayer(marker);
      if (!matched.has(id) && state.group.hasLayer(marker)) state.group.removeLayer(marker);
    }
  }, [matchedKey, focusable]);
  const hadSelection = useRef<string | null>(null);
  useEffect(() => {
    if (hadSelection.current && !activeRow) leaflet.current?.map.closePopup();
    hadSelection.current = activeRow;
  }, [activeRow]);

  useEffect(() => {
    let active = true;
    const element = container.current;
    loadLeaflet().then(async (L) => {
      if (!active || !element) return;
      if (!L) { setMode("failed"); setStatusText("No se pudo cargar el mapa. Consultá las direcciones en la tabla."); return; }
      const map = L.map(element).setView([-38.4, -63.6], 4);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);
      const group = L.featureGroup().addTo(map);
      const state = { L, map, group, markers: new Map<string, LMarker>(), userSelected: false };
      leaflet.current = state;
      setMode("ready");
      map.on("dragstart", () => { state.userSelected = true; });
      const icon = L.divIcon({ className: "dispositivo-map-marker", iconSize: [20, 20], iconAnchor: [10, 10] });
      const fit = () => { if (group.getLayers().length) map.fitBounds(group.getBounds(), { padding: [30, 30], maxZoom: 14 }); };
      const autoFit = () => { if (!state.userSelected) fit(); };
      focusRef.current = (id: string) => {
        const marker = state.markers.get(id);
        if (!marker || !group.hasLayer(marker)) return;
        state.userSelected = true;
        selectRow(id);
        map.setView(marker.getLatLng(), 16);
        marker.openPopup();
        element.scrollIntoView({ behavior: "smooth", block: "center" });
      };
      fitAll.current = () => { state.userSelected = true; fit(); };
      let located = 0, processed = 0, reused = 0, unavailable = false;
      const ordered = [...devices.filter((d) => d.location), ...devices.filter((d) => !d.location)];
      for (const device of ordered) {
        const id = String(device.id);
        let result: Location = device.location || { status: "unavailable" };
        if (device.location) reused += 1;
        if (!device.location && !unavailable) result = await lookup(device.location_url);
        if (!active) return;
        if (result.status === "unavailable") unavailable = true;
        statusRef.current = { ...statusRef.current, [id]: result.status };
        setLocations(statusRef.current);
        if (result.status === "located") {
          const popup = document.createElement("div");
          const title = document.createElement("strong"); title.textContent = device.name;
          const address = document.createElement("p"); address.textContent = device.address;
          const type = document.createElement("p"); type.textContent = device.type;
          const representative = document.createElement("p"); representative.textContent = `Representante: ${device.representative || "Sin datos"}`;
          const phone = document.createElement("p"); phone.textContent = `Teléfono: ${device.phone || "Sin datos"}`;
          const link = document.createElement("a"); link.href = device.detail_url; link.textContent = "Ver detalle"; link.className = "btn btn-ver";
          popup.append(title, address, type, representative, phone, link);
          const marker = L.marker([result.lat as number, result.lon as number], { title: device.name, icon }).bindPopup(popup).addTo(group);
          state.markers.set(id, marker);
          marker.on("popupopen", () => { state.userSelected = true; selectRow(id); });
          setFocusable((prev) => ({ ...prev, [id]: true }));
          located += 1;
        }
        if (located === 1 && result.status === "located") autoFit();
        if (id === String(data.initial_device) && result.status === "located") window.setTimeout(() => focusRef.current(id), 0);
        processed += 1;
        const label = LABELS[result.status] || "Pendiente";
        setLabels((prev) => ({ ...prev, [id]: label }));
        setStatusText(`${located} ubicados · ${reused} guardados · ${processed - located} sin ubicar · ${processed}/${devices.length} revisados`);
        if (processed % 20 === 0) autoFit();
      }
      autoFit();
      let final = "";
      if (!devices.length) final = "No hay dispositivos para mostrar con los filtros seleccionados.";
      if (unavailable) setStatusText((prev) => `${final || prev}. No se pudo consultar el servicio de ubicación. Volvé a intentar recargando la página.`);
      else if (final) setStatusText(final);
    });
    return () => { active = false; leaflet.current?.map.remove(); leaflet.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one run per loaded page, like the native script.
  }, []);
  const count = ready
    ? (filtered.length ? `Mostrando ${offset + 1}–${Math.min(offset + PAGE_SIZE, filtered.length)} de ${filtered.length} dispositivos` : "No se encontraron dispositivos")
    : `${devices.length} dispositivos en el listado.`;
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <link rel="stylesheet" href={LEAFLET_CSS} integrity={LEAFLET_CSS_SRI} crossOrigin="anonymous" />
      <link rel="stylesheet" href="/static/custom/css/dispositivosMap.css" />
      <div className="list-container">
        <h2 className="text-center mb-4 poncho-titulo">Mapa de dispositivos</h2>
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <p id="map-status" className="mb-0" role="status" aria-live="polite">{statusText}</p>
          <button id="map-fit" type="button" className="poncho-btn poncho-btn--neutro" disabled={!ready || markerCount === 0}
            onClick={() => fitAll.current()}>
            <i className="fas fa-expand" aria-hidden="true" />Ver todos
          </button>
        </div>
        <div className="card comedor-table-card">
          <div className="card-body">
            <div id="dispositivos-map" ref={container} aria-label="Mapa de ubicación de dispositivos" data-focus-device={String(data.initial_device)} />
          </div>
        </div>
        <details className="mt-4" open>
          <summary className="mb-4">Dispositivos ({devices.length})</summary>
          <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
          <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
          <h2 className="text-center mb-4 poncho-titulo">{data.titulo}</h2>
          <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
          <SearchActions mapUrl={null} mapText="" resetUrl={data.urls.reset} addUrl={null} addText="" />
          <p id="map-filter-count" role="status" aria-live="polite">{count}</p>
          <div className="card comedor-table-card mt-4">
            <div ref={cardRef} className={`card-body ${classes.card}`}>
              <div ref={tableRef} className={`table-responsive-lg ${classes.table}`}>
                <table id="map-devices-table" className="table table-comedor-moderno">
                  <thead>
                    <tr><th>Institución</th><th>Tipo</th><th>Provincia</th><th>Municipio</th><th>Dirección</th><th>Ubicación</th><th>Acciones</th></tr>
                  </thead>
                  <tbody>
                    {devices.length ? devices.map((d) => {
                      const id = String(d.id);
                      const canFocus = !!focusable[id];
                      const label = labels[id];
                      const title = canFocus ? `Ver ${d.name} en el mapa` : label && label !== "Ubicado" ? label : "Ubicación pendiente";
                      return (
                        <tr key={d.id} id={`map-device-${d.id}`} data-device-id={d.id} hidden={ready && !pageIds.has(id)}
                          className={activeRow === id ? "table-active" : undefined}>
                          <td>{d.name}</td>
                          <td>{d.type}</td>
                          <td>{d.province}</td>
                          <td>{d.municipio}</td>
                          <td>{d.street}</td>
                          <td id={`location-status-${d.id}`}>{label ?? "Pendiente"}</td>
                          <td>
                            <div className="comedor-actions">
                              <button type="button" className="btn btn-ver" data-map-focus={d.id} title={title} disabled={!canFocus}
                                onClick={() => { if (canFocus) focusRef.current(id); }}>
                                <i className="fas fa-map-marker-alt" aria-hidden="true" />Ver en mapa
                              </button>
                              <a href={d.detail_url} className="btn btn-ver"><i className="fas fa-eye" aria-hidden="true" />Ver detalle</a>
                            </div>
                          </td>
                        </tr>
                      );
                    }) : (
                      <tr>
                        <td colSpan={7}>
                          <div className="no-data-message">
                            <h3>No se encontraron dispositivos</h3>
                            <p>No hay dispositivos que coincidan con los criterios de búsqueda.</p>
                          </div>
                        </td>
                      </tr>
                    )}
                    {devices.length > 0 && (
                      <tr id="map-filter-empty" hidden={!ready || filtered.length > 0}>
                        <td colSpan={7}>
                          <div className="no-data-message">
                            <h3>No se encontraron dispositivos</h3>
                            <p>No hay dispositivos que coincidan con la provincia y el estado seleccionados.</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <nav id="map-pagination" className="mt-2" aria-label="Páginas de dispositivos" hidden={!ready || pageCount <= 1}>
            <ul id="map-pagination-pages" className="pagination">
              {ready && pageItems(current, pageCount).map((item, i) => (
                <li key={i} className={`page-item${item.disabled ? " disabled" : ""}${item.active ? " active" : ""}`}>
                  <button type="button" className="page-link" disabled={item.disabled || item.active} aria-current={item.active ? "page" : undefined}
                    onClick={() => setPage(item.page)}>{item.label}</button>
                </li>
              ))}
            </ul>
          </nav>
        </details>
      </div>
    </>
  );
}

export function Mapa() {
  const state = useCdfPage(`${API}${window.location.search}`, mapaValid);
  return renderCdf(state, (data) => ({ title: "Mapa de dispositivos", breadcrumb: null, content: <MapaContent data={data} /> }));
}
