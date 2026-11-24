/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";
import { accepted, internal, record, text, webClient } from "./MainFrame";
import { urlsValid } from "./coreCommon";
import type { RouteDefinition } from "./types";

/**
 * T03.01: `core/mapa_arquitectura.html`, a standalone document (no AdminLTE frame). GET
 * `/api/web/core/arquitectura/` says whether the graph exists and when it was generated; the viewer is the
 * existing `static/arquitectura/mapa.js` + `mapa.css`, which still read the graph from the session-only
 * `arquitectura/grafo.json` (never copied into an asset or into this payload). While the page is mounted the
 * shell's stylesheets are switched off, as the native document loads none of them.
 */
export type ArquitecturaData = { grafo_disponible: boolean; generado: string | null; urls: { data: string; back: string } };

export const arquitecturaValid = (v: unknown): v is ArquitecturaData =>
  record(v) && typeof v.grafo_disponible === "boolean" && (v.generado === null || text(v.generado)) && urlsValid(v.urls, ["data", "back"]);

const FONTS = "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap";
const STYLE = "/static/arquitectura/mapa.css";
const SCRIPT = "/static/arquitectura/mapa.js";

type State = { status: "loading" } | { status: "error" } | { status: "forbidden"; prerequisite: WebPrerequisite | null } | { status: "ready"; data: ArquitecturaData };

/** The native document: its own title and fonts, no inherited stylesheet, no body classes, no theme attribute. */
function useStandaloneDocument(active: boolean, withMap: boolean) {
  useEffect(() => {
    if (!active) return undefined;
    const title = document.title;
    const bodyClass = document.body.className;
    const root = document.documentElement;
    const theme = root.getAttribute("data-bs-theme");
    root.removeAttribute("data-bs-theme");
    const shell = Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]'));
    const previous = shell.map((link) => link.hasAttribute("disabled"));
    shell.forEach((link) => link.setAttribute("disabled", ""));
    document.title = "Arquitectura de SISOC";
    document.body.className = "";
    const added: HTMLElement[] = [];
    const link = (attrs: Record<string, string>) => {
      const el = document.createElement("link");
      Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
      document.head.appendChild(el); added.push(el);
    };
    link({ rel: "preconnect", href: "https://fonts.gstatic.com", crossorigin: "" });
    link({ rel: "stylesheet", href: FONTS });
    if (withMap) {
      link({ rel: "stylesheet", href: STYLE });
      const script = document.createElement("script");
      script.src = SCRIPT; script.defer = true;
      document.body.appendChild(script); added.push(script);
    }
    return () => {
      added.forEach((el) => el.remove());
      shell.forEach((el, i) => { if (!previous[i]) el.removeAttribute("disabled"); });
      document.title = title; document.body.className = bodyClass;
      if (theme !== null) root.setAttribute("data-bs-theme", theme);
    };
  }, [active, withMap]);
}

export function ArquitecturaContent({ data }: { data: ArquitecturaData }) {
  useStandaloneDocument(true, data.grafo_disponible);
  if (data.grafo_disponible) {
    // `.mapa-app` must be a direct child of `<body>` (the stylesheet matches `html:has(> body > .mapa-app)`).
    return createPortal(<div id="mapa" data-grafo={data.urls.data} data-volver={data.urls.back} />, document.body);
  }
  return (
    <div className="container py-5">
      <h1 className="h4">El mapa de arquitectura todavía no fue generado</h1>
      <p className="text-muted">
        En desarrollo se arma leyendo el repositorio. En deploy se genera con
        el código completo al construir la imagen y se conserva en cada arranque.
        Para generarlo a mano: <code>python manage.py generar_mapa_arquitectura</code>.
      </p>
      <a href={data.urls.back}>Volver a Novedades</a>
    </div>
  );
}

function ArquitecturaPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    let active = true;
    webClient.get("web/core/arquitectura/", { validateStatus: accepted }).then((res) => {
      if (!active) return;
      if (res.status === 403) setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(res.data) });
      else setState(arquitecturaValid(res.data) && internal(res.data.urls.data) ? { status: "ready", data: res.data } : { status: "error" });
    }).catch(() => { if (active) setState({ status: "error" }); });
    return () => { active = false; };
  }, []);
  if (state.status === "loading") return <main role="status">Cargando arquitectura…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar la página.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  return <ArquitecturaContent data={state.data} />;
}

export const coreArquitecturaRoute: RouteDefinition<Record<string, never>> = {
  name: "core-arquitectura",
  match: (pathname) => (pathname === "/arquitectura/" ? {} : null),
  render: () => <ArquitecturaPage />,
};
