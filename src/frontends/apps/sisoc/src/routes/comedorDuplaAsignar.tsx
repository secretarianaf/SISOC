/* eslint-disable react-refresh/only-export-components -- route module: the validator and the navigation seam are exported for the tests. */
import { useRef, useState, type MouseEvent } from "react";
import { sameOriginTarget } from "./cdiObservaciones";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CO07 `comedor/asignar_dupla_form.html` (`comedores/dupla/asignar/<pk>`): the active technical
 * teams with a name filter and one «Asignar» button per row. Data and the POST go through
 * `/api/web/comedores/asignar-dupla/<pk>/`, which runs the native `AsignarDuplaListView` (scoped
 * comedor, native messages); the confirmed redirect is a full-page navigation like the native 302.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type DuplaAsignarData = {
  comedor: { id: number; nombre: string; url: string }; dupla_actual_id: number | null;
  duplas: { id: number; nombre: string; coordinador: string; tecnicos: string; abogado: string }[];
  urls: { comedores: string }; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const CONFIRM = "¿Estás seguro de que deseas asignar esta dupla?";
const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);

export function duplaAsignarValid(v: unknown): v is DuplaAsignarData {
  return record(v) && record(v.comedor) && integer(v.comedor.id) && text(v.comedor.nombre) && internal(v.comedor.url) &&
    (v.dupla_actual_id === null || integer(v.dupla_actual_id)) && record(v.urls) && internal(v.urls.comedores) &&
    Array.isArray(v.duplas) && v.duplas.every((d) => record(d) && integer(d.id) && text(d.nombre) && text(d.coordinador) && text(d.tecnicos) && text(d.abogado)) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const duplaAsignarNavigation = { assign: (to: string) => window.location.assign(to), confirm: (message: string) => window.confirm(message) };

function DuplaTable({ data, endpoint }: { data: DuplaAsignarData; endpoint: string }) {
  const [filter, setFilter] = useState("");
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  // The native `filterTable()` (keyup) hides every row whose first cell does not contain the text.
  const shown = (name: string) => name.toUpperCase().includes(filter.toUpperCase());
  async function assign(event: MouseEvent, id: number) {
    event.preventDefault();
    if (busy.current || uncertain || !duplaAsignarNavigation.confirm(CONFIRM)) return;
    busy.current = true; setPending(true);
    let message = UNCERTAIN;
    try {
      const { data: response, status } = await webClient.post(endpoint, new URLSearchParams({ dupla_id: String(id) }), { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 403 || s === 404 });
      const to = status < 300 && record(response) && response.ok === true ? sameOriginTarget(response.redirect) : null;
      if (to) { duplaAsignarNavigation.assign(to); return; }
      if (status === 403 && record(response) && text(response.detail)) message = response.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    busy.current = false; setPending(false); setUncertain(message);
  }
  return <>
    <div className="mb-3">
      <input type="text" id="duplaFilter" className="form-control" placeholder="Filtrar por nombre de equipo técnico..." data-filter-table-on-keyup="true"
        onKeyUp={(event) => setFilter(event.currentTarget.value)} />
    </div>
    <form method="post" onSubmit={(event) => event.preventDefault()}>
      <table className="table table-striped" id="duplaTable">
        <thead>
          <tr><th>Nombre</th><th>Coordinador</th><th>Técnicos</th><th>Abogado</th><th>Acciones</th><th /></tr>
        </thead>
        <tbody>
          {data.duplas.map((dupla) => (
            <tr key={dupla.id} style={shown(dupla.nombre) ? undefined : { display: "none" }}>
              <td>{dupla.nombre}</td>
              <td>{dupla.coordinador}</td>
              <td>{dupla.tecnicos}</td>
              <td>{dupla.abogado}</td>
              <td>
                <button type="submit" name="dupla_id" value={dupla.id} data-confirm-click={CONFIRM} className="btn btn-primary btn-sm" disabled={pending}
                  onClick={(event) => void assign(event, dupla.id)}>Asignar</button>
              </td>
              <td style={{ width: 100 }}>
                {dupla.id === data.dupla_actual_id && <i className="bi bi-check-circle-fill text-success" />}
              </td>
            </tr>
          ))}
          {data.duplas.length === 0 && (
            <tr style={shown("No hay equipos técnicos activos disponibles.") ? undefined : { display: "none" }}>
              <td colSpan={6}>No hay equipos técnicos activos disponibles.</td>
            </tr>
          )}
        </tbody>
      </table>
      {uncertain && <p role="alert">{uncertain}</p>}
    </form>
  </>;
}

function DuplaAsignarPage({ pk }: { pk: string }) {
  const endpoint = `web/comedores/asignar-dupla/${pk}/`;
  const [state] = useMainResource(endpoint, duplaAsignarValid);
  return renderMain(state, "Cargando comedor…", (data) => ({
    title: `Espacio Comunitario: ${data.comedor.nombre}`,
    heading: <span className="ml-2 h5">Asignar equipo técnico</span>,
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <div className="breadcrumb-item"><a href={data.urls.comedores}>Espacios Comunitarios</a></div>
        <div className="breadcrumb-item active"><a href={data.comedor.url}>{data.comedor.nombre}</a></div>
      </ol>
    ),
    content: <>
      <NativeToasts messages={data.messages} />
      <div className="container mt-4">
        <h2>Asignar Equipo Técnico</h2>
        <DuplaTable data={data} endpoint={endpoint} />
      </div>
    </>,
  }));
}

// Native URL `comedores/dupla/asignar/<pk>` (no trailing slash).
export const comedorDuplaAsignarRoute: RouteDefinition<{ pk: string }> = {
  name: "comedores-dupla-asignar",
  match(pathname) {
    const m = /^\/comedores\/dupla\/asignar\/([1-9]\d*)$/.exec(pathname);
    return m ? { pk: m[1] } : null;
  },
  render: ({ pk }) => <DuplaAsignarPage key={pk} pk={pk} />,
};
