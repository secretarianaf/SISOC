/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from "react";
import { leaflet, loadLeaflet } from "./inspeccionesTableroLeaflet";
import type { Punto } from "./inspeccionesTableroApi";

/**
 * Coverage map of `tablero.js` (`iniciarMapa` / `pintarMapa`): Leaflet 1.9.4 and
 * markercluster 1.5.3 from the same CDN files and integrity hashes as the native
 * page (they are not bundled), the IGN Argenmap tiles, clusters coloured by how
 * many visits were verified and a popup built with `textContent`. If the
 * libraries cannot be loaded the container says so, as the native page does.
 */
const ARGENTINA: [[number, number], [number, number]] = [[-55.1, -73.6], [-21.7, -53.6]];
const TEAL = "#3b8681";
const NARANJA = "#c26a00";
const formatoNumero = new Intl.NumberFormat("es-AR");
function element(tag: string, className?: string | null, text?: string | null) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function actaLink(punto: Punto) {
  if (!punto.url) return element("span", "insp-tablero-numero", punto.numero);
  const link = element("a", "insp-tablero-numero", punto.numero) as HTMLAnchorElement;
  link.href = punto.url;
  return link;
}

function popup(punto: Punto) {
  const box = element("div", "insp-tablero-popup");
  box.appendChild(element("strong", null, punto.escuela || "Escuela sin nombre"));
  const list = element("dl");
  const row = (title: string, value: string | Node) => {
    list.appendChild(element("dt", null, title));
    const item = element("dd");
    if (typeof value === "string") item.textContent = value || "–"; else item.appendChild(value);
    list.appendChild(item);
  };
  row("Cueanexo", punto.cueanexo);
  row("Turno", punto.turno);
  row("Inspector", punto.inspector);
  row("Acta", actaLink(punto));
  row("Resultado", punto.resultado);
  box.appendChild(list);
  return box;
}

function clusterIcon(group: any) {
  const markers: any[] = group.getAllChildMarkers();
  const verified = markers.filter((m) => m.options.constatada).length;
  let className = "insp-tablero-grupo";
  if (verified === 0) className += " insp-tablero-grupo-sin-constatacion";
  else if (verified < markers.length) className += " insp-tablero-grupo-mixto";
  const total = markers.length;
  const side = total < 10 ? 30 : total < 100 ? 38 : 48;
  const body = document.createElement("span");
  body.textContent = formatoNumero.format(total);
  return leaflet().divIcon({ html: body, className, iconSize: leaflet().point(side, side) });
}

type Live = { map: any; layer: any; signature: string | null };

export default function TableroMapa({ puntos, fitToken, territory }: { puntos: Punto[] | null; fitToken: number; territory: boolean }) {
  const container = useRef<HTMLDivElement>(null);
  const live = useRef<Live | null>(null);
  // `ajustarMapa`: true at load and after each change of filters; consumed by the next answer.
  const pendingFit = useRef(true);
  const [state, setState] = useState<"loading" | "ready" | "failed">("loading");

  useEffect(() => {
    let active = true;
    loadLeaflet().then(() => {
      if (!active || !container.current || live.current) return;
      const L = leaflet();
      const limits = L.latLngBounds(ARGENTINA).pad(0.08);
      const map = L.map(container.current, { scrollWheelZoom: false, maxBounds: limits, maxBoundsViscosity: 1.0, zoomSnap: 0.25, worldCopyJump: false });
      map.attributionControl.setPrefix(false);
      map.fitBounds(ARGENTINA);
      // The minimum zoom shows the whole country: it cannot be zoomed out further.
      map.setMinZoom(map.getZoom());
      L.tileLayer("https://wms.ign.gob.ar/geoserver/gwc/service/tms/1.0.0/capabaseargenmap@EPSG%3A3857@png/{z}/{x}/{-y}.png", {
        maxZoom: 18, noWrap: true, bounds: limits,
        attribution: '<a href="https://www.ign.gob.ar/" target="_blank" rel="noopener">Instituto Geográfico Nacional</a>',
      }).addTo(map);
      const layer = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 50, chunkedLoading: true, iconCreateFunction: clusterIcon });
      map.addLayer(layer);
      map.on("focus click", () => map.scrollWheelZoom.enable());
      map.on("blur mouseout", () => map.scrollWheelZoom.disable());
      live.current = { map, layer, signature: null };
      setState("ready");
    }).catch(() => { if (active) setState("failed"); });
    return () => {
      active = false;
      live.current?.map.remove();
      live.current = null;
    };
  }, []);

  useEffect(() => { pendingFit.current = true; }, [fitToken]);

  useEffect(() => {
    const current = live.current;
    if (state !== "ready" || !current || !puntos) return;
    const L = leaflet();
    const signature = puntos.map((p) => `${p.numero}${p.constatada ? "+" : "-"}`).join(",");
    if (signature !== current.signature) {
      current.signature = signature;
      current.layer.clearLayers();
      current.layer.addLayers(puntos.map((punto) => {
        const marker = L.circleMarker([punto.lat, punto.lng], {
          radius: 7, color: "#ffffff", weight: 2, fillColor: punto.constatada ? TEAL : NARANJA, fillOpacity: 0.95, constatada: punto.constatada,
        });
        marker.bindPopup(() => popup(punto));
        return marker;
      }));
    }
    if (pendingFit.current) {
      pendingFit.current = false;
      if (territory && puntos.length) current.map.fitBounds(current.layer.getBounds(), { padding: [30, 30], maxZoom: 13 });
      else current.map.fitBounds(ARGENTINA);
    }
  }, [state, puntos, territory]);

  return (
    <div className="insp-tablero-mapa" data-tablero-mapa="" ref={container} role="region" aria-label="Mapa de Argentina con las visitas con ubicación GPS, agrupadas por zona">
      {state === "failed" ? "No se pudo cargar el mapa." : null}
    </div>
  );
}
