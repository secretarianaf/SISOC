/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen and validator live here with the route. */
import { useState, type KeyboardEvent } from "react";
import { safeInternalPath } from "../webAccess";
import { internal, messagesValid, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import type { RouteDefinition } from "./types";

/**
 * CDI04.01 beneficiary detail (`centrodeinfancia/destinatario_detail.html`):
 * collapsible section cards of label/value fields, badge lists and the
 * NOMIVAC vaccine table. Every value comes rendered by the backend with the
 * native template expressions; this page only draws the sections.
 */
type Tone = "warning" | "info" | "danger";
type Block =
  | { kind: "fields"; items: { label: string; value: string }[]; spaced: boolean }
  | { kind: "badges"; label: string; tone: Tone; items: string[]; spaced: boolean }
  | { kind: "rule" }
  | { kind: "caption"; text: string }
  | { kind: "vaccines"; rows: { vaccine: string; doses: string; date: string }[] | null }
  | { kind: "text"; text: string };
type Section = { key: string; icon: string; title: string; subtitle: string | null; blocks: Block[] };
export type NominaData = {
  id: number;
  label: string;
  centro: { id: number; nombre: string; url: string };
  editar_url: string | null;
  sections: Section[];
  messages: CdiMessage[];
};

const TONES: Record<Tone, { background: string; color: string; border: string }> = {
  warning: { background: "rgba(243,156,18,0.15)", color: "#f39c12", border: "1px solid rgba(243,156,18,0.3)" },
  info: { background: "rgba(52,152,219,0.15)", color: "#74b9e7", border: "1px solid rgba(52,152,219,0.3)" },
  danger: { background: "rgba(231,76,60,0.15)", color: "#e74c3c", border: "1px solid rgba(231,76,60,0.3)" },
};

function blockValid(b: unknown): boolean {
  if (!record(b)) return false;
  switch (b.kind) {
    case "fields": return typeof b.spaced === "boolean" && Array.isArray(b.items) && b.items.every((i) => record(i) && text(i.label) && text(i.value));
    case "badges": return typeof b.spaced === "boolean" && text(b.label) && (b.tone === "warning" || b.tone === "info" || b.tone === "danger") && Array.isArray(b.items) && b.items.every(text);
    case "rule": return true;
    case "caption": case "text": return text(b.text);
    case "vaccines": return b.rows === null || (Array.isArray(b.rows) && b.rows.every((r) => record(r) && text(r.vaccine) && text(r.doses) && text(r.date)));
    default: return false;
  }
}

export function nominaValid(v: unknown): v is NominaData {
  if (!record(v) || !record(v.centro)) return false;
  return Number.isSafeInteger(v.id) && text(v.label) && Number.isSafeInteger(v.centro.id) && text(v.centro.nombre) && internal(v.centro.url) &&
    (v.editar_url === null || internal(v.editar_url)) && messagesValid(v.messages) &&
    Array.isArray(v.sections) && v.sections.every((s) => record(s) && text(s.key) && text(s.icon) && text(s.title) &&
      (s.subtitle === null || text(s.subtitle)) && Array.isArray(s.blocks) && s.blocks.every(blockValid));
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="col-md-3 col-sm-6">
      <p className="small mb-1" style={{ color: "#9ca3af" }}>{label}</p>
      <p className="mb-0" style={{ color: "#e5e7eb" }}>{value}</p>
    </div>
  );
}

