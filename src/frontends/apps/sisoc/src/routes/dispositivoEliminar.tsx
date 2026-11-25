/* eslint-disable react-refresh/only-export-components -- route module: the navigation seam is exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { csrfToken, integer, internal, messagesValid, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import type { RouteDefinition } from "./types";

/**
 * Delete confirmation of a Dispositivo: `dispositivos_confirm_delete.html` on its canonical URL.
 * GET `/api/web/dispositivos/<pk>/eliminar/` runs the native guard (`delete_dispositivo`) and the
 * scope 404 of `DispositivoDeleteView`. The confirmation is the native form POST to the same
 * canonical URL: the native view deletes, queues its message and redirects (full-page navigation).
 */
export type DispositivoEliminarData = { id: number; nombre_institucion: string; cancel_url: string; messages: CdfMessage[] };

const valid = (v: unknown): v is DispositivoEliminarData =>
  record(v) && integer(v.id) && text(v.nombre_institucion) && internal(v.cancel_url) && messagesValid(v.messages);

/** The confirmed POST is a native browser submission; replaceable in tests. */
export const dispositivoEliminarNavigation = { submit: (form: HTMLFormElement) => form.submit() };

function Confirmacion({ data }: { data: DispositivoEliminarData }) {
  const [pending, setPending] = useState(false);
  const sent = useRef(false);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // One submission per page: the native view answers with a redirect, never resubmitted.
    if (sent.current) return;
    sent.current = true;
    setPending(true);
    dispositivoEliminarNavigation.submit(event.currentTarget);
  }
  return (
    <div className="container mt-4">
      <div className="card">
        <div className="card-header bg-danger text-white">
          <h5 className="mb-0">Confirmar eliminación</h5>
        </div>
        <div className="card-body">
          <p className="mb-3">
            ¿Seguro que desea eliminar el dispositivo{" "}
            <strong>{data.nombre_institucion}</strong>?
          </p>
          <form method="post" action={`/dispositivos/${data.id}/eliminar`} onSubmit={submit}>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
            <button type="submit" className="btn btn-danger" disabled={pending}>Eliminar</button>{" "}
            <a href={data.cancel_url} className="btn btn-secondary">Cancelar</a>
          </form>
        </div>
      </div>
    </div>
  );
}

function DispositivoEliminar({ id }: { id: string }) {
  const state = useCdfPage(`web/dispositivos/${id}/eliminar/`, valid);
  return renderCdf(state, (data) => ({
    title: "Eliminar dispositivo",
    breadcrumb: null,
    content: <Confirmacion data={data} />,
  }));
}

const ELIMINAR = /^\/dispositivos\/([1-9]\d*)\/eliminar$/;

// Native URL without trailing slash, like `dispositivos/urls.py`.
export const dispositivoEliminarRoute: RouteDefinition<{ id: string }> = {
  name: "dispositivo-eliminar",
  match: (pathname) => {
    const found = ELIMINAR.exec(pathname);
    return found ? { id: found[1] } : null;
  },
  render: ({ id }) => <DispositivoEliminar id={id} />,
};
