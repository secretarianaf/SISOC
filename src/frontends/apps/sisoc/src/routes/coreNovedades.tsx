/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useState } from "react";
import { NativeToasts } from "./nativeParity";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { messagesValid, type CoreMessage } from "./coreCommon";
import type { RouteDefinition } from "./types";

/**
 * T02.01: `changelog.html`. GET `/api/web/core/novedades/` projects `changelog_view`: the parsed
 * `CHANGELOG.md` blocks (already HTML, like the native `|safe`) and the cached "last update" label.
 */
export type NovedadesData = {
  current_version: string; versions: { version: string; html: string }[]; error: boolean;
  urls: { architecture: string; home: string }; messages: CoreMessage[];
};

export const novedadesValid = (v: unknown): v is NovedadesData =>
  record(v) && text(v.current_version) && typeof v.error === "boolean" && messagesValid(v.messages) &&
  Array.isArray(v.versions) && v.versions.every((e) => record(e) && text(e.version) && text(e.html)) &&
  record(v.urls) && internal(v.urls.architecture) && internal(v.urls.home);

function Version({ entry, index }: { entry: NovedadesData["versions"][number]; index: number }) {
  // Bootstrap collapse: the first block starts open and "Ver detalle" toggles it.
  const [open, setOpen] = useState(index === 0);
  return (
    <div className="card mb-3">
      <div className="card-header d-flex align-items-center gap-2">
        <h5 className="mb-0 flex-grow-1">
          <i className="bi bi-tag-fill me-2" />{" "}
          Versión SISOC {entry.version}
        </h5>
        <button className="btn btn-sm btn-outline-secondary ms-auto" type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
          Ver detalle
        </button>
      </div>
      <div id={`version-${index + 1}`} className={`collapse${open ? " show" : ""}`}>
        {/* Trusted: the backend converts the repository's own CHANGELOG.md, as the native template did with |safe. */}
        <div className="card-body" dangerouslySetInnerHTML={{ __html: entry.html }} />
      </div>
    </div>
  );
}

export function NovedadesContent({ data }: { data: NovedadesData }) {
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row">
        <div className="col-12">
          {!data.error ? (
            <>
              <div className="mb-3 d-flex align-items-center gap-2">
                <span className="badge bg-primary fs-6">
                  <i className="bi bi-info-circle-fill me-1" />{" "}
                  Última actualización: {data.current_version}
                </span>
                <a href={data.urls.architecture} className="btn btn-sm btn-outline-primary" target="_blank" rel="noopener">
                  <i className="bi bi-diagram-3 me-1" />{" "}
                  Ver arquitectura
                </a>
              </div>
              {data.versions.map((entry, index) => <Version key={entry.version + index} entry={entry} index={index} />)}
            </>
          ) : (
            <div className="alert alert-danger">
              <i className="bi bi-exclamation-triangle-fill me-2" />{" "}
              <strong>No fue posible obtener las novedades del sistema en este momento.</strong>
              <p className="mb-0 mt-2">Por favor, intente más tarde o contacte al administrador del sistema.</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function NovedadesPage() {
  const [state] = useMainResource("web/core/novedades/", novedadesValid);
  // The native template defines no `title` block ("SISOC - ").
  return renderMain(state, "Cargando novedades…", (data) => ({
    title: "",
    activePath: "novedades/",
    heading: "Novedades del Sistema",
    breadcrumb: (
      <>
        <li className="breadcrumb-item"><a href={data.urls.home}>Inicio</a></li>
        <li className="breadcrumb-item active" aria-current="page">Novedades</li>
      </>
    ),
    content: <NovedadesContent data={data} />,
  }));
}

export const coreNovedadesRoute: RouteDefinition<Record<string, never>> = {
  name: "core-novedades",
  match: (pathname) => (pathname === "/novedades/" ? {} : null),
  render: () => <NovedadesPage />,
};
