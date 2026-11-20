/* eslint-disable react-refresh/only-export-components -- the module exports the page validator next to the page component. */
import type { ReactNode } from "react";
import { ConveniosSection, conveniosSectionValid } from "./organizacionConvenio";
import { DocumentosSection, documentosSectionValid } from "./organizacionDocumentos";
import { AvalesSection, avalesSectionValid, FirmantesSection, firmantesSectionValid } from "./organizacionFirmantes";
import { ComedoresSection, comedoresSectionValid, ProyectosSection, proyectosSectionValid, RegionSection, regionSectionValid } from "./organizacionLegajoDatos";
import { RendicionesFiltro, rendicionesFiltroValid, RendicionesTable, rendicionesSectionValid } from "./organizacionRendiciones";
import type { Message } from "./organizacionesForm";
import { internal, record, text } from "./MainFrame";

/**
 * O05.01 `organizacion_detail.html` (legajo) composed in React. The API follows the
 * native template's control flow over the view's context and sends the page as data:
 * header, program selector, "Datos de la Organización", notices, program strip, tabs and
 * the ordered blocks (each legajo section carries its own JSON). Markup, classes, texts and
 * order are the template's; its `<style>` arrives as `css`.
 */
export type Block = { kind: string } & Record<string, unknown>;
type Header = { name: string; cuit: string; tipo: string; subtipo: string | null; history_url: string | null; edit_url: string | null; delete_url: string | null };
type SwitchItem = { id: number; name: string; color: string; active: boolean; url: string };
type Selector = { kind: "switch"; items: SwitchItem[] } | { kind: "chip"; name: string; color: string } | { kind: "none" };
type Datos = {
  edit_url: string | null; name: string; cuit: string; tipo: string; subtipo: string; phone: string; email: string; programs: string[]; comedores_count: number;
  provincia: string; municipio: string; localidad: string; partido: string; domicilio: string; expiry: { text: string; state: "vigente" | "vencido" | null }; created: string;
};
export type LegajoPage = { title: string; css: string; header: Header; selector: Selector; datos: Datos; blocks: Block[] };

const optionalPath = (v: unknown) => v === null || internal(v);
const headerValid = (v: unknown): v is Header =>
  record(v) && text(v.name) && text(v.cuit) && text(v.tipo) && (v.subtipo === null || text(v.subtipo)) &&
  optionalPath(v.history_url) && optionalPath(v.edit_url) && optionalPath(v.delete_url);
const selectorValid = (v: unknown): v is Selector =>
  record(v) && (v.kind === "none" || (v.kind === "chip" && text(v.name) && text(v.color)) ||
    (v.kind === "switch" && Array.isArray(v.items) && v.items.every((i) => record(i) && typeof i.id === "number" && text(i.name) && text(i.color) && typeof i.active === "boolean" && text(i.url))));
const datosValid = (v: unknown): v is Datos =>
  record(v) && optionalPath(v.edit_url) && ["name", "cuit", "tipo", "subtipo", "phone", "email", "provincia", "municipio", "localidad", "partido", "domicilio", "created"].every((k) => text(v[k])) &&
  Array.isArray(v.programs) && v.programs.every(text) && typeof v.comedores_count === "number" &&
  record(v.expiry) && text(v.expiry.text) && (v.expiry.state === null || v.expiry.state === "vigente" || v.expiry.state === "vencido");

const LEVELS = ["success", "error", "warning", "info"];

