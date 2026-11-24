/* eslint-disable react-refresh/only-export-components -- the screen exports its validator for the unit tests. */
import { useState, type FormEvent } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { UNCERTAIN, postApi, relevamientosNavigation, useToasts, type Message } from "./relevamientosApi";

/**
 * R01.02 `relevamiento_confirm_delete.html` + `components/delete_confirm.html`:
 * the cascade preview of `build_delete_preview` and the «Dar de baja» POST
 * through the native `RelevamientoDeleteView`. The native redirect goes to the
 * comedor, which shows the success message the baja queued.
 */
type Item = { modelo: string; cantidad: number; modo: string; ejemplos: string[] };
type Preview = { total_afectados: number; total_baja_logica?: number; total_borrado_fisico?: number; desglose_por_modelo: Item[] };
export type BajaData = {
  id: number; nombre: string; comedor: { id: number; nombre: string }; fecha_visita: string; cascade_preview: Preview | null;
  confirm_text: string; cancel_text: string; cancel_url: string; urls: { comedores: string }; messages: Message[];
};

const API = "web/comedores/relevamientos/";
const LEVELS = ["success", "error", "warning", "info"];

export function bajaValid(v: unknown): v is BajaData {
  return record(v) && typeof v.id === "number" && text(v.nombre) && record(v.comedor) && typeof v.comedor.id === "number" && text(v.comedor.nombre) && text(v.fecha_visita) &&
    text(v.confirm_text) && text(v.cancel_text) && internal(v.cancel_url) && record(v.urls) && internal(v.urls.comedores) &&
    (v.cascade_preview === null || (record(v.cascade_preview) && typeof v.cascade_preview.total_afectados === "number" && Array.isArray(v.cascade_preview.desglose_por_modelo) &&
      v.cascade_preview.desglose_por_modelo.every((i) => record(i) && text(i.modelo) && typeof i.cantidad === "number" && text(i.modo) && Array.isArray(i.ejemplos) && i.ejemplos.every(text)))) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

function BajaContent({ data }: { data: BajaData }) {
  const { toasts, push } = useToasts(data.messages);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const preview = data.cascade_preview;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const result = await postApi(`${API}${data.comedor.id}/relevamiento/${data.id}/eliminar/`, new URLSearchParams());
    if (result.kind === "ok") { relevamientosNavigation.assign(result.redirect); return; }
    if (result.kind === "error") push({ message: result.message, level: "error" });
    else setUncertain(true);
    setPending(false);
  }
  return (
    <>
      {toasts}
      <div className="error-page mt-5 px-3">
        <div className="error-content">
          <h3><i className="fas fa-exclamation-triangle text-danger px-2" /> Atención!</h3>
          <p>¿Estás seguro que deseas realizar una baja lógica en cascada del registro <span className="font-weight-bold">{data.nombre.toUpperCase()}</span>?</p>
          {preview && (
            <>
              <div className="alert alert-info">
                <div><strong>Total de registros afectados:</strong> {preview.total_afectados}</div>
                {preview.total_baja_logica ? <div>Bajas lógicas: {preview.total_baja_logica}</div> : null}
                {preview.total_borrado_fisico ? <div>Borrados físicos técnicos: {preview.total_borrado_fisico}</div> : null}
              </div>
              <div className="table-responsive mb-3">
                <table className="table table-sm table-striped mb-0">
                  <thead><tr><th>Modelo</th><th>Cantidad</th><th>Acción</th><th>Ejemplos</th></tr></thead>
                  <tbody>
                    {preview.desglose_por_modelo.map((item) => (
                      <tr key={item.modelo}>
                        <td>{item.modelo}</td><td>{item.cantidad}</td>
                        <td>{item.modo === "baja_logica" ? "Baja lógica" : "Borrado físico técnico"}</td>
                        <td>{item.ejemplos.length ? item.ejemplos.join(", ") : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          <div className="text-left">
            <form method="post" onSubmit={submit}>
              <button type="submit" className="btn btn-danger btn-sm" disabled={pending || uncertain}>{data.confirm_text}</button>{" "}
              <a href={data.cancel_url} className="btn btn-secondary btn-sm">{data.cancel_text}</a>
              {uncertain && <div role="alert" className="alert alert-warning mt-2">{UNCERTAIN}{" "}
                <button type="button" className="btn btn-link p-0 align-baseline" onClick={() => relevamientosNavigation.assign(window.location.pathname)}>Recargar</button></div>}
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

export default function RelevamientoBaja({ comedor, id }: { comedor: string; id: string }) {
  const [state] = useMainResource(`${API}${comedor}/relevamiento/${id}/eliminar/`, bajaValid);
  return renderMain(state, "Cargando acompañamiento territorial…", (data) => ({
    title: `Acompañamiento Territorial - ${data.id}`,
    breadcrumb: (
      <>
        <div className="breadcrumb-item"><a href={data.urls.comedores}>Comedores</a></div>
        <div className="breadcrumb-item"><a href={`/comedores/${data.comedor.id}`}>{data.comedor.nombre}</a></div>
        <div className="breadcrumb-item active"><a href={data.cancel_url}>Acompañamiento Territorial {data.fecha_visita}</a></div>
        <div className="breadcrumb-item">Eliminar</div>
      </>
    ),
    content: <BajaContent data={data} />,
  }));
}
