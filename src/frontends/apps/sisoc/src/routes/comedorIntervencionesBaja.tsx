/* eslint-disable react-refresh/only-export-components -- route module: the validator, the confirmation and the navigation seam are shared with the observation screens and the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { sameOriginTarget } from "./cdiObservaciones";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts } from "./nativeParity";

/**
 * `components/delete_confirm.html` as the comedor soft-delete screens use it (intervention CO02,
 * observation CO06): the cascade preview, «Dar de baja» and the cancel link. GET and the confirmed
 * POST go to the vertical's web API, which runs the native `DeleteView`; the redirect is a
 * full-page navigation like the native 302 and the message shows on the next page.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type PreviewItem = { modelo: string; cantidad: number; modo: string; ejemplos: string[] };
export type BajaData = {
  id: number; object_name: string; confirm_text: string; cancel_text: string; cancel_url: string; messages: Message[];
  cascade_preview: { total_afectados: number; total_baja_logica: number; total_borrado_fisico: number; desglose_por_modelo: PreviewItem[] } | null;
};
export type IntervencionBajaData = BajaData & { breadcrumb: { etiqueta: string; url: string } };

const LEVELS = ["success", "error", "warning", "info"];
const count = (v: unknown) => Number.isSafeInteger(v) && (v as number) >= 0;

export function bajaValid(v: unknown): v is BajaData {
  if (!record(v) || !Number.isSafeInteger(v.id) || !Array.isArray(v.messages) ||
    !v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string))) return false;
  const p = v.cascade_preview;
  const previewOk = p === null || (record(p) && count(p.total_afectados) && count(p.total_baja_logica) && count(p.total_borrado_fisico) &&
    Array.isArray(p.desglose_por_modelo) && p.desglose_por_modelo.every((i) => record(i) && text(i.modelo) && count(i.cantidad) && text(i.modo) &&
      Array.isArray(i.ejemplos) && i.ejemplos.every(text)));
  return previewOk && text(v.object_name) && text(v.confirm_text) && text(v.cancel_text) && internal(v.cancel_url);
}

export function intervencionBajaValid(v: unknown): v is IntervencionBajaData {
  return bajaValid(v) && record((v as Record<string, unknown>).breadcrumb) &&
    text(((v as Record<string, unknown>).breadcrumb as Record<string, unknown>).etiqueta) &&
    internal(((v as Record<string, unknown>).breadcrumb as Record<string, unknown>).url);
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const bajaNavigation = { assign: (to: string) => window.location.assign(to) };

const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";

export function BajaContent({ data, endpoint }: { data: BajaData; endpoint: string }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  const preview = data.cascade_preview;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || error) return;
    busy.current = true; setPending(true);
    let message = UNCERTAIN;
    try {
      const { data: response, status } = await webClient.post(endpoint, new URLSearchParams(), { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 403 });
      const to = status < 300 && record(response) && response.ok === true ? sameOriginTarget(response.redirect) : null;
      if (to) { bajaNavigation.assign(to); return; }
      if (status === 403 && record(response) && text(response.detail)) message = response.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    setError(message);
    setPending(false);
  }
  return <>
    <NativeToasts messages={data.messages} />
    <div className="error-page mt-5 px-3">
      <div className="error-content">
        <h3><i className="fas fa-exclamation-triangle text-danger px-2" />{" "}Atención!</h3>
        <p>
          ¿Estás seguro que deseas realizar una baja lógica en cascada del registro
          {" "}<span className="font-weight-bold">{data.object_name}</span>?
        </p>
        {preview && <>
          <div className="alert alert-info">
            <div><strong>Total de registros afectados:</strong>{" "}{preview.total_afectados}</div>
            {preview.total_baja_logica > 0 && <div>Bajas lógicas: {preview.total_baja_logica}</div>}
            {preview.total_borrado_fisico > 0 && <div>Borrados físicos técnicos: {preview.total_borrado_fisico}</div>}
          </div>
          <div className="table-responsive mb-3">
            <table className="table table-sm table-striped mb-0">
              <thead><tr><th>Modelo</th><th>Cantidad</th><th>Acción</th><th>Ejemplos</th></tr></thead>
              <tbody>
                {preview.desglose_por_modelo.map((item, index) => (
                  <tr key={index}>
                    <td>{item.modelo}</td>
                    <td>{item.cantidad}</td>
                    <td>{item.modo === "baja_logica" ? "Baja lógica" : "Borrado físico técnico"}</td>
                    <td>{item.ejemplos.length ? item.ejemplos.join(", ") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>}
        <div className="text-left">
          <form method="post" action="" onSubmit={submit}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <button type="submit" className="btn btn-danger btn-sm" disabled={pending || !!error}>{data.confirm_text}</button>
            {" "}<a href={data.cancel_url} className="btn btn-secondary btn-sm">{data.cancel_text}</a>
            {error && <p role="alert" className="mb-0">{error}</p>}
          </form>
        </div>
      </div>
    </div>
  </>;
}

/** `intervencion_confirm_delete.html`: the breadcrumb of the template, then the shared confirmation. */
export function IntervencionBajaPage({ comedor, intervencion }: { comedor: string; intervencion: string }) {
  const endpoint = `web/comedores/intervenciones/comedor/${comedor}/baja/${intervencion}/`;
  const [state] = useMainResource(endpoint, intervencionBajaValid);
  return renderMain(state, "Cargando intervención…", (data) => ({
    title: "Acciones",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      {/* The template has `href=""`, which resolves to this very page (React drops an empty href). */}
      <li className="breadcrumb-item"><a href={`${window.location.pathname}${window.location.search}`} title="Ver listado de admisiones">Admisiones</a></li>
      <li className="breadcrumb-item "><a href={data.breadcrumb.url} title="Ver ciudadano">{data.breadcrumb.etiqueta}</a></li>
      <li className="breadcrumb-item active">Detalle</li>
    </ol>,
    content: <BajaContent data={data} endpoint={endpoint} />,
  }));
}
