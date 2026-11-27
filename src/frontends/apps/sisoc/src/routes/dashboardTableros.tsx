/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useEffect } from "react";
import { Breadcrumb, internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { useCardCollapse } from "./relevamientos";
import type { RouteDefinition } from "./types";

/**
 * Dashboards (`dashboard/dashboard.html`, `/dashboard/centro-de-familia`) and embedded boards
 * (`dashboard/dashboard_tablero.html`, `/dashboard/<slug>/`). GET `/api/web/dashboard/centro-de-familia/` runs
 * `DashboardView` and GET `/api/web/dashboard/<slug>/` runs `TableroEmbedView` (403 when the board denies the
 * user, 404 for an unknown or inactive board; a board with its own screen answers the native redirect). The
 * indicators arrive as the template prints them ("Sin información" without a value): a zero never stands for
 * missing data, and when the remote source failed the page says so. The remote reports stay in their iframes.
 * Read only.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
const METRICAS = ["cantidad_comedores_activos", "cantidad_relevamientos_activos", "presupuesto_desayuno", "presupuesto_merienda", "presupuesto_comida"] as const;
export type DashboardData = {
  can_view: boolean; metricas_desactualizadas: boolean; metricas_disponibles: boolean; metricas: Record<(typeof METRICAS)[number], string> | null; messages: Message[];
  embed_centro_de_familia?: string | null;
  embed_comedores?: string | null;
};
export type TableroData = {
  titulo: string; nombre: string; url: string; embed_url: string; looker_compartible: boolean; mensaje_construccion: string; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const list = (v: unknown, ok: (x: unknown) => boolean) => Array.isArray(v) && v.every(ok);
const strings = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));
const messagesOk = (v: unknown) => list(v, (m) => strings(m, ["message"]) && LEVELS.includes((m as Message).level));
const redirectOnly = (v: unknown): v is { redirect: string } => record(v) && internal(v.redirect) && Object.keys(v).length === 1;
const remote = (v: unknown) => v === "" || (text(v) && /^https:\/\//.test(v));

const optionalEmbed = (v: unknown) => v == null || (v !== "" && remote(v));

export function dashboardValid(v: unknown): v is DashboardData {
  return record(v) && typeof v.can_view === "boolean" && typeof v.metricas_desactualizadas === "boolean" && typeof v.metricas_disponibles === "boolean" &&
    (v.can_view ? strings(v.metricas, [...METRICAS]) : v.metricas === null) &&
    optionalEmbed(v.embed_centro_de_familia) && optionalEmbed(v.embed_comedores) && messagesOk(v.messages);
}

export function tableroValid(v: unknown): v is TableroData {
  return strings(v, ["titulo", "nombre", "url", "embed_url", "mensaje_construccion"]) && remote((v as TableroData).url) && remote((v as TableroData).embed_url) &&
    typeof (v as TableroData).looker_compartible === "boolean" && messagesOk((v as TableroData).messages);
}

const Colapsar = () => <div className="card-tools"><button type="button" className="btn btn-tool" data-card-widget="collapse"><i className="fas fa-minus"></i></button></div>;

export function DashboardContent({ data }: { data: DashboardData }) {
  useCardCollapse();
  const { metricas: m, embed_centro_de_familia: cdf, embed_comedores: comedores } = data;
  const tarjeta = (cls: string, icon: string, amount: string, title: string) => (
    <div className="col-4">
      <div className={`custom-card ${cls}`}>
        <div className="card-icon"><i className={icon}></i></div>
        <div className="card-content"><div className="card-amount">{amount}</div><div className="card-title">{title}</div></div>
      </div>
    </div>
  );
  const lateral = (icon: string, title: string, amount: string) => (
    <div className="custom-card mb-2">
      <div className="card-icon"><i className={icon}></i></div>
      <div className="card-content"><div className="card-title">{title}</div><div className="card-amount">{amount}</div></div>
    </div>
  );
  const dinero = (v: string) => `$${v}`;
  return (
    <>
      <link rel="stylesheet" href="https://code.ionicframework.com/ionicons/2.0.1/css/ionicons.min.css" />
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/charts.css/dist/charts.min.css" />
      <link rel="stylesheet" href="/static/custom/css/dashboard.css" />
      {data.metricas_desactualizadas && (
        <div className="alert alert-warning" role="status">
          No se pudieron actualizar los indicadores de Comedores.{" "}
          {data.metricas_disponibles ? "Se muestran los últimos valores disponibles." : "Todavía no hay información disponible."}
        </div>
      )}
      {cdf ? (
        <div className="row">
          <div className="container">
            <div className="card">
              <div className="card-header"><h3 className="card-title">Datos de Centro De Familia</h3><Colapsar /></div>
              <div className="card-body p-0">
                <div className="row">
                  <div className="col-12">
                    <div className="position-relative" style={{ minHeight: "75vh" }}>
                      <iframe title="Centros de Familia - Seguimiento del programa v3" src={cdf} frameBorder="0" allowFullScreen
                        style={{ position: "absolute", top: 0, left: 0, width: "100%", border: 0, minHeight: "75vh" }}></iframe>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
      {m ? (
        <div className="row mb-4">
          {tarjeta("card-violet", "fas fa-utensils", m.cantidad_comedores_activos, "Comedores Activos")}
          {tarjeta("card-red", "fas fa-clipboard-check", m.cantidad_relevamientos_activos, "Relevamientos Activos")}
          {tarjeta("card-green", "fas fa-users", "0", "Beneficiarios")}
        </div>
      ) : null}
      {comedores || m ? (
        <div className="row">
          {comedores ? (
            <div className={m ? "col-md-9" : "col-12"}>
              <div className="embed-responsive embed-responsive-16by9 w-100">
                <iframe className="embed-responsive-item" title="Tablero - Comedores" src={comedores} allowFullScreen></iframe>
              </div>
            </div>
          ) : null}
          {m ? (
            <div className="col-md-3">
              {lateral("fas fa-users", "Duplas", m.presupuesto_desayuno)}
              {lateral("fas fa-coffee", "Presupuesto Desayuno", dinero(m.presupuesto_desayuno))}
              {lateral("fas fa-cookie", "Presupuesto Merienda", dinero(m.presupuesto_merienda))}
              {lateral("fas fa-utensils", "Presupuesto Comida", dinero(m.presupuesto_comida))}
            </div>
          ) : null}
        </div>
      ) : null}
      {!cdf && !comedores && !m ? (
        <div className="d-flex justify-content-center align-items-center" style={{ height: "70vh" }}>
          <img src="/static/custom/img/sisoc_logo.png" className="img-fluid" alt="Capacitación Humano" />
        </div>
      ) : null}
      <NativeToasts messages={data.messages} />
    </>
  );
}

export function TableroContent({ data }: { data: TableroData }) {
  useCardCollapse();
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/tableroEmbed.css" />
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header"><h3 className="card-title mb-0">{data.titulo}</h3><Colapsar /></div>
            <div className="card-body p-0">
              {data.url ? (
                <>
                  <div className="tablero-embed">
                    <iframe className="tablero-embed-frame" title={data.nombre} src={data.embed_url} allowFullScreen></iframe>
                  </div>
                  <div className="border-top p-3 bg-light">
                    <a href={data.url} className="btn btn-outline-secondary btn-sm" target="_blank" rel="noopener noreferrer">Abrir tablero en una pestana nueva</a>
                    {data.looker_compartible && (
                      <p className="text-muted small mb-0 mt-2">
                        Si Looker Studio sigue bloqueando el iframe, reemplaza esta URL por la generada en{" "}
                        <strong>File &gt; Embed report</strong>.
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <div className="d-flex align-items-center justify-content-center" style={{ minHeight: "75vh" }}>
                  <div className="text-center">
                    <i className="fas fa-chart-line fa-3x text-muted mb-3"></i>
                    <h4 className="text-muted">Tablero en confección</h4>
                    <p className="text-muted">{data.mensaje_construccion}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <NativeToasts messages={data.messages} />
    </>
  );
}

const dashboardPageValid = (v: unknown): v is DashboardData => dashboardValid(v);
const tableroPageValid = (v: unknown): v is TableroData | { redirect: string } => tableroValid(v) || redirectOnly(v);

function DashboardPage() {
  const [state] = useMainResource("web/dashboard/centro-de-familia/", dashboardPageValid);
  return renderMain(state, "Cargando tablero…", (data) => ({
    title: "", activePath: "/dashboard/centro-de-familia", breadcrumb: <Breadcrumb items={[]} />, content: <DashboardContent data={data} />,
  }));
}

function Redirecting({ to }: { to: string }) {
  useEffect(() => { window.location.replace(to); }, [to]);
  return <main role="status">Cargando tablero…</main>;
}

function TableroPage({ slug }: { slug: string }) {
  const [state] = useMainResource(`web/dashboard/${slug}/`, tableroPageValid);
  if (state.status === "ready" && redirectOnly(state.data)) return <Redirecting to={state.data.redirect} />;
  return renderMain(state, "Cargando tablero…", (data) => ({
    title: "", activePath: `/dashboard/${slug}/`, breadcrumb: <Breadcrumb items={[]} />, content: tableroValid(data) ? <TableroContent data={data} /> : null,
  }));
}

export const dashboardRoute: RouteDefinition<Record<string, never>> = {
  name: "dashboard-centro-de-familia",
  match: (pathname) => (pathname === "/dashboard/centro-de-familia" ? {} : null),
  render: () => <DashboardPage />,
};

export const dashboardTableroRoute: RouteDefinition<{ slug: string }> = {
  name: "dashboard-tablero",
  match(pathname) {
    const found = /^\/dashboard\/([-a-zA-Z0-9_]+)\/$/.exec(pathname);
    return found ? { slug: found[1] } : null;
  },
  render: ({ slug }) => <TableroPage slug={slug} />,
};
