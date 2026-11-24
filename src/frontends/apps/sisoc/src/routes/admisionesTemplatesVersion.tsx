/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens, validators and the asset/navigation seams live here with the route. */
import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { InsumosToastList } from "../InsumosToast";
import { Csrf, Crumbs, Frame, Hero, HEADING, ROOT, API, BASE, int, messagesValid, navValid, texts, type Message, type Nav } from "./admisionesTemplates";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * AD01.02 version editor (`.../<plantilla>/versiones/<version>/editar/`, `version_form.html`).
 * `/api/web/comedores/admisiones/plantillas-informe/<pk>/versiones/<version_pk>/` runs the native
 * `PlantillaInformeTecnicoVersionUpdateView`. The rich editor is the native one: this route
 * renders the same DOM contract and loads jQuery 3.6.0, jQuery UI 1.12.1, Summernote 0.8.18 and the native
 * `gestor_templates_editor.js` (plan section 9.1), whose `submit` listener syncs the textarea
 * before this form posts it. The backend is the only HTML sanitiser. A POST is never retried.
 */
type Params = { id: string; version: string };
type Field = { label: string; value: string; errors: string[]; placeholder: string };
type Variable = { categoria: string; nombre: string; codigo: string; token: string };
type VersionData = {
  version: { id: number; numero: number }; plantilla: { id: number; codigo: string; nombre: string };
  contenido_html: Field; observaciones: Field; non_field_errors: string[]; variables: Variable[];
  urls: Nav & { detalle: string; previsualizar: string }; messages: Message[];
};
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const JQUERY = "https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js";
const JQUERY_UI = "https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js";
const SUMMERNOTE_JS = "https://cdnjs.cloudflare.com/ajax/libs/summernote/0.8.18/summernote-bs4.min.js";
const SUMMERNOTE_CSS = "https://cdnjs.cloudflare.com/ajax/libs/summernote/0.8.18/summernote-bs4.min.css";
const EDITOR_JS = "/static/custom/js/gestor_templates_editor.js?v=20260731-toolbar3";

const fieldValid = (f: unknown): f is Field => texts(f, ["label", "value", "placeholder"]) && record(f) && Array.isArray(f.errors) && f.errors.every(text);
const variableValid = (v: unknown): v is Variable => texts(v, ["categoria", "nombre", "codigo", "token"]);
export const versionValid = (v: unknown): v is VersionData => record(v) && record(v.version) && int(v.version.id) && int(v.version.numero) &&
  record(v.plantilla) && int(v.plantilla.id) && texts(v.plantilla, ["codigo", "nombre"]) && fieldValid(v.contenido_html) && fieldValid(v.observaciones) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && Array.isArray(v.variables) && v.variables.every(variableValid) &&
  navValid(v.urls, ["detalle", "previsualizar"]) && internal((v.urls as Record<string, unknown>).previsualizar) && messagesValid(v.messages);

