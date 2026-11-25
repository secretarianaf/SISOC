/* eslint-disable react-refresh/only-export-components -- frame module: PAS shared markup and validators travel together. */
import type { ReactNode } from "react";
import { internal, record, text } from "./MainFrame";

/**
 * Shared pieces of the PAS back-office templates that extend `includes/main.html`
 * with `pas.css`: the module header and `pas/includes/workflow_nav.html`. The
 * `app-header` block (`pas-top-actions`) goes to the shell through `appHeader`.
 * Data comes from `/api/web/pas/`.
 */
export const PAS_API = "web/pas/";
export const PAS_STYLESHEET = <link rel="stylesheet" href="/static/custom/css/pas.css" />;
export const BUSCADOR_URL = "/pas/listar";
export const EYEBROW = "Programa de Acompañamiento Social";

/**
 * Resolves once every stylesheet link of the page is applied. The native page
 * loads `pas.css` in `<head>`; here it is a body link, so layout-dependent work
 * (scroll observers, fragment scroll) waits for it like the native scripts do.
 */
export function stylesheetsReady(): Promise<void> {
  const pending = [...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')].filter((l) => !l.sheet);
  return Promise.all(pending.map((l) => new Promise<void>((done) => {
    l.addEventListener("load", () => done(), { once: true });
    l.addEventListener("error", () => done(), { once: true });
  }))).then(() => undefined);
}

/** Django's `urlencode` filter: `quote(value, safe="/")`. */
export function urlencode(value: string) {
  return encodeURIComponent(value)
    .replace(/[!'()*]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`)
    .replace(/%2F/g, "/");
}

export const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
export const bool = (v: unknown): v is boolean => typeof v === "boolean";
export const nullable = <T,>(check: (v: unknown) => v is T) => (v: unknown): v is T | null => v === null || check(v);
export const list = <T,>(check: (v: unknown) => v is T) => (v: unknown): v is T[] => Array.isArray(v) && v.every(check);
export const shape = (v: unknown, fields: Record<string, (x: unknown) => boolean>): boolean =>
  record(v) && Object.entries(fields).every(([k, check]) => check(v[k]));

export type WorkflowCard = { key: string; number: string; title: string; subtitle: string; url: string; active: boolean; source_status: string };
export const workflowValid = list((v: unknown): v is WorkflowCard =>
  shape(v, { key: text, number: text, title: text, subtitle: text, url: internal, active: bool, source_status: text }));

export function BuscadorButton() {
  return <a href={BUSCADOR_URL} className="btn btn-light">
    <i className="bi bi-arrow-left" aria-hidden="true" />{" "}Buscador PAS
  </a>;
}

export function SourceChip({ pending = true, icon = "bi-cloud-slash", children }: { pending?: boolean; icon?: string; children: ReactNode }) {
  return <span className={`pas-source-chip${pending ? " is-pending" : ""}`}>
    <i className={`bi ${icon}`} aria-hidden="true" />{" "}{children}
  </span>;
}

export function ModuleHeader({ title, subtitle, aside }: { title: string; subtitle?: string; aside?: ReactNode }) {
  return <header className="pas-module-header">
    <div>
      <span className="pas-eyebrow">{EYEBROW}</span>
      <h1>{title}</h1>
      {subtitle !== undefined && <p>{subtitle}</p>}
    </div>
    {aside}
  </header>;
}

export function WorkflowNav({ cards }: { cards: WorkflowCard[] }) {
  return <nav className="pas-workflow" aria-label="Circuito PAS">
    {cards.map((item) => <a key={item.key} className={`pas-workflow-card ${item.active ? "is-active" : ""}`} href={item.url}>
      <span className="pas-workflow-number">{item.number}</span>
      <strong>{item.title}</strong>
      <span>{item.subtitle}</span>
      {item.source_status === "pendiente" && <i className="bi bi-cloud-slash pas-workflow-source" title="Integración pendiente" aria-label="Integración pendiente" />}
    </a>)}
  </nav>;
}

export function EmptyState({ icon, title, detail, large = false, className = "" }: { icon?: string; title: string; detail?: string; large?: boolean; className?: string }) {
  return <div className={`pas-empty-state${large ? " pas-empty-state-large" : ""}${className ? ` ${className}` : ""}`}>
    {icon && <i className={`bi ${icon}`} aria-hidden="true" />}
    <strong>{title}</strong>
    {detail && <span>{detail}</span>}
  </div>;
}

/** Source rows of the courses tables; the source has none yet, the markup is kept. */
export type Formacion = { curso: string; fuente: string; inicio: string; fin: string; progreso: string; puntos: string; estado: string; estado_codigo: string; certificado_url: string };
export const formacionValid = (v: unknown): v is Formacion =>
  shape(v, Object.fromEntries(["curso", "fuente", "inicio", "fin", "progreso", "puntos", "estado", "estado_codigo", "certificado_url"].map((k) => [k, text])));
