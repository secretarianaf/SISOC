/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useState } from "react";
import { InsumosToastList } from "../InsumosToast";
import { Breadcrumb, Card, cdfListValid, DataTable, DetailHead, Dl, listNavigation, Pagination, SearchBar, type CdfListData } from "./cdfDataTable";
import { PreinscripcionPage } from "./cdfPreinscripcion";
import { ResponsableDetail, ResponsablesList } from "./cdfResponsables";
import { client, internal, messagesValid, nullableText, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import type { RouteDefinition } from "./types";

/**
 * CDF03.01: `beneficiarios/beneficiarios_list.html` (exact pages of 10,
 * filters, column preferences, CSV export) and `beneficiarios_detail.html`.
 * The CSV stays the native GET; before navigating, `exportar/disponible/`
 * tells whether it has rows, because the native "no rows" notice is a Django
 * message a React page never receives. No centre or territorial scope (D1).
 */
const API = "web/cdf/beneficiarios/";

export type BeneficiariosListData = CdfListData & {
  can_export: boolean;
  urls: { list: string; reset: string; add: string; export: string; export_available: string };
};

export function beneficiariosListValid(v: unknown): v is BeneficiariosListData {
  const x = v as Record<string, unknown>;
  return cdfListValid(v) && typeof x.can_export === "boolean" && record(x.urls) &&
    ["list", "reset", "add", "export", "export_available"].every((k) => internal((x.urls as Record<string, unknown>)[k]));
}

/** `export_helper.js`: current query plus the active local sort (`sort`/`direction`). */
function exportUrl(base: string) {
  const params = new URLSearchParams(window.location.search);
  const sorted = document.querySelector("th.sortable.sort-asc, th.sortable.sort-desc");
  const column = sorted?.getAttribute("data-column");
  if (sorted && column) {
    params.set("sort", column);
    params.set("direction", sorted.classList.contains("sort-asc") ? "asc" : "desc");
  }
  const url = new URL(base, window.location.href);
  params.forEach((value, key) => url.searchParams.set(key, value));
  return `${url.pathname}${url.search}`;
}

function ExportButton({ data, warn }: { data: BeneficiariosListData; warn: (m: CdfMessage) => void }) {
  const [busy, setBusy] = useState(false);
  async function exportar() {
    if (busy) return;
    setBusy(true);
    try {
      const { data: body } = await client.get(`${data.urls.export_available.replace(/^\/api\//, "")}${window.location.search}`);
      if (record(body) && body.exists === true) { listNavigation.assign(exportUrl(data.urls.export)); return; }
      if (record(body) && text(body.message) && body.message) warn({ message: body.message, level: "warning" });
    } catch {
      warn({ message: "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.", level: "warning" });
    } finally {
      setBusy(false);
    }
  }
  return (
    <button type="button" className="poncho-export btn-export-csv" data-url={data.urls.export} title="Descargar listado actual en CSV"
      onClick={() => void exportar()}>
      <i className="fas fa-file-excel" aria-hidden="true" />Exportar búsqueda
    </button>
  );
}

export function BeneficiariosListContent({ data }: { data: BeneficiariosListData }) {
  const [avisos, setAvisos] = useState<CdfMessage[]>([]);
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/cdf.css" />
      {avisos.length > 0 && <InsumosToastList messages={avisos} />}
      <SearchBar data={data} title="Buscar Beneficiario" reset={data.urls.reset} add={{ url: data.urls.add, text: "Crear un nuevo Preinscripto" }}
        exportButton={data.can_export ? <ExportButton data={data} warn={(m) => setAvisos((current) => [...current, m])} /> : null} />
      <div className="container mt-4 cdf-page">
        <h2>Listado de Preinscriptos</h2>
        <DataTable data={data} empty="No hay beneficiarios disponibles." />
        <Pagination data={data} />
      </div>
    </>
  );
}

function BeneficiariosList() {
  const state = useCdfPage(`${API}${window.location.search}`, beneficiariosListValid);
  return renderCdf(state, (data) => ({
    title: "Listado de Preinscriptos",
    heading: "Preinscriptos",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <BeneficiariosListContent data={data} />,
  }));
}

// --- Detail (`beneficiarios_detail.html`) -----------------------------------

export type BeneficiarioDetailData = {
  id: number; nombre_completo: string; dni: string; cuil: string; genero_display: string; fecha_nacimiento: string;
  correo_electronico: string; fecha_creado: string;
  responsable: { nombre_completo: string; dni: string; cuil: string; vinculo_display: string; celular: string; url: string };
  domicilio: { domicilio: string; calle: string; provincia: string; municipio: string; localidad: string; codigo_postal: string; barrio: string };
  academico: { estudia: boolean; nivel_actual: string | null; maximo_nivel: string; institucion: string };
  actividad_preferida: string[]; actividades_extracurriculares: boolean; actividades_detalle: string[];
  messages: CdfMessage[];
};

const texts = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));
const textList = (v: unknown) => Array.isArray(v) && v.every(text);

export function beneficiarioDetailValid(v: unknown): v is BeneficiarioDetailData {
  if (!record(v) || !record(v.responsable) || !record(v.academico)) return false;
  return texts(v, ["nombre_completo", "dni", "cuil", "genero_display", "fecha_nacimiento", "correo_electronico", "fecha_creado"]) &&
    texts(v.responsable, ["nombre_completo", "dni", "cuil", "vinculo_display", "celular"]) && internal(v.responsable.url) &&
    texts(v.domicilio, ["domicilio", "calle", "provincia", "municipio", "localidad", "codigo_postal", "barrio"]) &&
    typeof v.academico.estudia === "boolean" && nullableText(v.academico.nivel_actual) && text(v.academico.maximo_nivel) && text(v.academico.institucion) &&
    textList(v.actividad_preferida) && typeof v.actividades_extracurriculares === "boolean" && textList(v.actividades_detalle) && messagesValid(v.messages);
}

