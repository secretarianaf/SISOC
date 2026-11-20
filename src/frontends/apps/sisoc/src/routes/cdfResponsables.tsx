/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Breadcrumb, Card, cdfListValid, DataTable, DetailHead, Dl, Pagination, SearchBar, type CdfListData } from "./cdfDataTable";
import { integer, internal, messagesValid, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";

/**
 * CDF03.01: `beneficiarios/responsable_list.html` (NoCount pages of 10, no
 * add button, no export) and `responsable_detail.html` with the beneficiaries
 * in charge. No centre or territorial scope (D1).
 */
const API = "web/cdf/responsables/";

export type ResponsablesListData = CdfListData & { urls: { list: string; reset: string } };

export function responsablesListValid(v: unknown): v is ResponsablesListData {
  const x = v as Record<string, unknown>;
  return cdfListValid(v) && record(x.urls) && internal(x.urls.list) && internal(x.urls.reset);
}

export function ResponsablesListContent({ data }: { data: ResponsablesListData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/cdf.css" />
      <SearchBar data={data} title="Buscar Responsable" reset={data.urls.reset} />
      <div className="container mt-4 cdf-page">
        <h2>Listado de Responsables</h2>
        <DataTable data={data} empty="No hay responsables disponibles." />
        <Pagination data={data} />
      </div>
    </>
  );
}

export function ResponsablesList() {
  const state = useCdfPage(`${API}${window.location.search}`, responsablesListValid);
  return renderCdf(state, (data) => ({
    title: "Listado de responsables",
    heading: "Responsables",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <ResponsablesListContent data={data} />,
  }));
}

// --- Detail (`responsable_detail.html`) -------------------------------------

type Vinculo = {
  beneficiario_id: number; cuil: string; apellido_nombre: string; dni: string; genero_display: string; fecha_nacimiento: string;
  vinculo_display: string; fecha_creado: string; url: string;
};
export type ResponsableDetailData = {
  id: number; nombre_completo: string; dni: string; cuil: string; genero_display: string; fecha_nacimiento: string;
  celular: string; telefono_fijo: string; correo_electronico: string;
  domicilio: { calle: string; piso_vivienda: string; departamento_vivienda: string; barrio: string; provincia: string; municipio: string;
    localidad: string; codigo_postal: string; monoblock: string };
  vinculos: Vinculo[]; messages: CdfMessage[];
};

const texts = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));

export function responsableDetailValid(v: unknown): v is ResponsableDetailData {
  return record(v) && integer(v.id) &&
    texts(v, ["nombre_completo", "dni", "cuil", "genero_display", "fecha_nacimiento", "celular", "telefono_fijo", "correo_electronico"]) &&
    texts(v.domicilio, ["calle", "piso_vivienda", "departamento_vivienda", "barrio", "provincia", "municipio", "localidad", "codigo_postal", "monoblock"]) &&
    Array.isArray(v.vinculos) && v.vinculos.every((x) => record(x) && integer(x.beneficiario_id) && internal(x.url) &&
      texts(x, ["cuil", "apellido_nombre", "dni", "genero_display", "fecha_nacimiento", "vinculo_display", "fecha_creado"])) &&
    messagesValid(v.messages);
}

export function ResponsableDetailContent({ data }: { data: ResponsableDetailData }) {
  const d = data.domicilio;
  const total = data.vinculos.length;
  return (
    <>
      <DetailHead />
      <div className="container mt-4 cdf-page">
        <div className="cdf-hero">
          <div className="cdf-hero-block">
            <h1>{data.nombre_completo}</h1>
            <p className="cdf-hero-sub">
              <span><i className="fas fa-id-card" />DNI {data.dni}</span>{" "}
              <span><i className="fas fa-fingerprint" />CUIL {data.cuil}</span>{" "}
              <span><i className="fas fa-users" />{total} preinscripto(s) a cargo</span>
            </p>
          </div>
        </div>
        <div className="row gx-4">
          <Card icon="fa-user" title="Información Personal">
            <Dl rows={[["CUIL", data.cuil], ["DNI", data.dni], ["Género", data.genero_display], ["Fecha de Nacimiento", data.fecha_nacimiento]]} />
          </Card>
          <Card icon="fa-phone" title="Información de Contacto">
            <Dl rows={[["Celular", data.celular], ["Teléfono Fijo", data.telefono_fijo], ["Email", data.correo_electronico]]} />
          </Card>
        </div>
        <Card icon="fa-map-marker-alt" title="Domicilio" half={false}>
          <div className="row">
            <div className="col-md-6">
              <Dl rows={[["Calle", d.calle], ["Piso", d.piso_vivienda], ["Departamento", d.departamento_vivienda], ["Barrio", d.barrio]]} />
            </div>
            <div className="col-md-6">
              <Dl rows={[["Provincia", d.provincia], ["Municipio", d.municipio], ["Localidad", d.localidad], ["Código Postal", d.codigo_postal],
                ["Monoblock", d.monoblock]]} />
            </div>
          </div>
        </Card>
        <div className="cdf-card">
          <div className="cdf-card-head">
            <i className="fas fa-users" />
            <span>Preinscriptos a Cargo</span>{" "}
            <span className="cdf-pill cdf-pill--gold">{total}</span>
          </div>
          <div className="cdf-card-body cdf-card-body--flush">
            {total ? (
              <div className="cdf-tbl-scroll">
                <table className="cdf-table">
                  <thead>
                    <tr>
                      {["CUIL", "Apellido y Nombre", "DNI", "Género", "Fecha de Nacimiento", "Vínculo Parental", "Fecha Agregado"].map((h) => <th key={h}>{h}</th>)}
                      <th className="text-end">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.vinculos.map((v, i) => (
                      <tr key={`${v.beneficiario_id}-${i}`}>
                        <td>{v.cuil}</td>
                        <td>{v.apellido_nombre}</td>
                        <td>{v.dni}</td>
                        <td>{v.genero_display}</td>
                        <td>{v.fecha_nacimiento}</td>
                        <td><span className="cdf-pill cdf-pill--teal">{v.vinculo_display}</span></td>
                        <td><span className="cdf-td-muted">{v.fecha_creado}</span></td>
                        <td className="text-end"><a href={v.url} className="cdf-btn"><i className="fas fa-eye" />Ver</a></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="cdf-empty">
                <i className="fas fa-users" />
                <p className="cdf-empty-t">Sin preinscriptos asignados</p>
                <p className="cdf-empty-s">Este responsable no tiene preinscriptos a cargo.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export function ResponsableDetail({ id }: { id: string }) {
  const state = useCdfPage(`${API}${id}/`, responsableDetailValid);
  return renderCdf(state, (data) => ({
    title: "Detalle del Responsable",
    heading: "Detalle del Responsable",
    breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <ResponsableDetailContent data={data} />,
  }));
}
