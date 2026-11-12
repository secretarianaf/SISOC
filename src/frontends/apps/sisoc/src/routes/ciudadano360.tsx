/* eslint-disable react-refresh/only-export-components -- unit surface is this route module; its validator is exported for the tests. */
import InsumosAccessError from "../InsumosAccessError";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import {
  AportesProvider, CdfCard, CdfMonto, CeliaquiaCard, ColaboracionesCard, ComedoresCard, PwaBadges, PwaFilas, VatCard,
  useAporte, useAportesPrerequisite, type Aporte,
} from "./ciudadano360Aportes";
import { CIUDADANO_360_CSS } from "./ciudadano360Css";
import type { RouteDefinition } from "./types";

/**
 * C05.01 piece that C04 needs: the header of `ciudadanos/ciudadano_detail.html` and the places of the cards the verticals add
 * (`ciudadano360Aportes`). Data comes from `GET /api/web/ciudadanos/<pk>/`; the rest of the ficha (tabs, familia, programas,
 * interacciones, actions) stays native until C05.01 migrates it, so this route is only reachable through the local preview entry.
 */
export type FichaData = {
  id: number; nombre: string; apellido: string; tipo_documento_texto: string; numero_documento: string | null;
  pais_emisor: string | null; identificador_interno: string | null; aportes: Aporte[];
};

const nullableText = (v: unknown) => v === null || text(v);

export function fichaValid(v: unknown): v is FichaData {
  return record(v) && typeof v.id === "number" && text(v.nombre) && text(v.apellido) && text(v.tipo_documento_texto) &&
    nullableText(v.numero_documento) && nullableText(v.pais_emisor) && nullableText(v.identificador_interno) &&
    Array.isArray(v.aportes) && v.aportes.every((a) => record(a) && text(a.aporte) && Array.isArray(a.secciones) && a.secciones.every(text) && internal(a.url));
}

/** Renders `children` only when the server listed the aporte (an unresolved backend is not listed: nothing is drawn). */
function Listed({ aporte, children }: { aporte: string; children: (state: ReturnType<typeof useAporte>) => React.ReactNode }) {
  const state = useAporte(aporte);
  return <>{children(state)}</>;
}

function Ficha({ data }: { data: FichaData }) {
  const prerequisite = useAportesPrerequisite();
  const listed = (name: string) => data.aportes.some((a) => a.aporte === name);
  if (prerequisite) return <InsumosAccessError prerequisite={prerequisite} />;
  return (
    <div className="container-fluid p-0">
      <div className="legajo-header">
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h1>
              {data.nombre} {data.apellido}
              {listed("pwa") && <Listed aporte="pwa">{(s) => <PwaBadges state={s} />}</Listed>}
            </h1>
            <p className="subtitle mb-0">
              {data.tipo_documento_texto} {data.numero_documento || "Sin documento"}
              {data.pais_emisor && <span className="ms-1">({data.pais_emisor})</span>}
            </p>
            {data.identificador_interno && (
              <p className="mb-0" style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                <code style={{ color: "rgba(255,255,255,0.75)" }}>{data.identificador_interno}</code>
              </p>
            )}
          </div>
        </div>
      </div>
      {listed("pwa") && <div className="row px-4"><div className="col-12"><div className="datos-card"><Listed aporte="pwa">{(s) => <PwaFilas state={s} />}</Listed></div></div></div>}
      {listed("centrodefamilia") && (
        <div className="row px-4"><div className="col-12">
          <div className="programa-card centro-familia">
            <div className="icono"><i className="fas fa-home" /></div>
            <div className="info"><div className="nombre">Centro de Familia</div>
              <div className="monto"><Listed aporte="centrodefamilia">{(s) => <CdfMonto state={s} />}</Listed></div></div>
          </div>
        </div></div>
      )}
      {listed("comedores") && <div className="row px-4"><div className="col-12"><Listed aporte="comedores">{(s) => <ComedoresCard state={s} />}</Listed></div></div>}
      {listed("celiaquia") && <div className="row px-4"><div className="col-12"><Listed aporte="celiaquia">{(s) => <CeliaquiaCard state={s} />}</Listed></div></div>}
      {listed("centrodefamilia") && <div className="row px-4"><div className="col-12"><Listed aporte="centrodefamilia">{(s) => <CdfCard state={s} />}</Listed></div></div>}
      {listed("vat") && <div className="row px-4"><div className="col-12"><Listed aporte="vat">{(s) => <VatCard state={s} />}</Listed></div></div>}
      {listed("comedores") && <Listed aporte="comedores">{(s) => <ColaboracionesCard state={s} />}</Listed>}
    </div>
  );
}

function FichaPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`web/ciudadanos/${pk}/`, fichaValid);
  return renderMain(state, "Cargando ciudadano…", (data) => ({
    // The native ficha defines no title block ("SISOC - ").
    title: "",
    heading: "",
    breadcrumb: null,
    content: <><style>{CIUDADANO_360_CSS}</style><AportesProvider aportes={data.aportes}><Ficha data={data} /></AportesProvider></>,
  }));
}

const DETAIL = /^\/ciudadanos\/ver\/([0-9]+)$/;

export const ciudadano360Route: RouteDefinition<{ pk: string }> = {
  name: "ciudadano-360",
  match(pathname) {
    const found = DETAIL.exec(pathname);
    return found ? { pk: found[1] } : null;
  },
  render({ pk }) {
    return <FichaPage pk={pk} />;
  },
};
