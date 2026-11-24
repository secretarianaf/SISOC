/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect } from "react";

/** CDN files of the native tablero page: same versions and integrity hashes, loaded once, never bundled. */
const LEAFLET_CSS = [
  { href: "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css", integrity: "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" },
  { href: "https://cdn.jsdelivr.net/npm/leaflet.markercluster@1.5.3/dist/MarkerCluster.css", integrity: "sha256-YU3qCpj/P06tdPBJGPax0bm6Q1wltfwjsho5TR4+TYc=" },
];
const LEAFLET_JS = [
  { src: "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js", integrity: "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" },
  { src: "https://cdn.jsdelivr.net/npm/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js", integrity: "sha256-Hk4dIpcqOSb0hZjgyvFOP+cEmDXUKKNE/tT542ZbNQg=" },
];
export const leaflet = (): any => (window as unknown as { L?: any }).L;
export const ready = () => !!leaflet()?.markerClusterGroup;

/** Leaflet stylesheets in the head of the native page, after `panel.css` and before `tablero.css`. */
export function useLeafletStyles() {
  useEffect(() => {
    const links = LEAFLET_CSS.map(({ href, integrity }) => {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.setAttribute("integrity", integrity);
      link.setAttribute("crossorigin", "anonymous");
      link.dataset.claroFrame = "";
      document.head.appendChild(link);
      return link;
    });
    return () => links.forEach((link) => link.remove());
  }, []);
}

function addScript({ src, integrity }: { src: string; integrity: string }) {
  return new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.setAttribute("integrity", integrity);
    script.setAttribute("crossorigin", "anonymous");
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(src));
    document.body.appendChild(script);
  });
}

let loading: Promise<void> | null = null;
/** Scripts load once per page, in order (markercluster extends Leaflet). */
export function loadLeaflet(): Promise<void> {
  if (ready()) return Promise.resolve();
  loading ??= LEAFLET_JS.reduce((chain, script) => chain.then(() => addScript(script)), Promise.resolve())
    .then(() => { if (!ready()) throw new Error("leaflet"); })
    .catch((error) => { loading = null; throw error; });
  return loading;
}
