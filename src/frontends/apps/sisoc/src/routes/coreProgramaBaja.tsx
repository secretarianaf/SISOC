/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeToasts } from "./nativeParity";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { count, messagesValid, urlsValid, type CoreMessage } from "./coreCommon";
import type { RouteDefinition } from "./types";

/**
 * T05.02: `programa_confirm_delete.html`. GET `/api/web/core/programas/<pk>/eliminar/` runs `ProgramaDeleteView`
 * (404 for a missing program); the confirmed POST runs its `post()` and the redirect to the list is a
 * full-page navigation, like the native 302. Any authenticated user may delete (decision 2026-11-10).
 */
export type BajaData = { id: number; nombre: string; urls: { detail: string }; messages: CoreMessage[] };

export const bajaValid = (v: unknown): v is BajaData =>
  record(v) && count(v.id) && text(v.nombre) && messagesValid(v.messages) && urlsValid(v.urls, ["detail"]);

const UNCERTAIN = "No se pudo confirmar el resultado. Revise el listado de programas antes de volver a intentar.";

/** Replaceable in tests: the confirmed redirect is a full-page navigation. */
export const coreProgramaBajaNavigation = { assign: (to: string) => window.location.assign(to) };

export function BajaContent({ data }: { data: BajaData }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || error) return;
    busy.current = true; setPending(true);
    const outcome = await postForm(`web/core/programas/${data.id}/eliminar/`, new URLSearchParams());
    if (outcome.kind === "redirect" && internal(outcome.url)) { coreProgramaBajaNavigation.assign(outcome.url); return; }
    setError(outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN);
    setPending(false);
  }
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row">
        <div className="col-md-6">
          <div className="card card-danger">
            <div className="card-header bg-danger text-white">
              <h3 className="card-title">Confirmar eliminación</h3>
            </div>
            <div className="card-body">
              <p>¿Eliminar el programa <strong>{data.nombre}</strong>?</p>
              <p className="text-muted small">Esta acción no se puede deshacer. Verificá que el programa no esté en uso antes de eliminarlo.</p>
              {error && <p role="alert" className="text-danger">{error}</p>}
            </div>
            <div className="card-footer">
              <form method="post" action="" onSubmit={submit}>
                <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
                <button type="submit" className="btn btn-danger" disabled={pending || !!error}>
                  <i className="fas fa-trash" />{" "}Eliminar
                </button>{" "}
                <a href={data.urls.detail} className="btn btn-secondary">Cancelar</a>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function BajaPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`web/core/programas/${pk}/eliminar/`, bajaValid);
  return renderMain(state, "Cargando programa…", (data) => ({
    title: "Confirmar eliminación",
    activePath: "programas/<int:pk>/eliminar/",
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <li className="breadcrumb-item"><a href="/programas/">Programas</a></li>
        <li className="breadcrumb-item active">Eliminar</li>
      </ol>
    ),
    content: <BajaContent data={data} />,
  }));
}

export const coreProgramaBajaRoute: RouteDefinition<{ pk: string }> = {
  name: "core-programa-baja",
  match(pathname) {
    const found = /^\/programas\/([0-9]+)\/eliminar\/$/.exec(pathname);
    return found ? { pk: found[1] } : null;
  },
  render: ({ pk }) => <BajaPage pk={pk} />,
};
