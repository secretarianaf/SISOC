/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, modal and validator live here with the route. */
import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { safeInternalPath } from "../webAccess";
import { client, internal, messagesValid, navigation, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import { NativeModal } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDI05 worker detail (`centrodeinfancia/trabajador_detail.html`): collapsible
 * section cards of label/value fields and badge lists, the edit link and the
 * delete modal. Every value comes rendered by the backend with the native
 * template expressions; this page only draws the sections. The delete is the
 * existing native soft delete behind `/api/web/cdi/`; the native redirect is
 * followed and a failure is announced, never retried.
 */
type Tone = "warning" | "info" | "danger";
type Block =
  | { kind: "fields"; items: { label: string; value: string }[]; spaced: boolean }
  | { kind: "badges"; label: string; tone: Tone; items: string[]; wrapper: string };
export type Section = { key: string; icon: string; title: string; subtitle: string | null; blocks: Block[] };
export type TrabajadorData = {
  id: number;
  label: string;
  centro: { id: number; nombre: string; url: string };
  editar_url: string | null;
  eliminar_url: string | null;
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
  if (b.kind === "fields") return typeof b.spaced === "boolean" && Array.isArray(b.items) && b.items.every((i) => record(i) && text(i.label) && text(i.value));
  return b.kind === "badges" && text(b.label) && text(b.wrapper) && (b.tone === "warning" || b.tone === "info" || b.tone === "danger") &&
    Array.isArray(b.items) && b.items.every(text);
}

export function trabajadorValid(v: unknown): v is TrabajadorData {
  if (!record(v) || !record(v.centro)) return false;
  return Number.isSafeInteger(v.id) && text(v.label) && Number.isSafeInteger(v.centro.id) && text(v.centro.nombre) && internal(v.centro.url) &&
    (v.editar_url === null || internal(v.editar_url)) && (v.eliminar_url === null || internal(v.eliminar_url)) && messagesValid(v.messages) &&
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
  if (block.kind === "fields") {
    return <div className={`row g-3${block.spaced ? " mb-3" : ""}`}>{block.items.map((i, n) => <Field key={`${n}:${i.label}`} label={i.label} value={i.value} />)}</div>;
  }
  return (
    <div className={block.wrapper || undefined}>
      <p className="small mb-2" style={{ color: "#9ca3af" }}>{block.label}</p>
      <div className="d-flex flex-wrap gap-2">
        {block.items.map((item, n) => <span key={`${n}:${item}`} className="badge" style={{ ...TONES[block.tone], fontSize: "0.8rem", padding: "5px 10px" }}>{item}</span>)}
      </div>
    </div>
  );
}

/** The native script gives each header `role=button`, `tabindex=0` and `aria-expanded`; Enter/Space toggle it. */
function SectionCard({ section, last }: { section: Section; last: boolean }) {
  const [open, setOpen] = useState(true);
  const toggle = () => setOpen((current) => !current);
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
  };
  return (
    <div className={`section-card${last ? " mb-4" : ""}`} data-section={section.key}>
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

const api = (url: string) => url.replace(/^\/api\//, "");

function EliminarModal({ nombre, url, close }: { nombre: string; url: string; close: () => void }) {
  const [busy, setBusy] = useState(false);
  const sending = useRef(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (sending.current) return;
    sending.current = true;
    setBusy(true);
    try {
      const { data, status } = await client.post(api(url), new URLSearchParams(), { validateStatus: () => true });
      if (record(data) && data.ok === true && internal(data.redirect)) { navigation.assign(data.redirect as string); return; }
      window.alert(record(data) && text(data.detail) ? data.detail : `No se pudo completar la acción (${status}).`);
    } catch {
      window.alert("Error de conexión. Intentá nuevamente.");
    }
    sending.current = false;
    setBusy(false);
  }
  return (
    <NativeModal id="modalEliminarTrabajador" title="Confirmar eliminación" close={close} busy={busy} size=" modal-dialog-centered">
      <div className="modal-content">
        <form method="post" onSubmit={submit}>
          <div className="modal-header">
            <h5 className="modal-title" id="modalEliminarTrabajadorLabel">Confirmar eliminación</h5>
            <button type="button" className="btn-close btn-close-white" aria-label="Cerrar" onClick={close} />
          </div>
          <div className="modal-body">
            <p className="mb-0">¿Está seguro de eliminar a <strong>{nombre}</strong>?</p>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className="btn btn-danger" disabled={busy}>Eliminar</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

export function TrabajadorContent({ data }: { data: TrabajadorData }) {
  const [modal, setModal] = useState(false);
  const close = () => setModal(false);
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <div className="d-flex justify-content-between align-items-center mb-3">
        <nav aria-label="breadcrumb">
          <ol className="breadcrumb mb-0">
            <li className="breadcrumb-item"><a href={safeInternalPath(data.centro.url) ?? "/"}>{data.centro.nombre}</a></li>
            <li className="breadcrumb-item active">{data.label}</li>
          </ol>
        </nav>
        <div className="d-flex gap-2">
          {data.editar_url && <a href={safeInternalPath(data.editar_url) ?? "/"} className="btn btn-warning btn-sm"><i className="fas fa-edit me-1" />Editar</a>}
          {data.eliminar_url && <button type="button" className="btn btn-danger btn-sm" onClick={() => setModal(true)}><i className="fas fa-trash me-1" />Eliminar</button>}
        </div>
      </div>
      {modal && data.eliminar_url && <EliminarModal nombre={data.label} url={data.eliminar_url} close={close} />}
      {data.sections.map((section, n) => <SectionCard key={section.key} section={section} last={n === data.sections.length - 1} />)}
    </>
  );
}

function TrabajadorPage({ centro, id }: { centro: string; id: string }) {
  const [state] = useCdiPage(`web/cdi/centros/${centro}/trabajadores/${id}/`, trabajadorValid);
  return renderCdi(state, (data) => ({
    title: `Trabajador — ${data.label}`,
    heading: "Detalle de trabajador",
    content: <TrabajadorContent data={data} />,
  }));
}

const OWN = /^\/centrodeinfancia\/([1-9]\d*)\/trabajadores\/([1-9]\d*)\/$/;

// Native URL of the CDI worker detail (CDI05); same trailing slash.
export const cdiTrabajadorRoute: RouteDefinition<{ centro: string; id: string }> = {
  name: "cdi-trabajador",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { centro: own[1], id: own[2] } : null;
  },
  render: ({ centro, id }) => <TrabajadorPage centro={centro} id={id} />,
};
