/* eslint-disable react-refresh/only-export-components -- the screen exports its validator and navigation seam for the unit tests. */
import { useState, type FormEvent } from "react";
import { InsumosToastList } from "../InsumosToast";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { CascadePreview, type Preview } from "./organizacionesBaja";
import type { RouteDefinition } from "./types";

/**
 * CO07.01 `comedor_confirm_delete.html` + `components/delete_confirm.html`: the
 * cascade preview and the «Dar de baja» POST through the native
 * `ComedorDeleteView`. On success the page goes to the list, which shows the
 * native message.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type BajaData = { id: number; nombre: string; cascade_preview: Preview | null; urls: { cancel: string; list: string }; messages: Message[] };

const LEVELS = ["success", "error", "warning", "info"];
const FAILED: Message = { message: "No se pudo dar de baja el comedor. Recargá la página para ver el estado actual.", level: "error" };

export function bajaValid(v: unknown): v is BajaData {
  return record(v) && typeof v.id === "number" && text(v.nombre) && record(v.urls) && internal(v.urls.cancel) && internal(v.urls.list) &&
    (v.cascade_preview === null || (record(v.cascade_preview) && Array.isArray(v.cascade_preview.desglose_por_modelo))) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Full-page navigation after the baja; replaceable in tests. */
export const comedorBajaNavigation = { assign: (to: string) => window.location.assign(to) };

function BajaContent({ data }: { data: BajaData }) {
  const [toasts, setToasts] = useState<Message[]>(data.messages);
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      const { data: body, status } = await webClient.post(`web/comedores/comedores/${data.id}/baja/`, new URLSearchParams(), { validateStatus: (s: number) => accepted(s) || s === 409 });
      if (status === 200 && record(body) && internal(body.redirect)) {
        comedorBajaNavigation.assign(body.redirect);
        return;
      }
      setToasts([FAILED]);
    } catch {
      // Network error or 5xx/504: the outcome is uncertain, nothing is retried.
      setToasts([FAILED]);
    } finally { setPending(false); }
  }
  return (
    <>
      <InsumosToastList messages={toasts} />
      <div className="error-page mt-5 px-3">
        <div className="error-content">
          <h3><i className="fas fa-exclamation-triangle text-danger px-2" /> Atención!</h3>
          <p>¿Estás seguro que deseas realizar una baja lógica en cascada del registro <span className="font-weight-bold">{data.nombre.toUpperCase()}</span>?</p>
          <CascadePreview preview={data.cascade_preview} />
          <div className="text-left">
            <form method="post" onSubmit={submit}>
              <button type="submit" className="btn btn-danger btn-sm" disabled={pending}>Dar de baja</button>{" "}
              <a href={data.urls.cancel} className="btn btn-secondary btn-sm">Cancelar</a>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

function BajaPage({ id }: { id: string }) {
  const [state] = useMainResource(`web/comedores/comedores/${id}/baja/`, bajaValid);
  return renderMain(state, "Cargando comedor…", (data) => ({
    title: `Espacio Comunitario - ${data.nombre}`,
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <div className="breadcrumb-item"><a href={data.urls.list}>Espacios Comunitarios</a></div>
        <div className="breadcrumb-item"><a href={data.urls.cancel}>{data.nombre}</a></div>
        <div className="breadcrumb-item">Eliminar</div>
      </ol>
    ),
    content: <BajaContent data={data} />,
  }));
}

// Native GET page `comedores/<pk>/eliminar` (no trailing slash).
export const comedorBajaRoute: RouteDefinition<{ id: string }> = {
  name: "comedores-baja",
  match(pathname) {
    const m = pathname.match(/^\/comedores\/([0-9]+)\/eliminar$/);
    return m ? { id: m[1] } : null;
  },
  render(params) {
    return <BajaPage key={params.id} id={params.id} />;
  },
};
