/* eslint-disable react-refresh/only-export-components -- the screen exports its validator and script seam for the unit tests. */
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { ConveniosSection, conveniosSectionValid } from "./organizacionConvenio";
import { DocumentosSection, documentosSectionValid } from "./organizacionDocumentos";
import { FirmantesSection, firmantesSectionValid } from "./organizacionFirmantes";
import { RendicionesFiltro, rendicionesFiltroValid, RendicionesTable, rendicionesSectionValid } from "./organizacionRendiciones";
import { FlashToasts } from "./organizacionesForm";
import { safeInternalPath } from "../webAccess";
import { record, renderMain, text, useMainResource } from "./MainFrame";

/**
 * O05.01 `organizacion_detail.html` (legajo). The API runs the native
 * `OrganizacionDetailView` and returns the template's own `content` block with
 * its partials. Until the O01-O04 lanes deliver convenios, documentación,
 * firmantes/avales and rendiciones in React, the legajo is that
 * server-rendered native fragment mounted inside the shared frame; the
 * documentation script of the native page runs on it once, as it does there.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
/** A section React draws itself in the placeholder `<div data-legajo-seccion="N">` of `html`. */
export type LegajoSection = { kind: string } & Record<string, unknown>;
export type OrganizacionLegajoData = { title: string; html: string; sections: LegajoSection[]; scripts: string[]; messages: Message[] };

const LEVELS = ["success", "error", "warning", "info"];

export function legajoValid(v: unknown): v is OrganizacionLegajoData {
  return record(v) && text(v.title) && text(v.html) &&
    Array.isArray(v.sections) && v.sections.every((x) => record(x) && text(x.kind)) &&
    Array.isArray(v.scripts) && v.scripts.every((s) => safeInternalPath(s) !== null) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Injects a native script once per page load; replaceable in tests. */
export const legajoScripts = {
  loaded: new Map<string, Promise<void>>(),
  load(src: string): Promise<void> {
    let pending = this.loaded.get(src);
    if (!pending) {
      pending = new Promise<void>((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.onload = () => resolve();
        script.onerror = () => { this.loaded.delete(src); reject(new Error(src)); };
        document.body.appendChild(script);
      });
      this.loaded.set(src, pending);
    }
    return pending;
  },
};

// The native script binds its handlers on `DOMContentLoaded`: run the same three initializers on the fragment.
const INITIALIZERS = ["orgInitRectificarModal", "orgInitDocumentoAdicional"];

function sectionView(section: LegajoSection): ReactNode {
  if (section.kind === "convenios" && conveniosSectionValid(section)) return <ConveniosSection section={section} />;
  if (section.kind === "documentos" && documentosSectionValid(section)) return <DocumentosSection section={section} />;
  if (section.kind === "firmantes" && firmantesSectionValid(section)) return <FirmantesSection section={section} />;
  if (section.kind === "rendiciones" && rendicionesSectionValid(section)) return <RendicionesTable section={section} />;
  if (section.kind === "rendiciones_filtro" && rendicionesFiltroValid(section)) return <RendicionesFiltro section={section} />;
  return null;
}

function LegajoFragment({ html, scripts, sections }: { html: string; scripts: string[]; sections: LegajoSection[] }) {
  const root = useRef<HTMLDivElement>(null);
  const [hosts, setHosts] = useState<HTMLElement[]>([]);
  useLayoutEffect(() => {
    setHosts(Array.from(root.current?.querySelectorAll<HTMLElement>("[data-legajo-seccion]") ?? []));
  }, [html]);
  useEffect(() => {
    let active = true;
    Promise.all(scripts.map((src) => legajoScripts.load(src))).then(() => {
      if (!active || !root.current || root.current.dataset.legajoInit === "1") return;
      root.current.dataset.legajoInit = "1";
      const globals = window as unknown as Record<string, unknown>;
      for (const name of INITIALIZERS) if (typeof globals[name] === "function") (globals[name] as () => void)();
      if (typeof globals.orgBindDynamicHandlers === "function") (globals.orgBindDynamicHandlers as (r: Document) => void)(document);
    }).catch(() => undefined);
    return () => { active = false; };
  }, [html, scripts]);
  // One element per `html`: a re-render with a fresh props object would reset the innerHTML and detach the section hosts.
  const fragment = useMemo(() => <div ref={root} dangerouslySetInnerHTML={{ __html: html }} />, [html]);
  return (
    <>
      {fragment}
      {hosts.map((host) => {
        const section = sections[Number(host.dataset.legajoSeccion)];
        return section ? createPortal(sectionView(section), host, host.dataset.legajoSeccion) : null;
      })}
    </>
  );
}

export default function OrganizacionLegajo({ id }: { id: number }) {
  const [state] = useMainResource(`web/comedores/organizaciones/${id}/${window.location.search}`, legajoValid);
  return renderMain(state, "Cargando organización…", (data) => ({
    title: data.title,
    breadcrumb: <></>,
    content: (
      <>
        <FlashToasts messages={data.messages} />
        <LegajoFragment html={data.html} scripts={data.scripts} sections={data.sections} />
      </>
    ),
  }));
}