function BlockView({ block }: { block: Block }) {
  switch (block.kind) {
    case "fields":
      return <div className={`row g-3${block.spaced ? " mb-3" : ""}`}>{block.items.map((i, n) => <Field key={`${n}:${i.label}`} label={i.label} value={i.value} />)}</div>;
    case "badges":
      return (
        <div className={block.spaced ? "mb-3" : undefined}>
          <p className="small mb-2" style={{ color: "#9ca3af" }}>{block.label}</p>
          <div className="d-flex flex-wrap gap-2">
            {block.items.map((item, n) => <span key={`${n}:${item}`} className="badge" style={{ ...TONES[block.tone], fontSize: "0.8rem", padding: "5px 10px" }}>{item}</span>)}
          </div>
        </div>
      );
    case "rule": return <hr style={{ borderColor: "#374151" }} />;
    case "caption": return <p className="small mb-2" style={{ color: "#9ca3af" }}>{block.text}</p>;
    case "text": return <p style={{ color: "#e5e7eb", whiteSpace: "pre-line" }}>{block.text}</p>;
    case "vaccines":
      return block.rows ? (
        <div className="table-responsive">
          <table className="table table-sm table-dark" style={{ fontSize: "0.875rem" }}>
            <thead><tr><th>Vacuna</th><th>Dosis recibidas</th><th>Fecha de última dosis</th></tr></thead>
            <tbody>{block.rows.map((r) => <tr key={r.vaccine}><td>{r.vaccine}</td><td>{r.doses}</td><td>{r.date}</td></tr>)}</tbody>
          </table>
        </div>
      ) : <p style={{ color: "#9ca3af" }} className="mb-0">Sin datos de vacunación cargados.</p>;
  }
}

/** The native script gives each header `role=button`, `tabindex=0` and `aria-expanded`; Enter/Space toggle it. */
function SectionCard({ section }: { section: Section }) {
  const [open, setOpen] = useState(true);
  const toggle = () => setOpen((current) => !current);
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
  };
  return (
    <div className={`section-card${section.key === "observaciones" ? " mb-4" : ""}`} data-section={section.key}>
      <div className={`section-header${open ? "" : " collapsed"}`} data-toggle-section={section.key} tabIndex={0} role="button" aria-expanded={open}
        onClick={toggle} onKeyDown={onKey}>
        <div className="section-header-left">
          <div className="section-icon"><i className={`fas ${section.icon}`} /></div>
          <div className="section-title-group">
            <h3 className="section-title">{section.title}</h3>
            {section.subtitle && <p className="section-subtitle">{section.subtitle}</p>}
          </div>
        </div>
        <div className="section-status"><div className="collapse-indicator"><i className="fas fa-chevron-down" /></div></div>
      </div>
      <div className={`section-body collapse${open ? " show" : ""}`} id={`section-${section.key}`}>
        {section.blocks.map((block, n) => <BlockView key={n} block={block} />)}
      </div>
    </div>
  );
}

export function NominaContent({ data }: { data: NominaData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <div className="d-flex justify-content-between align-items-center mb-3">
        <nav aria-label="breadcrumb">
          <ol className="breadcrumb mb-0">
            <li className="breadcrumb-item"><a href={safeInternalPath(data.centro.url) ?? "/"}>{data.centro.nombre} — Nómina</a></li>
            <li className="breadcrumb-item active">{data.label}</li>
          </ol>
        </nav>
        <div className="d-flex gap-2">
          {data.editar_url && <a href={safeInternalPath(data.editar_url) ?? "/"} className="btn btn-warning btn-sm"><i className="fas fa-edit me-1" />Editar</a>}
        </div>
      </div>
      {data.sections.map((section) => <SectionCard key={section.key} section={section} />)}
    </>
  );
}

function NominaPage({ centro, id }: { centro: string; id: string }) {
  const [state] = useCdiPage(`web/cdi/centros/${centro}/nomina/${id}/`, nominaValid);
  return renderCdi(state, (data) => ({
    title: `Destinatario — ${data.label}`,
    heading: "Detalle de destinatario",
    content: <NominaContent data={data} />,
  }));
}

const OWN = /^\/centrodeinfancia\/([1-9]\d*)\/nomina\/([1-9]\d*)\/ver\/$/;

// Native URL of the CDI beneficiary detail (CDI04.01); same trailing slash.
export const cdiNominaRoute: RouteDefinition<{ centro: string; id: string }> = {
  name: "cdi-nomina",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { centro: own[1], id: own[2] } : null;
  },
  render: ({ centro, id }) => <NominaPage centro={centro} id={id} />,
};
