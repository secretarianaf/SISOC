/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen and validator live here with the route. */
import { Fragment } from "react";
import { messagesValid, nullableText, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import { Breadcrumb, breadcrumbValid, type Breadcrumbs } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * DC02.01 (contract DC01-DC02, #2785): `datacalle/encuesta_detail.html` on its
 * native URL. Data comes projected from `EncuestaDetailView` through
 * `/api/web/dispositivos/datacalle/casos/<uuid>/` (G1 v1): only what the ficha
 * shows, answers already turned into labels by `respuestas_legibles`.
 */
const API = "web/dispositivos/datacalle/casos/";

type Item = { etiqueta: string; valor: string; historico: boolean };
type Pagina = { titulo: string; items: Item[] };
export type CasoData = {
  id: string; titulo: string; estado: string; estado_display: string; origen_display: string; relevador: string | null;
  fecha_inicio: string; variante_etiqueta: string; es_formulario_menores: boolean; sin_entrevista_por_franja: boolean;
  persona_entrevistada_etiqueta: string; respuestas: Pagina[]; breadcrumb: Breadcrumbs; messages: CdfMessage[];
};

const paginaValid = (p: unknown): p is Pagina => record(p) && text(p.titulo) && Array.isArray(p.items) &&
  p.items.every((i) => record(i) && text(i.etiqueta) && text(i.valor) && typeof i.historico === "boolean");

export function casoValid(v: unknown): v is CasoData {
  return record(v) && ["id", "titulo", "estado", "estado_display", "origen_display", "fecha_inicio", "variante_etiqueta", "persona_entrevistada_etiqueta"].every((k) => text(v[k])) &&
    nullableText(v.relevador) && typeof v.es_formulario_menores === "boolean" && typeof v.sin_entrevista_por_franja === "boolean" &&
    Array.isArray(v.respuestas) && v.respuestas.every(paginaValid) && breadcrumbValid(v.breadcrumb) && messagesValid(v.messages);
}

function Aviso({ children }: { children: React.ReactNode }) {
  return (
    <div className="dc-seccion mb-3">
      <div className="dc-seccion__body">
        <p className="dc-dato__valor mb-0"><i className="fas fa-info-circle" />{" "}{children}{" "}</p>
      </div>
    </div>
  );
}

const sep = (child: React.ReactNode) => <>{" "}<span>·</span>{" "}{child}</>;

export function CasoContent({ data }: { data: CasoData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/datacalle.css" />
      <div className="dc-header">
        <div>
          <h1 className="dc-header__title">{data.titulo}</h1>
          <div className="dc-header__meta">
            <span className={`dc-chip dc-chip--${data.estado === "completa" ? "finalizado" : "planificado"}`}>{" "}{data.estado_display}{" "}</span>
            {sep(<span><i className="fas fa-mobile-alt" />{data.origen_display}</span>)}
            {data.relevador !== null && sep(<span>{data.relevador}</span>)}
            {data.fecha_inicio && <>{" "}<span>·</span><span>{data.fecha_inicio}</span></>}
            {data.variante_etiqueta && sep(<span><i className="fas fa-file-alt" />{data.variante_etiqueta}</span>)}
          </div>
        </div>
      </div>
      {data.es_formulario_menores && <>{" "}<Aviso>
        Formulario de menores (14 a 17 años): se relevan el código de identificación y los vínculos, el documento, el nivel educativo,
        dónde duerme esta noche y desde cuándo está en situación de calle. Las demás preguntas del papel general no se le preguntan: no son
        datos faltantes.
      </Aviso></>}
      {data.sin_entrevista_por_franja && <>{" "}<Aviso>
        Por su franja etaria no correspondía entrevistarla: fue observada y cuenta en el grupo
        {data.persona_entrevistada_etiqueta && ` (${data.persona_entrevistada_etiqueta})`}.
      </Aviso></>}
      {data.respuestas.length ? data.respuestas.map((pagina, i) => (
        <Fragment key={i}>{" "}
          <div className="dc-seccion mb-3">
            <div className="dc-seccion__header"><i className="fas fa-clipboard-list" /> {pagina.titulo}{" "}</div>{" "}
            <div className="dc-seccion__body">
              {pagina.items.map((item, j) => (
                <Fragment key={j}>{j > 0 && " "}
                  <div className="dc-dato">
                    <div className="dc-dato__label">
                      {" "}{item.etiqueta}{" "}
                      {item.historico && <><span className="dc-chip dc-chip--zona">pregunta retirada</span>{" "}</>}
                    </div>{" "}
                    <div className={`dc-dato__valor ${item.valor ? "" : "dc-dato__valor--vacio"}`}>{item.valor || "—"}</div>
                  </div>
                </Fragment>
              ))}
            </div>
          </div>
        </Fragment>
      )) : (
        <>{" "}<div className="dc-seccion mb-3">
          <div className="dc-seccion__body">
            <div className="dc-vacio">
              <i className="fas fa-clipboard" />{" "}<h3>El caso no trae respuestas</h3>{" "}<p>Llegó desde la app sin contenido en el instrumento.</p>
            </div>
          </div>
        </div></>
      )}
    </>
  );
}

function Caso({ id }: { id: string }) {
  const state = useCdfPage(`${API}${id}/`, casoValid);
  return renderCdf(state, (data) => ({ title: data.titulo, breadcrumb: <Breadcrumb items={data.breadcrumb} />, content: <CasoContent data={data} /> }));
}

const CASO = /^\/datacalle\/casos\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\/$/;

// Native URL of the case ficha (DC02.01); lower-case UUID as `<uuid:pk>`.
export const datacalleCasosRoute: RouteDefinition<{ id: string }> = {
  name: "datacalle-casos",
  match: (pathname) => {
    const m = CASO.exec(pathname);
    return m ? { id: m[1] } : null;
  },
  render: ({ id }) => <Caso id={id} />,
};