/** Replaceable in tests: loads the editor scripts in the native order (jQuery and Summernote once per page). */
function script(src: string, force = false) {
  return new Promise<void>((resolve) => {
    if (!force && document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
    const element = document.createElement("script");
    element.src = src; element.async = false;
    element.onload = () => resolve(); element.onerror = () => resolve();
    document.body.appendChild(element);
  });
}
export const editorAssets = {
  load: async () => {
    const win = window as unknown as { jQuery?: { fn?: { summernote?: unknown } } };
    if (!win.jQuery) await script(JQUERY);
    // The native layout loads jQuery UI before Summernote; its buttons call the jQuery UI `tooltip`.
    if (!(win.jQuery?.fn as { tooltip?: unknown } | undefined)?.tooltip) await script(JQUERY_UI);
    if (!win.jQuery?.fn?.summernote) await script(SUMMERNOTE_JS);
    await script(EDITOR_JS, true);
  },
};
/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const versionFormNavigation = { assign: (to: string) => window.location.assign(to) };

function Panel({ cls, icon, title, open, children }: { cls: string; icon: string; title: string; open?: boolean; children: ReactNode }) {
  return <details className={`gt-editor-panel gt-editor-panel--${cls}`} open={open}>
    <summary>
      <span className="gt-editor-panel__title"><i className={`fas ${icon}`} /> {title}</span>
      <span className="gt-editor-panel__status">
        <span className="gt-editor-panel__closed">Expandir</span>
        <span className="gt-editor-panel__open">Ocultar</span>
        <i className="fas fa-chevron-down" />
      </span>
    </summary>
    <div className="gt-editor-panel__body">{children}</div>
  </details>;
}

function VersionPage({ data: first, endpoint }: { data: VersionData; endpoint: string }) {
  const [data, setData] = useState(first);
  const [revision, setRevision] = useState(0);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  useEffect(() => { void editorAssets.load(); }, [revision]);
  const groups: { categoria: string; items: Variable[] }[] = [];
  for (const v of data.variables) {
    const last = groups[groups.length - 1];
    if (last && last.categoria === v.categoria) last.items.push(v); else groups.push({ categoria: v.categoria, items: [v] });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const form = new FormData(event.currentTarget);
    const body = new URLSearchParams();
    body.append("contenido_html", String(form.get("contenido_html") ?? ""));
    body.append("observaciones", String(form.get("observaciones") ?? ""));
    const outcome = await postForm(endpoint, body);
    if (outcome.kind === "redirect") { versionFormNavigation.assign(outcome.url); return; }
    if (outcome.kind === "invalid" && versionValid(outcome.data)) {
      setData(outcome.data); setRevision((r) => r + 1);
      resetAfterRejectedPost();
    } else setUncertain(true);
    busy.current = false; setPending(false);
  }

  const { plantilla, version } = data;
  return <Frame section="templates" urls={data.urls}>
    <link rel="stylesheet" href={SUMMERNOTE_CSS} />
    <InsumosToastList messages={data.messages} />
    <Hero eyebrow={`${plantilla.codigo} · Versión ${version.numero}`} title="Editar contenido del template">
      {plantilla.nombre}. Guardá los cambios como borrador y publicá la versión cuando esté lista.
    </Hero>
    <form method="post" className="gt-form" key={revision} onSubmit={(e) => void submit(e)}>
      <Csrf />
      <Panel cls="variables" icon="fa-code" title="Variables disponibles">
        <div className="gt-variable-drawer__toolbar">
          <div><p className="mb-0">Hacé clic o arrastrá una variable para insertarla en la posición actual del cursor.</p></div>
          <div className="gt-variable-drawer__controls">
            <input id="buscar-variable-template" type="search" className="form-control form-control-sm" placeholder="Buscar una variable" />
            <a className="btn btn-sm btn-outline-primary" href={data.urls.variables} target="_blank" rel="noopener">Administrar catálogo</a>
          </div>
        </div>
        <div id="catalogo-variables-template" className="gt-variable-catalog">
          {groups.length === 0 ? <p className="text-muted mb-0">No hay variables activas en el catálogo.</p> : groups.map((g) => (
            <section key={g.categoria} className="gt-variable-category" data-categoria-variable>
              <header className="gt-variable-category__header"><h3 className="gt-category-title">{g.categoria}</h3><span className="gt-variable-category__count">{g.items.length}</span></header>
              <div className="gt-variable-category__items">
                {g.items.map((v) => (
                  <Fragment key={v.codigo}>
                    <button type="button" className="gt-variable variable-template" draggable data-template-variable={v.token}
                      data-variable-search={`${v.nombre.toLowerCase()} ${v.codigo.toLowerCase()} ${v.categoria.toLowerCase()}`} title={`Hacé clic o arrastrá para insertar ${v.token}`}>
                      <span>{v.nombre}</span><code>{v.token}</code>
                    </button>
                  </Fragment>
                ))}
              </div>
            </section>
          ))}
        </div>
      </Panel>
      <Panel cls="content" icon="fa-pen" title="Contenido del template" open>
        {data.non_field_errors.length > 0 && <div className="alert alert-danger"><ul className="errorlist nonfield">{data.non_field_errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
        <div className="gt-editor form-group mb-0">
          <label htmlFor="id_contenido_html">{data.contenido_html.label}</label>
          <textarea name="contenido_html" cols={40} rows={22} className="form-control font-monospace" data-template-editor-source="true" placeholder={data.contenido_html.placeholder}
            id="id_contenido_html" defaultValue={data.contenido_html.value} />
          {data.contenido_html.errors.map((e, i) => <div key={i} className="invalid-feedback">{e}</div>)}
        </div>
      </Panel>
      <Panel cls="observaciones" icon="fa-comment-alt" title="Observaciones de la versión">
        <div className="form-group mb-0">
          <label htmlFor="id_observaciones">{data.observaciones.label}</label>
          <textarea name="observaciones" cols={40} rows={3} className="form-control" id="id_observaciones" defaultValue={data.observaciones.value} />
        </div>
      </Panel>
      {uncertain && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
      <div className="gt-actions gt-editor-actions">
        <a href={data.urls.detalle} className="btn btn-outline-secondary">Cancelar</a>
        <button type="submit" className="btn btn-primary" disabled={pending || uncertain || undefined}>Guardar borrador</button>
      </div>
    </form>
    <Panel cls="preview" icon="fa-eye" title="Vista previa">
      <p>Probá esta versión con un Informe Técnico real. El DOCX se descarga con la marca de agua <em>VISTA PREVIA — DOCUMENTO NO VÁLIDO</em> y no se guarda en la admisión.</p>
      <form method="get" action={data.urls.previsualizar} target="_blank" className="row g-2 align-items-end gt-form">
        <div className="col-md-6 form-group mb-0">
          <label htmlFor="id_informe_id" className="form-label">ID del Informe Técnico</label>
          <input id="id_informe_id" name="informe_id" type="number" min="1" required className="form-control" />
        </div>
        <div className="col-md-auto"><button type="submit" className="btn btn-outline-primary">Descargar vista previa</button></div>
      </form>
    </Panel>
  </Frame>;
}

function VersionRoute({ id, version }: Params) {
  const endpoint = `${API}${id}/versiones/${version}/`;
  const [state] = useMainResource(endpoint, versionValid);
  return renderMain(state, "Cargando versión…", (data) => ({
    title: "Editar versión · Gestor de templates", heading: HEADING,
    breadcrumb: <Crumbs items={[ROOT, [data.plantilla.codigo, data.urls.detalle], [`Editar v${data.version.numero}`, null]]} />,
    content: <VersionPage data={data} endpoint={endpoint} />,
  }));
}

export const admisionesTemplatesVersionRoute: RouteDefinition<Params> = {
  name: "comedores-gestor-templates-version",
  match(pathname) {
    const m = pathname.match(new RegExp(`^${BASE}([0-9]+)/versiones/([0-9]+)/editar/$`));
    return m ? { id: m[1], version: m[2] } : null;
  },
  render: ({ id, version }) => <VersionRoute key={`${id}-${version}`} id={id} version={version} />,
};
