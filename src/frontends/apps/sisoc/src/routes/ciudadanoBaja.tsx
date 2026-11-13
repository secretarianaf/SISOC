/* eslint-disable react-refresh/only-export-components -- route module: the validator and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeToasts } from "./nativeParity";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * C05.03: `ciudadanos/ciudadano_confirm_delete.html` (the `components/delete_confirm.html` card). GET
 * `/api/web/ciudadanos/<pk>/baja/` runs `CiudadanosDeleteView` (403 without `ciudadanos.delete_ciudadano`, then 404); the
 * confirmed POST runs its `post()` (logical cascade delete) and the redirect to the list is a full-page navigation.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Fila = { modelo: string; cantidad: number; baja_logica: boolean; ejemplos: string[] };
export type BajaData = {
  id: number; nombre_mayusculas: string; cancelar_url: string; messages: Message[];
  cascade_preview: { total_afectados: number; total_baja_logica: number; total_borrado_fisico: number; desglose: Fila[] };
};

const LEVELS = ["success", "error", "warning", "info"];
const count = (v: unknown): v is number => Number.isSafeInteger(v);
const UNCERTAIN = "No se pudo confirmar el resultado. Revise la ficha del ciudadano antes de volver a intentar.";

export function bajaValid(v: unknown): v is BajaData {
  if (!record(v) || !count(v.id) || !text(v.nombre_mayusculas) || !internal(v.cancelar_url)) return false;
  const p = v.cascade_preview;
  return record(p) && count(p.total_afectados) && count(p.total_baja_logica) && count(p.total_borrado_fisico) && Array.isArray(p.desglose) &&
    p.desglose.every((f) => record(f) && text(f.modelo) && count(f.cantidad) && typeof f.baja_logica === "boolean" && Array.isArray(f.ejemplos) && f.ejemplos.every(text)) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const ciudadanoBajaNavigation = { assign: (to: string) => window.location.assign(to) };

/** `endpoint`: where the confirmed POST goes (the ciudadano baja by default; the familiar unlink reuses this card). */
export function BajaContent({ data, endpoint }: { data: BajaData; endpoint?: string }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  const p = data.cascade_preview;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || error) return;
    busy.current = true; setPending(true);
    const outcome = await postForm(endpoint ?? `web/ciudadanos/${data.id}/baja/`, new URLSearchParams());
    if (outcome.kind === "redirect" && internal(outcome.url)) { ciudadanoBajaNavigation.assign(outcome.url); return; }
    setError(outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN);
    setPending(false);
  }
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="error-page mt-5 px-3">
        <div className="error-content">
          <h3><i className="fas fa-exclamation-triangle text-danger px-2" /> Atención!</h3>
          <p>
            ¿Estás seguro que deseas realizar una baja lógica en cascada del registro
            {" "}<span className="font-weight-bold">{data.nombre_mayusculas}</span>?
          </p>
          <div className="alert alert-info">
            <div><strong>Total de registros afectados:</strong>{" "}{p.total_afectados}</div>
            {p.total_baja_logica > 0 && <div>Bajas lógicas: {p.total_baja_logica}</div>}
            {p.total_borrado_fisico > 0 && <div>Borrados físicos técnicos: {p.total_borrado_fisico}</div>}
          </div>
          <div className="table-responsive mb-3">
            <table className="table table-sm table-striped mb-0">
              <thead><tr><th>Modelo</th><th>Cantidad</th><th>Acción</th><th>Ejemplos</th></tr></thead>
              <tbody>
                {p.desglose.map((f) => (
                  <tr key={f.modelo + String(f.baja_logica)}>
                    <td>{f.modelo}</td>
                    <td>{f.cantidad}</td>
                    <td>{f.baja_logica ? "Baja lógica" : "Borrado físico técnico"}</td>
                    <td>{f.ejemplos.length > 0 ? f.ejemplos.join(", ") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {error && <p role="alert" className="text-danger">{error}</p>}
          <div className="text-left">
            <form method="post" action="" onSubmit={submit}>
              <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
              <button type="submit" className="btn btn-danger btn-sm" disabled={pending || !!error}>Dar de baja</button>
              {" "}<a href={data.cancelar_url} className="btn btn-secondary btn-sm">Cancelar</a>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

function BajaPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`web/ciudadanos/${pk}/baja/`, bajaValid);
  // The native template defines no title block ("SISOC - ").
  return renderMain(state, "Cargando ciudadano…", (data) => ({ title: "", heading: "", breadcrumb: null, content: <BajaContent data={data} /> }));
}

const BAJA = /^\/ciudadanos\/eliminar\/([0-9]+)$/;

export const ciudadanoBajaRoute: RouteDefinition<{ pk: string }> = {
  name: "ciudadano-baja",
  match(pathname) {
    const found = BAJA.exec(pathname);
    return found ? { pk: found[1] } : null;
  },
  render({ pk }) {
    return <BajaPage pk={pk} />;
  },
};
