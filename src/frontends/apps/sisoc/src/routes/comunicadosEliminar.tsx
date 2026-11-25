/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";

/**
 * CM02.02 delete confirmation: `comunicado_confirm_delete.html`. GET
 * `/api/web/comedores/comunicados/<id>/eliminar/` runs `ComunicadoDeleteView`
 * (404, then 403 without the delete permission); the confirmed POST runs its
 * `post()` and the redirect to the management list is a full-page navigation.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type ComunicadoEliminarData = { id: number; titulo: string; fecha_creacion: string; creador: string; adjuntos_count: number; messages: Message[] };

const API = "web/comedores/comunicados/";
const GESTION = "/comunicados/gestion/";
const LEVELS = ["success", "error", "warning", "info"];
const UNCERTAIN = "No se pudo confirmar el resultado. Revise la gestión de comunicados antes de volver a intentar.";

export function eliminarValid(v: unknown): v is ComunicadoEliminarData {
  return record(v) && Number.isSafeInteger(v.id) && text(v.titulo) && text(v.fecha_creacion) && text(v.creador) &&
    Number.isSafeInteger(v.adjuntos_count) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const comunicadosEliminarNavigation = { assign: (to: string) => window.location.assign(to) };

export function ComunicadoEliminarContent({ data }: { data: ComunicadoEliminarData }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || error) return;
    busy.current = true; setPending(true);
    const outcome = await postForm(`${API}${data.id}/eliminar/`, new URLSearchParams());
    if (outcome.kind === "redirect" && internal(outcome.url)) { comunicadosEliminarNavigation.assign(outcome.url); return; }
    setError(outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN);
    setPending(false);
  }
  return <>
    <InsumosToastList messages={data.messages} />
    <div className="container mt-4">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card border-danger">
            <div className="card-header bg-danger text-white">
              <h5 className="mb-0"><i className="fas fa-exclamation-triangle" />{" "}Confirmar Eliminación</h5>
            </div>
            <div className="card-body">
              <p className="lead">¿Estás seguro de que deseas eliminar el siguiente comunicado?</p>
              <div className="alert alert-secondary">
                <strong>{data.titulo}</strong>
                <br />
                <small className="text-muted">Creado el {data.fecha_creacion} por {data.creador}</small>
              </div>
              {data.adjuntos_count > 0 && (
                <div className="alert alert-warning">
                  <i className="fas fa-paperclip" />{" "}Este comunicado tiene <strong>{data.adjuntos_count}</strong> archivo(s) adjunto(s) que también serán eliminados.
                </div>
              )}
              <p className="text-danger"><i className="fas fa-exclamation-circle" />{" "}<strong>Esta acción no se puede deshacer.</strong></p>
              {error && <p role="alert" className="text-danger">{error}</p>}
              <form method="post" onSubmit={submit}>
                <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
                <div className="d-flex justify-content-between">
                  <a href={GESTION} className="btn btn-outline-secondary"><i className="fas fa-arrow-left" />{" "}Cancelar</a>
                  <button type="submit" className="btn btn-danger" disabled={pending || !!error}><i className="fas fa-trash" />{" "}Sí, Eliminar</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </>;
}

export function ComunicadoEliminarPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/eliminar/`, eliminarValid);
  return renderMain(state, "Cargando comunicado…", (data) => ({
    title: "Eliminar Comunicado",
    heading: "Eliminar Comunicado",
    breadcrumb: null,
    content: <ComunicadoEliminarContent data={data} />,
  }));
}
