/* eslint-disable react-refresh/only-export-components -- the detail screen exports its validator for the unit tests. */
import type { ReactNode } from "react";
import { InsumosToastList } from "../InsumosToast";
import { safeInternalPath } from "../webAccess";
import { API, integer, messagesValid, record, renderDuplas, text, useDuplasResource, type Message } from "./duplasShared";

/** `dupla_detail.html`: actions, then the "Información de la Dupla" card. */
export type DuplaDetailData = {
  id: number; nombre: string; estado: string; tecnicos: string; abogado: string; coordinador: string | null; fecha: string;
  urls: { list: string; edit: string; delete: string };
  messages: Message[];
};

export function detailValid(v: unknown): v is DuplaDetailData {
  return record(v) && integer(v.id) && ["nombre", "estado", "tecnicos", "abogado", "fecha"].every((k) => text(v[k])) &&
    (v.coordinador === null || text(v.coordinador)) && record(v.urls) &&
    ["list", "edit", "delete"].every((k) => safeInternalPath((v.urls as Record<string, unknown>)[k]) !== null) && messagesValid(v.messages);
}

function Item({ term, children }: { term: string; children: ReactNode }) {
  return <><dt className="col-sm-4">{term}</dt>{" "}<dd className="col-sm-8">{children}</dd>{" "}</>;
}

export function DuplaDetailContent({ data }: { data: DuplaDetailData }) {
  return (
    <>
      {/* `includes/base.html` loads hitos.css (card header titles); the React index does not. */}
      <link rel="stylesheet" href="/static/custom/css/hitos.css" />
      <link rel="stylesheet" href="/static/custom/css/cardsDetail.css" />
      <InsumosToastList messages={data.messages} />
      <div className="row justify-content-between d-print-none mx-1 mb-3">
        <div className="col-auto">
          <a href={data.urls.edit} className="btn btn-primary mr-1">Editar</a>
          {" "}<a href={data.urls.delete} className="btn btn-danger">Eliminar</a>
        </div>
      </div>
      <div className="card card-outline card-primary">
        <div className="card-header">
          <h3 className="card-title">Información de la Dupla</h3>
        </div>
        <div className="card-body">
          <div className="row">
            <div className="col-md-6">
              <dl className="row">
                <Item term="Nombre:">{data.nombre}</Item>
                <Item term="Estado:">{data.estado}</Item>
                <Item term="Técnico/s:">{data.tecnicos}</Item>
              </dl>
            </div>
            <div className="col-md-6">
              <dl className="row">
                <Item term="Abogado:">{data.abogado}</Item>
                <Item term="Coordinador:">{data.coordinador ?? <span className="badge badge-warning">Sin asignar</span>}</Item>
                <Item term="Fecha de creación:">{data.fecha}</Item>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default function DuplaDetail({ id }: { id: string }) {
  const state = useDuplasResource(`${API}${id}/`, detailValid);
  return renderDuplas(state, (data) => ({
    title: `Dupla: ${data.nombre}`,
    heading: data.nombre,
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <div className="breadcrumb-item"><a href={data.urls.list}>Duplas</a></div>
        {" "}<div className="breadcrumb-item active">{data.nombre}</div>
      </ol>
    ),
    content: <DuplaDetailContent data={data} />,
  }));
}
