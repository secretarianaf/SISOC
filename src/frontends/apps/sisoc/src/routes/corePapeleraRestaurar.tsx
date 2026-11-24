/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeToasts } from "./nativeParity";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { count, messagesValid, strings, urlsValid, type CoreMessage } from "./coreCommon";
import type { RouteDefinition } from "./types";

/**
 * T06.02: `core/trash_restore_confirm.html`. GET `/api/web/core/papelera/restaurar/<app>/<model>/<pk>/` previews the
 * cascade (`TrashRestorePreviewView`, 404 outside the trash); the confirmed POST (`confirmed=1`, plus the safe `next`)
 * runs `TrashRestoreView.post` (cascade restore, queued message) and its redirect is a full-page navigation.
 * Superusers only; a failed restore leaves the page with the refusal and nothing restored.
 */
export type RestaurarData = {
  id: number; label: string; model_identifier: string; total_afectados: number;
  details: { label: string; value: string }[]; breakdown: { modelo: string; cantidad: number; ejemplos: string[] }[];
  restore_url: string; back_url: string; next_url: string | null; urls: { home: string; list: string }; messages: CoreMessage[];
};

export const restaurarValid = (v: unknown): v is RestaurarData =>
  record(v) && count(v.id) && text(v.label) && text(v.model_identifier) && count(v.total_afectados) && internal(v.restore_url) && internal(v.back_url) &&
  (v.next_url === null || internal(v.next_url)) && messagesValid(v.messages) && urlsValid(v.urls, ["home", "list"]) &&
  Array.isArray(v.details) && v.details.every((d) => record(d) && text(d.label) && text(d.value)) &&
  Array.isArray(v.breakdown) && v.breakdown.every((b) => record(b) && text(b.modelo) && count(b.cantidad) && strings(b.ejemplos));

const UNCERTAIN = "No se pudo confirmar el resultado. Revise la papelera antes de volver a intentar.";

/** Replaceable in tests: the confirmed redirect is a full-page navigation. */
export const corePapeleraNavigation = { assign: (to: string) => window.location.assign(to) };

type Target = { app: string; model: string; pk: string };

export function RestaurarContent({ data, target }: { data: RestaurarData; target: Target }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || error) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams({ confirmed: "1" });
    if (data.next_url) body.append("next", data.next_url);
    const outcome = await postForm(`web/core/papelera/restaurar/${target.app}/${target.model}/${target.pk}/`, body);
    if (outcome.kind === "redirect" && internal(outcome.url)) { corePapeleraNavigation.assign(outcome.url); return; }
    setError(outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN);
    setPending(false);
  }
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
              <h3 className="card-title mb-0">Vista previa de restauración</h3>
              <span className="badge bg-info text-dark">ID {data.id}</span>
            </div>
            <div className="card-body">
              <p className="mb-2">Se restaurará <strong>{data.label}</strong> y su cascada de registros relacionados.</p>
              <p className="text-muted mb-3">Revisá el impacto antes de confirmar. Esta acción volverá a habilitar los registros listados a continuación.</p>
              <div className="alert alert-info d-flex justify-content-between align-items-center flex-wrap gap-2">
                <div><strong>Total afectados:</strong> {data.total_afectados}</div>
                <div className="small text-muted">Modelo: {data.model_identifier}</div>
              </div>
              <div className="card border-0 shadow-sm mb-3 text-white">
                <div className="card-body p-3">
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <span className="fw-semibold">Detalle de la instancia</span>
                    <span className="small text-muted">{data.label}</span>
                  </div>
                  <div className="row g-2">
                    {data.details.map((item) => (
                      <div className="col-6 col-md-4" key={item.label}>
                        <div className="text-muted small">{item.label}</div>
                        <div className="fw-semibold">{item.value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="table-responsive">
                <table className="table table-sm table-striped align-middle">
                  <thead><tr><th>Modelo</th><th>Cantidad</th><th>Ejemplos</th></tr></thead>
                  <tbody>
                    {data.breakdown.map((item) => (
                      <tr key={item.modelo}>
                        <td>{item.modelo}</td>
                        <td><span className="badge bg-secondary">{item.cantidad}</span></td>
                        <td>{item.ejemplos.length > 0 ? item.ejemplos.join(", ") : <span className="text-muted">-</span>}</td>
                      </tr>
                    ))}
                    {data.breakdown.length === 0 && (
                      <tr><td colSpan={3} className="text-center py-3"><div className="fw-semibold">No hay elementos a restaurar.</div></td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {error && <p role="alert" className="text-danger">{error}</p>}
              <form method="post" action={data.restore_url} className="mt-3 d-flex flex-wrap gap-2" onSubmit={submit}>
                <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
                <input type="hidden" name="confirmed" value="1" />
                {data.next_url && <input type="hidden" name="next" value={data.next_url} />}
                <button type="submit" className="btn btn-success" disabled={pending || !!error}>Restaurar en cascada</button>
                <a href={data.back_url} className="btn btn-outline-secondary">Volver al listado</a>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function RestaurarPage({ target }: { target: Target }) {
  const [state] = useMainResource(`web/core/papelera/restaurar/${target.app}/${target.model}/${target.pk}/${window.location.search}`, restaurarValid);
  return renderMain(state, "Cargando vista previa…", (data) => ({
    title: "Confirmar Restauración",
    // The native menu rules read `request.resolver_match.route`, not the URL (the URL has "ciudadanos/" in it).
    activePath: "papelera/preview-restore/<str:app_label>/<str:model_name>/<int:pk>/",
    heading: "Confirmar restauración",
    breadcrumb: (
      <>
        <li className="breadcrumb-item"><a href={data.urls.home}>Inicio</a></li>
        <li className="breadcrumb-item"><a href={data.back_url}>Papelera</a></li>
        <li className="breadcrumb-item active">Confirmar</li>
      </>
    ),
    content: <RestaurarContent data={data} target={target} />,
  }));
}

export const corePapeleraRestaurarRoute: RouteDefinition<Target> = {
  name: "core-papelera-restaurar",
  match(pathname) {
    const found = /^\/papelera\/preview-restore\/([^/]+)\/([^/]+)\/([0-9]+)\/$/.exec(pathname);
    return found ? { app: found[1], model: found[2], pk: found[3] } : null;
  },
  render: (target) => <RestaurarPage target={target} />,
};