export function BeneficiarioDetailContent({ data }: { data: BeneficiarioDetailData }) {
  const { responsable: r, domicilio: d, academico: a } = data;
  return (
    <>
      <DetailHead />
      <div className="container mt-4 cdf-page">
        <div className="cdf-hero">
          <div className="cdf-hero-block">
            <h1>{data.nombre_completo}</h1>
            <p className="cdf-hero-sub">
              <span><i className="fas fa-id-card" />DNI {data.dni}</span>{" "}
              <span><i className="fas fa-fingerprint" />CUIL {data.cuil}</span>
            </p>
          </div>
        </div>
        <div className="row gx-4">
          <Card icon="fa-user" title="Información Personal">
            <Dl rows={[["CUIL", data.cuil], ["DNI", data.dni], ["Género", data.genero_display], ["Fecha de Nacimiento", data.fecha_nacimiento],
              ["Email", data.correo_electronico], ["Fecha Agregado", <span className="cdf-td-muted">{data.fecha_creado}</span>]]} />
          </Card>
          <Card icon="fa-user-friends" title="Responsable"
            tools={<div className="cdf-head-tools"><a href={r.url} className="cdf-btn"><i className="fas fa-eye" />Ver detalle</a></div>}>
            <Dl rows={[["Nombre", r.nombre_completo], ["DNI", r.dni], ["CUIL", r.cuil], ["Vínculo", r.vinculo_display], ["Celular", r.celular]]} />
          </Card>
        </div>
        <div className="row gx-4">
          <Card icon="fa-map-marker-alt" title="Domicilio">
            <Dl rows={[["Dirección", d.domicilio], ["Calle", d.calle], ["Provincia", d.provincia], ["Municipio", d.municipio],
              ["Localidad", d.localidad], ["Código Postal", d.codigo_postal], ["Barrio", d.barrio]]} />
          </Card>
          <Card icon="fa-graduation-cap" title="Información Académica">
            <Dl dt="col-sm-5" dd="col-sm-7" rows={[
              ["Estudia actualmente", a.estudia ? <span className="cdf-pill cdf-pill--success">Estudiando</span> : <span className="cdf-pill cdf-pill--muted">No estudiando</span>],
              ...(a.nivel_actual ? [["Nivel Actual", a.nivel_actual] as [string, string]] : []),
              ["Máximo Nivel", a.maximo_nivel], ["Institución", a.institucion]]} />
          </Card>
        </div>
        <Card icon="fa-person-running" title="Actividades e Intereses" half={false}>
          <div className="row">
            <div className="col-md-6">
              <div className="cdf-info-label mb-2">Actividades Preferidas</div>
              {data.actividad_preferida.length ? (
                <div className="d-flex flex-wrap" style={{ gap: "0.4rem" }}>
                  {data.actividad_preferida.map((x, i) => <span key={i} className="cdf-pill cdf-pill--teal">{x}</span>)}
                </div>
              ) : <p className="cdf-td-muted mb-0">No especificadas</p>}
            </div>
            <div className="col-md-6">
              <div className="cdf-info-label mb-2">Actividades Extracurriculares</div>
              {!data.actividades_extracurriculares ? <p className="cdf-td-muted mb-0">No participa</p>
                : data.actividades_detalle.length ? (
                  <div className="d-flex flex-wrap" style={{ gap: "0.4rem" }}>
                    {data.actividades_detalle.map((x, i) => <span key={i} className="cdf-pill cdf-pill--gold">{x}</span>)}
                  </div>
                ) : <p className="cdf-td-muted mb-0">Sí, pero sin detalles especificados</p>}
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}

function BeneficiarioDetail({ id }: { id: string }) {
  const state = useCdfPage(`${API}${id}/`, beneficiarioDetailValid);
  return renderCdf(state, (data) => ({
    title: "Detalle del Preinscripto",
    heading: "Detalle del Preinscripto",
    breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <BeneficiarioDetailContent data={data} />,
  }));
}

type Screen = { screen: "beneficiarios" | "responsables" | "nuevo"; id?: string };

// Native URLs of CDF03: beneficiaries and responsables (list and detail) and the preinscription.
export const cdfBeneficiariosRoute: RouteDefinition<Screen> = {
  name: "cdf-beneficiarios",
  match: (pathname) => {
    if (pathname === "/centrodefamilia/beneficiarios/nuevo/") return { screen: "nuevo" };
    const m = /^\/centrodefamilia\/beneficiarios\/(beneficiarios|responsables)\/(?:([1-9]\d*)\/)?$/.exec(pathname);
    if (!m) return null;
    return m[2] ? { screen: m[1] as Screen["screen"], id: m[2] } : { screen: m[1] as Screen["screen"] };
  },
  render: ({ screen, id }) => {
    if (screen === "nuevo") return <PreinscripcionPage />;
    if (screen === "responsables") return id ? <ResponsableDetail id={id} /> : <ResponsablesList />;
    return id ? <BeneficiarioDetail id={id} /> : <BeneficiariosList />;
  },
};
