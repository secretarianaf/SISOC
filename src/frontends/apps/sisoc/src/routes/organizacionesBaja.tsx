/* eslint-disable react-refresh/only-export-components -- the screen exports its validator for the unit tests. */
import { useState, type FormEvent } from "react";
import { InsumosToastList } from "../InsumosToast";
import { FLASH_KEY, organizacionesNavigation } from "./organizacionesForm";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";

/**
 * O05.02 `organizacion_confirm_delete.html` + `components/delete_confirm.html`:
 * the cascade preview of `build_delete_preview` and the «Dar de baja
 * Organización» POST through the native `OrganizacionDeleteView`. A blocked
 * baja (409) keeps the page and shows the native error message.
 */
type Item = { modelo: string; cantidad: number; modo: string; ejemplos: string[] };
type Preview = { total_afectados: number; total_baja_logica?: number; total_borrado_fisico?: number; desglose_por_modelo: Item[] };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type BajaData = { id: number; nombre: string; cascade_preview: Preview | null; motivo: string | null; urls: { cancel: string; list: string }; messages: Message[] };

const LEVELS = ["success", "error", "warning", "info"];
const FAILED: Message = { message: "No se pudo dar de baja la organización. Recargá la página para ver el estado actual.", level: "error" };

export function bajaValid(v: unknown): v is BajaData {
  return record(v) && typeof v.id === "number" && text(v.nombre) && record(v.urls) && internal(v.urls.cancel) && internal(v.urls.list) &&
    (v.cascade_preview === null || (record(v.cascade_preview) && Array.isArray(v.cascade_preview.desglose_por_modelo))) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

function BajaContent({ data }: { data: BajaData }) {
  const [toasts, setToasts] = useState<Message[]>(data.messages);
  const [pending, setPending] = useState(false);
  const preview = data.cascade_preview;
  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      const { data: body, status } = await webClient.post(`web/comedores/organizaciones/${data.id}/baja/`, new URLSearchParams(), { validateStatus: (s: number) => accepted(s) || s === 409 });
      if (status === 200 && record(body) && internal(body.redirect)) {
        if (Array.isArray(body.messages) && body.messages.length) { try { window.sessionStorage.setItem(FLASH_KEY, JSON.stringify(body.messages)); } catch { /* the message is optional */ } }
        organizacionesNavigation.assign(body.redirect);
        return;
      }
      setToasts(status === 409 && record(body) && Array.isArray(body.messages) ? (body.messages as Message[]) : [FAILED]);
    } catch {
      setToasts([FAILED]);
    } finally { setPending(false); }
  }
  return (
    <>
      <InsumosToastList messages={toasts} />
      <div className="error-page mt-5 px-3">
        <div className="error-content">
          <h3><i className="fas fa-exclamation-triangle text-danger px-2" /> Dar de baja Organización</h3>
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
                        <td>{item.ejemplos?.length ? item.ejemplos.join(", ") : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          <div className="text-left">
            <form method="post" onSubmit={submit}>
              <button type="submit" className="btn btn-danger btn-sm" disabled={pending}>Dar de baja Organización</button>{" "}
              <a href={data.urls.cancel} className="btn btn-secondary btn-sm">Cancelar</a>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

export default function OrganizacionBaja({ id }: { id: number }) {
  const [state] = useMainResource(`web/comedores/organizaciones/${id}/baja/`, bajaValid);
  return renderMain(state, "Cargando organización…", (data) => ({
    title: `Organizacion - ${data.nombre}`,
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <div className="breadcrumb-item"><a href="/organizaciones/listar">Organizaciones</a></div>
        <div className="breadcrumb-item"><a href={data.urls.cancel}>{data.nombre}</a></div>
        <div className="breadcrumb-item">Eliminar</div>
      </ol>
    ),
    content: <BajaContent data={data} />,
  }));
}