export function legajoValid(v: unknown): v is LegajoPage & { messages: Message[] } {
  return record(v) && text(v.title) && typeof v.css === "string" && headerValid(v.header) && selectorValid(v.selector) && datosValid(v.datos) &&
    Array.isArray(v.blocks) && v.blocks.every((b) => record(b) && text(b.kind)) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

function Selector({ selector }: { selector: Selector }) {
  if (selector.kind === "switch") {
    return (
      <nav className="programa-switch" aria-label="Programa del legajo">
        {selector.items.map((item) => (
          <a key={item.id} href={item.url} className={item.active ? `activo color-${item.color}` : ""} aria-current={item.active ? "page" : undefined}>{item.name}</a>
        ))}
      </nav>
    );
  }
  if (selector.kind === "chip") return <span className={`chip-legajo color-${selector.color} text-dark`}>{selector.name}</span>;
  return <span className="chip-legajo">Sin programas</span>;
}

function Header({ header, selector }: { header: Header; selector: Selector }) {
  return (
    <div className="legajo-header mt-4">
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-3">
        <div>
          <h1>{header.name}</h1>
          <p className="subtitle mb-0">CUIT: {header.cuit} | {header.tipo}{header.subtipo ? ` - ${header.subtipo}` : ""}</p>
        </div>
        <div className="btn-group">
          {header.history_url && <a href={header.history_url} className="btn btn-outline-light">Historial</a>}
          {header.edit_url && <a href={header.edit_url} className="btn btn-outline-light">Editar</a>}
          {header.delete_url && <a href={header.delete_url} className="btn btn-danger">Eliminar</a>}
        </div>
      </div>
      <div className="d-flex flex-wrap align-items-center gap-3 mt-3 pt-3 border-top border-secondary">
        <span className="eyebrow-legajo">Programa</span>
        <Selector selector={selector} />
      </div>
    </div>
  );
}

const Row = ({ label, children }: { label: string; children: ReactNode }) => <div className="info-row"><strong>{label}</strong><span className="value">{children}</span></div>;

function DatosCard({ datos }: { datos: Datos }) {
  return (
    <div className="datos-card" style={{ position: "relative" }}>
      {datos.edit_url && <a href={datos.edit_url} className="btn-edit-card" aria-label="Editar datos de la organización"><i className="fas fa-pen" /></a>}
      <h5>Datos de la Organización <span className="chip-legajo ms-2">Común a todos los programas</span></h5>
      <div className="datos-card-content">
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
          <div className="icon-placeholder"><i className="fas fa-building" /></div>
        </div>
        <div className="info-column">
          <Row label="Nombre:">{datos.name}</Row>
          <Row label="CUIT:">{datos.cuit}</Row>
          <Row label="Tipo de Entidad:">{datos.tipo}</Row>
          <Row label="Subtipo de Entidad:">{datos.subtipo}</Row>
          <Row label="Teléfono:">{datos.phone}</Row>
          <Row label="Email:">{datos.email}</Row>
          <div className="info-row">
            <strong>Programas:</strong>
            <span className="value text-end">{datos.programs.length > 0 ? datos.programs.join(" · ") : "Sin programas"}</span>
          </div>
          <Row label="Comedores asociados:">{datos.comedores_count} en total</Row>
        </div>
        <div className="info-column">
          <Row label="Provincia:">{datos.provincia}</Row>
          <Row label="Municipio:">{datos.municipio}</Row>
          <Row label="Localidad:">{datos.localidad}</Row>
          <Row label="Partido:">{datos.partido}</Row>
          <Row label="Domicilio:">{datos.domicilio}</Row>
          <Row label="Fecha de Vencimiento:">
            {datos.expiry.text}
            {datos.expiry.state === "vigente" && <>{" "}<span className="badge-status vigente"><i className="fas fa-check-circle" /> Vigente</span></>}
            {datos.expiry.state === "vencido" && <>{" "}<span className="badge-status vencido"><i className="fas fa-exclamation-circle" /> Vencido</span></>}
          </Row>
          <Row label="Fecha de Creación:">{datos.created}</Row>
        </div>
      </div>
    </div>
  );
}

/** A legajo section the API built with a partial's builder; null when the payload does not match. */
function sectionView(section: Block): ReactNode {
  if (section.kind === "convenios" && conveniosSectionValid(section)) return <ConveniosSection section={section} />;
  if (section.kind === "documentos" && documentosSectionValid(section)) return <DocumentosSection section={section} />;
  if (section.kind === "firmantes" && firmantesSectionValid(section)) return <FirmantesSection section={section} />;
  if (section.kind === "avales" && avalesSectionValid(section)) return <AvalesSection section={section} />;
  if (section.kind === "rendiciones" && rendicionesSectionValid(section)) return <RendicionesTable section={section} />;
  if (section.kind === "rendiciones_filtro" && rendicionesFiltroValid(section)) return <RendicionesFiltro section={section} />;
  if (section.kind === "region" && regionSectionValid(section)) return <RegionSection section={section} />;
  if (section.kind === "proyectos" && proyectosSectionValid(section)) return <ProyectosSection section={section} />;
  if (section.kind === "comedores" && comedoresSectionValid(section)) return <ComedoresSection section={section} />;
  return null;
}

const asBlock = (v: unknown): Block | null => (record(v) && text(v.kind) ? (v as Block) : null);
const str = (v: unknown) => (typeof v === "string" ? v : "");
const num = (v: unknown) => (typeof v === "number" ? v : 0);
const path = (v: unknown) => (typeof v === "string" && internal(v) ? v : null);

const EMPTY_RENDICIONES = <p className="mb-0 texto-vacio">No hay rendiciones presentadas para la selección actual.</p>;

function RendicionesCard({ block, className, title }: { block: Block; className: string; title: string }) {
  const table = asBlock(block.table);
  return (
    <div className={className}>
      <div className="d-flex justify-content-between align-items-end flex-wrap gap-3 mb-3">
        <h5 className="mb-0">{title} <span className="badge badge-gold ms-2">{num(block.total)} Total</span></h5>
        {sectionView(asBlock(block.filter) ?? { kind: "" })}
      </div>
      {table ? sectionView(table) : EMPTY_RENDICIONES}
    </div>
  );
}

function PageBlock({ block }: { block: Block }): ReactNode {
  switch (block.kind) {
    case "sin_programas": {
      const edit = path(block.edit_url);
      return (
        <div className="bloque-vacio">
          <strong>Sin programas asignados</strong>
          <span className="nota-legajo">Para ver firmantes, comedores, proyectos y rendiciones por programa, cargá los programas de la organización.</span>
          {edit && <a href={edit} className="btn btn-success btn-sm">Cargar programas</a>}
        </div>
      );
    }
    case "aviso_abordaje":
      return <div className="aviso-legajo">La organización tiene datos de Abordaje Comunitario pero no tiene cargada Línea Secos ni Línea Tradicional.</div>;
    case "rendiciones_generales":
      return <RendicionesCard block={block} className="tabla-legajo card-programa card-otro" title="Rendiciones Presentadas" />;
    case "franja":
      return (
        <div className={`franja-programa color-${str(block.color)}`}>
          <small>{str(block.label)}</small> <b>{str(block.name)}</b> <span className="ms-auto">{str(block.summary)}</span>
        </div>
      );
    case "tabs": {
      const items = Array.isArray(block.items) ? block.items.filter(record) : [];
      return (
        <nav className="seccion-tabs" aria-label="Secciones del programa">
          {items.map((item) => (
            <a key={str(item.url)} href={str(item.url)} className={item.active ? `activo color-${str(block.color)}` : ""} aria-current={item.active ? "page" : undefined}>{str(item.label)}</a>
          ))}
        </nav>
      );
    }
    case "rendiciones_programa":
      return <RendicionesCard block={block} className={`tabla-legajo card-programa card-${str(block.color)}`} title={str(block.title)} />;
    case "rendiciones_otras": {
      const table = asBlock(block.table);
      return (
        <div className="tabla-legajo card-sin">
          <h5 className="mb-1">Rendiciones de otras líneas <span className="badge badge-gold ms-2">{num(block.total)} Total</span></h5>
          <p className="nota-legajo mb-3">Su línea no está entre los programas de la organización. Se muestran acá para que no queden ocultas.</p>
          {table && sectionView(table)}
        </div>
      );
    }
    case "aviso_sin_linea": {
      const edit = path(block.edit_url);
      const codes = Array.isArray(block.codes) ? block.codes.filter(text) : [];
      return (
        <div className="aviso-legajo d-flex flex-wrap align-items-center gap-2">
          <span className="flex-grow-1">
            <strong>{num(block.count)} proyecto{str(block.plural)} sin línea</strong>{" "}
            no aparece{str(block.plural_n)} en las líneas de la organización: no tiene{str(block.plural_n)} línea o su línea no está cargada en la organización. Asignale{str(block.plural_s)} una:{" "}
            {codes.map((code, i) => <span key={code}>{i > 0 && " "}<span className="badge rounded-pill bg-primary px-2 py-1">{code}</span></span>)}
          </span>
          {edit && <a href={edit} className="btn btn-success btn-sm">Asignar línea</a>}
        </div>
      );
    }
    case "sin_programa": {
      const sections = Array.isArray(block.sections) ? block.sections.map(asBlock).filter((s): s is Block => s !== null) : [];
      return (
        <div className="tabla-legajo card-sin">
          <h5 className="mb-1">Sin programa asignado <span className="chip-legajo ms-2">Visible en cualquier programa</span></h5>
          <p className="nota-legajo mb-3">Registros de la organización que no tienen programa, o cuyo programa no está cargado en la organización. Editalos para asignarles uno.</p>
          {sections.map((section, i) => <PageSection key={`${section.kind}-${i}`} section={section} />)}
        </div>
      );
    }
    default:
      return <PageSection section={block} />;
  }
}

const PageSection = ({ section }: { section: Block }) => <>{sectionView(section)}</>;

export function LegajoContent({ page }: { page: LegajoPage }) {
  return (
    <>
      <style>{page.css}</style>
      <div className="container-fluid p-0">
        <Header header={page.header} selector={page.selector} />
        <div className="px-4">
          <DatosCard datos={page.datos} />
          {page.blocks.map((block, i) => <PageBlock key={`${block.kind}-${i}`} block={block} />)}
        </div>
      </div>
    </>
  );
}
