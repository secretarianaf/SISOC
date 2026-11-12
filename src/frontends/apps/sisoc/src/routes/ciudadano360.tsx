/* eslint-disable react-refresh/only-export-components -- unit surface is this route module; its validator is exported for the tests. */
import { useState } from "react";
import InsumosAccessError from "../InsumosAccessError";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import {
  AportesProvider, CdfCard, CdfMonto, CeliaquiaCard, ColaboracionesCard, ComedoresCard, PwaBadges, PwaFilas, VatCard,
  useAporte, useAportesPrerequisite, type Aporte,
} from "./ciudadano360Aportes";
import {
  DatosPersonales, GrupoFamiliar, HeaderActions, HistorialCard, IdentityNotice, InteraccionesTabla, ObservacionesTabla, PaneEnDesarrollo,
  ProgramasSection, TabNav, TabPane, fichaExtraValid, type FichaExtra, type TabId,
} from "./ciudadano360Ficha";
import { CIUDADANO_360_CSS } from "./ciudadano360Css";
import { NativeToasts } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * C05.01: `ciudadanos/ciudadano_detail.html`. Data comes from `GET /api/web/ciudadanos/<pk>/` (the ficha of
 * `ciudadanos.web_ficha`) and the cards the verticals add (`ciudadano360Aportes`); the sections of the page itself live in
 * `ciudadano360Ficha`. Only reachable through the local preview entry until the native URL is switched.
 */
export type FichaData = FichaExtra & {
  id: number; nombre: string; apellido: string; tipo_documento_texto: string; numero_documento: string | null;
  pais_emisor: string | null; identificador_interno: string | null; aportes: Aporte[];
};

const nullableText = (v: unknown) => v === null || text(v);

export function fichaValid(v: unknown): v is FichaData {
  return record(v) && typeof v.id === "number" && text(v.nombre) && text(v.apellido) && text(v.tipo_documento_texto) &&
    nullableText(v.numero_documento) && nullableText(v.pais_emisor) && nullableText(v.identificador_interno) &&
    Array.isArray(v.aportes) && v.aportes.every((a) => record(a) && text(a.aporte) && Array.isArray(a.secciones) && a.secciones.every(text) && internal(a.url)) &&
    fichaExtraValid(v);
}

/** Renders `children` only when the server listed the aporte (an unresolved backend is not listed: nothing is drawn). */
function Listed({ aporte, children }: { aporte: string; children: (state: ReturnType<typeof useAporte>) => React.ReactNode }) {
  const state = useAporte(aporte);
  return <>{children(state)}</>;
}

function Ficha({ data }: { data: FichaData }) {
  const prerequisite = useAportesPrerequisite();
  const [tab, setTab] = useState<TabId>("datos-personales");
  const listed = (name: string) => data.aportes.some((a) => a.aporte === name);
  if (prerequisite) return <InsumosAccessError prerequisite={prerequisite} />;
  const cards = (aporte: string, card: (s: ReturnType<typeof useAporte>) => React.ReactNode) => listed(aporte) && <Listed aporte={aporte}>{card}</Listed>;
  const tablas = <><InteraccionesTabla interacciones={data.interacciones} /><ObservacionesTabla observaciones={data.observaciones} /></>;
  return (
    <div className="container-fluid p-0">
      <NativeToasts messages={data.messages} />
      <div className="legajo-header">
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h1>
              {data.nombre} {data.apellido}
              {cards("pwa", (s) => <PwaBadges state={s} />)}
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
          <HeaderActions acciones={data.acciones} />
        </div>
      </div>
      <IdentityNotice identidad={data.identidad} />
      <TabNav active={tab} onSelect={setTab} />
      <div className="tab-content px-4">
        <TabPane id="datos-personales" active={tab}>
          <div className="row"><div className="col-12">
            <DatosPersonales extra={data} tail={cards("pwa", (s) => <PwaFilas state={s} />)} />
          </div></div>
          <div className="row">
            <div className="col-md-8">
              <GrupoFamiliar familia={data.familia} nuevaUrl={data.acciones.familiar_nuevo_url} />
              <HistorialCard historial={data.historial} />
            </div>
            <div className="col-md-4">
              <ProgramasSection centroFamiliaMonto={cards("centrodefamilia", (s) => <CdfMonto state={s} />) || "$0.00"} />
            </div>
          </div>
          <div className="row mt-3"><div className="col-12"><InteraccionesTabla interacciones={data.interacciones} conTilde /></div></div>
          <ObservacionesTabla observaciones={data.observaciones} />
        </TabPane>
        <TabPane id="socioeconomico" active={tab}><PaneEnDesarrollo titulo="Socioeconómico" extra={data} /></TabPane>
        <TabPane id="pas" active={tab}><PaneEnDesarrollo titulo="PAS" extra={data} /></TabPane>
        <TabPane id="prestacion-alimentar" active={tab}><PaneEnDesarrollo titulo="Prestación Alimentar" extra={data} /></TabPane>
        <TabPane id="comedor" active={tab}><div className="row"><div className="col-12">{cards("comedores", (s) => <ComedoresCard state={s} />)}{tablas}</div></div></TabPane>
        <TabPane id="cdf" active={tab}><div className="row"><div className="col-12">{cards("centrodefamilia", (s) => <CdfCard state={s} />)}{tablas}</div></div></TabPane>
        <TabPane id="celiaquia" active={tab}><div className="row"><div className="col-12">{cards("celiaquia", (s) => <CeliaquiaCard state={s} />)}{tablas}</div></div></TabPane>
        <TabPane id="fch" active={tab}><PaneEnDesarrollo titulo="FCH" extra={data} /></TabPane>
        <TabPane id="situacion-calle" active={tab}><PaneEnDesarrollo titulo="Situación de Calle" extra={data} /></TabPane>
        <TabPane id="aduana" active={tab}><PaneEnDesarrollo titulo="Aduana" extra={data} /></TabPane>
        <TabPane id="vat" active={tab}><div className="row"><div className="col-12">{cards("vat", (s) => <VatCard state={s} />)}</div></div></TabPane>
      </div>
      {cards("comedores", (s) => <ColaboracionesCard state={s} />)}
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
